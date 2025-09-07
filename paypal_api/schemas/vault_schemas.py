from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ShippingAddressRequest(BaseModel):
    """Dirección de envío para el vault"""
    full_name: str = Field(..., description="Nombre completo")
    address_line_1: str = Field(..., description="Línea de dirección 1")
    address_line_2: Optional[str] = Field(None, description="Línea de dirección 2")
    admin_area_2: str = Field(..., description="Ciudad")
    admin_area_1: str = Field(..., description="Estado/Región")
    postal_code: str = Field(..., description="Código postal")
    country_code: str = Field(..., description="Código de país (ej: CL)")


class VaultCustomerRequest(BaseModel):
    """Request para crear un cliente vault"""
    email_address: str = Field(..., description="Email del cliente")
    given_name: Optional[str] = Field(None, description="Nombre")
    surname: Optional[str] = Field(None, description="Apellido")
    phone_number: Optional[str] = Field(None, description="Número de teléfono")
    merchant_customer_id: Optional[str] = Field(None, description="ID interno del merchant")
    shipping_address: Optional[ShippingAddressRequest] = Field(None, description="Dirección de envío")
    usage_type: str = Field("MERCHANT", description="Tipo de uso")
    permit_multiple_payment_tokens: bool = Field(False, description="Permitir múltiples tokens")


class VaultCustomerResponse(BaseModel):
    """Response del cliente vault registrado"""
    id: str = Field(..., description="ID del payment token")
    customer_id: str = Field(..., description="ID del customer en PayPal")
    merchant_customer_id: Optional[str] = Field(None, description="ID interno del merchant")
    payer_id: str = Field(..., description="ID del pagador")
    email_address: str = Field(..., description="Email del cliente")
    given_name: Optional[str] = Field(None, description="Nombre")
    surname: Optional[str] = Field(None, description="Apellido")
    phone_number: Optional[str] = Field(None, description="Teléfono")
    usage_type: str = Field(..., description="Tipo de uso")
    customer_type: str = Field(..., description="Tipo de cliente")
    permit_multiple_payment_tokens: bool = Field(..., description="Múltiples tokens permitidos")
    payment_source_type: str = Field(..., description="Tipo de fuente de pago")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")

    class Config:
        from_attributes = True


class VaultCustomerListResponse(BaseModel):
    """Response para lista de clientes vault"""
    customers: List[VaultCustomerResponse]
    total: int
    page: int
    limit: int
