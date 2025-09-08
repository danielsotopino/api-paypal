from typing import Optional, Dict, Any, List
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
import structlog
import uuid
from paypal_api.config import settings
from paypal_api.core.exceptions import PayPalCommunicationException

# Importaciones del SDK de PayPal
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from paypalserversdk.configuration import Environment

logger = structlog.get_logger(__name__)


class PaypalOrdersService:
    def __init__(self):
        """
        Inicializa el servicio de Orders con el SDK oficial de PayPal
        """
        try:
            # Determinar el ambiente
            environment = Environment.SANDBOX if settings.PAYPAL_MODE == "sandbox" else Environment.PRODUCTION
            
            # Inicializar el cliente de PayPal
            self.client = PaypalServersdkClient(
                environment=environment,
                client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                    o_auth_client_id=settings.PAYPAL_CLIENT_ID, 
                    o_auth_client_secret=settings.PAYPAL_CLIENT_SECRET
                )
            )
            
            # Obtener el controlador de Orders
            self.orders_controller = self.client.orders
            
            logger.info("PaypalOrdersService inicializado correctamente", 
                       mode=settings.PAYPAL_MODE, 
                       environment=environment.value)
                       
        except Exception as e:
            logger.error(f"Error inicializando PaypalOrdersService: {str(e)}", exc_info=True)
            raise PayPalCommunicationException(f"Error inicializando PaypalOrdersService: {str(e)}")
    
    def create_order(
        self,
        intent: str = "CAPTURE",
        purchase_units: List[Dict[str, Any]] = None,
        payment_source: Optional[Dict[str, Any]] = None,
        application_context: Optional[Dict[str, Any]] = None,
        paypal_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crear una nueva orden usando el SDK de PayPal
        
        Args:
            intent: Intención de la orden (CAPTURE, AUTHORIZE)
            purchase_units: Lista de unidades de compra
            payment_source: Fuente de pago (incluyendo vault_id para tokens guardados)
            application_context: Contexto de la aplicación (URLs de retorno, etc.)
            paypal_request_id: ID de request de PayPal para idempotencia
            
        Returns:
            Dict con la respuesta de PayPal
        """
        try:
            # Generar ID de request si no se proporciona
            if not paypal_request_id:
                paypal_request_id = f"order-{uuid.uuid4()}"
            
            # Preparar el cuerpo de la petición
            request = {
                "body": {
                    "intent": intent,
                    "purchase_units": purchase_units if purchase_units is not None else [],
                    "payment_source": payment_source if payment_source is not None else None,
                    "application_context": application_context if application_context is not None else None,
                },
                "prefer": "return=minimal",
                "paypal_request_id": paypal_request_id,
            }
            # Clean up None values in body
            request["body"] = {k: v for k, v in request["body"].items() if v is not None}


            # Crear la orden usando el SDK
            response = self.orders_controller.create_order(request)
            
            if response.is_success():
                order_response = response.body
                logger.info("Orden creada exitosamente", 
                           order_id=order_response.get("id"),
                           status=order_response.get("status"))
                return order_response
            else:
                error_details = response.body if hasattr(response, 'body') else str(response)
                logger.error("Error creando orden", 
                           status_code=response.status_code,
                           error=error_details)
                raise PayPalCommunicationException(f"Error creando orden: {error_details}")
                
        except Exception as e:
            logger.error("Error en create_order", error=str(e), exc_info=True)
            raise PayPalCommunicationException(f"Error creando orden: {str(e)}")
    
    def create_order_with_vault_token(
        self,
        vault_id: str,
        amount: str,
        currency_code: str = "USD",
        intent: str = "CAPTURE",
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        paypal_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crear una orden usando un token guardado en el vault
        
        Args:
            vault_id: ID del payment token guardado en el vault
            amount: Monto de la orden
            currency_code: Código de moneda
            intent: Intención de la orden
            description: Descripción de la orden
            reference_id: ID de referencia del comerciante
            return_url: URL de retorno exitoso
            cancel_url: URL de retorno cancelado
            paypal_request_id: ID de request de PayPal
            
        Returns:
            Dict con la respuesta de PayPal
        """
        try:
            # Preparar purchase units
            purchase_units = [{
                "amount": {
                    "currency_code": currency_code,
                    "value": amount
                }
            }]
            
            # Agregar descripción y referencia si se proporcionan
            if description or reference_id:
                purchase_units[0].update({
                    "description": description,
                    "reference_id": reference_id
                })
            
            # Preparar payment source con vault token
            payment_source = {
                "paypal": {
                    "vault_id": vault_id,
                    "stored_credential": {
                        "payment_initiator": "MERCHANT",
                        "usage": "SUBSEQUENT",
                        "usage_pattern": "SUBSCRIPTION_PREPAID"
                    }
                }
            }
            
            # Preparar application context si se proporcionan URLs
            application_context = None
            if return_url or cancel_url:
                application_context = {}
                if return_url:
                    application_context["return_url"] = return_url
                if cancel_url:
                    application_context["cancel_url"] = cancel_url
            
            logger.info("Creando orden con vault token", 
                       vault_id=vault_id,
                       amount=amount,
                       currency_code=currency_code,
                       intent=intent)
            
            # Crear la orden
            return self.create_order(
                intent=intent,
                purchase_units=purchase_units,
                payment_source=payment_source,
                application_context=application_context,
                paypal_request_id=paypal_request_id
            )
            
        except Exception as e:
            logger.error("Error en create_order_with_vault_token", 
                        vault_id=vault_id,
                        error=str(e), 
                        exc_info=True)
            raise PayPalCommunicationException(f"Error creando orden con vault token: {str(e)}")
    
    def create_order_with_items(
        self,
        items: List[Dict[str, Any]],
        total_amount: str,
        currency_code: str = "USD",
        intent: str = "CAPTURE",
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        paypal_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crear una orden con items detallados
        
        Args:
            items: Lista de items con name, quantity, unit_amount, etc.
            total_amount: Monto total de la orden
            currency_code: Código de moneda
            intent: Intención de la orden
            description: Descripción de la orden
            reference_id: ID de referencia del comerciante
            return_url: URL de retorno exitoso
            cancel_url: URL de retorno cancelado
            paypal_request_id: ID de request de PayPal
            
        Returns:
            Dict con la respuesta de PayPal
        """
        try:
            # Preparar purchase units con items
            purchase_units = [{
                "amount": {
                    "currency_code": currency_code,
                    "value": total_amount,
                    "breakdown": {
                        "item_total": {
                            "currency_code": currency_code,
                            "value": total_amount
                        }
                    }
                },
                "items": items
            }]
            
            # Agregar descripción y referencia si se proporcionan
            if description or reference_id:
                purchase_units[0].update({
                    "description": description,
                    "reference_id": reference_id
                })
            
            # Preparar application context si se proporcionan URLs
            application_context = None
            if return_url or cancel_url:
                application_context = {}
                if return_url:
                    application_context["return_url"] = return_url
                if cancel_url:
                    application_context["cancel_url"] = cancel_url
            
            logger.info("Creando orden con items", 
                       items_count=len(items),
                       total_amount=total_amount,
                       currency_code=currency_code,
                       intent=intent)
            
            # Crear la orden
            return self.create_order(
                intent=intent,
                purchase_units=purchase_units,
                application_context=application_context,
                paypal_request_id=paypal_request_id
            )
            
        except Exception as e:
            logger.error("Error en create_order_with_items", 
                        items_count=len(items),
                        error=str(e), 
                        exc_info=True)
            raise PayPalCommunicationException(f"Error creando orden con items: {str(e)}")
