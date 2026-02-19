import enum
from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class MaintenanceType(str, enum.Enum):
    PREVENTIVO = "preventivo"   # Mantenimiento programado
    CORRECTIVO = "correctivo"   # Reparación de falla
    PREDICTIVO = "predictivo"   # Basado en condición
    INSPECCION = "inspeccion"   # Solo inspección visual


class TaskStatus(str, enum.Enum):
    PENDIENTE = "pendiente"         # Sin iniciar
    EN_PROGRESO = "en progreso" # En ejecución
    COMPLETADO = "completado"     # Finalizado
    CANCELADO = "cancelado"     # Cancelado
    VENCIDO = "vencido"         # Vencido sin completar


class TaskPriority(str, enum.Enum):
    BAJA = "baja"
    MEDIANA = "mediana"
    ALTA = "alta"
    CRITICA = "critica"


class MaintenanceTask(BaseModel):
    """
    Tarea de mantenimiento asignada a una máquina.
    Puede ser programada (preventivo) o reactiva (correctivo).
    """
    __tablename__ = "maintenance_tasks"

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    maintenance_type = Column(
        Enum(MaintenanceType),
        nullable=False,
        default=MaintenanceType.PREVENTIVO
    )
    status = Column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDIENTE
    )
    priority = Column(
        Enum(TaskPriority),
        nullable=False,
        default=TaskPriority.MEDIANA
    )

    # Fechas
    scheduled_date = Column(DateTime, nullable=True)  # Fecha programada
    started_at = Column(DateTime, nullable=True)       # Cuándo se inició
    completed_at = Column(DateTime, nullable=True)     # Cuándo se completó
    due_date = Column(DateTime, nullable=True)         # Fecha límite

    # Resultado
    completion_notes = Column(Text, nullable=True)     # Observaciones al completar
    estimated_hours = Column(Integer, nullable=True)   # Horas estimadas
    actual_hours = Column(Integer, nullable=True)      # Horas reales

    # Relaciones FK
    machine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assigned_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # Relaciones ORM
    machine = relationship("Machine", back_populates="maintenance_tasks")
    assigned_to = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[assigned_to_id]
    )
    created_by = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by_id]
    )
    activity_logs = relationship(
        "MaintenanceActivityLog",
        back_populates="task",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MaintenanceTask {self.title} - {self.status}>"


class MaintenanceActivityLog(BaseModel):
    """
    Historial de actividad de una tarea.
    Registra cada cambio de estado con notas y usuario responsable.
    """
    __tablename__ = "maintenance_activity_logs"

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    previous_status = Column(Enum(TaskStatus), nullable=True)
    new_status = Column(Enum(TaskStatus), nullable=False)
    notes = Column(Text, nullable=True)

    # Relaciones
    task = relationship("MaintenanceTask", back_populates="activity_logs")
    user = relationship("User")

    def __repr__(self):
        return f"<ActivityLog task={self.task_id} {self.previous_status}→{self.new_status}>"