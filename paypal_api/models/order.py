from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from paypal_api.database import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "paypal"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    paypal_order_id = Column(String, unique=True, nullable=False, index=True)  # PayPal order.id
    
    # Relaciones
    customer_id = Column(Integer, ForeignKey("paypal.customers.id"), nullable=True, index=True)
    vault_payment_method_id = Column(Integer, ForeignKey("paypal.vault_payment_methods.id"), nullable=True, index=True)
    
    # Información del pagador (PayPal)
    payer_id = Column(String, nullable=True, index=True)  # PayPal payer ID
    payer_email = Column(String, nullable=True, index=True)
    payer_name_given = Column(String)  # payer.name.given_name
    payer_name_surname = Column(String)  # payer.name.surname
    payer_address_country = Column(String(2))  # payer.address.country_code
    
    # Detalles de la orden
    intent = Column(String, nullable=False, default="CAPTURE")  # CAPTURE, AUTHORIZE
    status = Column(String, nullable=False, index=True)  # CREATED, APPROVED, VOIDED, COMPLETED, etc.
    
    # Montos
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Información de captura
    capture_id = Column(String, nullable=True, index=True)  # ID de la captura principal
    capture_status = Column(String, nullable=True)  # Status de la captura
    final_capture = Column(Boolean, default=True)  # Si es captura final
    capture_time = Column(DateTime(timezone=True), nullable=True)  # create_time de la captura
    
    # Desglose de montos
    gross_amount = Column(Numeric(10, 2), nullable=True)  # seller_receivable_breakdown.gross_amount.value
    paypal_fee = Column(Numeric(10, 2), nullable=True)  # seller_receivable_breakdown.paypal_fee.value
    net_amount = Column(Numeric(10, 2), nullable=True)  # seller_receivable_breakdown.net_amount.value
    
    # Detalles adicionales
    description = Column(Text)
    reference_id = Column(String, index=True)  # ID de referencia del comerciante
    
    # URLs de retorno
    return_url = Column(String)
    cancel_url = Column(String)
    
    # Información de aprobación
    approval_url = Column(String)
    approved_at = Column(DateTime(timezone=True))
    
    # Datos complejos de PayPal (JSON)
    payment_source = Column(JSON)  # Información completa de payment_source
    captures = Column(JSON)  # Información de todas las capturas
    seller_protection = Column(JSON)  # Información de seller protection
    paypal_links = Column(JSON)  # Enlaces de PayPal
    
    # Respuesta completa de PayPal (para auditoría)
    paypal_response = Column(JSON)
    
    # Control
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    customer = relationship("Customer", back_populates="orders")
    vault_payment_method = relationship("VaultPaymentMethod", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, paypal_order_id='{self.paypal_order_id}', status='{self.status}')>"


# Actualizar el modelo Customer para incluir la relación
