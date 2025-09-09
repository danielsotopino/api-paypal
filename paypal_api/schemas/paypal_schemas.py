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


class VaultSetupTokenRequest(BaseModel):
    customer_id: Optional[str] = Field(..., description="ID del cliente")
    merchant_customer_id: Optional[str] = Field(..., description="ID del merchant")
    paypal_request_id: Optional[str] = Field(..., description="ID de la solicitud de PayPal")
    usage_type: Optional[str] = Field(..., description="Tipo de uso")
    usage_pattern: Optional[str] = Field(..., description="Patrón de uso")
    billing_plan_price_value: str = Field(..., description="Valor del plan de facturación")
    billing_plan_frequency_interval_count: str = Field(..., description="Cantidad de intervalos del plan de facturación")
    billing_plan_start_date: str = Field(..., description="Fecha de inicio del plan de facturación")
    billing_plan_one_time_charges_product_value: str = Field(..., description="Valor del producto del plan de facturación")
    billing_plan_one_time_charges_total_amount_value: str = Field(..., description="Valor total del plan de facturación")
    product_description: str = Field(..., description="Descripción del producto")
    name: str = Field(..., description="Nombre del producto")
    return_url: str = Field(..., description="URL de retorno")
    cancel_url: str = Field(..., description="URL de cancelación")


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
    payer_id: str = Field(..., description="ID del pagador")
    type: str = Field(..., description="Tipo de método de pago")
    credit_card: Optional[CreditCardResponse] = None
    is_active: bool = Field(..., description="Estado del método de pago")
    create_time: str = Field(..., description="Fecha de creación")
    update_time: Optional[str] = None


class VaultPaymentRequest(BaseModel):
    payment_method_id: str = Field(..., description="ID del método de pago almacenado")
    amount: str = Field(..., description="Monto del pago")
    currency: str = Field("USD", description="Moneda del pago")
    description: str = Field(..., description="Descripción del pago")


class VaultPaymentMethodRequest(BaseModel):
    """Esquema para la respuesta de payment-tokens de PayPal"""
    facilitatorAccessToken: str = Field(..., description="Token de acceso del facilitador")
    payerID: str = Field(..., description="ID del pagador")
    paymentSource: str = Field(..., description="Fuente del pago (ej: 'paypal')")
    vaultSetupToken: str = Field(..., description="Token de configuración del vault")


# Order Schemas
class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SAVED = "SAVED"
    APPROVED = "APPROVED"
    VOIDED = "VOIDED"
    COMPLETED = "COMPLETED"
    PAYER_ACTION_REQUIRED = "PAYER_ACTION_REQUIRED"


class CaptureStatus(str, Enum):
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    PENDING = "PENDING"
    REFUNDED = "REFUNDED"


class MoneyResponse(BaseModel):
    currency_code: str = Field(..., description="Código de moneda")
    value: str = Field(..., description="Valor monetario")


class LinkResponse(BaseModel):
    href: str = Field(..., description="URL del enlace")
    rel: str = Field(..., description="Relación del enlace")
    method: str = Field(..., description="Método HTTP")


class AddressResponse(BaseModel):
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    admin_area_2: Optional[str] = None
    admin_area_1: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None


class NameResponse(BaseModel):
    given_name: Optional[str] = None
    surname: Optional[str] = None


class PayerResponse(BaseModel):
    email_address: Optional[str] = None
    payer_id: Optional[str] = None
    name: Optional[NameResponse] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    tax_info: Optional[Dict[str, Any]] = None
    address: Optional[AddressResponse] = None


class SellerProtectionResponse(BaseModel):
    status: str = Field(..., description="Estado de protección del vendedor")
    dispute_categories: List[str] = Field(default_factory=list, description="Categorías de disputa")


class SellerReceivableBreakdownResponse(BaseModel):
    gross_amount: MoneyResponse
    paypal_fee: MoneyResponse
    paypal_fee_in_receivable_currency: Optional[MoneyResponse] = None
    net_amount: MoneyResponse
    receivable_amount: Optional[MoneyResponse] = None
    exchange_rate: Optional[str] = None
    platform_fees: Optional[List[Dict[str, Any]]] = None


