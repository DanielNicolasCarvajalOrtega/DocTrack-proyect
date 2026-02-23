import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class MaintenanceType(str, enum.Enum):
    PREVENTIVO = "preventivo"
    CORRECTIVO = "correctivo"
    PREDICTIVO = "predictivo"
    INSPECCION = "inspeccion"


class TaskStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en progreso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"
    VENCIDO = "vencido"


class TaskPriority(str, enum.Enum):
    BAJO = "baja"
    MEDIANO = "mediana"
    ALTO = "alta"
    CRITICO = "critico"


class MaintenanceTask(BaseModel):
    __tablename__ = "maintenance_tasks"

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    maintenance_type = Column(Enum(MaintenanceType), nullable=False, default=MaintenanceType.PREVENTIVO)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDIENTE)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIANO)
    
    scheduled_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    completion_notes = Column(Text, nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    machine = relationship("Machine", back_populates="maintenance_tasks")
    assigned_to = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to_id])
    created_by = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])
    activity_logs = relationship("MaintenanceActivityLog", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_maintenance_machine', 'machine_id'),
        Index('ix_maintenance_assigned', 'assigned_to_id'),
        Index('ix_maintenance_status', 'status'),
        Index('ix_maintenance_priority', 'priority'),
    )
    
    def __repr__(self):
        return f"<MaintenanceTask {self.title}>"


class MaintenanceActivityLog(BaseModel):
    __tablename__ = "maintenance_activity_logs"

    task_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    previous_status = Column(Enum(TaskStatus), nullable=True)
    new_status = Column(Enum(TaskStatus), nullable=False)
    notes = Column(Text, nullable=True)
    
    task = relationship("MaintenanceTask", back_populates="activity_logs")
    user = relationship("User", backref="activity_logs")
    
    def __repr__(self):
        return f"<MaintenanceActivityLog task={self.task_id}>"