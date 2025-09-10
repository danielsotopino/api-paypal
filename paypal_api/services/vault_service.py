from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from paypal_api.services.paypal.paypal_vault_service import PaypalVaultService
from paypal_api.services.customer_service import CustomerService
from paypal_api.repositories.vault_payment_method_repository import VaultPaymentMethodRepository
from paypal_api.models.customer import Customer
from paypal_api.models.vault_payment_method import VaultPaymentMethod
from paypal_api.schemas.paypal_schemas import VaultPaymentMethodRequest
from paypal_api.core.exceptions import PayPalCommunicationException
import structlog

logger = structlog.get_logger(__name__)


class VaultService:
    """
    Servicio de alto nivel que coordina operaciones entre PayPal Vault API y la base de datos local.
    
    Este servicio actúa como una capa de abstracción que:
    1. Coordina llamadas a PaypalVaultService (API de PayPal)
    2. Persiste datos en la base de datos local usando repositorios
    3. Mantiene sincronización entre PayPal y nuestra DB
    4. Proporciona una interfaz unificada para operaciones de Vault
    """

    def __init__(self):
        self.paypal_vault_service = PaypalVaultService()
        self.customer_service = CustomerService()
        self.payment_method_repo = VaultPaymentMethodRepository()

    # =============================================================================
    # GESTIÓN DE CLIENTES
    # =============================================================================

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
        Crear un cliente o obtenerlo si ya existe (delega a CustomerService)
        """
        return self.customer_service.create_or_get_customer(
            db=db,
            paypal_customer_id=paypal_customer_id,
            email_address=email_address,
            given_name=given_name,
            surname=surname,
            phone_number=phone_number,
            default_shipping_address=default_shipping_address
        )

    def get_customer_by_paypal_id(self, db: Session, paypal_customer_id: str) -> Optional[Customer]:
        """Obtener cliente por PayPal customer ID (delega a CustomerService)"""
        return self.customer_service.get_customer_by_paypal_id(db, paypal_customer_id)

    def get_customer_by_email(self, db: Session, email: str) -> Optional[Customer]:
        """Obtener cliente por email (delega a CustomerService)"""
        return self.customer_service.get_customer_by_email(db, email)

    def list_customers(
        self, 
        db: Session,
        skip: int = 0,
        limit: int = 100,
        email_filter: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Customer], int]:
        """Listar clientes con paginación y filtros (delega a CustomerService)"""
        return self.customer_service.list_customers(
            db, skip=skip, limit=limit, email_filter=email_filter, is_active=is_active
        )

    # =============================================================================
    # GESTIÓN DE SETUP TOKENS
    # =============================================================================

    def create_setup_token(
        self,
        customer_id: Optional[str] = None,
        merchant_customer_id: Optional[str] = None,
        paypal_request_id: Optional[str] = None,
        usage_type: Optional[str] = None,
        usage_pattern: Optional[str] = None,
        billing_plan_price_value: Optional[str] = None,
        billing_plan_frequency_interval_count: Optional[str] = None,
        billing_plan_start_date: Optional[str] = None,
        billing_plan_one_time_charges_product_price_value: Optional[str] = None,
        billing_plan_one_time_charges_total_amount_value: Optional[str] = None,
        product_description: Optional[str] = None,
        name: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crear un Setup Token para almacenar temporalmente un método de pago
        (Delega completamente a PaypalVaultService)
        """
        return self.paypal_vault_service.create_setup_token(
            customer_id=customer_id,
            merchant_customer_id=merchant_customer_id,
            paypal_request_id=paypal_request_id,
            usage_type=usage_type,
            usage_pattern=usage_pattern,
            billing_plan_price_value=billing_plan_price_value,
            billing_plan_frequency_interval_count=billing_plan_frequency_interval_count,
            billing_plan_start_date=billing_plan_start_date,
            billing_plan_one_time_charges_product_price_value=billing_plan_one_time_charges_product_price_value,
            billing_plan_one_time_charges_total_amount_value=billing_plan_one_time_charges_total_amount_value,
            product_description=product_description,
            name=name,
            return_url=return_url,
            cancel_url=cancel_url
        )

    def get_setup_token(self, setup_token_id: str) -> Dict[str, Any]:
        """
        Obtener información de un Setup Token
        (Delega completamente a PaypalVaultService)
        """
        return self.paypal_vault_service.get_setup_token(setup_token_id)

    # =============================================================================
    # GESTIÓN DE PAYMENT TOKENS
    # =============================================================================

    def create_payment_token_and_store(
        self,
        db: Session,
        vault_payment_method_request: VaultPaymentMethodRequest
    ) -> Tuple[VaultPaymentMethod, Dict[str, Any]]:
        """
        Crear un Payment Token en PayPal y almacenarlo en la base de datos
        
        Returns:
            Tuple[VaultPaymentMethod, Dict[str, Any]]: El registro en DB y la respuesta de PayPal
        """
        try:
            # 1. Crear el payment token en PayPal
            paypal_response = self.paypal_vault_service.create_payment_token(vault_payment_method_request)
            
            # 2. Extraer información del cliente de la respuesta
            customer_info = paypal_response.get('customer', {})
            payment_source = paypal_response.get('payment_source', {})
            paypal_info = payment_source.get('paypal', {}) if payment_source else {}
            
            # 3. Crear o obtener el cliente en nuestra DB
            customer = self.create_or_get_customer(
                db=db,
                paypal_customer_id=customer_info.get('id', vault_payment_method_request.payerID),
                email_address=paypal_info.get('email_address', ''),
                given_name=paypal_info.get('name', {}).get('given_name'),
                surname=paypal_info.get('name', {}).get('surname')
            )

            # 4. Almacenar el payment method en nuestra DB
            payment_method_data = {
                'customer_id': customer.id,
                'paypal_payment_token_id': paypal_response.get('id'),
                'payment_source_type': 'paypal',  # Por ahora solo PayPal
                'usage_type': paypal_info.get('usage_type', 'MERCHANT'),
                'customer_type': paypal_info.get('customer_type', 'CONSUMER'),
                'payer_id': paypal_info.get('payer_id'),
                'permit_multiple_tokens': paypal_info.get('permit_multiple_payment_tokens', False),
                'status': 'ACTIVE',
                'paypal_status': paypal_response.get('status'),
                'paypal_links': paypal_response.get('links', [])
            }

            payment_method = self.payment_method_repo.get_or_create(db, payment_method_data)
            
            logger.info("Payment token creado y almacenado exitosamente",
                       payment_method_id=payment_method.id,
                       paypal_token_id=payment_method.paypal_payment_token_id,
                       customer_id=customer.id)

            return payment_method, paypal_response

        except Exception as e:
            logger.error("Error creando y almacenando payment token", 
                        error=str(e), exc_info=True)
            raise

    def get_payment_token(
        self, 
        db: Session, 
        payment_token_id: str,
        sync_with_paypal: bool = False
    ) -> Optional[VaultPaymentMethod]:
        """
        Obtener un Payment Token desde la DB, con opción de sincronizar con PayPal
        """
        try:
            # Obtener desde DB
            payment_method = self.payment_method_repo.get_by_paypal_token_id(db, payment_token_id)
            
            if not payment_method:
                logger.warning("Payment token no encontrado en DB", token_id=payment_token_id)
                return None

            # Sincronizar con PayPal si se solicita
            if sync_with_paypal:
                try:
                    paypal_response = self.paypal_vault_service.get_payment_token(payment_token_id)
                    
                    # Actualizar estado si hay diferencias
                    paypal_status = paypal_response.get('status')
                    if paypal_status and paypal_status != payment_method.paypal_status:
                        self.payment_method_repo.update(db, payment_method.id, {
                            'paypal_status': paypal_status,
                            'paypal_links': paypal_response.get('links', [])
                        })
                        logger.info("Payment token sincronizado con PayPal", 
                                   token_id=payment_token_id,
                                   new_status=paypal_status)
                        
                except PayPalCommunicationException as e:
                    logger.warning("Error sincronizando con PayPal, usando datos locales", 
                                 token_id=payment_token_id, error=str(e))

            return payment_method

        except Exception as e:
            logger.error("Error obteniendo payment token", 
                        token_id=payment_token_id, error=str(e), exc_info=True)
            raise
    
    def get_payment_tokens_by_customer_id(
        self,
        db: Session,
        customer_id: int,
        sync_with_paypal: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> list[VaultPaymentMethod]:
        """
        Obtener Payment Tokens de un cliente por customer_id, con opción de sincronizar con PayPal
        """
        try:
            payment_methods, _ = self.payment_method_repo.get_active_by_customer_id(
                db, customer_id, skip=skip, limit=limit
            )

            if sync_with_paypal:
                for payment_method in payment_methods:
                    try:
                        paypal_response = self.paypal_vault_service.get_payment_token(
                            payment_method.paypal_payment_token_id
                        )
                        paypal_status = paypal_response.get('status')
                        if paypal_status and paypal_status != payment_method.paypal_status:
                            self.payment_method_repo.update(db, payment_method.id, {
                                'paypal_status': paypal_status,
                                'paypal_links': paypal_response.get('links', [])
                            })
                            logger.info(
                                "Payment token sincronizado con PayPal",
                                token_id=payment_method.paypal_payment_token_id,
                                new_status=paypal_status
                            )
                    except PayPalCommunicationException as e:
                        logger.warning(
                            "Error sincronizando con PayPal, usando datos locales",
                            token_id=payment_method.paypal_payment_token_id,
                            error=str(e)
                        )
            return payment_methods

        except Exception as e:
            logger.error(
                "Error obteniendo payment tokens por customer_id",
                customer_id=customer_id,
                error=str(e),
                exc_info=True
            )
            raise

    def delete_payment_token(self, db: Session, payment_token_id: str) -> bool:
        """
        Eliminar un Payment Token de PayPal y marcarlo como eliminado en DB
        """
        try:
            # 1. Obtener el payment method de la DB
            payment_method = self.payment_method_repo.get_by_paypal_token_id(db, payment_token_id)
            
            if not payment_method:
                logger.warning("Payment token no encontrado en DB para eliminar", 
                             token_id=payment_token_id)
                return False

            # 2. Eliminar de PayPal
            paypal_success = self.paypal_vault_service.delete_payment_token(payment_token_id)
            
            if paypal_success:
                # 3. Marcar como eliminado en nuestra DB
                db_success = self.payment_method_repo.soft_delete(db, payment_method.id)
                
                logger.info("Payment token eliminado exitosamente", 
                           token_id=payment_token_id,
                           payment_method_id=payment_method.id)
                return db_success
            else:
                logger.error("Error eliminando payment token de PayPal", 
                           token_id=payment_token_id)
                return False

        except Exception as e:
            logger.error("Error eliminando payment token", 
                        token_id=payment_token_id, error=str(e), exc_info=True)
            raise

    def list_customer_payment_tokens(
        self,
        db: Session,
        customer_id: str,
        page_size: int = 5,
        page: int = 1,
        total_required: bool = False,
        use_local_db: bool = True
    ) -> Dict[str, Any]:
        """
        Listar Payment Tokens de un cliente desde DB local o PayPal
        """
        try:
            if use_local_db:
                # Buscar cliente por PayPal customer ID
                customer = self.customer_service.get_customer_by_id(db, customer_id)
                
                if not customer:
                    logger.warning("Cliente no encontrado en DB", customer_id=customer_id)
                    return {
                        "payment_tokens": [],
                        "total_items": 0,
                        "page": page,
                        "page_size": page_size
                    }

                # Calcular offset
                skip = (page - 1) * page_size
                
                # Obtener payment methods activos
                payment_methods, total = self.payment_method_repo.get_active_by_customer_id(
                    db, customer.id, skip=skip, limit=page_size
                )

                # Convertir a formato de respuesta
                payment_tokens = []
                for pm in payment_methods:
                    payment_tokens.append({
                        "id": pm.paypal_payment_token_id,
                        "customer_id": customer.paypal_customer_id,
                        "payment_source_type": pm.payment_source_type,
                        "is_active": pm.paypal_status or pm.is_active,
                        "create_time": pm.created_at.isoformat() if pm.created_at else None,
                        "update_time": pm.updated_at.isoformat() if pm.updated_at else None
                    })

                result = {
                    "payment_tokens": payment_tokens,
                    "page": page,
                    "page_size": page_size
                }
                
                if total_required:
                    result["total_items"] = total

                logger.info("Payment tokens listados desde DB", 
                           customer_id=customer_id, 
                           total_tokens=len(payment_tokens))
                return result

            else:
                # Usar PayPal API directamente
                return self.paypal_vault_service.list_customer_payment_tokens(
                    customer_id=customer_id,
                    page_size=page_size,
                    page=page,
                    total_required=total_required
                )

        except Exception as e:
            logger.error("Error listando payment tokens del cliente", 
                        customer_id=customer_id, error=str(e), exc_info=True)
            raise

    # =============================================================================
    # OPERACIONES DE SINCRONIZACIÓN
    # =============================================================================

    def sync_payment_token_with_paypal(self, db: Session, payment_token_id: str) -> Optional[VaultPaymentMethod]:
        """
        Sincronizar un Payment Token específico con PayPal
        """
        return self.get_payment_token(db, payment_token_id, sync_with_paypal=True)

    def sync_customer_payment_tokens(self, db: Session, customer_id: str) -> Dict[str, Any]:
        """
        Sincronizar todos los Payment Tokens de un cliente con PayPal
        """
        try:
            # Obtener tokens desde PayPal
            paypal_tokens = self.paypal_vault_service.list_customer_payment_tokens(
                customer_id=customer_id,
                page_size=50,  # Aumentar para obtener más tokens
                total_required=True
            )

            # Obtener customer desde DB
            customer = self.customer_service.get_customer_by_paypal_id(db, customer_id)
            if not customer:
                logger.warning("Cliente no encontrado para sincronización", customer_id=customer_id)
                return {"synchronized": 0, "errors": 1}

            synchronized_count = 0
            error_count = 0

            for token_data in paypal_tokens.get('payment_tokens', []):
                try:
                    token_id = token_data.get('id')
                    if not token_id:
                        continue

                    # Buscar en DB local
                    local_payment_method = self.payment_method_repo.get_by_paypal_token_id(db, token_id)
                    
                    if local_payment_method:
                        # Actualizar datos existentes
                        update_data = {
                            'paypal_status': token_data.get('status'),
                            'paypal_links': token_data.get('links', [])
                        }
                        self.payment_method_repo.update(db, local_payment_method.id, update_data)
                    else:
                        # Crear nuevo registro si no existe
                        payment_method_data = {
                            'customer_id': customer.id,
                            'paypal_payment_token_id': token_id,
                            'payment_source_type': 'paypal',
                            'status': 'ACTIVE',
                            'paypal_status': token_data.get('status'),
                            'paypal_links': token_data.get('links', [])
                        }
                        self.payment_method_repo.create(db, payment_method_data)

                    synchronized_count += 1

                except Exception as e:
                    logger.error("Error sincronizando token individual", 
                               token_id=token_data.get('id'), error=str(e), exc_info=True)
                    error_count += 1

            logger.info("Sincronización de customer completada",
                       customer_id=customer_id,
                       synchronized=synchronized_count,
                       errors=error_count)

            return {
                "synchronized": synchronized_count,
                "errors": error_count,
                "total_paypal_tokens": len(paypal_tokens.get('payment_tokens', []))
            }

        except Exception as e:
            logger.error("Error sincronizando payment tokens del cliente",
                        customer_id=customer_id, error=str(e), exc_info=True)
            raise