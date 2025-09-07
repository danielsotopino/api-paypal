from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from paypal_api.models.vault_customer import VaultCustomer
from paypal_api.schemas.vault_schemas import VaultCustomerRequest


class VaultCustomerRepository:
    """Repositorio para operaciones con VaultCustomer"""

    @staticmethod
    def create(db: Session, payment_token_data: dict) -> VaultCustomer:
        """Crear un nuevo cliente vault desde datos de PayPal"""
        
        # Extraer datos del payment token response
        customer_data = payment_token_data.get('customer', {})
        payment_source = payment_token_data.get('payment_source', {})
        paypal_data = payment_source.get('paypal', {})
        shipping = paypal_data.get('shipping', {})
        shipping_name = shipping.get('name', {})
        shipping_address = shipping.get('address', {})
        name_data = paypal_data.get('name', {})
        phone_data = paypal_data.get('phone', {})
        phone_number_data = phone_data.get('phone_number', {}) if phone_data else {}
        
        vault_customer = VaultCustomer(
            id=payment_token_data['id'],
            customer_id=customer_data['id'],
            merchant_customer_id=customer_data.get('merchant_customer_id'),
            payer_id=paypal_data.get('payer_id'),
            email_address=paypal_data.get('email_address'),
            given_name=name_data.get('given_name'),
            surname=name_data.get('surname'),
            phone_number=phone_number_data.get('national_number'),
            phone_type=phone_data.get('phone_type'),
            shipping_full_name=shipping_name.get('full_name'),
            shipping_address_line_1=shipping_address.get('address_line_1'),
            shipping_address_line_2=shipping_address.get('address_line_2'),
            shipping_admin_area_2=shipping_address.get('admin_area_2'),
            shipping_admin_area_1=shipping_address.get('admin_area_1'),
            shipping_postal_code=shipping_address.get('postal_code'),
            shipping_country_code=shipping_address.get('country_code'),
            usage_type=paypal_data.get('usage_type', 'MERCHANT'),
            customer_type=paypal_data.get('customer_type', 'CONSUMER'),
            permit_multiple_payment_tokens=paypal_data.get('permit_multiple_payment_tokens', False),
            payment_source_type='paypal',
            links=payment_token_data.get('links', [])
        )
        
        db.add(vault_customer)
        db.commit()
        db.refresh(vault_customer)
        return vault_customer

    @staticmethod
    def get_by_id(db: Session, customer_id: str) -> Optional[VaultCustomer]:
        """Obtener cliente por ID"""
        return db.query(VaultCustomer).filter(VaultCustomer.id == customer_id).first()

    @staticmethod
    def get_by_customer_id(db: Session, customer_id: str) -> Optional[VaultCustomer]:
        """Obtener cliente por customer_id de PayPal"""
        return db.query(VaultCustomer).filter(VaultCustomer.customer_id == customer_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[VaultCustomer]:
        """Obtener cliente por email"""
        return db.query(VaultCustomer).filter(VaultCustomer.email_address == email).first()

    @staticmethod
    def get_by_payer_id(db: Session, payer_id: str) -> Optional[VaultCustomer]:
        """Obtener cliente por payer_id"""
        return db.query(VaultCustomer).filter(VaultCustomer.payer_id == payer_id).first()

    @staticmethod
    def list_customers(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        email_filter: Optional[str] = None
    ) -> tuple[List[VaultCustomer], int]:
        """Listar clientes con paginación y filtros opcionales"""
        query = db.query(VaultCustomer)
        
        if email_filter:
            query = query.filter(VaultCustomer.email_address.ilike(f"%{email_filter}%"))
        
        total = query.count()
        customers = query.offset(skip).limit(limit).all()
        
        return customers, total

    @staticmethod
    def update(db: Session, customer_id: str, update_data: dict) -> Optional[VaultCustomer]:
        """Actualizar datos del cliente"""
        customer = db.query(VaultCustomer).filter(VaultCustomer.id == customer_id).first()
        if not customer:
            return None
            
        for key, value in update_data.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def delete(db: Session, customer_id: str) -> bool:
        """Eliminar cliente"""
        customer = db.query(VaultCustomer).filter(VaultCustomer.id == customer_id).first()
        if not customer:
            return False
            
        db.delete(customer)
        db.commit()
        return True