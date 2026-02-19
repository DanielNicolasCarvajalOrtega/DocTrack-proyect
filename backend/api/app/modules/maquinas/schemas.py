from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.modules.maquinas.models import MachineStatus

class MachineResponse(BaseModel):

    id: UUID
    name: str
    model: str | None
    brand: str | None
    serial_number: str | None
    description: str | None
    location_detail: str | None
    status: MachineStatus
    qr_code: str
    image_url: str | None
    area_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MachineDetailResponse(MachineResponse):
    """DETALLE COMPLETO CON EL AREA E PLANTA"""

    area_name: str | None = None
    plant_name: str | None = None

    