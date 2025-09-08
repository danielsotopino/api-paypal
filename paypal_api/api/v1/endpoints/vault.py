from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from paypal_api.schemas.paypal_schemas import (
    PaymentMethodRequest,
    PaymentMethodResponse,
    CreditCardRequest,
    VaultPaymentMethodRequest,
    VaultPaymentRequest,
    PaymentResponse
)
from paypal_api.schemas.response_models import ApiResponse
from paypal_api.services.vault_service import VaultService
from paypal_api.database import get_db
from paypal_api.core.exceptions import PayPalCommunicationException
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_vault_service() -> VaultService:
    """Dependencia para obtener el servicio de Vault"""
    return VaultService()


@router.post("/setup-tokens", response_model=ApiResponse[dict])
async def create_setup_token(
    payment_method: PaymentMethodRequest,
    paypal_request_id: Optional[str] = Header(None, alias="PayPal-Request-Id"),
    vault_service: VaultService = Depends(get_vault_service)
):
    """
    Crea un Setup Token para almacenar temporalmente un método de pago
    
    Un Setup Token es útil cuando quieres:
    - Validar un método de pago antes de guardarlo permanentemente
    - Permitir al usuario aprobar el almacenamiento del método de pago
    - Crear un flujo de dos pasos para el vaulting
    """
    try:
        logger.info("Creando setup token")
        
        result = vault_service.create_setup_token()
        
        logger.info("Setup token creado exitosamente", result=result)
        return ApiResponse.success_response(result)
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno creando setup token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/setup-tokens/{setup_token_id}", response_model=ApiResponse[dict])
async def get_setup_token(
    setup_token_id: str,
    vault_service: VaultService = Depends(get_vault_service)
):
    """
    Obtiene información de un Setup Token
    """
    try:
        logger.info("Obteniendo setup token", token_id=setup_token_id)
        
        result = vault_service.get_setup_token(setup_token_id)
        
        logger.info("Setup token obtenido exitosamente", token_id=setup_token_id)
        return ApiResponse.success_response(result)
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=404, detail="Setup token no encontrado")
    except Exception as e:
        logger.error("Error interno obteniendo setup token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/payment-tokens", response_model=ApiResponse[PaymentMethodResponse])
async def create_payment_token(
    payment_method: VaultPaymentMethodRequest,
    vault_service: VaultService = Depends(get_vault_service),
    db: Session = Depends(get_db)
):
    """
    Crea un Payment Token permanente en el Vault
    
    Puedes crear un payment token de dos formas:
    1. Directamente con datos de tarjeta (para flujos simples)
    2. Usando un setup_token_id (para flujos de dos pasos)
    """
    try:
        logger.info("Creando payment token", 
                   payer_id=payment_method.payerID)
        
        # Crear payment token y almacenar en DB
        payment_method_db, paypal_response = vault_service.create_payment_token_and_store(
            db, payment_method
        )
        
        # Convertir a formato de respuesta
        response_data = PaymentMethodResponse(
            id=payment_method_db.paypal_payment_token_id,
            payer_id=payment_method_db.payer_id,
            type=payment_method_db.payment_source_type,
            state=payment_method_db.status,
            create_time=payment_method_db.created_at.isoformat() if payment_method_db.created_at else None,
            update_time=payment_method_db.updated_at.isoformat() if payment_method_db.updated_at else None
        )
        
        logger.info("Payment token creado exitosamente", 
                   token_id=payment_method_db.paypal_payment_token_id,
                   db_id=payment_method_db.id)
        return ApiResponse.success_response(response_data.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno creando payment token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/payment-tokens/{payment_token_id}", response_model=ApiResponse[PaymentMethodResponse])
async def get_payment_token(
    payment_token_id: str,
    sync_with_paypal: bool = Query(False, description="Sincronizar con PayPal antes de responder"),
    vault_service: VaultService = Depends(get_vault_service),
    db: Session = Depends(get_db)
):
    """
    Obtiene información de un Payment Token almacenado en el Vault
    """
    try:
        logger.info("Obteniendo payment token", token_id=payment_token_id)
        
        payment_method = vault_service.get_payment_token(
            db, payment_token_id, sync_with_paypal=sync_with_paypal
        )
        
        if not payment_method:
            raise HTTPException(status_code=404, detail="Payment token no encontrado")
        
        # Convertir la respuesta al formato esperado
        payment_method_response = PaymentMethodResponse(
            id=payment_method.paypal_payment_token_id,
            payer_id=payment_method.payer_id,
            type=payment_method.payment_source_type,
            is_active=payment_method.is_active,
            create_time=payment_method.created_at.isoformat() if payment_method.created_at else None,
            update_time=payment_method.updated_at.isoformat() if payment_method.updated_at else None
        )
        
        logger.info("Payment token obtenido exitosamente", token_id=payment_token_id)
        return ApiResponse.success_response(payment_method_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=404, detail="Payment token no encontrado")
    except Exception as e:
        logger.error("Error interno obteniendo payment token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/payment-tokens/{payment_token_id}", response_model=ApiResponse[dict])
async def delete_payment_token(
    payment_token_id: str,
    vault_service: VaultService = Depends(get_vault_service),
    db: Session = Depends(get_db)
):
    """
    Elimina un Payment Token del Vault
    """
    try:
        logger.info("Eliminando payment token", token_id=payment_token_id)
        
        success = vault_service.delete_payment_token(db, payment_token_id)
        
        if success:
            logger.info("Payment token eliminado exitosamente", token_id=payment_token_id)
            return ApiResponse.success_response({
                "message": "Payment token eliminado exitosamente",
                "payment_token_id": payment_token_id
            })
        else:
            raise HTTPException(status_code=400, detail="No se pudo eliminar el payment token")
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=404, detail="Payment token no encontrado")
    except Exception as e:
        logger.error("Error interno eliminando payment token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/customers/{customer_id}/payment-tokens", response_model=ApiResponse[dict])
