from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime
import structlog

from paypal_api.repositories.order_repository import OrderRepository
from paypal_api.repositories.customer_repository import CustomerRepository
from paypal_api.services.paypal.paypal_orders_service import PaypalOrdersService
from paypal_api.models.order import Order
from paypal_api.models.customer import Customer
from paypal_api.schemas.order_schemas import (
    OrderCreateRequest, OrderUpdateRequest, OrderResponse, 
    OrderListResponse, OrderCaptureRequest, OrderAuthorizeRequest,
    CaptureResponse, AuthorizationResponse
)
from paypal_api.core.exceptions import PayPalCommunicationException

logger = structlog.get_logger(__name__)


class OrderService:
    """
    Servicio de alto nivel que coordina operaciones entre PayPal Orders API y la base de datos local.
    
    Este servicio actúa como una capa de abstracción que:
    1. Coordina llamadas a PayPal Orders API
    2. Persiste datos en la base de datos local usando repositorios
    3. Mantiene sincronización entre PayPal y nuestra DB
    4. Proporciona una interfaz unificada para operaciones de Orders
    """

    def __init__(self):
        self.order_repo = OrderRepository()
        self.customer_repo = CustomerRepository()
        self.paypal_orders_service = PaypalOrdersService()

        # self.paypal_orders_service.create_order_with_vault_token(
        #     vault_id="vault_id",
        #     amount=100,
        #     currency_code="USD",
        #     description="Test order",
        #     reference_id="test_reference_id",
        # )
    pass

    # def create_order_with_vault_token(
    #     self, 
    #     db: Session, 
    #     vault_id: str, 
    #     amount: Decimal, 
    #     currency: str = "USD",
    #     description: Optional[str] = None,
    #     reference_id: Optional[str] = None,
    #     return_url: Optional[str] = None,
    #     cancel_url: Optional[str] = None
    # ) -> OrderResponse:
    #     """Crear una orden usando un token guardado en el vault"""
    #     try:
    #         logger.info("Creando orden con vault token", 
    #                    vault_id=vault_id,
    #                    amount=amount,
    #                    currency=currency)
            
    #         # Crear orden en PayPal usando el SDK con vault token
    #         paypal_response = self.paypal_orders_service.create_order_with_vault_token(
    #             vault_id=vault_id,
    #             amount=str(amount),
    #             currency_code=currency,
    #             description=description,
    #             reference_id=reference_id,
    #             return_url=return_url,
    #             cancel_url=cancel_url
    #         )
            
    #         # Extraer URL de aprobación
    #         approval_url = None
    #         for link in paypal_response.get("links", []):
    #             if link.get("rel") == "approve":
    #                 approval_url = link.get("href")
    #                 break
            
    #         # Almacenar en base de datos local
    #         order_data = {
    #             "paypal_order_id": paypal_response["id"],
    #             "customer_id": None,  # Se puede asociar después
    #             "payer_email": None,
    #             "intent": paypal_response.get("intent", "CAPTURE"),
    #             "status": paypal_response["status"],
    #             "amount": amount,
    #             "currency": currency,
    #             "description": description,
    #             "reference_id": reference_id,
    #             "return_url": return_url,
    #             "cancel_url": cancel_url,
    #             "paypal_response": paypal_response,
    #             "approval_url": approval_url
    #         }
            
    #         order_db = self.order_repo.create(db, order_data)
            
    #         # Convertir a respuesta
    #         response = OrderResponse(
    #             id=order_db.paypal_order_id,
    #             status=order_db.status,
    #             intent=order_db.intent,
    #             amount=order_db.amount,
    #             currency=order_db.currency,
    #             reference_id=order_db.reference_id,
    #             description=order_db.description,
    #             approval_url=approval_url,
    #             links=[
    #                 {"href": link["href"], "rel": link["rel"], "method": link["method"]}
    #                 for link in paypal_response.get("links", [])
    #             ],
    #             created_at=order_db.created_at
    #         )
            
    #         logger.info("Orden con vault token creada exitosamente", 
    #                    paypal_order_id=order_db.paypal_order_id,
    #                    db_id=order_db.id)
        #     return response
            
        # except Exception as e:
        #     logger.error("Error creando orden con vault token", 
        #                 vault_id=vault_id,
        #                 error=str(e), 
        #                 exc_info=True)
        #     raise

    def create_order(self, db: Session, order_request: OrderCreateRequest) -> OrderResponse:
        """Crear una nueva orden en PayPal y almacenarla localmente"""
        try:
            logger.info("Creando orden", amount=order_request.amount.value, currency=order_request.amount.currency_code)
            
            # Preparar purchase units
            purchase_units = [{
                "reference_id": order_request.reference_id or "default",
                "description": order_request.description,
                "amount": {
                    "currency_code": order_request.amount.currency_code,
                    "value": str(order_request.amount.value)
                }
            }]
            
            # Agregar items si están presentes
            if order_request.items:
                purchase_units[0]["items"] = [
                    {
                        "name": item.name,
                        "unit_amount": {
                            "currency_code": item.unit_amount.currency_code,
                            "value": str(item.unit_amount.value)
                        },
                        "quantity": item.quantity,
                        "description": item.description,
                        "category": item.category
                    } for item in order_request.items
                ]
            
            # Agregar información de envío si está presente
            if order_request.shipping:
                purchase_units[0]["shipping"] = {
                    "name": {
                        "full_name": order_request.shipping.name or "Destinatario"
                    },
                    "address": {
                        "address_line_1": order_request.shipping.address.address_line_1,
                        "address_line_2": order_request.shipping.address.address_line_2,
                        "admin_area_1": order_request.shipping.address.admin_area_1,
                        "admin_area_2": order_request.shipping.address.admin_area_2,
                        "postal_code": order_request.shipping.address.postal_code,
                        "country_code": order_request.shipping.address.country_code
                    }
                }
            
            # Preparar application context
            application_context = {
                "return_url": order_request.return_url,
                "cancel_url": order_request.cancel_url,
                "brand_name": "Tu Tienda",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW"
            }
            
            # Crear orden en PayPal usando el SDK
            paypal_response = self.paypal_orders_service.create_order(
                intent=order_request.intent.value,
                purchase_units=purchase_units,
                application_context=application_context
            )
            
            # Extraer URL de aprobación
            approval_url = None
            for link in paypal_response.get("links", []):
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break
            
            # Buscar o crear cliente si se proporciona email
            customer_id = None
            if order_request.payer_email:
                customer = self.customer_repo.get_by_email(db, order_request.payer_email)
                if customer:
                    customer_id = customer.id
            
            # Almacenar en base de datos local
            order_data = {
                "paypal_order_id": paypal_response["id"],
                "customer_id": customer_id,
                "payer_email": order_request.payer_email,
                "intent": order_request.intent.value,
                "status": paypal_response["status"],
                "amount": order_request.amount.value,
                "currency": order_request.amount.currency_code,
                "description": order_request.description,
                "reference_id": order_request.reference_id,
                "return_url": order_request.return_url,
                "cancel_url": order_request.cancel_url,
                "paypal_response": paypal_response,
                "approval_url": approval_url
            }
            
            order_db = self.order_repo.create(db, order_data)
            
            # Convertir a respuesta
            response = OrderResponse(
                id=order_db.paypal_order_id,
                status=order_db.status,
                intent=order_db.intent,
                amount=order_db.amount,
                currency=order_db.currency,
                reference_id=order_db.reference_id,
                description=order_db.description,
                approval_url=approval_url,
                links=[
                    {"href": link["href"], "rel": link["rel"], "method": link["method"]}
                    for link in paypal_response.get("links", [])
                ],
                created_at=order_db.created_at
            )
            
            logger.info("Orden creada exitosamente", 
                       paypal_order_id=order_db.paypal_order_id,
                       db_id=order_db.id)
            return response
            
        except Exception as e:
            logger.error("Error creando orden", error=str(e), exc_info=True)
            raise

    def get_order(self, db: Session, order_id: str, sync_with_paypal: bool = False) -> Optional[OrderResponse]:
        """Obtener orden por ID"""
        try:
            # Buscar en base de datos local
            order_db = self.order_repo.get_by_paypal_order_id(db, order_id)
            if not order_db:
                return None
            
            # Sincronizar con PayPal si se solicita
            if sync_with_paypal:
                try:
                    paypal_response = self._make_paypal_request("GET", f"/v2/checkout/orders/{order_id}")
                    
                    # Actualizar datos locales
                    update_data = {
                        "status": paypal_response["status"],
                        "paypal_response": paypal_response
                    }
                    
                    # Actualizar información del pagador si está disponible
                    payer = paypal_response.get("payer")
                    if payer:
                        update_data["payer_id"] = payer.get("payer_id")
                        if payer.get("email_address"):
                            update_data["payer_email"] = payer["email_address"]
                    
                    order_db = self.order_repo.update_by_paypal_id(db, order_id, update_data)
                    
                except Exception as e:
                    logger.warning("Error sincronizando con PayPal", error=str(e))
            
            # Convertir a respuesta
            approval_url = None
            links = []
            if order_db.paypal_response:
                for link in order_db.paypal_response.get("links", []):
                    if link.get("rel") == "approve":
                        approval_url = link.get("href")
                    links.append({
                        "href": link["href"],
                        "rel": link["rel"],
                        "method": link["method"]
                    })
            
            response = OrderResponse(
                id=order_db.paypal_order_id,
                status=order_db.status,
                intent=order_db.intent,
                amount=order_db.amount,
                currency=order_db.currency,
                reference_id=order_db.reference_id,
                description=order_db.description,
                approval_url=approval_url or order_db.approval_url,
                links=links,
                payer={
                    "payer_id": order_db.payer_id,
                    "email_address": order_db.payer_email
                } if order_db.payer_id or order_db.payer_email else None,
                created_at=order_db.created_at,
                updated_at=order_db.updated_at,
                approved_at=order_db.approved_at
            )
            
            return response
            
        except Exception as e:
            logger.error("Error obteniendo orden", order_id=order_id, error=str(e))
            raise

    def capture_order(self, db: Session, order_id: str, capture_request: Optional[OrderCaptureRequest] = None) -> CaptureResponse:
        """Capturar pago de una orden aprobada"""
        try:
            logger.info("Capturando orden", order_id=order_id)
            
            # Datos para captura
            capture_data = {}
            if capture_request and capture_request.note_to_payer:
                capture_data["note_to_payer"] = capture_request.note_to_payer
            
            # Capturar en PayPal
            paypal_response = self._make_paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture", capture_data)
            
            # Actualizar estado en base de datos
            update_data = {
                "status": paypal_response["status"],
                "paypal_response": paypal_response
            }
            
            # Obtener información del payer si está disponible
            payer = paypal_response.get("payer")
            if payer:
                update_data["payer_id"] = payer.get("payer_id")
                if payer.get("email_address"):
                    update_data["payer_email"] = payer["email_address"]
            
            self.order_repo.update_by_paypal_id(db, order_id, update_data)
            
            # Extraer información de la captura
            capture_info = paypal_response["purchase_units"][0]["payments"]["captures"][0]
            
            response = CaptureResponse(
                capture_id=capture_info["id"],
                status=capture_info["status"],
                amount=Decimal(capture_info["amount"]["value"]),
                currency=capture_info["amount"]["currency_code"],
                final_capture=capture_request.final_capture if capture_request else True,
                created_at=datetime.fromisoformat(capture_info["create_time"].replace("Z", "+00:00"))
            )
            
            logger.info("Orden capturada exitosamente", 
                       order_id=order_id, 
                       capture_id=response.capture_id)
            return response
            
        except Exception as e:
            logger.error("Error capturando orden", order_id=order_id, error=str(e))
            raise

    def list_orders(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        customer_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> OrderListResponse:
        """Listar órdenes con paginación"""
        try:
            skip = (page - 1) * page_size
            
            orders_db, total = self.order_repo.list_orders(
                db=db,
                skip=skip,
                limit=page_size,
                customer_id=customer_id,
                status=status,
                is_active=True
            )
            
            # Convertir a respuestas
            order_responses = []
            for order_db in orders_db:
                approval_url = None
                links = []
                if order_db.paypal_response:
                    for link in order_db.paypal_response.get("links", []):
                        if link.get("rel") == "approve":
                            approval_url = link.get("href")
                        links.append({
                            "href": link["href"],
                            "rel": link["rel"],
                            "method": link["method"]
                        })
                
                order_responses.append(OrderResponse(
                    id=order_db.paypal_order_id,
                    status=order_db.status,
                    intent=order_db.intent,
                    amount=order_db.amount,
                    currency=order_db.currency,
                    reference_id=order_db.reference_id,
                    description=order_db.description,
                    approval_url=approval_url or order_db.approval_url,
                    links=links,
                    payer={
                        "payer_id": order_db.payer_id,
                        "email_address": order_db.payer_email
                    } if order_db.payer_id or order_db.payer_email else None,
                    created_at=order_db.created_at,
                    updated_at=order_db.updated_at,
                    approved_at=order_db.approved_at
                ))
            
            total_pages = (total + page_size - 1) // page_size
            
            return OrderListResponse(
                orders=order_responses,
                total_items=total,
                total_pages=total_pages,
                current_page=page,
                page_size=page_size
            )
            
        except Exception as e:
            logger.error("Error listando órdenes", error=str(e))
            raise
