from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20),  nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at  = Column(DateTime, nullable=True)
    """
      FIX: renombrado de "companies" a "company_memberships"
      Retorna objetos CompanyUser, no Company directamente
     Para obtener las compañías: [m.company for m in user.company_memberships]
    """
  
    company_memberships = relationship(
        "CompanyUser",
        back_populates="user",
        foreign_keys="CompanyUser.user_id",
    )

    assigned_tasks = relationship(
        "MaintenanceTask",
        back_populates="assigned_to",
        foreign_keys="MaintenanceTask.assigned_to_id",
    )
    created_tasks = relationship(
        "MaintenanceTask",
        back_populates="created_by",
        foreign_keys="MaintenanceTask.created_by_id",
    )

    __table_args__ = (
        Index("ix_user_email",       "email"),
        Index("ix_user_super_admin", "is_super_admin"),
    )

    def __repr__(self):
        return f"<User {self.email}>"