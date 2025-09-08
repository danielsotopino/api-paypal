from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from paypal_api.services.customer_service import CustomerService
from paypal_api.database import get_db
from paypal_api.schemas.response_models import ApiResponse
from paypal_api.core.exceptions import PayPalCommunicationException
from pydantic import BaseModel, EmailStr
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


# =============================================================================
# SCHEMAS PARA CUSTOMERS
# =============================================================================

class CustomerResponse(BaseModel):
    """Esquema de respuesta para Customer"""
    id: int
    paypal_customer_id: str
    email_address: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    default_shipping_address: Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerUpdateRequest(BaseModel):
    """Esquema para actualizar Customer"""
    email_address: Optional[EmailStr] = None
    given_name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    default_shipping_address: Optional[dict] = None


class CustomerListResponse(BaseModel):
    """Esquema de respuesta para lista de customers"""
    customers: List[CustomerResponse]
    total: int
    page: int
    page_size: int


class CustomerStatsResponse(BaseModel):
    """Esquema de respuesta para estadísticas de customers"""
    total_customers: int
    active_customers: int
    inactive_customers: int
    activation_rate: float


# =============================================================================
# DEPENDENCIAS
# =============================================================================

def get_customer_service() -> CustomerService:
    """Dependencia para obtener el servicio de Customer"""
    return CustomerService()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/", response_model=ApiResponse[CustomerListResponse])
