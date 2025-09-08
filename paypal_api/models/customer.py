from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from paypal_api.database import Base

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "paypal"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Serial autogenerado
    paypal_customer_id = Column(String, unique=True, nullable=False, index=True)  # PayPal customer.id
    email_address = Column(String, nullable=False, index=True)
    given_name = Column(String)
    surname = Column(String)
    phone_number = Column(String)
    
    # Dirección por defecto
    default_shipping_address = Column(JSON)
    
    # Control
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    payment_methods = relationship("VaultPaymentMethod", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, paypal_customer_id='{self.paypal_customer_id}', email='{self.email_address}')>"