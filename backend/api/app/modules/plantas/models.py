from sqlalchemy import Column, String, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class Plant(BaseModel):
    """
    Planta industrial (ej: Planta Maipú)
    Una empresa puede tener múltiples plantas
    simpre filtrar por company_id
    """
    __tablename__ = "plants"

    name = Column(String(200), nullable=False)
    company_id = Column(UUID(as_uuid=True), 
                        ForeignKey("companies.id", 
                        on_delete="CASCADE"),
                        nullable=False, index=True)
    
    location = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Relaciones
    company = relationship(
        "Company", back_populates="plants"
    )
    areas = relationship(
        "Area",
        back_populates="plant",
        cascade="all, delete-orphan"
    )
    user_accesses = relationship(
        "UserPlantAccess",
        back_populates="plant",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_plant_company_active', "company_id", "is_active"),
        UniqueConstraint("company_id", "name", name="uq_plant_name_per_company")
    )

    def __repr__(self):
        return f"<Plant {self.name} - Company={self.company_id}>"


class Area(BaseModel):
    """
    Área o sector dentro de una planta
    (ej: Área de Molienda, Área de Envasado)
    """
    __tablename__ = "areas"

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    plant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relaciones
    plant = relationship("Plant", back_populates="areas")
    machines = relationship(
        "Machine",
        back_populates="area",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_area_plant_active', 'plant_id', 'is_active'),
        UniqueConstraint('plant_id', 'name', name='uq_area_name_per_plant'),
    )

    def __repr__(self):
        return f"<Area {self.name}>"


class UserPlantAccess(BaseModel):
    """
    Tabla pivote: controla a qué plantas tiene acceso cada usuario
    y con qué rol específico en esa planta.
    Un supervisor puede serlo en Planta A pero operario en Planta B
    """
    __tablename__ = "user_plant_accesses"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    plant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Relaciones
    user = relationship("User", back_populates="plant_accesses")
    plant = relationship("Plant", back_populates="user_accesses")

    def __repr__(self):
        return f"<UserPlantAccess user={self.user_id} plant={self.plant_id}>"