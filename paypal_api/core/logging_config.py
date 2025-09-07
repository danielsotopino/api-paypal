import logging
import json
import os
from datetime import datetime
from contextvars import ContextVar
from typing import Optional
import structlog
import sys

correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
endpoint_var: ContextVar[Optional[str]] = ContextVar('endpoint', default=None)
method_var: ContextVar[Optional[str]] = ContextVar('method', default=None)


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "artifact": os.getenv("SERVICE_NAME", "api-paypal"),
            "version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "correlation_id": correlation_id_var.get(),
            "endpoint": endpoint_var.get(),
            "method": method_var.get(),
            "message": record.getMessage(),
        }
        
        if hasattr(record, 'context'):
            log_entry["context"] = record.context
            
        if hasattr(record, 'error'):
            log_entry["error"] = record.error
            
        if record.exc_info:
            log_entry["traceback"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", json_logs: bool = True):
    """
    Configura structlog para la aplicación FastAPI
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        json_logs: Si usar formato JSON o formato legible para desarrollo
    """
    
    # Configurar el logging estándar de Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Procesadores comunes
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_logs:
        # Procesadores para producción (JSON)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Procesadores para desarrollo (más legible)
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configurar structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )