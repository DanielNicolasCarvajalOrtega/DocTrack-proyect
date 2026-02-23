from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relaciones
    companies = relationship("CompanyUser", back_populates="user", foreign_keys="CompanyUser.user_id")
    assigned_tasks = relationship("MaintenanceTask", back_populates="assigned_to", foreign_keys="MaintenanceTask.assigned_to_id")
    created_tasks = relationship("MaintenanceTask", back_populates="created_by", foreign_keys="MaintenanceTask.created_by_id")
    
    def __repr__(self):
        return f"<User {self.email}>"