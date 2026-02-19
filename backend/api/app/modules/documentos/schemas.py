from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.modules.documentos.models import DocumentType, DocumentStatus

class DocumentResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    doc_type: DocumentType
    status: DocumentStatus
    version: str
    version_number: int
    file_url: str
    file_name: str
    file_size: int | None
    file_type: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    machine_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

        