async def list_customer_payment_tokens(
    customer_id: str,
    page_size: int = Query(5, ge=1, le=5, description="Número de tokens por página"),
    page: int = Query(1, ge=1, le=10, description="Número de página"),
    total_required: bool = Query(False, description="Incluir totales en la respuesta"),
    use_local_db: bool = Query(True, description="Usar base de datos local en lugar de PayPal API"),
    vault_service: VaultService = Depends(get_vault_service),
    db: Session = Depends(get_db)
):
    """
    Lista todos los Payment Tokens de un cliente
    """
    try:
        logger.info("Listando payment tokens de cliente", 
                   customer_id=customer_id,
                   page=page,
                   page_size=page_size)
        
        result = vault_service.list_customer_payment_tokens(
            db=db,
            customer_id=customer_id,
            page_size=page_size,
            page=page,
            total_required=total_required,
            use_local_db=use_local_db
        )
        
        logger.info("Payment tokens listados exitosamente", 
                   customer_id=customer_id,
                   total_tokens=result.get('total_items', 0))
        return ApiResponse.success_response(result)
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error interno listando payment tokens", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/payments/with-token", response_model=ApiResponse[PaymentResponse])
async def create_payment_with_vault_token(
    vault_payment: VaultPaymentRequest,
    vault_service: VaultService = Depends(get_vault_service),
    db: Session = Depends(get_db)
):
    """
    Crea un pago usando un Payment Token almacenado en el Vault
    
    Esta funcionalidad permite cobrar a un cliente usando un método de pago
    previamente guardado sin solicitar nuevamente los datos de la tarjeta.
    """
    try:
        logger.info("Creando pago con vault token", 
                   payment_method_id=vault_payment.payment_method_id,
                   amount=vault_payment.amount)
        
        # Crear el pago usando el token (incluye validación interna)
        payment_result = vault_service.create_payment_with_vault_token(
            db=db,
            payment_token_id=vault_payment.payment_method_id,
            amount=float(vault_payment.amount),
            currency=vault_payment.currency,
            description=vault_payment.description
        )
        
        # Convertir la respuesta al formato esperado
        payment_response = PaymentResponse(
            payment_id=payment_result.get('id'),
            status=payment_result.get('state', 'created').lower(),
            amount=vault_payment.amount,
            currency=vault_payment.currency,
            description=vault_payment.description,
            created_at=datetime.now()
        )
        
        logger.info("Pago con vault token creado exitosamente", 
                   payment_id=payment_response.payment_id)
        return ApiResponse.success_response(payment_response.dict())
        
    except PayPalCommunicationException as e:
        logger.error("Error de comunicación con PayPal", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error interno creando pago con vault token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
