from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os
from pathlib import Path

from app.core.config import settings
from app.core.database import Base

from app.modules.users.models import User
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.plantas.models import Plant, Area
from app.modules.maquinas.models import Machine, MachineStatus
from app.modules.mantenimiento.models import (
    MaintenanceTask,
    MaintenanceActivityLog,
    MaintenanceType,
    TaskStatus,
    TaskPriority
)
from app.modules.documentos.models import (
    Document,
    DocumentReadConfirmation,
    DocumentType,
    DocumentStatus
)

config = context.config

# Configurar URL
database_url = str(settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()
