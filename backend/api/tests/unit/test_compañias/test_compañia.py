import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.modules.compañias.repository.repository import (
    CompanyRepository, _validate_color, _validate_company_data, 
    _validate_email, _validate_positive_int, _validate_slug)
from backend.api.app.modules.compañias.repository.company_user_repository import CompanyUserRepository
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan

class TestCompanyRepositoryLectura:

    def test_get_by_id_retorna_company(self, db, fake_company, company_id):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.get_by_id(db, company_id)
        assert result == fake_company

    def test_get_by_id_retorna_none_si_no_existe(self, db, company_id):
        db.query().filter().first.return_value = None
        result = CompanyRepository.get_by_id(db, company_id)
        assert result is None

    def test_get_by_id_lanza_runtime_si_falla_db(self, db, company_id):
        db.query.side_effect = SQLAlchemyError("error de coneccion")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyRepository.get_by_id(db, company_id)

    
    def test_get_by_slug_valido(self, db, fake_company):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.get_by_slug(db, "carozzi")
        assert result == fake_company

    
    def test_get_by_slug_invalido_lanza_error(self,db):
        with pytest.raises(ValueError, match="slug invalido"):
            CompanyRepository.get_by_slug(db, "%carozii!&%")


    def test_get_by_slug_vacio_lanza_error(self, db):
        with pytest.raises(ValueError, match="vacio"):
            CompanyRepository.get_by_slug(db, "")


    def test_get_by_email_valido(self, db, fake_company):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.get_by_email(db, "alimentosmascotas@carozzicorp.cl")
        assert result == fake_company

    def test_get_by_email_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="invalido"):
            CompanyRepository.get_by_email(db, "esto/noes/email")
    

    def test_get_all_actives_retorna_lista(self, db, fake_company):
        db.query().filter().offset().limit().all.return_value = [fake_company]
        result = CompanyRepository.get_all_active(db)
        assert len(result) == 1


    def test_get_all_actives_skip_negativo_lanza_error(self,db):
        with pytest.raises(ValueError, match="negativo"):
            CompanyRepository.get_all_active(db, skip= -2)


    def test_get_all_active_limit_se_clampea_a_100(self, db):
        db.query().filter().offset().limit().all.return_value = []
        # no lanza error, se ajusta automaticamente a 100 internamente
        CompanyRepository.get_all_active(db, limit= 9999)

    
    def test_get_by_billing_plan_valido(self, db, fake_company):
        db.query().filter().offset().limit().all.return_value = [fake_company]
        result = CompanyRepository.get_all_billing_plan(db, BillingPlan.empresas)
        assert fake_company in result

    def test_get_trials_expiring_soon(self, db, fake_company):
        db.query().filter().all.return_value = [fake_company]
        result = CompanyRepository.get_trials_expiring_soon(db, datetime.now())
        assert fake_company in result

    def test_get_trials_expiring_soon_before_invalido(self, db):
        with pytest.raises(ValueError, match = "datetime"):
            CompanyRepository.get_trials_expiring_soon(db, "no-fecha-valida")

    def test_get_subscriptions_expiring_soon(self, db, fake_company):
        db.query().filter().all.return_value = [fake_company]
        result = CompanyRepository.get_subscriptions_expiring_soon(db, datetime.now())
        assert fake_company in result


class TestCompanyRepositoryEscritura:

    def test_create_exitoso(self, db):
        data = {
            "name": "Carozzi S.A",
            "slug": "carozzi",
            "billing_plan": BillingPlan.empresas
        }

        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        
        with patch("app.modules.compañias.repository") as MockCompany:
            fake = MagicMock()
            MockCompany.return_value = fake
            result = CompanyRepository.create(db, data)
            assert result == fake
            db.commit.assert_called_once()


    def test_create_sin_nombre_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(
                db,
                {
                    "slug":"carozzi"
                }
            )

    def test_create_sin_slug_lanza_error(self, db):
        with pytest.raises(ValueError, match="obligatorios"):
            CompanyRepository.create(
                db,
                {
                    "name":"Carozzi S.A"
                }
            )

    def test_create_slug_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="slug invalido"):
            CompanyRepository.create(
                db,
                {
                    "slug": "caro!%zi!!"
                }    
            )
        
    def test_create_integrity_error_slug_duplicado(self, db):
        data = {
            "name": "Carozzi S.A",
            "slug": "carozzi"
        }
        db.commit.side_effect = IntegrityError(
            "slug",
            {},
            Exception("unique constraint slug")
        )
        with pytest.raises(ValueError, match="slug"):
            CompanyRepository.create(db, data)
        db.rollback.assert_called_once()

    
    def test_create_sqlalchemy_error_lanza_runtime(self, db):
        data = {
            "name": "Carozzi S.A",
            "slug": "carozzi"
        }
        db.commit.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyRepository.create(db, data)
        db.rollback.assert_called_once()

    def test_update_exitoso(self, db, fake_company, company_id):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.update(db,company_id, {"name":"Carozzi nuevo"})
        db.commit.assert_called_once()
        assert result == fake_company


    def test_update_sin_datos_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="no se enviarion"):
            CompanyRepository.update(db, company_id, {})


    def test_update_campo_no_permitido_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="no permitidos"):
            CompanyRepository.update(db, company_id, {"is_active": False})

    
    
