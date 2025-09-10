# PayPal API

**API REST completa para integración con PayPal Vault y servicios de pagos**, desarrollada con FastAPI y diseñada para gestionar métodos de pago almacenados de forma segura, procesar pagos recurrentes y manejar suscripciones empresariales.

Este microservicio proporciona una capa de abstracción robusta sobre la API de PayPal, incluyendo persistencia local, sincronización automática y manejo avanzado de excepciones.

## Características Principales

### 🔐 PayPal Vault API Integration
- **Setup Tokens**: Validación temporal de métodos de pago con flujo de aprobación
- **Payment Tokens**: Almacenamiento seguro permanente de métodos de pago
- **Tokenized Payments**: Procesamiento de pagos sin re-solicitar datos sensibles
- **Multi-customer Support**: Gestión de múltiples clientes y sus métodos de pago

### 💰 Gestión de Pagos y Suscripciones
- Procesamiento de pagos únicos y recurrentes
- Creación y gestión de planes de suscripción
- Integración completa con PayPal Orders API
- Webhooks para notificaciones en tiempo real

### 🏗️ Arquitectura Empresarial
- **Persistencia Dual**: Base de datos local con sincronización automática con PayPal
- **Repository Pattern**: Abstracción de acceso a datos para flexibilidad
- **Service Layer**: Lógica de negocio desacoplada y testeable
- **Exception Handling**: Manejo robusto de errores con logging estructurado

### 🔧 Características Técnicas
- **FastAPI Framework**: API REST moderna con documentación automática
- **Structured Logging**: Logging avanzado con correlación de requests
- **Middleware Stack**: CORS, correlación, logging y validación de headers PayPal
- **Database Migrations**: Gestión de esquemas con Alembic
- **Health Checks**: Endpoints de monitoreo y verificación de estado

## Estructura del Proyecto

```
paypal_api/
├── api/v1/endpoints/            # API Endpoints v1
│   ├── vault.py                 # 🔐 PayPal Vault API (Setup/Payment Tokens)
│   ├── orders.py                # 💰 PayPal Orders API (Pagos)
│   ├── customers.py             # 👥 Gestión de clientes
│   └── webhooks.py              # 🔔 Webhooks de PayPal
├── core/                        # 🏗️ Infraestructura base
│   ├── middleware.py            # Middleware de correlación y PayPal headers
│   ├── logging_middleware.py    # Middleware de logging estructurado
│   ├── exceptions.py            # Excepciones personalizadas
│   ├── exception_handlers.py    # Manejadores globales de errores
│   └── logging_config.py        # Configuración de logging
├── models/                      # 🗄️ Modelos de base de datos (SQLAlchemy)
│   ├── customer.py              # Modelo de clientes
│   ├── vault_payment_method.py  # Métodos de pago del vault
│   └── order.py                 # Órdenes de pago
├── repositories/                # 📊 Capa de acceso a datos
│   ├── customer_repository.py           
│   ├── vault_payment_method_repository.py
│   └── order_repository.py      
├── services/                    # 🔧 Lógica de negocio
│   ├── vault_service.py         # Servicio principal de Vault (orquestador)
│   ├── customer_service.py      # Gestión de clientes
│   ├── order_service.py         # Gestión de órdenes
│   └── paypal/                  # Servicios específicos de PayPal SDK
│       ├── paypal_vault_service.py     # PayPal Vault API wrapper
│       └── paypal_orders_service.py    # PayPal Orders API wrapper
├── schemas/                     # 📋 Validación y serialización (Pydantic)
│   ├── paypal_schemas.py        # Schemas específicos de PayPal
│   ├── vault_schemas.py         # Schemas del vault
│   ├── order_schemas.py         # Schemas de órdenes
│   └── response_models.py       # Modelos de respuesta estándar
├── alembic/                     # 🔄 Migraciones de base de datos
├── config.py                    # ⚙️ Configuración de la aplicación
├── database.py                  # 🗄️ Setup de conexión a base de datos
└── main.py                      # 🚀 Aplicación principal FastAPI
```

## 🚀 Instalación y Configuración

### 1. Requisitos del Sistema
- Python 3.11+
- PostgreSQL 12+ (para persistencia)
- Redis (opcional, para caché)

### 2. Instalación
```bash
# Clonar el repositorio (si aplica)
git clone <repository-url>
cd api-paypal

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno
```bash
# Copiar archivo de configuración
cp .env.example .env

# Editar variables de entorno
nano .env
```

**Variables requeridas:**
```bash
# PayPal Configuration
PAYPAL_MODE=sandbox              # sandbox | live
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_WEBHOOK_ID=your-webhook-id

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/paypal_api

# Application
SECRET_KEY=your-super-secret-key
ENVIRONMENT=development
DEBUG=true
```

### 4. Base de Datos
```bash
# Ejecutar migraciones
alembic upgrade head

# (Opcional) Generar nueva migración
alembic revision --autogenerate -m "descripción"
```

### 5. Ejecutar la Aplicación
```bash
# Desarrollo
uvicorn paypal_api.main:app --host 0.0.0.0 --port 8000 --reload

# Producción
uvicorn paypal_api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔐 Uso de PayPal Vault API

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

### 📋 Endpoints Disponibles

**PayPal Vault:**
- `POST /api/v1/vault/setup-tokens` - Crear Setup Token
- `GET /api/v1/vault/setup-tokens/{id}` - Obtener Setup Token  
- `POST /api/v1/vault/payment-tokens` - Crear Payment Token
- `GET /api/v1/vault/payment-tokens/{id}` - Obtener Payment Token
- `DELETE /api/v1/vault/payment-tokens/{id}` - Eliminar Payment Token
- `GET /api/v1/vault/customers/{customer_id}/payment-tokens` - Listar Payment Tokens
- `POST /api/v1/vault/payments/with-token` - Pagar con Payment Token

**Gestión de Clientes:**
- `POST /api/v1/customers` - Crear cliente
- `GET /api/v1/customers/{customer_id}` - Obtener cliente
- `GET /api/v1/customers` - Listar clientes

**Órdenes de Pago:**
- `POST /api/v1/orders` - Crear orden de pago
- `GET /api/v1/orders/{order_id}` - Obtener orden
- `POST /api/v1/orders/{order_id}/capture` - Capturar pago

**Webhooks:**
- `POST /api/v1/webhooks/paypal` - Endpoint para webhooks de PayPal

## 📖 Documentación y Monitoreo

### Documentación Interactiva
Una vez ejecutada la aplicación:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

### Health Checks y Monitoreo
- **Health Check**: `GET /health`
- **Root Info**: `GET /`
- **Metrics**: Logging estructurado con correlación de requests

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