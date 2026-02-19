from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class AreaResponse(BaseModel):
    """area básica"""
    id: UUID
    name: str
    description: str | None
    plant_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AreaDetailResponse(AreaResponse):
    """area con información de planta"""
    plant_name: str | None
    plant_company: str | None
    total_machines: int = 0


class AreaCreateRequest(BaseModel):
    """Crear área"""
    name: str = Field(..., min_length=2, max_length=200)
    plant_id: UUID
    description: Optional[str] = Field(None, max_length=1000)


class AreaUpdateRequest(BaseModel):
    """Actualizar area"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class AreaStatsResponse(BaseModel):
    """Estadísticas de un area"""
    area_id: UUID
    area_name: str
    plant_name: str | None
    machines: dict


class PlantResponse(BaseModel):
    """Planta basica"""
    id: UUID
    name: str
    company: str
    location: str | None
    description: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlantDetailResponse(PlantResponse):
    """Planta con areas"""
    areas: list[AreaResponse] = []
    total_areas: int = 0
    total_users: int = 0


class PlantCreateRequest(BaseModel):
    """Crear planta"""
    name: str = Field(..., min_length=2, max_length=200)
    company: str = Field(..., min_length=2, max_length=200)
    location: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    logo_url: Optional[str] = Field(None, max_length=500)


class PlantUpdateRequest(BaseModel):
    """Actualizar planta"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    company: Optional[str] = Field(None, min_length=2, max_length=200)
    location: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = Field(None, max_length=1000)
    logo_url: Optional[str] = Field(None, max_length=500)


class PlantStatsResponse(BaseModel):
    """Estadísticas de una planta"""
    plant_id: UUID
    plant_name: str
    total_areas: int
    total_machines: int
    users: dict


class AssignUsersRequest(BaseModel):
    """Asignar usuarios a planta (REEMPLAZA existentes)"""
    user_ids: list[UUID] = Field(..., min_items=1)


class AddUserAccessRequest(BaseModel):
    """Agregar un usuario sin afectar los demas"""
    user_id: UUID


class MessageResponse(BaseModel):
    """Respuesta generica"""
    message: str
    data: dict = {}