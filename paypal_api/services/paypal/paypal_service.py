from typing import Optional, Dict, Any
import paypalrestsdk
from paypal_api.config import settings
from paypal_api.core.exceptions import PayPalCommunicationException
import structlog

logger = structlog.get_logger(__name__)


class PayPalService:
    def __init__(self):
        """
        Inicializa el servicio de PayPal con las credenciales configuradas
        """
        self.api = paypalrestsdk.configure({
            'mode': settings.PAYPAL_MODE,
            'client_id': settings.PAYPAL_CLIENT_ID,
            'client_secret': settings.PAYPAL_CLIENT_SECRET
        })
    
    def create_payment(
        self, 
        amount: float, 
        currency: str, 
        description: str,
        return_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """
        Crea un pago en PayPal
        """
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": return_url,
                    "cancel_url": cancel_url
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": description,
                            "sku": "item",
                            "price": str(amount),
                            "currency": currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }]
            })
            
            if payment.create():
                logger.info(f"Pago creado exitosamente: {payment.id}")
                return payment.to_dict()
            else:
                logger.error(f"Error creando pago: {payment.error}")
                raise PayPalCommunicationException(str(payment.error))
                
        except Exception as e:
            logger.error(f"Error en comunicación con PayPal: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un pago
        """
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            return payment.to_dict()
        except Exception as e:
            logger.error(f"Error obteniendo pago {payment_id}: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def execute_payment(self, payment_id: str, payer_id: str) -> Dict[str, Any]:
        """
        Ejecuta un pago aprobado
        """
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                logger.info(f"Pago ejecutado exitosamente: {payment_id}")
                return payment.to_dict()
            else:
                logger.error(f"Error ejecutando pago: {payment.error}")
                raise PayPalCommunicationException(str(payment.error))
                
        except Exception as e:
            logger.error(f"Error ejecutando pago {payment_id}: {str(e)}")
            raise PayPalCommunicationException(str(e))
    
    def create_payment_with_vault_token(
        self,
        payment_token_id: str,
        amount: float,
        currency: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Crea un pago usando un token almacenado en el Vault
        """
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "credit_card",
                    "funding_instruments": [{
                        "credit_card_token": {
                            "credit_card_id": payment_token_id
                        }
                    }]
                },
                "transactions": [{
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }]
            })
            
            if payment.create():
                logger.info(f"Pago con vault token creado exitosamente: {payment.id}")
                return payment.to_dict()
            else:
                logger.error(f"Error creando pago con vault token: {payment.error}")
                raise PayPalCommunicationException(str(payment.error))
                
        except Exception as e:
            logger.error(f"Error en comunicación con PayPal (vault payment): {str(e)}")
            raise PayPalCommunicationException(str(e))