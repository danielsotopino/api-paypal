from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    CREATED = "created"
    APPROVED = "approved"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SubscriptionStatus(str, Enum):
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Monto del pago")
    currency: str = Field("USD", description="Moneda del pago")
    description: str = Field(..., description="Descripción del pago")
    return_url: str = Field(..., description="URL de retorno exitoso")
    cancel_url: str = Field(..., description="URL de retorno cancelado")


class PaymentResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    approval_url: Optional[str] = None
    amount: Decimal
    currency: str
    description: str
    created_at: datetime


class SubscriptionPlanRequest(BaseModel):
    name: str = Field(..., description="Nombre del plan")
    description: str = Field(..., description="Descripción del plan")
    amount: Decimal = Field(..., gt=0, description="Monto de la suscripción")
    currency: str = Field("USD", description="Moneda")
    interval: str = Field("month", description="Intervalo de facturación")
    interval_count: int = Field(1, description="Número de intervalos")


class SubscriptionRequest(BaseModel):
    plan_id: str = Field(..., description="ID del plan de suscripción")
    subscriber_email: str = Field(..., description="Email del suscriptor")
    return_url: str = Field(..., description="URL de retorno exitoso")
    cancel_url: str = Field(..., description="URL de retorno cancelado")


class SubscriptionResponse(BaseModel):
    subscription_id: str
    status: SubscriptionStatus
    approval_url: Optional[str] = None
    plan_id: str
    subscriber_email: str
    created_at: datetime


class WebhookEvent(BaseModel):
    id: str
    event_type: str
    resource_type: str
    summary: str
    resource: dict
    create_time: datetime


# Vault Schemas
class CreditCardType(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    DISCOVER = "discover"
    AMEX = "amex"


class PaymentMethodType(str, Enum):
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"


class CreditCardRequest(BaseModel):
    type: CreditCardType = Field(..., description="Tipo de tarjeta")
    number: str = Field(..., description="Número de tarjeta")
    expire_month: int = Field(..., ge=1, le=12, description="Mes de expiración")
    expire_year: int = Field(..., description="Año de expiración")
    cvv2: str = Field(..., min_length=3, max_length=4, description="Código CVV")
    first_name: str = Field(..., description="Nombre del titular")
    last_name: str = Field(..., description="Apellido del titular")
    billing_address: Optional[dict] = Field(None, description="Dirección de facturación")


class BillingCycle(BaseModel):
    tenure_type: str = Field(..., description="Tipo de tenencia")
    pricing_scheme: Dict[str, Any] = Field(..., description="Esquema de precios")
    frequency: Dict[str, Any] = Field(..., description="Frecuencia de facturación")
    total_cycles: str = Field(..., description="Total de ciclos")
    start_date: str = Field(..., description="Fecha de inicio")


class BillingPlan(BaseModel):
    billing_cycles: List[BillingCycle] = Field(..., description="Ciclos de facturación")
    one_time_charges: Optional[Dict[str, Any]] = Field(None, description="Cargos únicos")
    product: Optional[Dict[str, Any]] = Field(None, description="Información del producto")
    name: str = Field(..., description="Nombre del plan")


class ExperienceContext(BaseModel):
    return_url: str = Field(..., description="URL de retorno")
    cancel_url: str = Field(..., description="URL de cancelación")


class PayPalPaymentSource(BaseModel):
    usage_type: str = Field(..., description="Tipo de uso")
    usage_pattern: str = Field(..., description="Patrón de uso")
    billing_plan: Optional[BillingPlan] = Field(None, description="Plan de facturación")
    experience_context: Optional[ExperienceContext] = Field(None, description="Contexto de experiencia")


class PaymentMethodRequest(BaseModel):
    pass
    # payer_id: str = Field(..., description="ID del pagador")
    # type: PaymentMethodType = Field(..., description="Tipo de método de pago")
    # credit_card: Optional[CreditCardRequest] = Field(None, description="Datos de tarjeta de crédito")
    # paypal: Optional[PayPalPaymentSource] = Field(None, description="Datos de PayPal con billing plan")
    # use_paypal_payment_source: bool = Field(False, description="Usar PayPal como fuente de pago")


class CreditCardResponse(BaseModel):
    type: CreditCardType
    number: str = Field(..., description="Últimos 4 dígitos enmascarados")
    expire_month: int
    expire_year: int
    first_name: str
    last_name: str
    state: str = Field(..., description="Estado de la tarjeta")
    valid_until: datetime


class PaymentMethodResponse(BaseModel):
    id: str = Field(..., description="ID del método de pago")
    payer_id: str
    type: PaymentMethodType
    credit_card: Optional[CreditCardResponse] = None
    state: str = Field(..., description="Estado del método de pago")
    create_time: datetime
    update_time: datetime


class VaultPaymentRequest(BaseModel):
    payment_method_id: str = Field(..., description="ID del método de pago almacenado")
    amount: str = Field(..., description="Monto del pago")
    currency: str = Field("USD", description="Moneda del pago")
    description: str = Field(..., description="Descripción del pago")


class PaymentTokenResponse(BaseModel):
    """Esquema para la respuesta de payment-tokens de PayPal"""
    facilitatorAccessToken: str = Field(..., description="Token de acceso del facilitador")
    payerID: str = Field(..., description="ID del pagador")
    paymentSource: str = Field(..., description="Fuente del pago (ej: 'paypal')")
    vaultSetupToken: str = Field(..., description="Token de configuración del vault")