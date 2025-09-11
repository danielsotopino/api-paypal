from typing import Optional, Dict, Any, List
from paypalserversdk.http.api_response import ApiResponse
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
import structlog
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from paypal_api.config import settings
from paypal_api.core.exceptions import PayPalCommunicationException
from paypal_api.schemas.paypal_schemas import (
    OrderCreateResponse, 
    OrderStatus, 
    CaptureResponse,
    CaptureStatus,
    MoneyResponse,
    LinkResponse,
    SellerProtectionResponse,
    SellerReceivableBreakdownResponse
)
from paypal_api.repositories.order_repository import OrderRepository

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
    
    def _process_order_response(self, paypal_response: Any) -> OrderCreateResponse:
        """
        Procesa la respuesta de PayPal y la convierte a nuestro esquema
        
        Args:
            paypal_response: Respuesta del SDK de PayPal
            
        Returns:
            OrderCreateResponse: Respuesta procesada
        """
        try:
            # Extraer información básica
            order_id = paypal_response.id
            status = OrderStatus(paypal_response.status)
            
            # Extraer información del pagador
            payer_email = None
            payer_id = None
            if paypal_response.payer:
                payer_email = paypal_response.payer.email_address
                payer_id = paypal_response.payer.payer_id
            
            # Extraer información de la fuente de pago
            payment_source = None
            if paypal_response.payment_source:
                if paypal_response.payment_source.paypal:
                    payment_source = "paypal"
                elif paypal_response.payment_source.card:
                    payment_source = "card"
                else:
                    payment_source = "unknown"
            
            # Extraer información de monto (del primer purchase unit)
            total_amount = None
            currency_code = None
            # if paypal_response.purchase_units and len(paypal_response.purchase_units) > 0:
            #     first_unit = paypal_response.purchase_units[0]
            #     print(first_unit)
            #     if first_unit:
            #         total_amount = first_unit.value
            #         currency_code = first_unit.currency_code
            
            # Extraer capturas
            captures = []
            if paypal_response.purchase_units:
                for unit in paypal_response.purchase_units:
                    if unit.payments and unit.payments.captures:
                        for capture in unit.payments.captures:
                            # Procesar seller_protection
                            seller_protection = None
                            if capture.seller_protection:
                                seller_protection = SellerProtectionResponse(
                                    status=capture.seller_protection.status,
                                    dispute_categories=capture.seller_protection.dispute_categories or []
                                )
                            
                            # Procesar seller_receivable_breakdown
                            seller_breakdown = None
                            if capture.seller_receivable_breakdown:
                                breakdown = capture.seller_receivable_breakdown
                                print(breakdown)
                                seller_breakdown = SellerReceivableBreakdownResponse(
                                    gross_amount=MoneyResponse(
                                        currency_code=breakdown.gross_amount.currency_code,
                                        value=breakdown.gross_amount.value
                                    ),
                                    paypal_fee=MoneyResponse(
                                        currency_code=breakdown.paypal_fee.currency_code,
                                        value=breakdown.paypal_fee.value
                                    ),
                                    net_amount=MoneyResponse(
                                        currency_code=breakdown.net_amount.currency_code,
                                        value=breakdown.net_amount.value
                                    ),
                                    # paypal_fee_in_receivable_currency=(
                                    #     MoneyResponse(
                                    #         currency_code=breakdown.paypal_fee_in_receivable_currency.currency_code,
                                    #         value=breakdown.paypal_fee_in_receivable_currency.value
                                    #     ) if breakdown.paypal_fee_in_receivable_currency else None
                                    # ) if breakdown.paypal_fee_in_receivable_currency else None,
                                    # receivable_amount=(
                                    #     MoneyResponse(
                                    #         currency_code=breakdown.receivable_amount.currency_code,
                                    #         value=breakdown.receivable_amount.value
                                    #     ) if breakdown.receivable_amount else None
                                    # ) if breakdown.receivable_amount else None,
                                    # exchange_rate=breakdown.exchange_rate,
                                    # platform_fees=breakdown.platform_fees
                                )
                            
                            # Procesar links
                            links = []
                            if capture.links:
                                for link in capture.links:
                                    links.append(LinkResponse(
                                        href=link.href,
                                        rel=link.rel,
                                        method=link.method
                                    ))
                            print(capture)
                            capture_response = CaptureResponse(
                                status=CaptureStatus(capture.status),
                                status_details=capture.status_details if hasattr(capture, 'status_details') else None,
                                id=capture.id,
                                amount=MoneyResponse(
                                    currency_code=capture.amount.currency_code,
                                    value=capture.amount.value
                                ),
                                invoice_id=capture.invoice_id if hasattr(capture, 'invoice_id') else None,
                                custom_id=capture.custom_id if hasattr(capture, 'custom_id') else None,
                                network_transaction_reference=capture.network_transaction_reference if hasattr(capture, 'network_transaction_reference') else None,
                                seller_protection=seller_protection,
                                final_capture=capture.final_capture if hasattr(capture, 'final_capture') else None,
                                seller_receivable_breakdown=seller_breakdown if hasattr(capture, 'seller_receivable_breakdown') else None,
                                disbursement_mode=capture.disbursement_mode if hasattr(capture, 'disbursement_mode') else None,
                                links=links,
                                processor_response=capture.processor_response if hasattr(capture, 'processor_response') else None,
                                create_time=capture.create_time if hasattr(capture, 'create_time') else None,
                                update_time=capture.update_time if hasattr(capture, 'update_time') else None    
                            )
                            captures.append(capture_response)
            
            # Extraer enlaces de la orden
            order_links = []
            if paypal_response.links:
                for link in paypal_response.links:
                    order_links.append(LinkResponse(
                        href=link.href,
                        rel=link.rel,
                        method=link.method
                    ))
            
            # Buscar URL de aprobación
            approval_url = None
            for link in order_links:
                if link.rel == "approve":
                    approval_url = link.href
                    break
            
            return OrderCreateResponse(
                order_id=order_id,
                status=status,
                payment_source=payment_source,
                payer_email=payer_email,
                payer_id=payer_id,
                total_amount=total_amount,
                currency_code=currency_code,
                create_time=paypal_response.create_time if hasattr(paypal_response, 'create_time') else None,
                approval_url=approval_url,
                captures=captures,
                links=order_links
            )
            
        except Exception as e:
            logger.error("Error procesando respuesta de orden", error=str(e), exc_info=True)
            # Retorno mínimo en caso de error
            return OrderCreateResponse(
                order_id=paypal_response.id if hasattr(paypal_response, 'id') else "unknown",
                status=OrderStatus.CREATED,
                payment_source=None,
                payer_email=None,
                payer_id=None,
                total_amount=None,
                currency_code=None,
                create_time=None,
                approval_url=None,
                captures=[],
                links=[]
            )
    
    def create_order(
        self,
        intent: str = "CAPTURE",
        purchase_units: List[Dict[str, Any]] = None,
        payment_source: Optional[Dict[str, Any]] = None,
        application_context: Optional[Dict[str, Any]] = None,
        paypal_request_id: Optional[str] = None
    ) -> OrderCreateResponse:
        """
        Crear una nueva orden usando el SDK de PayPal
        
        Args:
            intent: Intención de la orden (CAPTURE, AUTHORIZE)
            purchase_units: Lista de unidades de compra
            payment_source: Fuente de pago (incluyendo vault_id para tokens guardados)
            application_context: Contexto de la aplicación (URLs de retorno, etc.)
            paypal_request_id: ID de request de PayPal para idempotencia
            
        Returns:
            OrderCreateResponse: Respuesta procesada de la orden
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
                processed_response = self._process_order_response(order_response)
                
                logger.info("Orden procesada exitosamente",
                           order_id=processed_response.order_id,
                           status=processed_response.status.value,
                           payment_source=processed_response.payment_source,
                           captures_count=len(processed_response.captures))
                
                return processed_response
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
    ) -> OrderCreateResponse:
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
    
    def create_order_with_vault_token_and_store(
        self,
        db: Session,
        vault_id: str,
        amount: str,
        currency_code: str = "USD",
        intent: str = "CAPTURE",
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        paypal_request_id: Optional[str] = None,
        customer_id: Optional[int] = None,
        vault_payment_method_id: Optional[int] = None
    ) -> tuple[OrderCreateResponse, int]:
        """
        Crear una orden usando un token guardado en el vault y almacenar en la base de datos
        
        Args:
            db: Sesión de base de datos
            vault_id: ID del payment token guardado en el vault
            amount: Monto de la orden
            currency_code: Código de moneda
            intent: Intención de la orden
            description: Descripción de la orden
            reference_id: ID de referencia del comerciante
            return_url: URL de retorno exitoso
            cancel_url: URL de retorno cancelado
            paypal_request_id: ID de request de PayPal
            customer_id: ID del cliente en nuestra base de datos
            vault_payment_method_id: ID del método de pago guardado
            
        Returns:
            Tuple con OrderCreateResponse y el ID de la orden en la base de datos
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
            
            logger.info("Creando orden con vault token y almacenando en DB", 
                       vault_id=vault_id,
                       amount=amount,
                       currency_code=currency_code,
                       intent=intent,
                       customer_id=customer_id)
            
            # Crear la orden en PayPal
            paypal_response = self.create_order(
                intent=intent,
                purchase_units=purchase_units,
                payment_source=payment_source,
                application_context=application_context,
                paypal_request_id=paypal_request_id
            )
            
            # Preparar datos para almacenar en la base de datos
            order_data = {
                'paypal_order_id': paypal_response.order_id,
                'customer_id': customer_id,
                'vault_payment_method_id': vault_payment_method_id,
                'payer_id': paypal_response.payer_id,
                'payer_email': paypal_response.payer_email,
                'intent': intent,
                'status': paypal_response.status.value,
                'amount': Decimal(amount),
                'currency': currency_code,
                'description': description,
                'reference_id': reference_id,
                'return_url': return_url,
                'cancel_url': cancel_url,
                'approval_url': paypal_response.approval_url,
                'paypal_response': {
                    'order_id': paypal_response.order_id,
                    'status': paypal_response.status.value,
                    'payment_source': paypal_response.payment_source,
                    'payer_email': paypal_response.payer_email,
                    'payer_id': paypal_response.payer_id,
                    'total_amount': paypal_response.total_amount,
                    'currency_code': paypal_response.currency_code,
                    'create_time': paypal_response.create_time,
                    'approval_url': paypal_response.approval_url,
                    'captures': [
                        {
                            'id': capture.id,
                            'status': capture.status.value,
                            'amount': {
                                'currency_code': capture.amount.currency_code,
                                'value': capture.amount.value
                            },
                            'create_time': capture.create_time,
                            'update_time': capture.update_time,
                            'final_capture': capture.final_capture,
                            'seller_protection': {
                                'status': capture.seller_protection.status,
                                'dispute_categories': capture.seller_protection.dispute_categories
                            } if capture.seller_protection else None,
                            'seller_receivable_breakdown': {
                                'gross_amount': {
                                    'currency_code': capture.seller_receivable_breakdown.gross_amount.currency_code,
                                    'value': capture.seller_receivable_breakdown.gross_amount.value
                                },
                                'paypal_fee': {
                                    'currency_code': capture.seller_receivable_breakdown.paypal_fee.currency_code,
                                    'value': capture.seller_receivable_breakdown.paypal_fee.value
                                },
                                'net_amount': {
                                    'currency_code': capture.seller_receivable_breakdown.net_amount.currency_code,
                                    'value': capture.seller_receivable_breakdown.net_amount.value
                                }
                            } if capture.seller_receivable_breakdown else None
                        } for capture in paypal_response.captures
                    ],
                    'links': [
                        {
                            'href': link.href,
                            'rel': link.rel,
                            'method': link.method
                        } for link in paypal_response.links
                    ]
                }
            }
            
            # Procesar capturas si existen
            if paypal_response.captures:
                primary_capture = paypal_response.captures[0]  # Tomar la primera captura
                order_data.update({
                    'capture_id': primary_capture.id,
                    'capture_status': primary_capture.status.value,
                    'final_capture': primary_capture.final_capture,
                    'capture_time': datetime.fromisoformat(primary_capture.create_time.replace('Z', '+00:00')) if primary_capture.create_time else None,
                    'captures': order_data['paypal_response']['captures'],
                    'seller_protection': {
                        'status': primary_capture.seller_protection.status,
                        'dispute_categories': primary_capture.seller_protection.dispute_categories
                    } if primary_capture.seller_protection else None
                })
                
                # Procesar breakdown de la captura
                if primary_capture.seller_receivable_breakdown:
                    breakdown = primary_capture.seller_receivable_breakdown
                    order_data.update({
                        'gross_amount': Decimal(breakdown.gross_amount.value),
                        'paypal_fee': Decimal(breakdown.paypal_fee.value),
                        'net_amount': Decimal(breakdown.net_amount.value)
                    })
            
            # Procesar enlaces de PayPal
            if paypal_response.links:
                order_data['paypal_links'] = [
                    {
                        'href': link.href,
                        'rel': link.rel,
                        'method': link.method
                    } for link in paypal_response.links
                ]
            
            # Almacenar en la base de datos
            db_order = OrderRepository.create(db, order_data)
            
            logger.info("Orden creada exitosamente en PayPal y almacenada en DB", 
                       paypal_order_id=paypal_response.order_id,
                       db_order_id=db_order.id,
                       status=paypal_response.status.value)
            
            return paypal_response, db_order.id
            
        except Exception as e:
            logger.error("Error en create_order_with_vault_token_and_store", 
                        vault_id=vault_id,
                        error=str(e), 
                        exc_info=True)
            raise PayPalCommunicationException(f"Error creando orden con vault token y almacenando: {str(e)}")
    
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
    ) -> OrderCreateResponse:
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
