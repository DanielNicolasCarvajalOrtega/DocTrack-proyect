
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.modules.users.models import UserRole



# ==================== RESPONSE SCHEMAS ====================

class PlantAccessResponse(BaseModel):
    """Acceso a planta (resumido)"""
    plant_id: UUID
    plant_name: str
    company: str
    location: str | None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Usuario básico (para listados)"""
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    phone: str | None
    avatar_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Usuario con detalles completos (incluye plantas)"""
    plant_accesses: list[PlantAccessResponse] = []


class UserStatsResponse(BaseModel):
    """Estadísticas de usuarios por rol"""
    total: int
    admins: int
    supervisors: int
    technicians: int
    operators: int


# ==================== REQUEST SCHEMAS ====================

class UserCreateRequest(BaseModel):
    """Crear nuevo usuario"""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: UserRole
    phone: Optional[str] = Field(None, max_length=20)
    plant_ids: Optional[list[UUID]] = Field(
        default=[],
        description="IDs de plantas a las que tendrá acceso"
    )

    @validator('password')
    def validate_password(cls, v):
        """Validar fortaleza de contraseña"""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class UserUpdateRequest(BaseModel):
    """Actualizar usuario (todos los campos opcionales)"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserPasswordUpdateRequest(BaseModel):
    """Cambiar contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v


class AssignPlantsRequest(BaseModel):
    """Asignar plantas a un usuario"""
    plant_ids: list[UUID] = Field(..., min_items=1)


class AddPlantAccessRequest(BaseModel):
    """Agregar acceso a una planta"""
    plant_id: UUID


# ==================== RESPONSE WRAPPERS ====================

class UserListResponse(BaseModel):
    """Respuesta paginada de usuarios"""
    total: int
    users: list[UserResponse]


class MessageResponse(BaseModel):
    """Respuesta genérica de éxito"""
    message: str
    data: dict = {}
