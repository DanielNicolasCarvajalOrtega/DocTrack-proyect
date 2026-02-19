from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Importar configuración y Base
from app.core.config import settings
from app.core.database import Base

# IMPORTANTE: Importar TODOS los modelos
from app.modules.users.models import User
from app.modules.plantas.models import Plant, Area, UserPlantAccess
from app.modules.maquinas.models import Machine
from app.modules.documentos.models import Document, DocumentReadConfirmation
from app.modules.mantenimiento.models import (
    MaintenanceTask,
    MaintenanceActivityLog
)

config = context.config

# Sobrescribir URL con la de settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