async def list_customers(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    email_filter: Optional[str] = Query(None, description="Filtro por email"),
    is_active: Optional[bool] = Query(None, description="Filtro por estado activo"),
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Listar todos los clientes con paginación y filtros
    """
    try:
        skip = (page - 1) * page_size
        
        logger.info("Listando clientes", 
                   page=page, 
                   page_size=page_size,
                   email_filter=email_filter,
                   is_active=is_active)
        
        customers, total = customer_service.list_customers(
            db=db,
            skip=skip,
            limit=page_size,
            email_filter=email_filter,
            is_active=is_active
        )

        # Convertir a esquemas de respuesta
        customer_responses = [
            CustomerResponse.from_orm(customer) for customer in customers
        ]

        response_data = CustomerListResponse(
            customers=customer_responses,
            total=total,
            page=page,
            page_size=page_size
        )

        logger.info("Clientes listados exitosamente", 
                   total_found=len(customers),
                   total_records=total)
        
        return ApiResponse.success_response(response_data.dict())

    except Exception as e:
        logger.error("Error listando clientes", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{customer_id}", response_model=ApiResponse[CustomerResponse])
async def get_customer_by_id(
    customer_id: int,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Obtener cliente por ID interno
    """
    try:
        logger.info("Obteniendo cliente por ID", customer_id=customer_id)
        
        customer = customer_service.get_customer_by_id(db, customer_id)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        customer_response = CustomerResponse.from_orm(customer)
        
        logger.info("Cliente obtenido exitosamente", customer_id=customer_id)
        return ApiResponse.success_response(customer_response.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo cliente", customer_id=customer_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/paypal/{paypal_customer_id}", response_model=ApiResponse[CustomerResponse])
async def get_customer_by_paypal_id(
    paypal_customer_id: str,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Obtener cliente por PayPal customer ID
    """
    try:
        logger.info("Obteniendo cliente por PayPal ID", paypal_customer_id=paypal_customer_id)
        
        customer = customer_service.get_customer_by_paypal_id(db, paypal_customer_id)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        customer_response = CustomerResponse.from_orm(customer)
        
        logger.info("Cliente obtenido exitosamente", paypal_customer_id=paypal_customer_id)
        return ApiResponse.success_response(customer_response.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo cliente por PayPal ID", 
                    paypal_customer_id=paypal_customer_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/email/{email}", response_model=ApiResponse[CustomerResponse])
async def get_customer_by_email(
    email: str,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Obtener cliente por email
    """
    try:
        logger.info("Obteniendo cliente por email", email=email)
        
        customer = customer_service.get_customer_by_email(db, email)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        customer_response = CustomerResponse.from_orm(customer)
        
        logger.info("Cliente obtenido exitosamente", email=email)
        return ApiResponse.success_response(customer_response.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo cliente por email", 
                    email=email, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/{customer_id}", response_model=ApiResponse[CustomerResponse])
async def update_customer(
    customer_id: int,
    update_data: CustomerUpdateRequest,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Actualizar información del cliente
    """
    try:
        logger.info("Actualizando cliente", customer_id=customer_id)
        
        # Convertir a diccionario excluyendo campos None
        update_dict = update_data.dict(exclude_unset=True)
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No se proporcionaron datos para actualizar")

        customer = customer_service.update_customer(db, customer_id, update_dict)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        customer_response = CustomerResponse.from_orm(customer)
        
        logger.info("Cliente actualizado exitosamente", 
                   customer_id=customer_id,
                   updated_fields=list(update_dict.keys()))
        return ApiResponse.success_response(customer_response.dict())

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Error de validación actualizando cliente", 
                    customer_id=customer_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error actualizando cliente", 
                    customer_id=customer_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/{customer_id}/deactivate", response_model=ApiResponse[dict])
async def deactivate_customer(
    customer_id: int,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Desactivar cliente (soft delete)
    """
    try:
        logger.info("Desactivando cliente", customer_id=customer_id)
        
        success = customer_service.deactivate_customer(db, customer_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        logger.info("Cliente desactivado exitosamente", customer_id=customer_id)
        return ApiResponse.success_response({
            "message": "Cliente desactivado exitosamente",
            "customer_id": customer_id
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error desactivando cliente", 
                    customer_id=customer_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/{customer_id}/activate", response_model=ApiResponse[dict])
async def activate_customer(
    customer_id: int,
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Reactivar cliente
    """
    try:
        logger.info("Reactivando cliente", customer_id=customer_id)
        
        success = customer_service.activate_customer(db, customer_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        logger.info("Cliente reactivado exitosamente", customer_id=customer_id)
        return ApiResponse.success_response({
            "message": "Cliente reactivado exitosamente",
            "customer_id": customer_id
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reactivando cliente", 
                    customer_id=customer_id, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/search/", response_model=ApiResponse[CustomerListResponse])
async def search_customers(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Buscar clientes por término de búsqueda
    """
    try:
        skip = (page - 1) * page_size
        
        logger.info("Buscando clientes", 
                   search_term=q, 
                   page=page, 
                   page_size=page_size)
        
        customers, total = customer_service.search_customers(
            db=db,
            search_term=q,
            skip=skip,
            limit=page_size
        )

        # Convertir a esquemas de respuesta
        customer_responses = [
            CustomerResponse.from_orm(customer) for customer in customers
        ]

        response_data = CustomerListResponse(
            customers=customer_responses,
            total=total,
            page=page,
            page_size=page_size
        )

        logger.info("Búsqueda de clientes completada", 
                   search_term=q,
                   total_found=len(customers),
                   total_records=total)
        
        return ApiResponse.success_response(response_data.dict())

    except Exception as e:
        logger.error("Error buscando clientes", 
                    search_term=q, 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/stats/summary", response_model=ApiResponse[CustomerStatsResponse])
async def get_customer_statistics(
    customer_service: CustomerService = Depends(get_customer_service),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de clientes
    """
    try:
        logger.info("Obteniendo estadísticas de clientes")
        
        stats = customer_service.get_customer_statistics(db)
        
        stats_response = CustomerStatsResponse(**stats)
        
        logger.info("Estadísticas de clientes obtenidas exitosamente", **stats)
        return ApiResponse.success_response(stats_response.dict())

    except Exception as e:
        logger.error("Error obteniendo estadísticas de clientes", 
                    error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
