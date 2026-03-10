import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class MaintenanceType(str, enum.Enum):
    preventivo = "preventivo"
    reporte_falla = "reporte_falla"
    correctivo = "correctivo"
    predictivo = "predictivo"
    inspeccion = "inspeccion"
    bloqueo_loto = "bloqueo_loto"


class TaskStatus(str, enum.Enum):
    pendiente = "pendiente"
    en_progreso = "en_progreso"
    completado = "completado"
    cancelado = "cancelado"
    vencido = "vencido"


class TaskPriority(str, enum.Enum):
    bajo = "bajo"
    mediano = "mediano"
    alto = "alto"
    critico = "critico"


class MaintenanceTask(BaseModel):
    __tablename__ = "maintenance_tasks"

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    maintenance_type = Column(Enum(MaintenanceType), nullable=False, default=MaintenanceType.preventivo)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.pendiente)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.mediano)
    
    scheduled_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    
    is_loto_required= Column(Boolean, nullable=False, default=False)
    loto_applied_at = Column(DateTime, nullable=True)
    loto_applied_by_id =Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    evidence_photo_url = Column(String(600), nullable=True)
    completion_notes = Column(Text, nullable=True)
        
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    machine = relationship("Machine", back_populates="maintenance_tasks")
    assigned_to = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to_id])
    created_by = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])
    loto_aplied_by = relationship("User", foreign_keys=[loto_applied_by_id])
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

    task_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_tasks.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    previous_status = Column(Enum(TaskStatus), nullable=True)
    new_status = Column(Enum(TaskStatus), nullable=False)
    notes = Column(Text, nullable=True)
    
    task = relationship("MaintenanceTask", back_populates="activity_logs")
    user = relationship("User", backref="activity_logs")
    
    def __repr__(self):
        return f"<MaintenanceActivityLog task={self.task_id}>"