class CaptureResponse(BaseModel):
    status: CaptureStatus = Field(..., description="Estado de la captura")
    status_details: Optional[Dict[str, Any]] = None
    id: str = Field(..., description="ID de la captura")
    amount: MoneyResponse
    invoice_id: Optional[str] = None
    custom_id: Optional[str] = None
    network_transaction_reference: Optional[Dict[str, Any]] = None
    seller_protection: Optional[SellerProtectionResponse] = None
    final_capture: Optional[bool] = None
    seller_receivable_breakdown: Optional[SellerReceivableBreakdownResponse] = None
    disbursement_mode: Optional[str] = None
    links: List[LinkResponse] = Field(default_factory=list)
    processor_response: Optional[Dict[str, Any]] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class PaymentCollectionResponse(BaseModel):
    authorizations: Optional[List[Dict[str, Any]]] = None
    captures: List[CaptureResponse] = Field(default_factory=list)
    refunds: Optional[List[Dict[str, Any]]] = None


class PurchaseUnitResponse(BaseModel):
    reference_id: Optional[str] = None
    amount: Optional[MoneyResponse] = None
    payee: Optional[Dict[str, Any]] = None
    payment_instruction: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    custom_id: Optional[str] = None
    invoice_id: Optional[str] = None
    id: Optional[str] = None
    soft_descriptor: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    shipping: Optional[Dict[str, Any]] = None
    supplementary_data: Optional[Dict[str, Any]] = None
    payments: Optional[PaymentCollectionResponse] = None
    most_recent_errors: Optional[List[Dict[str, Any]]] = None


class PaypalWalletStoredCredentialResponse(BaseModel):
    payment_initiator: str = Field(..., description="Iniciador del pago")
    charge_pattern: Optional[str] = None
    usage_pattern: Optional[str] = None
    usage: str = Field(..., description="Tipo de uso")


class PaypalWalletResponse(BaseModel):
    email_address: Optional[str] = None
    account_id: Optional[str] = None
    account_status: Optional[str] = None
    name: Optional[NameResponse] = None
    phone_type: Optional[str] = None
    phone_number: Optional[str] = None
    birth_date: Optional[str] = None
    business_name: Optional[str] = None
    tax_info: Optional[Dict[str, Any]] = None
    address: Optional[AddressResponse] = None
    attributes: Optional[Dict[str, Any]] = None
    stored_credential: Optional[PaypalWalletStoredCredentialResponse] = None


class PaymentSourceResponse(BaseModel):
    card: Optional[Dict[str, Any]] = None
    paypal: Optional[PaypalWalletResponse] = None
    bancontact: Optional[Dict[str, Any]] = None
    blik: Optional[Dict[str, Any]] = None
    eps: Optional[Dict[str, Any]] = None
    giropay: Optional[Dict[str, Any]] = None
    ideal: Optional[Dict[str, Any]] = None
    mybank: Optional[Dict[str, Any]] = None
    p_24: Optional[Dict[str, Any]] = None
    sofort: Optional[Dict[str, Any]] = None
    trustly: Optional[Dict[str, Any]] = None
    apple_pay: Optional[Dict[str, Any]] = None
    google_pay: Optional[Dict[str, Any]] = None
    venmo: Optional[Dict[str, Any]] = None


class OrderResponse(BaseModel):
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    id: str = Field(..., description="ID de la orden")
    payment_source: Optional[PaymentSourceResponse] = None
    intent: Optional[str] = None
    payer: Optional[PayerResponse] = None
    purchase_units: List[PurchaseUnitResponse] = Field(default_factory=list)
    status: OrderStatus = Field(..., description="Estado de la orden")
    links: List[LinkResponse] = Field(default_factory=list)


class OrderCreateResponse(BaseModel):
    """Respuesta simplificada para la creación de órdenes"""
    order_id: str = Field(..., description="ID de la orden creada")
    status: OrderStatus = Field(..., description="Estado de la orden")
    payment_source: Optional[str] = Field(None, description="Fuente de pago utilizada")
    payer_email: Optional[str] = Field(None, description="Email del pagador")
    payer_id: Optional[str] = Field(None, description="ID del pagador")
    total_amount: Optional[str] = Field(None, description="Monto total")
    currency_code: Optional[str] = Field(None, description="Código de moneda")
    create_time: Optional[str] = Field(None, description="Fecha de creación")
    approval_url: Optional[str] = Field(None, description="URL de aprobación")
    captures: List[CaptureResponse] = Field(default_factory=list, description="Capturas realizadas")
    links: List[LinkResponse] = Field(default_factory=list, description="Enlaces relacionados")