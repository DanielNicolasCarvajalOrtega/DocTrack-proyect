from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from app.modules.mantenimiento.models import (
    MaintenanceType,
    TaskStatus,
    TaskPriority
)


class MaintenanceTaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    maintenance_type: MaintenanceType
    status: TaskStatus
    priority: TaskPriority
    scheduled_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    due_date: datetime | None
    completion_notes: str | None
    estimated_hours: int | None
    actual_hours: int | None
    machine_id: UUID
    assigned_to_id: UUID | None
    created_by_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True