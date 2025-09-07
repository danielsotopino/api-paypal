"""
PayPal API - FastAPI application for PayPal integration
"""

__version__ = "1.0.0"
__title__ = "PayPal API"
__description__ = "API REST para integración con PayPal"
__author__ = "Equipo EPC"
__license__ = "MIT"

from .main import app

__all__ = ["app"]