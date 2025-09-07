from typing import Optional, Dict, Any, List
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
import structlog
import uuid
from paypal_api.config import settings
from paypal_api.core.exceptions import PayPalCommunicationException

# Importaciones del SDK de PayPal
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient
from paypalserversdk.configuration import Environment

from paypal_api.schemas.paypal_schemas import PaymentTokenResponse

logger = structlog.get_logger(__name__)


class PaypalVaultService:
    def __init__(self):
        """
        Inicializa el servicio de Vault con el SDK oficial de PayPal
        """
        try:
            # Determinar el ambiente
            environment = Environment.SANDBOX if settings.PAYPAL_MODE == "sandbox" else Environment.PRODUCTION
            
            # Inicializar el cliente de PayPal (sin credenciales explícitas por ahora)
            self.client = PaypalServersdkClient(environment=environment,
            client_credentials_auth_credentials=ClientCredentialsAuthCredentials(o_auth_client_id=settings.PAYPAL_CLIENT_ID, o_auth_client_secret=settings.PAYPAL_CLIENT_SECRET))
            
            # Obtener el controlador de Vault
            self.vault_controller = self.client.vault
            
            logger.info("VaultService inicializado correctamente", 
                       mode=settings.PAYPAL_MODE, 
                       environment=environment.value)
                       
        except Exception as e:
            logger.error(f"Error inicializando VaultService: {str(e)}", exc_info=True)
            raise PayPalCommunicationException(f"Error inicializando VaultService: {str(e)}")
    
    def create_setup_token(
        self,
        customer_id: Optional[str] = None,
        merchant_customer_id: Optional[str] = None,
        paypal_request_id: Optional[str] = None,
        usage_type: Optional[str] = None,
        usage_pattern: Optional[str] = None,
        billing_plan: Optional[Dict[str, Any]] = None,
        experience_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crea un Setup Token para guardar un método de pago temporalmente
        Genera el objeto exacto requerido por PayPal Vault API
        """
        try:
            # Generar UUID para paypalRequestId si no se proporciona
            if not paypal_request_id:
                paypal_request_id = str(uuid.uuid4())
            
            # Construir el objeto collect exacto como se requiere
            # TODO: ver que debe ir a nivel de controller
            collect = {
                "paypal_request_id": paypal_request_id,
                "body": {
                    "payment_source": {
                        "paypal": {
                            "usage_type": usage_type or "MERCHANT",
                            "usage_pattern": usage_pattern or "SUBSCRIPTION_PREPAID",
                            "billing_plan": billing_plan or {
                                "billing_cycles": [
                                    {
                                        "tenure_type": "REGULAR",
                                        "pricing_scheme": {
                                            "pricing_model": "FIXED",
                                            "price": {
                                                "value": "100",
                                                "currency_code": "USD",
                                            },
                                        },
                                        "frequency": {
                                            "interval_unit": "MONTH",
                                            "interval_count": "1",
                                        },
                                        "total_cycles": "1",
                                        "start_date": "2025-09-06",
                                    },
                                ],
                                "one_time_charges": {
                                    "product_price": {
                                        "value": "10",
                                        "currency_code": "USD",
                                    },
                                    "total_amount": {
                                        "value": 10,
                                        "currency_code": "USD",
                                    },
                                },
                                "product": {
                                    "description": "Yearly Membership",
                                    "quantity": "1",
                                },
                                "name": "Company",
                            },
                            "experience_context": experience_context or {
                                "return_url": "https://example.com/returnUrl",
                                "cancel_url": "https://example.com/cancelUrl",
                            },
                        },
                    },
                },
            }
            
            # Agregar información del cliente si se proporciona
            if customer_id or merchant_customer_id:
                customer_data = {}
                if customer_id:
                    customer_data["id"] = customer_id
                if merchant_customer_id:
                    customer_data["merchant_customer_id"] = merchant_customer_id
                collect["body"]["customer"] = customer_data
            
            # Llamar a la API usando el controlador con el objeto collect
            result = self.vault_controller.create_setup_token(collect)
            
            if result.is_success():
                logger.info(f"Setup token creado exitosamente: {result.body.id}")
                return self._convert_api_response_to_dict(result.body)
            else:
                logger.error(f"Error creando setup token: {result.errors}")
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en create_setup_token: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def get_setup_token(self, setup_token_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un Setup Token
        """
        try:
            result = self.vault_controller.get_setup_token(setup_token_id)
            
            if result.is_success():
                logger.info(f"Setup token obtenido exitosamente: {setup_token_id}")
                return self._convert_api_response_to_dict(result.body)
            else:
                logger.error(f"Error obteniendo setup token {setup_token_id}: {result.errors}")
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en get_setup_token: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def create_payment_token(
        self,
        payment_token_response: PaymentTokenResponse
    ) -> Dict[str, Any]:
        """
        Crea un Payment Token permanente en el Vault
        """
        try:

            # Objeto como diccionario
            payment_token_request = {
                "paypalRequestId": str(uuid.uuid4()),
                "body": {
                    "payment_source": {
                        "token": {
                            "id": payment_token_response.vaultSetupToken,
                            "type": "SETUP_TOKEN"
                        }
                    },
                    "customer": {
                        "id": payment_token_response.payerID
                    }
                }
            }
            
            result = self.vault_controller.create_payment_token(payment_token_request)
            
            if result.is_success():
                logger.info(f"Payment token creado exitosamente: {result.body}")
                return self._convert_api_response_to_dict(result.body)
            else:
                logger.error(f"Error creando payment token: {result.errors}", exc_info=True)
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en create_payment_token: {str(e)}", exc_info=True)
            raise PayPalCommunicationException(str(e))
    
    def get_payment_token(self, payment_token_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un Payment Token
        """
        try:
            result = self.vault_controller.get_payment_token(payment_token_id)
            
            if result.is_success():
                logger.info(f"Payment token obtenido exitosamente: {payment_token_id}")
                return self._convert_api_response_to_dict(result.body)
            else:
                logger.error(f"Error obteniendo payment token {payment_token_id}: {result.errors}")
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en get_payment_token: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def delete_payment_token(self, payment_token_id: str) -> bool:
        """
        Elimina un Payment Token del Vault
        """
        try:
            result = self.vault_controller.delete_payment_token(payment_token_id)
            
            if result.is_success():
                logger.info(f"Payment token eliminado exitosamente: {payment_token_id}")
                return True
            else:
                logger.error(f"Error eliminando payment token {payment_token_id}: {result.errors}")
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en delete_payment_token: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def list_customer_payment_tokens(
        self,
        customer_id: str,
        page_size: int = 5,
        page: int = 1,
        total_required: bool = False
    ) -> Dict[str, Any]:
        """
        Lista todos los Payment Tokens de un cliente
        """
        try:
            options = {
                'customer_id': customer_id,
                'page_size': page_size,
                'page': page,
                'total_required': total_required
            }
            
            result = self.vault_controller.list_customer_payment_tokens(options)
            
            if result.is_success():
                logger.info(f"Payment tokens listados exitosamente para cliente: {customer_id}")
                return self._convert_api_response_to_dict(result.body)
            else:
                logger.error(f"Error listando payment tokens para cliente {customer_id}: {result.errors}")
                raise PayPalCommunicationException(str(result.errors))
                
        except Exception as e:
            logger.error(f"Error en list_customer_payment_tokens: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def _convert_api_response_to_dict(self, api_response) -> Dict[str, Any]:
        """
        Convierte la respuesta de la API a un diccionario serializable
        """
        try:
            # Intentar usar el método to_dict si existe
            if hasattr(api_response, 'to_dict'):
                return api_response.to_dict()
            
            # Si no, usar __dict__ y filtrar atributos privados
            result = {}
            for key, value in api_response.__dict__.items():
                if not key.startswith('_'):
                    if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool)):
                        # Recursivamente convertir objetos anidados
                        result[key] = self._convert_api_response_to_dict(value)
                    elif isinstance(value, list):
                        # Manejar listas de objetos
                        result[key] = [
                            self._convert_api_response_to_dict(item) if hasattr(item, '__dict__') and not isinstance(item, (str, int, float, bool)) else item
                            for item in value
                        ]
                    else:
                        result[key] = value
            
            return result
            
        except Exception as e:
            logger.warning(f"Error convirtiendo respuesta API a dict: {str(e)}")
            # Fallback: retornar el objeto como string
            return {"raw_response": str(api_response)}