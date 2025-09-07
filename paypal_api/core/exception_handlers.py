from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .exceptions import DomainException
from ..schemas.response_models import ApiResponse, ApiError
import structlog

logger = structlog.get_logger(__name__)

async def domain_exception_handler(request: Request, exc: DomainException):
    logger.warning(
        f"Error de dominio: {exc.message}",
        context={
            "error_code": exc.error_code,
            "endpoint": str(request.url.path),
            "method": request.method
        }
    )
    
    response = ApiResponse.single_error(exc.error_code, exc.message)
    return JSONResponse(
        status_code=400,
        content=response.dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        f"HTTP Exception: {exc.detail}",
        context={
            "status_code": exc.status_code,
            "endpoint": str(request.url.path),
            "method": request.method
        }
    )
    
    response = ApiResponse.single_error("HTTP_ERROR", str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,
        content=response.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_name = error['loc'][-1] if error['loc'] else 'unknown'
        errors.append(ApiError(
            code="VALIDATION_ERROR",
            message=f"{field_name}: {error['msg']}"
        ))
    
    logger.error(
        event="Validation error",
        context={
            "errors": [{"field": err.code, "message": err.message} for err in errors],
            "endpoint": str(request.url.path),
            "method": request.method
        }
    )
    
    response = ApiResponse.error_response(errors)
    return JSONResponse(
        status_code=422,
        content=response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Error inesperado: {str(exc)}",
        context={
            "endpoint": str(request.url.path),
            "method": request.method
        },
        error={
            "type": type(exc).__name__,
            "message": str(exc)
        }
    )
    
    response = ApiResponse.single_error("INTERNAL_ERROR", "Error interno del servidor")
    return JSONResponse(
        status_code=500,
        content=response.dict()
    )


def register_exception_handlers(app):
    """Register all exception handlers"""
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)