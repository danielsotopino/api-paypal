from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from paypal_api.database import Base

class VaultPaymentMethod(Base):
    __tablename__ = "vault_payment_methods"
    __table_args__ = {"schema": "paypal"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Serial autogenerado
    customer_id = Column(Integer, ForeignKey("paypal.customers.id"), nullable=False, index=True)
    
    # PayPal payment token ID (separado del ID interno)
    paypal_payment_token_id = Column(String, unique=True, nullable=False, index=True)  # PaymentTokenResponse.id
    
    # Datos del método de pago
    payment_source_type = Column(String, nullable=False)  # paypal, card, venmo, apple_pay
    usage_type = Column(String, default="MERCHANT")
    customer_type = Column(String, default="CONSUMER")
    
    # PayPal specific data
    payer_id = Column(String, index=True)
    permit_multiple_tokens = Column(Boolean, default=False)
    
    # Estado del método de pago
    is_active = Column(Boolean, default=True)
    paypal_status = Column(String)  # Estado en PayPal si lo necesitamos
    
    # Metadatos de PayPal
    paypal_links = Column(JSON)
    
    # Auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relaciones
    customer = relationship("Customer", back_populates="payment_methods")
    orders = relationship("Order", back_populates="vault_payment_method")
    
    def __repr__(self):
        return f"<VaultPaymentMethod(id={self.id}, paypal_token='{self.paypal_payment_token_id}', customer={self.customer_id})>"