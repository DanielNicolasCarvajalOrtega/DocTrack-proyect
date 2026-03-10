import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.modules.compañias.repository.repository import (
    CompanyRepository, _validate_color, _validate_company_data, 
    _validate_email, _validate_positive_int, _validate_slug)
from app.modules.compañias.repository.company_repository import CompanyUserRepository
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan


class TestCreateGuardClauses:
    
    def test_sin_name_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db,{"name":"carozzi"})

    def test_sin_slug_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db, {"name": "Carozzi S.A."})

    def test_name_vacio_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db,{"name":"", "slug":"carozzi"})

    def test_slug_vacio_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db,{"name":"Carozzi S.A.", "slug":""})

    def test_dict_vacio_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db, {})

    def test_name_none_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(db, {"name":None, "slug": "carozzi"})

        
    def test_slug_none_lanza_error(self, db):
        with pytest.raises(ValueError, match="oblugatorios"):
            CompanyRepository.create(db, {"name":"Carozzi S.A.", "slug": None })

    

class TestCreateValidaciones:

    def test_slug_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="slug invalido"):
            CompanyRepository.create(db, {"name":"Carozzi S.A.", "slug":"Carozzi!!-"})

        
    def test_slug_con_mayusculas_lanza_error(self, db):
        with pytest.raises(ValueError, match="slug invalido"):
            CompanyRepository.create(db, {"name": "Carozzi", "slug": "Carozzi"})


    def test_name_muy_corto_lanza_error(self, db):    
        with pytest.raises(ValueError, match="2 caracteres"):
            CompanyRepository.create(db, {"name": "caroz", "slug": "carozzi"})

    def test_color_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="invalido"):
            CompanyRepository.create(
                db,
                {
                    "name": "Carozzi S.A.",
                    "slug": "carozzi",
                    "primary_color": "rojo"
                }
            )

    def test_email_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="invalido"):
            CompanyRepository.create(
                db,
                    {
                    "name": "Carozzi S.A.",
                    "slug": "carozzi",
                    "contact_email": "no-es_email"
                    }
                )