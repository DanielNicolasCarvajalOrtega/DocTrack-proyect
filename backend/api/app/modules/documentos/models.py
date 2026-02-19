import enum
from sqlalchemy import (
    Column, String, Text, Enum,
    ForeignKey, Integer, DateTime, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.base_models import BaseModel


class DocumentType(str, enum.Enum):
    """
    Tipos de documentos técnicos industriales
    """
    MANUALES = "manuales"                 
    INSTRUCCIONES_SEGURIDAD = "instruccion de seguridad"     
    PLAN_MANTENIMIENTO = "plan de mantenimiento"    
    FICHA_TECNICA = "ficha tecnica" 
    PROCEDIMIENTOS = "procedimiento operativo"          
    OTROS = "otros "                 


class DocumentStatus(str, enum.Enum):
    ACTIVO = "activo"       
    EXPIRADO = "expirado"     
    REMPLAZADO = "remplazado" # Reemplazado por nueva versión
    BORRADOR = "borrador"      


class Document(BaseModel):
    """
    Documento técnico asociado a una máquina.
    Soporta versionado — cada actualización crea nueva versión.
    """
    __tablename__ = "documents"

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    doc_type = Column(
        Enum(DocumentType),
        nullable=False,
        default=DocumentType.OTROS
    )
    status = Column(
        Enum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.ACTIVO
    )

    # Versionado
    version = Column(String(20), nullable=False, default="1.0")
    version_number = Column(Integer, nullable=False, default=1)

    # Archivo en Google Cloud Storage
    file_url = Column(String(1000), nullable=False)   # URL firmada GCS
    file_name = Column(String(300), nullable=False)   # Nombre original
    file_size = Column(Integer, nullable=True)         # Tamaño en bytes
    file_type = Column(String(50), nullable=True)      # pdf, docx, xlsx...

    # Vigencia del documento
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)

    # Control
    uploaded_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    machine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Si este documento reemplaza a uno anterior
    supersedes_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=True
    )

    # Relaciones
    machine = relationship("Machine", back_populates="documents")
    uploaded_by = relationship("User")
    read_confirmations = relationship(
        "DocumentReadConfirmation",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    supersedes = relationship(
        "Document",
        remote_side="Document.id",
        foreign_keys=[supersedes_id]
    )

    def __repr__(self):
        return f"<Document {self.title} v{self.version}>"


class DocumentReadConfirmation(BaseModel):
    """
    Registro de trazabilidad: quién leyó qué documento y cuándo.
    CRÍTICO para auditorías y cumplimiento normativo.
    """
    __tablename__ = "document_read_confirmations"

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)     # Cuando presiona "confirmar lectura"
    notes = Column(Text, nullable=True)                # Comentario opcional del usuario

    # Relaciones
    document = relationship("Document", back_populates="read_confirmations")
    user = relationship("User", back_populates="document_confirmations")

    __table_args__ = (
        Index('ix_document_machine_active', 'machine_id', 'is_active'),
        Index('ix_document_status', 'status'),
        Index('ix_document_valid_until', 'valid_until'),  # Para alertas de vencimiento
    )

    def __repr__(self):
        return f"<ReadConfirmation doc={self.document_id} user={self.user_id}>"