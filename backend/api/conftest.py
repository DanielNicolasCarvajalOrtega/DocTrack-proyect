import pytest
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4
import sys 
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.modules.compañias.repository.company_user_repository import CompanyUserRepository
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.plantas.models import Plant, UserAreaAccess, UserPlantAccess
import app.modules.compañias.models
import app.modules.plantas.models
import app.modules.maquinas.models
import app.modules.documentos.models
import app.modules.mantenimiento.models
import app.modules.users.models

@pytest.fixture
def db():
    session = MagicMock()
    session.add     = MagicMock()
    session.commit  = MagicMock()
    session.refresh = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def company_id():
    return uuid4()

@pytest.fixture
def user_id():
    return uuid4()

@pytest.fixture
def fake_company(company_id):
    """ objeto company falso con datos realistas"""
    c = MagicMock(spec=Company)
    c.id = company_id
    c.name = "CAROZZI S.A."
    c.slug = "carozzi"
    c.billing_plan = BillingPlan.empresas
    c.contact_email = "contacto@carozzi.cl"
    c.is_active = True
    c.max_users = 100
    c.max_plants = 10
    c.trials_ends_at = None
    return c

@pytest.fixture
def fake_membership(company_id, user_id):
    """ objeto CompanyUser con membresia activa """
    m = MagicMock(spec= CompanyUser)
    m.company_id = company_id
    m.user_id = user_id
    m.role = CompanyRole.tecnicos
    m.is_active = True
    return m

@pytest.fixture
def data_valida():
    """Dict mínimo válido para crear una compañía."""
    return {
        "name":          "Carozzi S.A.",
        "slug":          "carozzi",
        "billing_plan":  BillingPlan.empresas,
        "contact_email": "contacto@carozzi.cl",
        "max_users":     100,
        "max_plants":    10,
        "max_storage_gb":50,
        "primary_color": "#E3000F",
    }