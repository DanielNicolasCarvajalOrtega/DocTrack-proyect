import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class BaseModel(Base):
    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key = True,
        default=uuid.uuid4,
        index=True
    )
    created_at = Column(DateTime,default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True,nullable=False, index=True)
    
    def to_dict(self)-> dict:
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
        }

