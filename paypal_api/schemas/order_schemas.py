from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class OrderIntent(str, Enum):
    CAPTURE = "CAPTURE"
    AUTHORIZE = "AUTHORIZE"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SAVED = "SAVED"
    APPROVED = "APPROVED"
    VOIDED = "VOIDED"
    COMPLETED = "COMPLETED"
    PAYER_ACTION_REQUIRED = "PAYER_ACTION_REQUIRED"


class AmountRequest(BaseModel):
    currency_code: str = Field("USD", description="Código de moneda")
    value: Decimal = Field(..., gt=0, description="Valor del monto")


class ItemRequest(BaseModel):
    name: str = Field(..., description="Nombre del artículo")
    quantity: str = Field(..., description="Cantidad")
    unit_amount: AmountRequest = Field(..., description="Precio unitario")
    description: Optional[str] = Field(None, description="Descripción del artículo")
    category: Optional[str] = Field("PHYSICAL_GOODS", description="Categoría del artículo")


class ShippingAddressRequest(BaseModel):
    address_line_1: str = Field(..., description="Línea de dirección 1")
    address_line_2: Optional[str] = Field(None, description="Línea de dirección 2")
    admin_area_1: Optional[str] = Field(None, description="Estado/Provincia")
    admin_area_2: str = Field(..., description="Ciudad")
    postal_code: str = Field(..., description="Código postal")
    country_code: str = Field(..., description="Código de país")


class ShippingRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre del destinatario")
    address: ShippingAddressRequest = Field(..., description="Dirección de envío")


class OrderCreateRequest(BaseModel):
    intent: OrderIntent = Field(OrderIntent.CAPTURE, description="Intención de la orden")
    reference_id: Optional[str] = Field(None, description="ID de referencia del comerciante")
    description: Optional[str] = Field(None, description="Descripción de la orden")
    
    # Información del pago
    amount: AmountRequest = Field(..., description="Monto total")
    items: Optional[List[ItemRequest]] = Field(None, description="Lista de artículos")
    
    # Información de envío
    shipping: Optional[ShippingRequest] = Field(None, description="Información de envío")
    
    # URLs de retorno
    return_url: str = Field(..., description="URL de retorno exitoso")
    cancel_url: str = Field(..., description="URL de retorno cancelado")
    
    # Información adicional del pagador
    payer_email: Optional[str] = Field(None, description="Email del pagador")


class OrderUpdateRequest(BaseModel):
    reference_id: Optional[str] = Field(None, description="ID de referencia actualizado")
    description: Optional[str] = Field(None, description="Descripción actualizada")
    amount: Optional[AmountRequest] = Field(None, description="Monto actualizado")
    items: Optional[List[ItemRequest]] = Field(None, description="Lista de artículos actualizada")


class PayerInfo(BaseModel):
    payer_id: Optional[str] = Field(None, description="ID del pagador")
    email_address: Optional[str] = Field(None, description="Email del pagador")
    name: Optional[Dict[str, Any]] = Field(None, description="Nombre del pagador")


class LinkResponse(BaseModel):
    href: str = Field(..., description="URL del enlace")
    rel: str = Field(..., description="Relación del enlace")
    method: str = Field(..., description="Método HTTP")


class OrderResponse(BaseModel):
    id: str = Field(..., description="ID de la orden en PayPal")
    status: OrderStatus = Field(..., description="Estado de la orden")
    intent: OrderIntent = Field(..., description="Intención de la orden")
    
    # Información del pago
    amount: Decimal = Field(..., description="Monto total")
    currency: str = Field(..., description="Código de moneda")
    
    # Información adicional
    reference_id: Optional[str] = Field(None, description="ID de referencia del comerciante")
    description: Optional[str] = Field(None, description="Descripción de la orden")
    
    # URLs y enlaces
    approval_url: Optional[str] = Field(None, description="URL de aprobación")
    links: Optional[List[LinkResponse]] = Field(None, description="Enlaces relacionados")
    
    # Información del pagador
    payer: Optional[PayerInfo] = Field(None, description="Información del pagador")
    
    # Fechas
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")
    approved_at: Optional[datetime] = Field(None, description="Fecha de aprobación")


class OrderListResponse(BaseModel):
    orders: List[OrderResponse] = Field(..., description="Lista de órdenes")
    total_items: int = Field(..., description="Total de órdenes")
    total_pages: int = Field(..., description="Total de páginas")
    current_page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Tamaño de página")


class OrderCaptureRequest(BaseModel):
    note_to_payer: Optional[str] = Field(None, description="Nota para el pagador")
    final_capture: bool = Field(True, description="Captura final")


class OrderAuthorizeRequest(BaseModel):
    note_to_payer: Optional[str] = Field(None, description="Nota para el pagador")


class CaptureResponse(BaseModel):
    capture_id: str = Field(..., description="ID de la captura")
    status: str = Field(..., description="Estado de la captura")
    amount: Decimal = Field(..., description="Monto capturado")
    currency: str = Field(..., description="Código de moneda")
    final_capture: bool = Field(..., description="Captura final")
    created_at: datetime = Field(..., description="Fecha de captura")


class AuthorizationResponse(BaseModel):
    authorization_id: str = Field(..., description="ID de la autorización")
    status: str = Field(..., description="Estado de la autorización")
    amount: Decimal = Field(..., description="Monto autorizado")
    currency: str = Field(..., description="Código de moneda")
    expiration_time: Optional[datetime] = Field(None, description="Fecha de expiración")
    created_at: datetime = Field(..., description="Fecha de autorización")
