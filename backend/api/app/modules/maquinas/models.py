import enum
import uuid
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class MachineStatus(str, enum.Enum):
    """
    Estado operacional de la máquina
    """
    OPERATIVA = "operativa"       # Funcionando con normalidad
    MANTENIMIENTO = "mantenimiento"       # En mantenimiento programado
    FALLAS = "fuera de servicio"               # Falla / fuera de servicio
    DEBAJA = "dada de baja" # Dada de baja


class Machine(BaseModel):
    """
    Máquina industrial dentro de un área.
    Entidad central del sistema — todo orbita alrededor de la máquina.
    """
    __tablename__ = "machines"

    name = Column(String(200), nullable=False)
    model = Column(String(200), nullable=True)           
    brand = Column(String(200), nullable=True)      
    serial_number = Column(String(100), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    location_detail = Column(String(300), nullable=True) # Ej: "Nave 3, lado norte"
    status = Column(
        Enum(MachineStatus),
        nullable=False,
        default=MachineStatus.OPERATIVA
    )
    qr_code = Column(
        String(100),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()) # QR único por máquina
    )
    image_url = Column(String(500), nullable=True)
    area_id = Column(
        UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relaciones
    area = relationship("Area", back_populates="machines")
    documents = relationship(
        "Document",
        back_populates="machine",
        cascade="all, delete-orphan"
    )
    maintenance_tasks = relationship(
        "MaintenanceTask",
        back_populates="machine",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
    Index('ix_machine_area_active', 'area_id', 'is_active'),
    Index('ix_machine_qr', 'qr_code'),  # Para escaneo QR rápido
    Index('ix_machine_status', 'status'),  # Para dashboards
)

    def __repr__(self):
        return f"<Machine {self.name} - {self.serial_number}>"