import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .logging_config import correlation_id_var, endpoint_var, method_var
from fastapi.responses import JSONResponse
from paypal_api.config import settings


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        endpoint = str(request.url.path)
        method = request.method
        
        correlation_id_var.set(correlation_id)
        endpoint_var.set(endpoint)
        method_var.set(method)
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response

class PayPalHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Excluir health, docs y openapi
        if request.url.path.startswith("/health") or \
           request.url.path.startswith("/openapi") or \
           request.url.path.startswith("/docs"):
            return await call_next(request)

        # Obtener credenciales de PayPal de headers o configuración
        client_id = request.headers.get("PayPal-Client-Id") or settings.PAYPAL_CLIENT_ID
        client_secret = request.headers.get("PayPal-Client-Secret") or settings.PAYPAL_CLIENT_SECRET
        
        if not client_id or not client_secret:
            return JSONResponse(
                status_code=401,
                content={"detail": "Faltan credenciales de PayPal (header o settings)"}
            )
            
        # Adjuntar a request.state para uso en endpoints
        request.state.paypal_client_id = client_id
        request.state.paypal_client_secret = client_secret
        return await call_next(request)