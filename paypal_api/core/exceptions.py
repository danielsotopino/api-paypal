class DomainException(Exception):
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ClientNotFoundException(DomainException):
    def __init__(self, client_id: int):
        super().__init__(
            f"Cliente con ID {client_id} no encontrado",
            "CLIENT_NOT_FOUND"
        )


class UserNotFoundException(DomainException):
    def __init__(self, username: str):
        super().__init__(
            f"Usuario {username} no encontrado",
            "USER_NOT_FOUND"
        )


class PaymentNotFoundException(DomainException):
    def __init__(self, payment_id: str):
        super().__init__(
            f"Pago con ID {payment_id} no encontrado",
            "PAYMENT_NOT_FOUND"
        )


class SubscriptionNotFoundException(DomainException):
    def __init__(self, subscription_id: str):
        super().__init__(
            f"Suscripción con ID {subscription_id} no encontrada",
            "SUBSCRIPTION_NOT_FOUND"
        )


class PaymentRejectedException(DomainException):
    def __init__(self, response_code: str, message: str = None):
        default_message = f"Pago rechazado con código {response_code}"
        super().__init__(
            message or default_message,
            "PAYMENT_REJECTED"
        )


class InvalidAmountException(DomainException):
    def __init__(self, amount: float):
        super().__init__(
            f"Monto {amount} es inválido",
            "INVALID_AMOUNT"
        )


class PayPalCommunicationException(DomainException):
    def __init__(self, original_error: str):
        super().__init__(
            f"Error de comunicación con PayPal: {original_error}",
            "PAYPAL_COMMUNICATION_ERROR"
        )


class InvalidWebhookException(DomainException):
    def __init__(self, message: str = "Webhook inválido o no verificable"):
        super().__init__(
            message,
            "INVALID_WEBHOOK"
        )


class SubscriptionCancelledException(DomainException):
    def __init__(self, subscription_id: str):
        super().__init__(
            f"Suscripción {subscription_id} está cancelada",
            "SUBSCRIPTION_CANCELLED"
        )