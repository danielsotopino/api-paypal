from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from paypal_api.models.customer import Customer
import structlog

logger = structlog.get_logger(__name__)


class CustomerRepository:
    """Repositorio para operaciones con Customer"""

    @staticmethod
    def create(db: Session, customer_data: Dict[str, Any]) -> Customer:
        """Crear un nuevo cliente desde datos de PayPal"""
        try:
            customer = Customer(
                paypal_customer_id=customer_data['paypal_customer_id'],
                email_address=customer_data['email_address'],
                given_name=customer_data.get('given_name'),
                surname=customer_data.get('surname'),
                phone_number=customer_data.get('phone_number'),
                default_shipping_address=customer_data.get('default_shipping_address'),
                is_active=customer_data.get('is_active', True)
            )
            
            db.add(customer)
            db.commit()
            db.refresh(customer)
            
            logger.info("Cliente creado exitosamente", 
                       customer_id=customer.id,
                       paypal_customer_id=customer.paypal_customer_id)
            return customer
            
        except Exception as e:
            db.rollback()
            logger.error("Error creando cliente", error=str(e), exc_info=True)
            raise

    @staticmethod
    def get_by_id(db: Session, customer_id: int) -> Optional[Customer]:
        """Obtener cliente por ID interno"""
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def get_by_paypal_customer_id(db: Session, paypal_customer_id: str) -> Optional[Customer]:
        """Obtener cliente por PayPal customer ID"""
        return db.query(Customer).filter(Customer.paypal_customer_id == paypal_customer_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Customer]:
        """Obtener cliente por email"""
        return db.query(Customer).filter(Customer.email_address == email).first()

    @staticmethod
    def list_customers(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        email_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Customer], int]:
        """Listar clientes con paginación y filtros opcionales"""
        query = db.query(Customer)
        
        if email_filter:
            query = query.filter(Customer.email_address.ilike(f"%{email_filter}%"))
            
        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)
        
        total = query.count()
        customers = query.offset(skip).limit(limit).all()
        
        return customers, total

    @staticmethod
    def update(db: Session, customer_id: int, update_data: Dict[str, Any]) -> Optional[Customer]:
        """Actualizar datos del cliente"""
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return None
                
            for key, value in update_data.items():
                if hasattr(customer, key) and key != 'id':  # No permitir cambiar el ID
                    setattr(customer, key, value)
            
            db.commit()
            db.refresh(customer)
            
            logger.info("Cliente actualizado exitosamente", customer_id=customer_id)
            return customer
            
        except Exception as e:
            db.rollback()
            logger.error("Error actualizando cliente", customer_id=customer_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def soft_delete(db: Session, customer_id: int) -> bool:
        """Desactivar cliente (soft delete)"""
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return False
                
            customer.is_active = False
            db.commit()
            
            logger.info("Cliente desactivado exitosamente", customer_id=customer_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error desactivando cliente", customer_id=customer_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def delete(db: Session, customer_id: int) -> bool:
        """Eliminar cliente permanentemente (usar con precaución)"""
        try:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return False
                
            db.delete(customer)
            db.commit()
            
            logger.info("Cliente eliminado permanentemente", customer_id=customer_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error eliminando cliente", customer_id=customer_id, error=str(e), exc_info=True)
            raise
