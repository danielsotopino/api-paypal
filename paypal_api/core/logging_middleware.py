import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.routing import Match
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging automático de todas las requests
    """
    
    def __init__(
        self,
        app,
        *,
        skip_paths: Optional[list[str]] = None,
        skip_methods: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.skip_methods = skip_methods or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar ID único para la request
        request_id = str(uuid.uuid4())
        
        # Añadir request_id al contexto de structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Agregar request_id al state de la request
        request.state.request_id = request_id
        
        # Verificar si debemos skipear esta ruta
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Datos básicos de la request
        start_time = time.time()
        request_size = request.headers.get("content-length")
        
        # Log de request entrante
        await self._log_request_start(request, request_size)
        
        try:
            # Procesar la request
            response = await call_next(request)
            
            # Calcular tiempo de respuesta
            process_time = time.time() - start_time
            
            # Log de respuesta exitosa
            await self._log_request_success(
                request, response, process_time, request_size
            )
            
            # Añadir headers útiles
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            return response
            
        except Exception as e:
            # Calcular tiempo hasta el error
            process_time = time.time() - start_time
            
            # Log del error
            await self._log_request_error(
                request, e, process_time, request_size
            )
            
            # Re-raise la excepción
            raise
    
    def _should_skip_logging(self, request: Request) -> bool:
        """Determina si debemos skipear el logging para esta request"""
        return (
            request.url.path in self.skip_paths or
            request.method in self.skip_methods
        )
    
    async def _log_request_start(self, request: Request, request_size: str) -> None:
        """Log cuando inicia una request"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        logger.info(
            event="request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_ip=client_ip,
            user_agent=user_agent,
            request_size=request_size,
        )
    
    async def _log_request_success(
        self, 
        request: Request, 
        response: Response, 
        process_time: float,
        request_size: str
    ) -> None:
        """Log de request exitosa"""
        client_ip = self._get_client_ip(request)
        response_size = response.headers.get("content-length")
        
        logger.info(
            event="request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            client_ip=client_ip,
            request_size=request_size,
            response_size=response_size,
        )
    
    async def _log_request_error(
        self, 
        request: Request, 
        error: Exception, 
        process_time: float,
        request_size: str
    ) -> None:
        """Log cuando hay un error en la request"""
        client_ip = self._get_client_ip(request)
        
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error_type=type(error).__name__,
            error_message=str(error),
            process_time_ms=round(process_time * 1000, 2),
            client_ip=client_ip,
            request_size=request_size,
            exc_info=True,
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtiene la IP real del cliente considerando proxies"""
        # Revisar headers de proxy comunes
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback a la IP directa
        return request.client.host if request.client else "unknown"