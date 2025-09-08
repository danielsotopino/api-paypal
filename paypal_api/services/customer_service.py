from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from paypal_api.repositories.customer_repository import CustomerRepository
from paypal_api.models.customer import Customer
import structlog

logger = structlog.get_logger(__name__)


class CustomerService:
    """
    Servicio para gestión de clientes
    
    Este servicio se encarga de:
    1. Operaciones CRUD de clientes
    2. Validaciones de negocio relacionadas con clientes
    3. Lógica de creación/actualización desde datos de PayPal
    4. Búsquedas y filtros de clientes
    """

    def __init__(self):
        self.customer_repo = CustomerRepository()

    def create_or_get_customer(
        self, 
        db: Session,
        paypal_customer_id: str,
        email_address: str,
        given_name: Optional[str] = None,
        surname: Optional[str] = None,
        phone_number: Optional[str] = None,
        default_shipping_address: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """
        Crear un cliente o obtenerlo si ya existe
        
        Args:
            db: Sesión de base de datos
            paypal_customer_id: ID del cliente en PayPal
            email_address: Email del cliente (requerido)
            given_name: Nombre del cliente
            surname: Apellido del cliente
            phone_number: Teléfono del cliente
            default_shipping_address: Dirección de envío por defecto
            
        Returns:
            Customer: El cliente creado o existente
            
        Raises:
            Exception: Si hay error en la creación o búsqueda
        """
        try:
            # Buscar cliente existente por PayPal customer ID
            existing_customer = self.customer_repo.get_by_paypal_customer_id(
                db, paypal_customer_id
            )
            
            if existing_customer:
                logger.info("Cliente ya existe", 
                           customer_id=existing_customer.id,
                           paypal_customer_id=paypal_customer_id)
                
                # Actualizar información si es necesaria
                updated = self._update_customer_if_needed(
                    db, existing_customer, email_address, given_name, 
                    surname, phone_number, default_shipping_address
                )
                
                return updated if updated else existing_customer

            # Si no existe, crear nuevo cliente
            customer_data = {
                'paypal_customer_id': paypal_customer_id,
                'email_address': email_address,
                'given_name': given_name,
                'surname': surname,
                'phone_number': phone_number,
                'default_shipping_address': default_shipping_address
            }

            customer = self.customer_repo.create(db, customer_data)
            logger.info("Nuevo cliente creado", 
                       customer_id=customer.id,
                       paypal_customer_id=paypal_customer_id)
            
            return customer

        except Exception as e:
            logger.error("Error creando o obteniendo cliente", 
                        paypal_customer_id=paypal_customer_id, 
                        error=str(e), exc_info=True)
            raise

    def get_customer_by_id(self, db: Session, customer_id: int) -> Optional[Customer]:
        """Obtener cliente por ID interno"""
        return self.customer_repo.get_by_id(db, customer_id)

    def get_customer_by_paypal_id(self, db: Session, paypal_customer_id: str) -> Optional[Customer]:
        """Obtener cliente por PayPal customer ID"""
        return self.customer_repo.get_by_paypal_customer_id(db, paypal_customer_id)

    def get_customer_by_email(self, db: Session, email: str) -> Optional[Customer]:
        """Obtener cliente por email"""
        return self.customer_repo.get_by_email(db, email)

    def list_customers(
        self, 
        db: Session,
        skip: int = 0,
        limit: int = 100,
        email_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Customer], int]:
        """
        Listar clientes con paginación y filtros
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Límite de registros a retornar
            email_filter: Filtro por email (búsqueda parcial)
            is_active: Filtro por estado activo
            
        Returns:
            Tuple[List[Customer], int]: Lista de clientes y total de registros
        """
        return self.customer_repo.list_customers(
            db, skip=skip, limit=limit, email_filter=email_filter, is_active=is_active
        )

    def update_customer(
        self, 
        db: Session, 
        customer_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[Customer]:
        """
        Actualizar información del cliente
        
        Args:
            db: Sesión de base de datos
            customer_id: ID interno del cliente
            update_data: Datos a actualizar
            
        Returns:
            Customer: Cliente actualizado o None si no se encontró
        """
        try:
            # Validar datos antes de actualizar
            validated_data = self._validate_customer_update_data(update_data)
            
            customer = self.customer_repo.update(db, customer_id, validated_data)
            
            if customer:
                logger.info("Cliente actualizado exitosamente", 
                           customer_id=customer_id,
                           updated_fields=list(validated_data.keys()))
            
            return customer
            
        except Exception as e:
            logger.error("Error actualizando cliente", 
                        customer_id=customer_id, 
                        error=str(e), exc_info=True)
            raise

    def update_customer_by_paypal_id(
        self, 
        db: Session, 
        paypal_customer_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[Customer]:
        """
        Actualizar cliente por PayPal customer ID
        
        Args:
            db: Sesión de base de datos
            paypal_customer_id: PayPal customer ID
            update_data: Datos a actualizar
            
        Returns:
            Customer: Cliente actualizado o None si no se encontró
        """
        customer = self.get_customer_by_paypal_id(db, paypal_customer_id)
        if not customer:
            logger.warning("Cliente no encontrado para actualizar", 
                          paypal_customer_id=paypal_customer_id)
            return None
            
        return self.update_customer(db, customer.id, update_data)

    def deactivate_customer(self, db: Session, customer_id: int) -> bool:
        """
        Desactivar cliente (soft delete)
        
        Args:
            db: Sesión de base de datos
            customer_id: ID interno del cliente
            
        Returns:
            bool: True si se desactivó exitosamente
        """
        try:
            success = self.customer_repo.soft_delete(db, customer_id)
            
            if success:
                logger.info("Cliente desactivado exitosamente", customer_id=customer_id)
            else:
                logger.warning("Cliente no encontrado para desactivar", customer_id=customer_id)
                
            return success
            
        except Exception as e:
            logger.error("Error desactivando cliente", 
                        customer_id=customer_id, 
                        error=str(e), exc_info=True)
            raise

    def activate_customer(self, db: Session, customer_id: int) -> bool:
        """
        Reactivar cliente
        
        Args:
            db: Sesión de base de datos
            customer_id: ID interno del cliente
            
        Returns:
            bool: True si se reactivó exitosamente
        """
        try:
            customer = self.customer_repo.update(db, customer_id, {'is_active': True})
            
            if customer:
                logger.info("Cliente reactivado exitosamente", customer_id=customer_id)
                return True
            else:
                logger.warning("Cliente no encontrado para reactivar", customer_id=customer_id)
                return False
                
        except Exception as e:
            logger.error("Error reactivando cliente", 
                        customer_id=customer_id, 
                        error=str(e), exc_info=True)
            raise

    def search_customers(
        self, 
        db: Session,
        search_term: str,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Customer], int]:
        """
        Buscar clientes por término de búsqueda (email, nombre, apellido)
        
        Args:
            db: Sesión de base de datos
            search_term: Término de búsqueda
            skip: Número de registros a saltar
            limit: Límite de registros a retornar
            
        Returns:
            Tuple[List[Customer], int]: Lista de clientes y total de registros
        """
        # Por ahora usa el filtro de email, pero se puede extender
        return self.customer_repo.list_customers(
            db, skip=skip, limit=limit, email_filter=search_term, is_active=True
        )

    def get_customer_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Obtener estadísticas de clientes
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            Dict[str, Any]: Estadísticas de clientes
        """
        try:
            # Obtener totales
            all_customers, total_customers = self.customer_repo.list_customers(db, limit=1)
            active_customers, total_active = self.customer_repo.list_customers(
                db, is_active=True, limit=1
            )
            inactive_customers, total_inactive = self.customer_repo.list_customers(
                db, is_active=False, limit=1
            )

            stats = {
                'total_customers': total_customers,
                'active_customers': total_active,
                'inactive_customers': total_inactive,
                'activation_rate': round((total_active / total_customers * 100), 2) if total_customers > 0 else 0
            }

            logger.info("Estadísticas de clientes generadas", **stats)
            return stats

        except Exception as e:
            logger.error("Error generando estadísticas de clientes", 
                        error=str(e), exc_info=True)
            raise

    # =============================================================================
    # MÉTODOS PRIVADOS
    # =============================================================================

    def _update_customer_if_needed(
        self,
        db: Session,
        customer: Customer,
        email_address: str,
        given_name: Optional[str] = None,
        surname: Optional[str] = None,
        phone_number: Optional[str] = None,
        default_shipping_address: Optional[Dict[str, Any]] = None
    ) -> Optional[Customer]:
        """
        Actualizar cliente existente si hay cambios en los datos
        """
        update_data = {}
        
        # Verificar cambios en los campos
        if email_address and email_address != customer.email_address:
            update_data['email_address'] = email_address
            
        if given_name and given_name != customer.given_name:
            update_data['given_name'] = given_name
            
        if surname and surname != customer.surname:
            update_data['surname'] = surname
            
        if phone_number and phone_number != customer.phone_number:
            update_data['phone_number'] = phone_number
            
        if default_shipping_address and default_shipping_address != customer.default_shipping_address:
            update_data['default_shipping_address'] = default_shipping_address

        # Solo actualizar si hay cambios
        if update_data:
            logger.info("Actualizando información del cliente existente", 
                       customer_id=customer.id,
                       changes=list(update_data.keys()))
            return self.customer_repo.update(db, customer.id, update_data)
        
        return None

    def _validate_customer_update_data(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar y limpiar datos de actualización de cliente
        """
        validated_data = {}
        
        # Campos permitidos para actualización
        allowed_fields = {
            'email_address', 'given_name', 'surname', 'phone_number', 
            'default_shipping_address', 'is_active'
        }
        
        for key, value in update_data.items():
            if key in allowed_fields:
                # Validaciones específicas
                if key == 'email_address' and value:
                    if '@' not in str(value):
                        raise ValueError(f"Email inválido: {value}")
                        
                validated_data[key] = value
            else:
                logger.warning("Campo no permitido para actualización ignorado", 
                             field=key, value=value)
        
        return validated_data
