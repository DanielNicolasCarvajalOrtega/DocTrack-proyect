import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Index, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel

class MachineStatus(str, enum.Enum):
    operativa = "operativa"
    mantenimiento = "mantenimiento"
    fallas = "fallas"
    descontinuada = "descontinuada"

class Machine(BaseModel):
    __tablename__ = "machines"

    name = Column(String(200), nullable=False)
    model = Column(String(200), nullable=True)
    brand = Column(String(200), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    location_detail = Column(String(300), nullable=True)
    status = Column(Enum(MachineStatus), nullable=False, default=MachineStatus.operativa)
    qr_code = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    image_url = Column(String(500), nullable=True)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id", ondelete="RESTRICT"), nullable=False, index=True)
    requires_pin = Column(Boolean, default=False, nullable=False)
    security_pin = Column(String(255), nullable=True)
    # Auditoría
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    area = relationship("Area", back_populates="machines")
    documents = relationship("Document", back_populates="machine", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="machine", cascade="all, delete-orphan")
    pin_audit_logs = relationship("MachinePinAuditLog", back_populates="machine", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_machine_area_active', 'area_id', 'is_active'),
        Index('ix_machine_qr', 'qr_code'),
        Index('ix_machine_status', 'status'),
    )

class MachinePinAuditLog(BaseModel):
    __tablename__ = "machine_pin_audit_logs"

    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action = Column(String(50), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    machine = relationship("Machine", back_populates="pin_audit_logs")
    changed_by = relationship("User", backref="pin_audit_logs")