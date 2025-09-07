from fastapi import APIRouter
from .endpoints import payments, webhooks, vault, customers

api_router = APIRouter()

api_router.include_router(
    payments.router,
    prefix="/payments",
    tags=["payments"]
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)

api_router.include_router(
    vault.router,
    prefix="/vault",
    tags=["vault"]
)

api_router.include_router(
    customers.router,
    prefix="/customers",
    tags=["customers"]
)