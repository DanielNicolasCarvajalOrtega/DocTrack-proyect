import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class BillingPlan(str, enum.Enum):
    prueba = "prueba"
    basico = "basico"
    pro = "pro"
    empresas = "empresas"


class Company(BaseModel):
    __tablename__ = "companies"

    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    billing_plan = Column(Enum(BillingPlan), nullable=False, default=BillingPlan.prueba)
    max_users = Column(Integer, default=10, nullable=False)
    max_plants = Column(Integer, default=1, nullable=False)
    max_storage_gb = Column(Integer, default=5, nullable=False)
    trial_ends_at = Column(DateTime, nullable=True)
    subscription_ends_at = Column(DateTime, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#3B82F6")
    users = relationship(
        "CompanyUser",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin"  # Carga eager para evitar N+1
    )
    plants = relationship(
        "Plant",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    __table_args__ = (
        Index('ix_company_active', 'is_active'),
        Index('ix_company_billing_active', 'billing_plan', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Company {self.name}>"


class CompanyRole(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    tecnicos = "tecnicos"
    operadores = "operadores"


class CompanyUser(BaseModel):
    __tablename__ = "company_users"

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.operadores, index=True)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="users")
    user = relationship("User", back_populates="companies", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    
    __table_args__ = (
        Index('ix_company_user_active', 'company_id', 'is_active'),
        Index('ix_user_company_active', 'user_id', 'is_active'),
        Index('ix_company_user_lookup', 'company_id', 'user_id'),
        Index('ix_company_role_lookup', 'company_id', 'role'),
        UniqueConstraint('company_id', 'user_id', name='uq_company_user'),
    )
    
    def __repr__(self):
        return f"<CompanyUser company={self.company_id} user={self.user_id}>"