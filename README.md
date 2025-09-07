# PayPal API

API REST para integración con PayPal, permitiendo pagos y suscripciones mediante servicios de PayPal.

## Características

- ✅ Integración con PayPal SDK
- ✅ Manejo de pagos únicos
- ✅ Manejo de suscripciones
- ✅ Webhooks para notificaciones
- ✅ **PayPal Vault API** - Almacenamiento seguro de métodos de pago
- ✅ Setup Tokens para validación temporal de métodos de pago
- ✅ Payment Tokens permanentes para pagos recurrentes
- ✅ Pagos con métodos almacenados (sin re-introducir datos)
- ✅ Logging estructurado
- ✅ Manejo de excepciones personalizado
- ✅ Middleware de correlación de requests
- ✅ Documentación automática con FastAPI

## Estructura del Proyecto

```
paypal_api/
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── payments.py      # Endpoints de pagos
│       │   ├── subscriptions.py # Endpoints de suscripciones
│       │   ├── webhooks.py      # Endpoints de webhooks
│       │   └── vault.py         # Endpoints de PayPal Vault
│       └── router.py            # Router principal de la API
├── core/
│   ├── exceptions.py            # Excepciones personalizadas
│   ├── exception_handlers.py    # Manejadores de excepciones
│   ├── logging_config.py        # Configuración de logging
│   ├── logging_middleware.py    # Middleware de logging
│   └── middleware.py            # Middlewares personalizados
├── models/                      # Modelos de base de datos
├── schemas/                     # Schemas de Pydantic
│   ├── paypal_schemas.py        # Schemas específicos de PayPal
│   └── response_models.py       # Modelos de respuesta estándar
├── services/
│   ├── paypal_service.py        # Servicio de PayPal
│   └── vault_service.py         # Servicio de PayPal Vault
├── repositories/                # Repositorios de datos
├── utils/                       # Utilidades
├── config.py                    # Configuración de la aplicación
└── main.py                      # Aplicación principal FastAPI
```

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso de PayPal Vault API

La API de Vault permite almacenar métodos de pago de forma segura para uso futuro, ideal para:
- Suscripciones y pagos recurrentes
- Checkout express (sin re-introducir datos de tarjeta)
- Almacenamiento seguro de métodos de pago

### Flujo básico

1. **Crear Setup Token** (opcional): Para validar temporalmente un método de pago
2. **Crear Payment Token**: Almacenar permanentemente el método de pago
3. **Usar Payment Token**: Realizar pagos con métodos almacenados

### Ejemplos de uso

#### 1. Crear Setup Token (validación temporal)

```bash
curl -X POST "http://localhost:8000/api/v1/vault/setup-tokens" \
  -H "Content-Type: application/json" \
  -H "PayPal-Client-Id: YOUR_CLIENT_ID" \
  -H "PayPal-Client-Secret: YOUR_CLIENT_SECRET" \
  -d '{
    "payer_id": "customer_123",
    "type": "credit_card",
    "credit_card": {
      "type": "visa",
      "number": "4111111111111111",
      "expire_month": 12,
      "expire_year": 2025,
      "cvv2": "123",
      "first_name": "Juan",
      "last_name": "Pérez"
    }
  }'
```

#### 2. Crear Payment Token (almacenamiento permanente)

```bash
curl -X POST "http://localhost:8000/api/v1/vault/payment-tokens" \
  -H "Content-Type: application/json" \
  -H "PayPal-Client-Id: YOUR_CLIENT_ID" \
  -H "PayPal-Client-Secret: YOUR_CLIENT_SECRET" \
  -d '{
    "payer_id": "customer_123",
    "type": "credit_card",
    "credit_card": {
      "type": "visa",
      "number": "4111111111111111",
      "expire_month": 12,
      "expire_year": 2025,
      "cvv2": "123",
      "first_name": "Juan",
      "last_name": "Pérez"
    }
  }'
```

#### 3. Crear pago con Payment Token

```bash
curl -X POST "http://localhost:8000/api/v1/vault/payments/with-token" \
  -H "Content-Type: application/json" \
  -H "PayPal-Client-Id: YOUR_CLIENT_ID" \
  -H "PayPal-Client-Secret: YOUR_CLIENT_SECRET" \
  -d '{
    "payment_method_id": "CARD-1AB23456CD789012E",
    "amount": 29.99,
    "currency": "USD",
    "description": "Pago con método almacenado"
  }'
```

#### 4. Listar Payment Tokens de un cliente

```bash
curl -X GET "http://localhost:8000/api/v1/vault/customers/customer_123/payment-tokens?page_size=5&page=1" \
  -H "PayPal-Client-Id: YOUR_CLIENT_ID" \
  -H "PayPal-Client-Secret: YOUR_CLIENT_SECRET"
```

### Endpoints disponibles

- `POST /api/v1/vault/setup-tokens` - Crear Setup Token
- `GET /api/v1/vault/setup-tokens/{id}` - Obtener Setup Token
- `POST /api/v1/vault/payment-tokens` - Crear Payment Token
- `GET /api/v1/vault/payment-tokens/{id}` - Obtener Payment Token
- `DELETE /api/v1/vault/payment-tokens/{id}` - Eliminar Payment Token
- `GET /api/v1/vault/customers/{customer_id}/payment-tokens` - Listar Payment Tokens
- `POST /api/v1/vault/payments/with-token` - Pagar con Payment Token

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales de PayPal
```

## Configuración

### Variables de Entorno

```bash
# PayPal Configuration
PAYPAL_MODE=sandbox              # sandbox o live
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_WEBHOOK_ID=your-webhook-id

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/paypal_api

# Security
SECRET_KEY=your-super-secret-key-here
```

## Uso

### Ejecutar la aplicación

```bash
uvicorn paypal_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Documentación

Una vez ejecutada la aplicación, puedes acceder a:
- Documentación interactiva: http://localhost:8000/docs
- Documentación alternativa: http://localhost:8000/redoc

## Endpoints Principales

### Pagos
- `POST /api/v1/payments/create` - Crear pago
- `GET /api/v1/payments/{payment_id}` - Obtener pago
- `POST /api/v1/payments/{payment_id}/execute` - Ejecutar pago

### Suscripciones
- `POST /api/v1/subscriptions/plans` - Crear plan de suscripción
- `POST /api/v1/subscriptions/create` - Crear suscripción
- `GET /api/v1/subscriptions/{subscription_id}` - Obtener suscripción
- `POST /api/v1/subscriptions/{subscription_id}/cancel` - Cancelar suscripción

### Webhooks
- `POST /api/v1/webhooks/paypal` - Recibir notificaciones de PayPal

## Desarrollo

### Estructura de Respuestas

Todas las respuestas siguen el formato estándar:

```json
{
  "success": true,
  "data": { ... },
  "errors": []
}
```

### Logging

El sistema utiliza logging estructurado con correlación de requests para facilitar el debugging.

### Middleware

- **CorrelationMiddleware**: Añade IDs de correlación a las requests
- **PayPalHeaderMiddleware**: Maneja las credenciales de PayPal
- **LoggingMiddleware**: Logging automático de requests y responses