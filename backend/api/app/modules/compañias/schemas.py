from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.modules.compañias.models import BillingPlan, CompanyRole


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    billing_plan: BillingPlan
    max_users: int
    max_plants: int
    is_active: bool
    created_at: datetime

    @property
    def display_plan(self) -> str:
        return {
            BillingPlan.prueba: "Prueba gratuita",
            BillingPlan.basico : "Plan Basico",
            BillingPlan.pro: "Plan Pro",
            BillingPlan.empresas: "Para tu Empresa"

        }.get(self.billing_plan, self.billing_plan.value)
    
class CompanyDetailResponse(CompanyResponse):
    max_storage_gb: int
    trial_ends_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    updated_at: datetime
    
    # Contadores calculados - evitar N+1
    total_users: int = 0
    total_plants: int = 0
    storage_used_gb: float = 0.0


class CompanyStatsResponse(BaseModel):
    """Estadísticas de una empresa"""
    company_id: UUID
    company_name: str
    
    # Usuarios
    total_users: int
    users_by_role: dict[str, int]
    
    # Plantas y estructura
    total_plants: int
    total_areas: int
    total_machines: int
    
    # Documentos
    total_documents: int
    documents_active: int
    documents_expiring_soon: int 
    
    # Mantenimiento
    tasks_pending: int
    tasks_overdue: int
    tasks_completed_this_month: int



class CompanyCreateRequest(BaseModel):
    
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r'^[a-z0-9-]+$')
    billing_plan: BillingPlan = BillingPlan.prueba
    max_users: int = Field(10, ge=1, le=10000)
    max_plants: int = Field(1, ge=1, le=100)
    max_storage_gb: int = Field(5, ge=1, le=10000)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: str = Field("#3B82F6", pattern=r'^#[0-9A-Fa-f]{6}$')
    

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validar formato de slug"""
        if not v.islower():
            raise ValueError('El slug debe estar en minúsculas')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('El slug no puede empezar o terminar con guión')
        return v


class CompanyUpdateRequest(BaseModel):
    """Actualizar empresa (todos los campos opcionales)"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    
    billing_plan: Optional[BillingPlan] = None
    max_users: Optional[int] = Field(None, ge=1, le=10000)
    max_plants: Optional[int] = Field(None, ge=1, le=100)
    max_storage_gb: Optional[int] = Field(None, ge=1, le=10000)
    
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class CompanyUserAssignRequest(BaseModel):
    """Asignar usuario a empresa"""
    user_id: UUID
    role: CompanyRole


class MessageResponse(BaseModel):
    """Respuesta genérica de éxito"""
    message: str
    data: dict = {}