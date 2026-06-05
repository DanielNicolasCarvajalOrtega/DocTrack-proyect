from sqlalchemy import Column, String, Text, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel

"""
DIVISION
Solo existe cuando structure_type = divisional o corporativo.
Representa una unidad de negocio dentro de una compañía.

Ejemplos por industria:
- Alimentos -> "División Mascotas", "División Pastas"
- Minería -> "Faena Chuquicamata", "Faena El Teniente"
- Construcción -> "Proyecto Costanera", "Proyecto Metro L7"
- Manufactura  -> "Línea Automotriz", "Línea Electrónica"
"""

class Division(BaseModel):
    __tablename__ = "divisions"

    name = Column(String(200), nullable=False)
    description = Column(Text,        nullable=True)
    logo_url = Column(String(500), nullable=True)

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Gerente de división — rol auditor en la compañía
    manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company = relationship("Company", back_populates="divisions")
    manager = relationship("User", foreign_keys=[manager_id])
    plants = relationship("Plant", back_populates="division", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_division_company_active", "company_id", "is_active"),
        # Nombre unico dentro de la misma compañia
        UniqueConstraint("company_id", "name", name="uq_division_name_per_company"),
    )

    def __repr__(self):
        return f"<Division {self.name} company={self.company_id}>"


class Plant(BaseModel):
    __tablename__ = "plants"

    name = Column(String(200), nullable=False)
    location = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    """
    company_id — referencia directa para queries eficientes sin joins
    Se sincroniza automáticamente con division.company_id en el service
    Si structure_type=simple → company_id directo, division_id=NULL
    Si structure_type=divisional → ambos presentes
    """
    
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # division_id — NULL si structure_type=simple
    division_id = Column(
        UUID(as_uuid=True),
        ForeignKey("divisions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Gerente de planta — rol auditor en la compañía (rotativo)
    manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company = relationship("Company",  back_populates="plants")
    division = relationship("Division", back_populates="plants")
    manager = relationship("User",     foreign_keys=[manager_id])
    areas = relationship("Area",     back_populates="plant", cascade="all, delete-orphan")
    user_accesses = relationship("UserPlantAccess", back_populates="plant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_plant_company_active",  "company_id",  "is_active"),
        Index("ix_plant_division_active", "division_id", "is_active"),
        # Nombre único dentro de la misma compañía
        UniqueConstraint("company_id", "name", name="uq_plant_name_per_company"),
    )

    def __repr__(self):
        return f"<Plant {self.name}>"


class UserPlantAccess(BaseModel):
    __tablename__ = "user_plant_access"

    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id",  ondelete="CASCADE"), nullable=False, index=True)
    plant_id = Column(UUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)

    user  = relationship("User",  backref="plant_accesses")
    plant = relationship("Plant", back_populates="user_accesses")

    __table_args__ = (
        # Partial index — unicidad solo sobre registros activos
        # Permite re-agregar un usuario a una planta después de haberlo removido
        Index(
            "uq_active_user_plant_access",
            "user_id", "plant_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    def __repr__(self):
        return f"<UserPlantAccess user={self.user_id} plant={self.plant_id}>"


class Area(BaseModel):
    __tablename__ = "areas"

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    plant_id = Column(UUID(as_uuid=True), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id",  ondelete="SET NULL"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id",  ondelete="SET NULL"), nullable=True)

    plant = relationship("Plant", back_populates="areas")
    machines = relationship("Machine", back_populates="area", cascade="all, delete-orphan")
    user_accesses = relationship("UserAreaAccess", back_populates="area", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_area_plant_active", "plant_id", "is_active"),
        UniqueConstraint("plant_id", "name", name="uq_area_name_per_plant"),
    )

    def __repr__(self):
        return f"<Area {self.name}>"


class UserAreaAccess(BaseModel):
    __tablename__ = "user_area_access"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id",  ondelete="CASCADE"), nullable=False, index=True)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id",  ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User",  backref="area_accesses")
    area = relationship("Area",  back_populates="user_accesses")

    __table_args__ = (
        Index(
            "uq_active_user_area_access",
            "user_id", "area_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    def __repr__(self):
        return f"<UserAreaAccess user={self.user_id} area={self.area_id}>"