import pytest
from unittest.mock import MagicMock, patch, PropertyMock, call
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

    def test_max_users_coro_lanza_error(self, db):
        with pytest.raises(ValueError, match="max_users"):
            CompanyRepository.create(
                db,
                {
                    "name": "Carozzi S.A.",
                    "slug": "carozzi",
                    "max_users": 0
                }
            )
    
    def test_max_plants_negativo_lanza_error(self, db):
        with pytest.raises(ValueError, match="max_plants"):
            CompanyRepository.create(
                db,
                {
                    "name": "Carozzi S.A.",
                    "slug": "carozzi",
                    "max_users": -2
                }
            )
    
    def test_validacion_falla_antes_de_tocar_db(self, db):
        with pytest.raises(ValueError):
            CompanyRepository.create(
                db,
                {
                    "name": "Xxx",
                    "slug": "invalidd%4",
                    
                }
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()


class TestCreateExitoso:

    def test_retorna_objeto_company(self, db, data_valida):
        fake_company = MagicMock(spec=Company)

        with patch("app.modules.compañias.company_repository.Company") as MockCompany:
            MockCompany.return_value = fake_company
            result = CompanyRepository.create(db, data_valida)

        
        assert result == fake_company


    def test_llama_add_commit_refresh_en_orden(self, db, data_valida):
        fake_company = MagicMock(spec=Company)
        manager = MagicMock() # verificcamos orden de llamadas

        db.add = manager.add
        db.commit = manager.commit
        db.refresh = manager.refresh

        with patch("app.modules.compañias.company_repository.Company") as MockCompany:
            MockCompany.return_value = fake_company
            CompanyRepository.create(db, data_valida)

        assert manager.mock_calls == [
            call.add(fake_company),
            call.commit(),
            call.refresh(fake_company),
        ]

    
    def test_company_creada_con_los_datos_correctos(self, db, data_valida):
        with patch("app.modules.compañias.company_repository.Company") as MockCompany:
            MockCompany.return_value = MagicMock(spec=Company)
            CompanyRepository.create(db, data_valida)

        # verifica que Company fue instanciada con el diccionario que le proporcionamos exactamente
        MockCompany.assert_called_once_with(**data_valida)

        
    
class TestCreateErrores:

    def test_integrity_error_slug_duplicado_hace_rollback(self, db, data_valida):
        db.commit.side_effect = IntegrityError(
            "slug",
            {},
            Exception("unique constraint on slug")
        )

        with pytest.raises(ValueError, match="slug"):
            CompanyRepository.create(db, data_valida)

        db.rollback.assert_called_once()


    def test_integrity_error_name_duplicado_hace_rollback(self, db, data_valida):
        db.commit.side_effect = IntegrityError(
            "name",
            {},
            Exception("unique constraint on name")
        )
        with pytest.raises(ValueError, match="nombre"):
            CompanyRepository.create(db, data_valida)

        db.rollback.assert_called_once()

    
    def test_integrity_error_no_hace_commit(self, db, data_valida):
        db.commit.side_effect = IntegrityError(
            "slug",
            {},
            Exception("unique constraint on slug")
        )

        with pytest.raises(ValueError):
            CompanyRepository.create(db, data_valida)

        db.commit.assert_called_once() # intenta commit
        db.rollback.assert_called_once() # hace rollback al intentar
    
    def test_slqalchemy_error_lanza_runtime(self, db, data_valida):
        db.commit.side_effect = SQLAlchemyError("connection timeout")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyRepository.create(db, data_valida)

    def test_sqlalchemy_error_hace_rollback(self, db, data_valida):
            db.commit.side_effect = SQLAlchemyError("connection timeout")
            with pytest.raises(RuntimeError):
                CompanyRepository.create(db, data_valida)

            db.rollback.assert_called_once()

    def test_error_no_retorna_nada(self, db, data_valida):
        # nunca retorna un None silencioso, ante cualquier error lanza 
        # siempre lanza RuntimeError
        db.commit.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="error interno"):
            result = CompanyRepository.create(db, data_valida)
            assert result is None # nunca deberia llegar aca

    
        






