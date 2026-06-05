import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Enum,
    Text, Boolean, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class BillingPlan(str, enum.Enum):
    prueba = "prueba"
    basico = "basico"
    pro = "pro"
    empresas = "empresas"


class CompanyRole(str, enum.Enum):
    admin = "admin"
    auditor = "auditor"
    supervisor = "supervisor"
    tecnicos = "tecnicos"
    operadores = "operadores"


class IndustryType(str, enum.Enum): # --> tipo de industria - relacionada con compañia
    """
    Industria a la que pertenece la compañía.
    Se selecciona al momento de contratar el plan.
    Permite adaptar la terminología del sistema al cliente.
    Ej: "División" en alimentos -> "Faena" en minería -> "Proyecto" en construcción
    """
    alimentos_bebidas = "alimentos_bebidas"
    manufactura = "manufactura"
    construccion = "construccion"
    mineria = "mineria"
    energia = "energia"
    salud = "salud"
    logistica = "logistica"
    hoteleria = "hoteleria"
    petroquimica = "petroquimica"
    agroindustria = "agroindustria"
    otro = "otro"


class StructureType(str, enum.Enum):
    """
    Define qué niveles jerárquicos usa la compañía.

    simple  -> Company -> Plant -> Area -> Machine
                  (PYME con una o pocas plantas)

    divisional  -> Company -> Division -> Plant -> Area -> Machine
                  (empresa mediana con múltiples líneas de negocio)

    corporativo -> Parent Company -> Company -> Division -> Plant -> Area -> Machine (maquina)
                  (grupo empresarial con subsidiarias legales independientes)

    Determinado por el plan:
      prueba/basico → simple
      pro           → simple o divisional
      empresas      → cualquiera
    """
    simple = "simple"
    divisional = "divisional"
    corporativo = "corporativo"


class Company(BaseModel):
    __tablename__ = "companies"

    name = Column(String(200), nullable=False, unique=True)
    slug  = Column(String(100), nullable=False, unique=True, index=True)
    billing_plan = Column(Enum(BillingPlan),    nullable=False, default=BillingPlan.prueba)
    industry = Column(Enum(IndustryType),   nullable=True)
    structure_type = Column(Enum(StructureType), nullable=False, default=StructureType.simple)

    # Limites — definidos por el plan, nunca editables directamente por el admin
    # El service aplica estos valores automáticamente al cambiar el plan
    max_users_per_plant = Column(Integer, nullable=False, default=5)
    max_plants = Column(Integer, nullable=False, default=1)
    max_storage_gb = Column(Integer, nullable=False, default=2)
    max_children = Column(Integer, nullable=False, default=0)

    # Fechas de suscripcion
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)

    # Contacto
    contact_email = Column(String(255), nullable=True, unique=True)
    contact_phone = Column(String(50),  nullable=True)
    address  = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=False, default="#3B82F6")
    """
     PARENT-CHILD 
     parent_id = NULL -> compañía raíz (no tiene parent)
     parent_id = UUID -> es subsidiaria de esa compañía
     RESTRICT -> no se puede eliminar un parent que tenga hijos activos
    
    """
    
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Self-referential
    parent = relationship(
        "Company",
        remote_side="Company.id",
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children = relationship(
        "Company",
        foreign_keys=[parent_id],
        back_populates="parent",
    )

    # Otras relaciones
    users = relationship(
        "CompanyUser",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Division solo existe si structure_type = divisional o corporativo
    divisions = relationship(
        "Division",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Plantas directas — solo si structure_type = simple
    plants = relationship(
        "Plant",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents = relationship(
        "Document",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_company_active", "is_active"),
        Index("ix_company_billing_active", "billing_plan", "is_active"),
        Index("ix_company_parent", "parent_id"),
        Index("ix_company_parent_active", "parent_id", "is_active"),
        Index("ix_company_structure", "structure_type"),
        Index("ix_company_industry", "industry"),
    )

    def __repr__(self):
        return f"<Company {self.name} [{self.structure_type}]>"
    
class CompanyUser(BaseModel):
    __tablename__ = "company_users"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(CompanyRole),  nullable=False, default=CompanyRole.operadores, index=True)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=True)

    company = relationship("Company", back_populates="users")
    user = relationship("User", back_populates="company_memberships", foreign_keys=[user_id])
    invited_by = relationship("User",foreign_keys=[invited_by_id])

    __table_args__ = (
        # FIX: partial index en lugar de UniqueConstraint
        # UniqueConstraint bloquea re-agregar un usuario que fue removido (is_active=False)
        # El partial index solo aplica unicidad sobre registros activos
        Index(
            "uq_active_company_user",
            "company_id", "user_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
        Index("ix_company_user_active", "company_id", "is_active"),
        Index("ix_user_company_active", "user_id", "is_active"),
        Index("ix_company_user_lookup", "company_id", "user_id"),
        Index("ix_company_role_lookup", "company_id", "role"),
    )

    def __repr__(self):
        return f"<CompanyUser company={self.company_id} user={self.user_id} role={self.role}>"