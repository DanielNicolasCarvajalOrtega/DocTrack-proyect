import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, ForeignKey, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.base_models import BaseModel


class DocumentType(str, enum.Enum):
    manuales = "manuales"
    certificados = "certificados"
    instrucciones_seguridad = "instrucciones_de_seguridad"
    plan_mantenimiento = "mantenimiento"
    hoja_tecnica= "hoja_tecnica"
    procedimientos = "procedimientos"
    otros = "otros"


class DocumentStatus(str, enum.Enum):
    activo = "activo"
    expirado = "expirado"
    sustituido = "sustituido"
    borrador = "borrador"


class Document(BaseModel):
    __tablename__ = "documents"

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    doc_type = Column(Enum(DocumentType), nullable=False, default=DocumentType.otros)
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.activo)
    version = Column(String(20), nullable=False, default="1.0")
    version_number = Column(Integer, nullable=False, default=1)
    file_url = Column(String(1000), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False )
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    supersedes_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    machine = relationship("Machine", back_populates="documents")
    uploaded_by = relationship("User")
    read_confirmations = relationship("DocumentReadConfirmation", back_populates="document", cascade="all, delete-orphan")
    supersedes = relationship("Document", 
                              remote_side="[Document.id]", 
                              foreign_keys=[supersedes_id], 
                              backref = "superseded_by")
    
    __table_args__ = (
        Index('ix_document_machine_active', 'machine_id', 'is_active'),
        Index('ix_document_status', 'status'),
        Index('ix_document_valid_until', 'valid_until'),
    )
    
    def __repr__(self):
        return f"<Document {self.title}>"


class DocumentReadConfirmation(BaseModel):
    __tablename__ = "document_read_confirmations"

    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    document = relationship("Document", back_populates="read_confirmations")
    user = relationship("User")
    


    __table_args__ = (
        Index('ix_doc_confirmation_document', 'document_id'),
        Index('ix_doc_confirmation_user', 'user_id'),
    )
    
    def __repr__(self):
        return f"<DocumentReadConfirmation doc={self.document_id} user={self.user_id}>"