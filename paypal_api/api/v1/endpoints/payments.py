from fastapi import APIRouter, Depends, HTTPException
from paypal_api.schemas.paypal_schemas import PaymentRequest, PaymentResponse
from paypal_api.schemas.response_models import ApiResponse

router = APIRouter()


@router.post("/create", response_model=ApiResponse[PaymentResponse])
async def create_payment(payment_request: PaymentRequest):
    """
    Crear un nuevo pago con PayPal
    """
    # TODO: Implementar lógica de creación de pago
    pass


@router.get("/{payment_id}", response_model=ApiResponse[PaymentResponse])
async def get_payment(payment_id: str):
    """
    Obtener información de un pago
    """
    # TODO: Implementar lógica para obtener pago
    pass


@router.post("/{payment_id}/execute", response_model=ApiResponse[PaymentResponse])
async def execute_payment(payment_id: str, payer_id: str):
    """
    Ejecutar un pago aprobado
    """
    # TODO: Implementar lógica de ejecución de pago
    pass