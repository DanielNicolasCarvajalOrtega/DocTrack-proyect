from pydantic import BaseModel, Field, field_validator, ConfigDict, field_validator, computed_field
from datetime import datetime
from uuid import UUID
from typing import Optional
import re
from app.modules.compañias.models import BillingPlan, CompanyRole, IndustryType, StructureType

"""
schema valida lo que el cliente puede enviar (request)
con pydantic para validacion de entrada y serializaciones
"""

# Responses - lo que el serivdor entrega al cliente
class CompanyResponse(BaseModel):
    """
    usada en listados, creacion y respuestas de subsidiarias
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    billing_plan: BillingPlan
    industry: Optional[IndustryType]
    structure_type: StructureType
    parent_id: Optional[UUID]
    is_active: bool
    created_at: datetime

    @computed_field # comvierte la respuesta de modelo a json
    @property
    def display_plan(self) -> str:
        labels = {
            BillingPlan.prueba: "Prueba gratuita",
            BillingPlan.basico : "Plan Basico",
            BillingPlan.pro: "Plan Pro",
            BillingPlan.empresas: "Para tu Empresa"
        }
        return labels.get(self.billing_plan, self.billing_plan.value)
    

class CompanyDetailResponse(CompanyResponse):
    """
    respuesta completa de la compañia
    - solo los admin y auditores tienen acceso al detalle - endpoint get /{company_id}
    """
    # limite del plan - solo lectura, no son editables directamente
    max_users_per_plant: int
    max_plant: int
    max_storage_gb: int
    max_children: int
    #fechas de suscripcion
    trial_ends_at: Optional[datetime]
    subscription_ends_at: Optional[datetime]
    # contacto
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    logo_url: Optional[str]
    primary_color: str
    updated_at: datetime
    
    # Contadores calculados - el router los inyecta para evitar N+1
    # se calculan en el servide antes de retornar, no en la query principal
    total_users: int = 0
    total_plants: int = 0
    total_children: int = 0
    storage_used_gb: float = 0.0

class CompanyStatsResponse(BaseModel):
    """
    Estadísticas completas de una compañia
    Solo el admin y auditor pueden acceder a este endpoint
    """
    model_config = ConfigDict(from_attributes=True)
    company_id: UUID
    company_name: str
    
    # Usuarios
    total_users: int
    users_by_role: dict[str, int]
    
    # Plantas y estructura
    total_plants: int
    total_areas: int
    total_machines: int
    total_children:int
    
    # Documentos
    total_documents: int
    documents_active: int
    documents_expiring_soon: int 
    
    # Mantenimiento
    tasks_pending: int
    tasks_overdue: int
    tasks_completed_this_month: int

class CompanyUserResponse(BaseModel):
    """
    Respuesta de membresia (CompanyUser)
    se usa en agregar usuario, listar usuarios y cambiar rol.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    user_id:UUID
    role: CompanyRole
    joined_at: Optional[datetime]
    is_active:bool
    invited_by_id:Optional[UUID]

    @computed_field
    @property
    def display_role(self)-> str:
        labels = {
            CompanyRole.admin: "Administrador",
            CompanyRole.auditor: "Auditor",
            CompanyRole.supervisor: "Supervisor",
            CompanyRole.tecnicos: "Tecnicos",
            CompanyRole.operadores: "Operador"
        }
        return labels.get(self.role, self.role.value)

class CompanyCreate(BaseModel):
    """
    crear una compañia raiz
    No, incluye max_users_per_plant, max_plants, max_storage_gb, max_children:
    esos los define el plan automáticamente en el service.
    """
    name: str = Field(...,min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=200, pattern=r'^[a-z0-9-]+$')
    billing_plan: BillingPlan = BillingPlan.prueba
    indistry: Optional[IndustryType] = None
    structure_type: StructureType = StructureType.simple

    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address:Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    primaty_color:str = Field("#3B82F6", pattern=r'^#[0-9A-Fa-f]{6}$')

    @field_validator('contact_email')
    @classmethod
    def validate_email(cls, v:Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', v):
            raise ValueError(f"Email invalido: {v}")
        return v.lower().strip()

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validar formato de slug"""
        if not v.strip().lower():
            raise ValueError('El slug debe estar en minúsculas')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('El slug no puede empezar o terminar con guión')
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$',v):
            raise ValueError("Slug invalido, solo minusculas, numeros y guiones")
        return v


class CompanyUpdate(BaseModel):
    """Actualizar compañia, solo campos editables
    max_* se quitaron, los va a definir, por el plan que elija la compañia automaticamente.
    structure_type solo puede cambiar si el plan lo permite
    billing_plan se acomoda segun lo que elija la empresa, este se asigna automaticamente a prueba
    """
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=200)
    industry: Optional[IndustryType] = None
    structure_type: Optional[StructureType] = None

    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validar formato de slug"""
        if not v.strip().lower():
            raise ValueError('El slug debe estar en minúsculas')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('El slug no puede empezar o terminar con guión')
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$',v):
            raise ValueError("Slug invalido, solo minusculas, numeros y guiones")
        return v
    
class SubsidiaryCreate(CompanyCreate):
    """
    crear una subsidiaria, hereda todos los campos de:
    CompanyCreate y agrega el plan del hijo
    """
    child_plan: BillingPlan = BillingPlan.prueba


class UserInvite(BaseModel):
    # agrea el usuario a la compañia
    user_id:UUID
    role: CompanyRole = CompanyRole.operadores

class RoleUpdate(BaseModel):
    # cambia el rol del usuario en la compañia

    new_role: CompanyRole

class PlanUpdate(BaseModel):
    # cambia u modifica el plan de la compañia
    # solo usando el endpoint PUT/{company_id}/plan/

    new_plan: BillingPlan
    subscription_ends_at: Optional[datetime] = None

class MessageResponse(BaseModel):
    # respuesta generica para operaciones sin retorno de objeto
    message:str
    data: dict = {}