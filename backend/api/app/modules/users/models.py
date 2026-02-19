import enum
from sqlalchemy import Column, String, Enum, Boolean
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel

class UserRole(str, enum.Enum):

    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    TECNICOS = "tecnicos"
    OPERADORES = "operadores"


class User(BaseModel):
    __tablename__ = "users"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole),nullable=False,default=UserRole.OPERADORES)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relaciones
    plant_accesses = relationship(
        "UserPlantAccess",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    document_confirmations = relationship(
        "DocumentReadConfirmation",
        back_populates="user"
    )
    assigned_tasks = relationship(
        "MaintenanceTask",
        back_populates="assigned_to",
        foreign_keys="MaintenanceTask.assigned_to_id"
    )
    created_tasks = relationship(
        "MaintenanceTask",
        back_populates="created_by",
        foreign_keys="MaintenanceTask.created_by_id"
    )

    def __repr__(self):
        return f"<Usuario {self.email} - {self.role}>"