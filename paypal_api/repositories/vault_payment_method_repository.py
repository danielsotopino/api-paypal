from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from paypal_api.models.vault_payment_method import VaultPaymentMethod
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class VaultPaymentMethodRepository:
    """Repositorio para operaciones con VaultPaymentMethod"""

    @staticmethod
    def create(db: Session, payment_method_data: Dict[str, Any]) -> VaultPaymentMethod:
        """Crear un nuevo método de pago desde datos de PayPal"""
        try:
            payment_method = VaultPaymentMethod(
                customer_id=payment_method_data['customer_id'],
                paypal_payment_token_id=payment_method_data['paypal_payment_token_id'],
                payment_source_type=payment_method_data['payment_source_type'],
                usage_type=payment_method_data.get('usage_type', 'MERCHANT'),
                customer_type=payment_method_data.get('customer_type', 'CONSUMER'),
                payer_id=payment_method_data.get('payer_id'),
                permit_multiple_tokens=payment_method_data.get('permit_multiple_tokens', False),
                status=payment_method_data.get('status', 'ACTIVE'),
                paypal_status=payment_method_data.get('paypal_status'),
                paypal_links=payment_method_data.get('paypal_links')
            )
            
            db.add(payment_method)
            db.commit()
            db.refresh(payment_method)
            
            logger.info("Método de pago creado exitosamente", 
                       payment_method_id=payment_method.id,
                       paypal_token_id=payment_method.paypal_payment_token_id)
            return payment_method
            
        except Exception as e:
            db.rollback()
            logger.error("Error creando método de pago", error=str(e), exc_info=True)
            raise

    @staticmethod
    def get_by_id(db: Session, payment_method_id: int) -> Optional[VaultPaymentMethod]:
        """Obtener método de pago por ID interno"""
        return db.query(VaultPaymentMethod).filter(
            VaultPaymentMethod.id == payment_method_id
        ).first()

    @staticmethod
    def get_by_paypal_token_id(db: Session, paypal_token_id: str) -> Optional[VaultPaymentMethod]:
        """Obtener método de pago por PayPal token ID"""
        return db.query(VaultPaymentMethod).filter(
            VaultPaymentMethod.paypal_payment_token_id == paypal_token_id
        ).first()

    @staticmethod
    def get_by_customer_id(
        db: Session, 
        customer_id: int,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[VaultPaymentMethod], int]:
        """Obtener métodos de pago de un cliente"""
        query = db.query(VaultPaymentMethod).filter(
            VaultPaymentMethod.customer_id == customer_id
        )
        
        if is_active:
            query = query.filter(VaultPaymentMethod.is_active == True)
        
        # Excluir métodos de pago eliminados (soft delete)
        query = query.filter(VaultPaymentMethod.deleted_at.is_(None))
        
        total = query.count()
        payment_methods = query.offset(skip).limit(limit).all()
        
        return payment_methods, total

    @staticmethod
    def get_active_by_customer_id(
        db: Session, 
        customer_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[VaultPaymentMethod], int]:
        """Obtener métodos de pago activos de un cliente"""
        return VaultPaymentMethodRepository.get_by_customer_id(
            db, customer_id, is_active=True, skip=skip, limit=limit
        )

    @staticmethod
    def list_payment_methods(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        payment_source_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[VaultPaymentMethod], int]:
        """Listar métodos de pago con filtros opcionales"""
        query = db.query(VaultPaymentMethod)
        
        if payment_source_type:
            query = query.filter(VaultPaymentMethod.payment_source_type == payment_source_type)
            
        if status:
            query = query.filter(VaultPaymentMethod.status == status)
        
        # Excluir métodos de pago eliminados
        query = query.filter(VaultPaymentMethod.deleted_at.is_(None))
        
        total = query.count()
        payment_methods = query.offset(skip).limit(limit).all()
        
        return payment_methods, total

    @staticmethod
    def update(
        db: Session, 
        payment_method_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[VaultPaymentMethod]:
        """Actualizar datos del método de pago"""
        try:
            payment_method = db.query(VaultPaymentMethod).filter(
                VaultPaymentMethod.id == payment_method_id
            ).first()
            
            if not payment_method:
                return None
                
            for key, value in update_data.items():
                if hasattr(payment_method, key) and key not in ['id', 'created_at']:
                    setattr(payment_method, key, value)
            
            db.commit()
            db.refresh(payment_method)
            
            logger.info("Método de pago actualizado exitosamente", 
                       payment_method_id=payment_method_id)
            return payment_method
            
        except Exception as e:
            db.rollback()
            logger.error("Error actualizando método de pago", 
                        payment_method_id=payment_method_id, 
                        error=str(e), exc_info=True)
            raise

    @staticmethod
    def update_status(
        db: Session, 
        payment_method_id: int, 
        status: str,
        paypal_status: Optional[str] = None
    ) -> Optional[VaultPaymentMethod]:
        """Actualizar estado del método de pago"""
        update_data = {'status': status}
        if paypal_status:
            update_data['paypal_status'] = paypal_status
            
        return VaultPaymentMethodRepository.update(db, payment_method_id, update_data)

    @staticmethod
    def soft_delete(db: Session, payment_method_id: int) -> bool:
        """Marcar método de pago como eliminado (soft delete)"""
        try:
            payment_method = db.query(VaultPaymentMethod).filter(
                VaultPaymentMethod.id == payment_method_id
            ).first()
            
            if not payment_method:
                return False
                
            payment_method.is_active = False
            payment_method.deleted_at = datetime.utcnow()
            db.commit()
            
            logger.info("Método de pago eliminado exitosamente", 
                       payment_method_id=payment_method_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error eliminando método de pago", 
                        payment_method_id=payment_method_id, 
                        error=str(e), exc_info=True)
            raise

    @staticmethod
    def delete(db: Session, payment_method_id: int) -> bool:
        """Eliminar método de pago permanentemente (usar con precaución)"""
        try:
            payment_method = db.query(VaultPaymentMethod).filter(
                VaultPaymentMethod.id == payment_method_id
            ).first()
            
            if not payment_method:
                return False
                
            db.delete(payment_method)
            db.commit()
            
            logger.info("Método de pago eliminado permanentemente", 
                       payment_method_id=payment_method_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error eliminando permanentemente método de pago", 
                        payment_method_id=payment_method_id, 
                        error=str(e), exc_info=True)
            raise

    @staticmethod
    def get_by_payer_id(db: Session, payer_id: str) -> List[VaultPaymentMethod]:
        """Obtener métodos de pago por payer ID"""
        return db.query(VaultPaymentMethod).filter(
            and_(
                VaultPaymentMethod.payer_id == payer_id,
                VaultPaymentMethod.deleted_at.is_(None)
            )
        ).all()
