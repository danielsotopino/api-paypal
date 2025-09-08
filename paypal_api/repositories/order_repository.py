from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from paypal_api.models.order import Order
import structlog

logger = structlog.get_logger(__name__)


class OrderRepository:
    """Repositorio para operaciones con Order"""

    @staticmethod
    def create(db: Session, order_data: Dict[str, Any]) -> Order:
        """Crear una nueva orden desde datos de PayPal"""
        try:
            order = Order(
                paypal_order_id=order_data['paypal_order_id'],
                customer_id=order_data.get('customer_id'),
                payer_id=order_data.get('payer_id'),
                payer_email=order_data.get('payer_email'),
                intent=order_data.get('intent', 'CAPTURE'),
                status=order_data['status'],
                amount=order_data['amount'],
                currency=order_data.get('currency', 'USD'),
                description=order_data.get('description'),
                reference_id=order_data.get('reference_id'),
                return_url=order_data.get('return_url'),
                cancel_url=order_data.get('cancel_url'),
                paypal_response=order_data.get('paypal_response'),
                approval_url=order_data.get('approval_url'),
                approved_at=order_data.get('approved_at'),
                is_active=order_data.get('is_active', True)
            )
            
            db.add(order)
            db.commit()
            db.refresh(order)
            
            logger.info("Orden creada exitosamente", 
                       order_id=order.id,
                       paypal_order_id=order.paypal_order_id)
            return order
            
        except Exception as e:
            db.rollback()
            logger.error("Error creando orden", error=str(e), exc_info=True)
            raise

    @staticmethod
    def get_by_id(db: Session, order_id: int) -> Optional[Order]:
        """Obtener orden por ID interno"""
        return db.query(Order).filter(Order.id == order_id).first()

    @staticmethod
    def get_by_paypal_order_id(db: Session, paypal_order_id: str) -> Optional[Order]:
        """Obtener orden por PayPal order ID"""
        return db.query(Order).filter(Order.paypal_order_id == paypal_order_id).first()

    @staticmethod
    def get_by_reference_id(db: Session, reference_id: str) -> Optional[Order]:
        """Obtener orden por reference ID del comerciante"""
        return db.query(Order).filter(Order.reference_id == reference_id).first()

    @staticmethod
    def list_orders(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        customer_id: Optional[int] = None,
        payer_id: Optional[str] = None,
        status: Optional[str] = None,
        intent: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Order], int]:
        """Listar órdenes con paginación y filtros opcionales"""
        query = db.query(Order).order_by(desc(Order.created_at))
        
        if customer_id is not None:
            query = query.filter(Order.customer_id == customer_id)
            
        if payer_id:
            query = query.filter(Order.payer_id == payer_id)
            
        if status:
            query = query.filter(Order.status == status)
            
        if intent:
            query = query.filter(Order.intent == intent)
            
        if is_active is not None:
            query = query.filter(Order.is_active == is_active)
        
        total = query.count()
        orders = query.offset(skip).limit(limit).all()
        
        return orders, total

    @staticmethod
    def get_customer_orders(
        db: Session,
        customer_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> tuple[List[Order], int]:
        """Obtener órdenes de un cliente específico"""
        return OrderRepository.list_orders(
            db=db,
            skip=skip,
            limit=limit,
            customer_id=customer_id,
            status=status,
            is_active=True
        )

    @staticmethod
    def update(db: Session, order_id: int, update_data: Dict[str, Any]) -> Optional[Order]:
        """Actualizar datos de la orden"""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return None
                
            for key, value in update_data.items():
                if hasattr(order, key) and key not in ['id', 'paypal_order_id']:  # No permitir cambiar ID o PayPal order ID
                    setattr(order, key, value)
            
            db.commit()
            db.refresh(order)
            
            logger.info("Orden actualizada exitosamente", order_id=order_id)
            return order
            
        except Exception as e:
            db.rollback()
            logger.error("Error actualizando orden", order_id=order_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def update_by_paypal_id(db: Session, paypal_order_id: str, update_data: Dict[str, Any]) -> Optional[Order]:
        """Actualizar orden por PayPal order ID"""
        try:
            order = db.query(Order).filter(Order.paypal_order_id == paypal_order_id).first()
            if not order:
                return None
                
            for key, value in update_data.items():
                if hasattr(order, key) and key not in ['id', 'paypal_order_id']:
                    setattr(order, key, value)
            
            db.commit()
            db.refresh(order)
            
            logger.info("Orden actualizada exitosamente", paypal_order_id=paypal_order_id)
            return order
            
        except Exception as e:
            db.rollback()
            logger.error("Error actualizando orden", paypal_order_id=paypal_order_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def soft_delete(db: Session, order_id: int) -> bool:
        """Desactivar orden (soft delete)"""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False
                
            order.is_active = False
            db.commit()
            
            logger.info("Orden desactivada exitosamente", order_id=order_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error desactivando orden", order_id=order_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def delete(db: Session, order_id: int) -> bool:
        """Eliminar orden permanentemente (usar con precaución)"""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return False
                
            db.delete(order)
            db.commit()
            
            logger.info("Orden eliminada permanentemente", order_id=order_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Error eliminando orden", order_id=order_id, error=str(e), exc_info=True)
            raise

    @staticmethod
    def get_orders_by_status_count(db: Session) -> Dict[str, int]:
        """Obtener conteo de órdenes por status"""
        try:
            from sqlalchemy import func
            results = db.query(
                Order.status,
                func.count(Order.id).label('count')
            ).filter(Order.is_active == True).group_by(Order.status).all()
            
            return {result.status: result.count for result in results}
            
        except Exception as e:
            logger.error("Error obteniendo conteo de órdenes por status", error=str(e), exc_info=True)
            raise
