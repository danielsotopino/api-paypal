from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from paypal_api.schemas.order_schemas import (
    OrderCreateRequest, OrderResponse, OrderListResponse,
    OrderCaptureRequest, CaptureResponse
)
from paypal_api.schemas.paypal_schemas import VaultPaymentRequest
from paypal_api.schemas.response_models import ApiResponse
from paypal_api.services.order_service import OrderService
from paypal_api.database import get_db
from paypal_api.core.exceptions import PayPalCommunicationException
import structlog

from paypal_api.services.paypal.paypal_orders_service import PaypalOrdersService

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_order_service() -> OrderService:
    """Dependencia para obtener el servicio de Orders"""
    return OrderService()

def get_paypal_orders_service() -> PaypalOrdersService:
    """Dependencia para obtener el servicio de Orders"""
    return PaypalOrdersService()


@router.post("/", response_model=ApiResponse[OrderResponse])
async def create_order(
    order_request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):
    """
    Crear una nueva orden de pago
    
    Una orden representa una intención de pago que debe ser aprobada por el cliente.
    Después de la aprobación, la orden puede ser capturada para completar el pago.
    """
    try:
        logger.info("Creando orden", 
                   amount=order_request.amount.value,
                   currency=order_request.amount.currency_code,
                   intent=order_request.intent)
        
        order_response = order_service.create_order(db, order_request)
        
        logger.info("Orden creada exitosamente", 
                   order_id=order_response.id,
                   status=order_response.status)
        return ApiResponse.success_response(order_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno creando orden", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/with-vault-token", response_model=ApiResponse[OrderResponse])
async def create_order_with_vault_token(
    vault_payment: VaultPaymentRequest,
    order_service: OrderService = Depends(get_order_service),
    paypal_orders_service: PaypalOrdersService = Depends(get_paypal_orders_service),
    db: Session = Depends(get_db)
):
    """
    Crear una orden usando un Payment Token almacenado en el Vault
    
    Esta funcionalidad permite crear una orden de pago usando un método de pago
    previamente guardado sin solicitar nuevamente los datos de la tarjeta.
    """
    try:
        logger.info("Creando orden con vault token", 
                   payment_method_id=vault_payment.payment_method_id,
                   amount=vault_payment.amount)
        

        print("Creando orden con vault token")
        
        order_response = paypal_orders_service.create_order_with_vault_token(
            vault_id=vault_payment.payment_method_id,
            amount=vault_payment.amount,
            currency_code=vault_payment.currency,
            description=vault_payment.description
        )

        order_response = {
            "id": "123",
            "status": "CREATED",
            "amount": vault_payment.amount,
            "currency": vault_payment.currency,
            "description": vault_payment.description
        }

        print(order_response)
        
        logger.info("Orden con vault token creada exitosamente", 
                   order_id=order_response.id,
                   status=order_response.status)
        return ApiResponse.success_response(order_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno creando orden con vault token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{order_id}", response_model=ApiResponse[OrderResponse])
async def get_order(
    order_id: str,
    sync_with_paypal: bool = Query(False, description="Sincronizar con PayPal antes de responder"),
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):
    """
    Obtener información de una orden específica
    
    Permite consultar el estado actual de una orden y opcionalmente
    sincronizar con PayPal para obtener la información más actualizada.
    """
    try:
        logger.info("Obteniendo orden", order_id=order_id, sync=sync_with_paypal)
        
        order_response = order_service.get_order(db, order_id, sync_with_paypal)
        
        if not order_response:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        
        logger.info("Orden obtenida exitosamente", 
                   order_id=order_id,
                   status=order_response.status)
        return ApiResponse.success_response(order_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error interno obteniendo orden", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/{order_id}/capture", response_model=ApiResponse[CaptureResponse])
async def capture_order(
    order_id: str,
    capture_request: Optional[OrderCaptureRequest] = None,
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):
    """
    Capturar el pago de una orden aprobada
    
    Este endpoint debe ser llamado después de que el cliente haya aprobado
    la orden a través del flujo de PayPal. La captura completa la transacción.
    """
    try:
        logger.info("Capturando orden", order_id=order_id)
        
        capture_response = order_service.capture_order(db, order_id, capture_request)
        
        logger.info("Orden capturada exitosamente", 
                   order_id=order_id,
                   capture_id=capture_response.capture_id,
                   status=capture_response.status)
        return ApiResponse.success_response(capture_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno capturando orden", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/", response_model=ApiResponse[OrderListResponse])
async def list_orders(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(10, ge=1, le=50, description="Elementos por página"),
    customer_id: Optional[int] = Query(None, description="Filtrar por ID de cliente"),
    status: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):
    """
    Listar órdenes con paginación y filtros opcionales
    
    Permite consultar todas las órdenes del sistema con opciones de
    filtrado por cliente y estado, además de paginación.
    """
    try:
        logger.info("Listando órdenes", 
                   page=page,
                   page_size=page_size,
                   customer_id=customer_id,
                   status=status)
        
        orders_response = order_service.list_orders(
            db=db,
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status
        )
        
        logger.info("Órdenes listadas exitosamente", 
                   total_items=orders_response.total_items,
                   current_page=orders_response.current_page)
        return ApiResponse.success_response(orders_response.dict())
        
    except Exception as e:
        logger.error("Error interno listando órdenes", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/customer/{customer_id}", response_model=ApiResponse[OrderListResponse])
async def list_customer_orders(
    customer_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(10, ge=1, le=50, description="Elementos por página"),
    status: Optional[str] = Query(None, description="Filtrar por estado de la orden"),
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):
    """
    Listar órdenes de un cliente específico
    
    Endpoint conveniente para obtener todas las órdenes asociadas
    a un cliente particular con opciones de filtrado y paginación.
    """
    try:
        logger.info("Listando órdenes de cliente", 
                   customer_id=customer_id,
                   page=page,
                   page_size=page_size,
                   status=status)
        
        orders_response = order_service.list_orders(
            db=db,
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status
        )
        
        logger.info("Órdenes de cliente listadas exitosamente", 
                   customer_id=customer_id,
                   total_items=orders_response.total_items)
        return ApiResponse.success_response(orders_response.dict())
        
    except Exception as e:
        logger.error("Error interno listando órdenes de cliente", 
                    customer_id=customer_id,
                    error=str(e), 
                    exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
