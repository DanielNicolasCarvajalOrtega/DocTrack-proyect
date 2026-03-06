"""
Router para operaciones de Empresas (Companies).
Optimizado con:
- ORJSONResponse para serialización rápida
- Async endpoints
- Validación Pydantic en borde 
- Cache headers para GET
"""
from fastapi import APIRouter, Depends, Status, Query, BackgroundTasks
from fastapi.responses import ORJSONResponse
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.modules.compañias.services.company_service import CompanyService
from app.modules.users.models import User
from app.shared.exceptions import ForbiddenException
from pydantic import BaseModel, Field, EmailStr


class CompanyResponse(BaseModel):
    """Respuesta de empresa (DTO para API)."""
    id: UUID
    name: str
    slug: str
    billing_plan: str
    max_users: int
    max_plants: int
    max_storage_gb: int
    contact_email: Optional[str]
    contact_phone: Optional[str]

    class Config:
        from_attributes = True


class CompanyCreateRequest(BaseModel):
    """Request para crear empresa."""
    name: str = Field(..., min_length=3, max_length=200)
    slug: str = Field(..., min_length=3, max_length=100, regex="^[a-z0-9-]+$")
    billing_plan: str = Field("prueba", regex="^(prueba|basico|pro|empresas)$")
    max_users: Optional[int] = Field(None, ge=1)
    max_plants: Optional[int] = Field(None, ge=1)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class CompanyUpdateRequest(BaseModel):
    """Request para actualizar empresa."""
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None


router = APIRouter(prefix="/api/v1/companies", tags=["companies"])

@router.get(
    "",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_200_OK,
    summary="Listar empresas",
    responses={403: {"description": "No autorizado"}}
)

async def list_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> ORJSONResponse:
    """
    **SUPER_ADMIN only**: Obtiene listado paginado de empresas.
    
    - **limit**: Registros por página (máx 500)
    - **offset**: Desplazamiento para paginación
    """
    service = CompanyService(db)
    companies = await service.get_all_companies(current_user, limit=limit, offset=offset)
    
    # Serializar manualmente a dataclass para evitar overhead Pydantic
    data = [
        {
            "id": str(c.id),
            "name": c.name,
            "slug": c.slug,
            "billing_plan": c.billing_plan,
            "max_users": c.max_users,
            "max_plants": c.max_plants,
            "max_storage_gb": c.max_storage_gb,
        }
        for c in companies
    ]
    
    return ORJSONResponse(
        {"data": data, "count": len(companies)},
        headers={"Cache-Control": "public, max-age=300"}  # Cache 5 min
    )


@router.get(
    "/{company_id}",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_200_OK,
    summary="Obtener empresa"
)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ORJSONResponse:
    """
    Obtiene detalle de una empresa por ID.
    Usuario debe tener acceso a la empresa.
    """
    service = CompanyService(db)
    company = await service.get_company_by_id(company_id, current_user)
    
    data = {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "billing_plan": company.billing_plan,
        "max_users": company.max_users,
        "max_plants": company.max_plants,
        "max_storage_gb": company.max_storage_gb,
        "contact_email": company.contact_email,
        "contact_phone": company.contact_phone,
    }
    
    return ORJSONResponse(
        data,
        headers={"Cache-Control": "public, max-age=300"}
    )


@router.post(
    "",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_201_CREATED,
    summary="Crear empresa"
)
async def create_company(
    payload: CompanyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ORJSONResponse:
    """
    **SUPER_ADMIN only**: Crea nueva empresa.
    
    Validaciones:
    - Slug debe ser único
    - Slug solo puede contener minúsculas, números y guiones
    """
    service = CompanyService(db)
    company = await service.create_company(
        current_user,
        name=payload.name,
        slug=payload.slug,
        billing_plan=payload.billing_plan,
        max_users=payload.max_users,
        max_plants=payload.max_plants,
        max_storage_gb=payload.max_storage_gb,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        address=payload.address,
    )
    
    data = {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "billing_plan": company.billing_plan,
        "message": f"Empresa {company.name} creada exitosamente"
    }
    
    return ORJSONResponse(data)


@router.patch(
    "/{company_id}",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_200_OK,
    summary="Actualizar empresa"
)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ORJSONResponse:
    """
    Actualiza datos de una empresa.
    
    - **COMPANY_ADMIN**: Puede actualizar datos de contacto
    - **SUPER_ADMIN**: Puede cambiar plan y límites
    """
    service = CompanyService(db)
    company = await service.update_company(
        company_id,
        current_user,
        **payload.model_dump(exclude_none=True)
    )
    
    return ORJSONResponse({
        "id": str(company.id),
        "name": company.name,
        "updated": True
    })


@router.delete(
    "/{company_id}",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_204_NO_CONTENT,
    summary="Eliminar empresa"
)
async def delete_company(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ORJSONResponse:
    """
    **SUPER_ADMIN only**: Elimina una empresa (soft delete).
    """
    service = CompanyService(db)
    await service.delete_company(company_id, current_user)
    
    return ORJSONResponse(
        {"deleted": True},
        status_code=Status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/{company_id}/limits",
    response_class=ORJSONResponse,
    status_code=Status.HTTP_200_OK,
    summary="Obtener límites de empresa"
)
async def get_company_limits(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ORJSONResponse:
    """
    Obtiene límites y uso actual de recursos de una empresa.
    
    Usuario debe tener acceso a la empresa.
    """
    service = CompanyService(db)
    await service.get_company_by_id(company_id, current_user)  # Validar acceso
    
    limits = await service.get_company_limits(company_id)
    
    data = {
        "max_users": limits.max_users,
        "current_users": limits.current_users,
        "users_available": limits.users_available,
        "can_add_user": limits.can_add_user,
        "max_plants": limits.max_plants,
        "current_plants": limits.current_plants,
        "plants_available": limits.plants_available,
        "can_add_plants": limits.can_add_plants,
        "max_storage_gb": limits.max_storage,
        "current_storage_gb": limits.current_storage_company,
        "storage_available_gb": limits.storage_available_gb,
    }
    
    return ORJSONResponse(
        data,
        headers={"Cache-Control": "public, max-age=60"}  # Cache 1 min
    )
