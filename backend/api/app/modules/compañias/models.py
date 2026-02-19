from datetime import datetime
import enum
from sqlalchemy import Column, Index, String, Integer, DateTime, Enum, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UUID, Uuid
from app.core.base_models import BaseModel


class BillingPlan(str, enum.Enum):
    """ PLAN FACTURACION"""
    PRUEBA = "prueba"
    BASICO = "basico"
    PRO = "pro"
    EMPRESAS = "empresas"

class Company(BaseModel):
    """
        EMPRESA CLIENTE 
        CADA EMPRESA ES UN CLIENTE DEL SISTEMA COMPLETAMENTE 
        ASLADA 
    """

    __tablename__ = "companies"

    name = Column(String(200), nullable=False, unique=True)
    slug = Column(
        String(200),
        nullable=False,
        unique = True,
        index = True  # para subdomain routing
    )
    billing_plan = Column(
        Enum(BillingPlan),
        nullable= False,
        default= BillingPlan.PRUEBA,
    )
    max_users = Column(Integer, default=8, nullable=False)
    max_plants = Column(Integer, default=1, nullable=False)
    max_storage_gb = Column(Integer, default= 5, nullable= False)

    trial_end_at = Column(DateTime, nullable=True)
    subscription_end_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    contact_email = Column(String(180), nullable=True)
    contact_phone = Column(String(10), nullable=True)
    address = Column(Text, nullable= True)

    logo_url = Column(String(600), nullable=True)
    primary_color = Column(String(10), default="#3B82F6")

    users = relationship(
        "CompanyUser",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    plants = relationship(
        "Plant",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"< Company {self.name}-({self.slug})>"
    
class CompanyRole(str, enum.Enum):
    """ 
    CADA USUARIO TIENE UN ROL POR EMPRESA
    """

    ADMINISTRADOR_COMPANIA = "administrador" # acceso y administra toda la empresa
    SUPERVISOR = "supervisor"  # supervisa areas
    TECNICO = "tecnico" # ejecuta mantenimiento 
    OPERADOR = "operador" # solo lectura

class CompanyUser(BaseModel):

    __tablename__ = "company_users"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Índice compuesto abajo
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(
        Enum(CompanyRole),
        nullable=False,
        default=CompanyRole.OPERADOR,
        index=True  # Para queries por rol
    )
    
    # Metadata
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    company = relationship("Company", back_populates="users")
    user = relationship("User", back_populates="companies", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    
    # Índice compuesto para queries rápidas
    __table_args__ = (
        Index('ix_company_user_lookup', 'company_id', 'user_id'),
        Index('ix_company_role_lookup', 'company_id', 'role'),
    )
    
    def __repr__(self):
        return f"<CompanyUser company={self.company_id} user={self.user_id} role={self.role}>"
    
    
