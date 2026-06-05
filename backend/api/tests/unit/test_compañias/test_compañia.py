import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.repository.repository import (
    CompanyRepository, _validate_color, _validate_company_data, 
    _validate_email, _validate_positive_int, _validate_slug)
from app.modules.compañias.repository.company_user_repository import CompanyUserRepository
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
        with pytest.raises(ValueError, match="Slug inválido"):
            CompanyRepository.get_by_slug(db, "carozii!&%")


    def test_get_by_slug_vacio_lanza_error(self, db):
        with pytest.raises(ValueError, match="slug vacio"):
            CompanyRepository.get_by_slug(db, "")


    def test_get_by_email_valido(self, db, fake_company):
        mock_query = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = fake_company
        result = CompanyRepository.get_by_email(db, "alimentosmascotas@carozzicorp.cl")
        assert result == fake_company

    def test_get_by_email_invalido_lanza_error(self, db):
        with pytest.raises(ValueError, match="inválido"):
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
        
        with patch("app.modules.compañias.repository.repository.Company") as MockCompany:
            fake = MagicMock()
            MockCompany.return_value = fake
            result = CompanyRepository.create(db, data)

            assert result == fake
            db.add.assert_called_once_with(fake)
            db.commit.assert_called_once()
            db.refresh.assert_called_once_with(fake)


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
        with pytest.raises(ValueError, match="Slug inválido"):
            CompanyRepository.create(
                db,
                {   "name":"Carozzi S.A",
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
        with pytest.raises(RuntimeError, match="Error interno"):
            CompanyRepository.create(db, data)
        db.rollback.assert_called_once()

    def test_update_exitoso(self, db, fake_company, company_id):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.update(db,company_id, {"name":"Carozzi nuevo"})
        db.commit.assert_called_once()
        assert result == fake_company


    def test_update_sin_datos_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="no se enviaron datos para actualizar"):
            CompanyRepository.update(db, company_id, {})


    def test_update_campo_no_permitido_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="no permitidos"):
            CompanyRepository.update(db, company_id, {"is_active": False})

    
    def test_update_integrity_error_hace_rollback(self, db, fake_company, company_id):
        db.commit.side_effect = IntegrityError("name", {}, Exception("unique constraint name"))
        with patch.object(CompanyRepository, "get_by_id", return_value = fake_company):
            with pytest.raises(ValueError):
                CompanyRepository.update(db, company_id, {"name":"Nombre duplicado"})
        db.rollback.assert_called_once()

 
    def test_update_billing_plan_exitoso(self, db, fake_company, company_id):
        db.query().filter().first.return_value = fake_company
        result = CompanyRepository.update_billing_plan(db, company_id, BillingPlan.pro)
        db.commit.assert_called_once()
        assert result == fake_company

    def test_update_billing_plan_invalido_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="invalido"):
            CompanyRepository.update_billing_plan(db, company_id, "plan_inventado")
    
    def test_update_billing_plan_company_inexistente_retorna_none(self, db, company_id):
        db.query().filter().first.return_value = None
        result = CompanyRepository.update_billing_plan(db, company_id, BillingPlan.pro)
        assert result is None

    
    def test_deactivate_exitoso(self, db, fake_company, company_id):
        with patch.object(CompanyRepository, "get_by_id", return_value = fake_company):
            result = CompanyRepository.deactivate(db, company_id)
        assert result is True
        assert fake_company.is_active == False
        db.commit.assert_called_once()

    def test_deactivate_company_inexistente_retorna_false(self, db, company_id):
        with patch.object(CompanyRepository, "get_by_id", return_value =None):
            result = CompanyRepository.deactivate(db, company_id)
        assert result is False

    def test_deactivate_sqlalchemy_error_hace_rollback(self, db, fake_company, company_id):
        db.commit.side_effect = SQLAlchemyError("timeout")
        with patch.object(CompanyRepository, "get_by_id", return_value = fake_company):
            with pytest.raises(RuntimeError, match="Error interno"):
                CompanyRepository.deactivate(db, company_id)
            db.rollback.assert_called_once()