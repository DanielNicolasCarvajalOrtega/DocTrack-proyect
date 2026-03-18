import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock, call
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.repository.repository import (
    CompanyRepository, _validate_color, _validate_company_data, 
    _validate_email, _validate_positive_int, _validate_slug)
from app.modules.compañias.repository.company_user_repository import CompanyUserRepository
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan


class TestCompanyUserRepositoryLectura:

    def test_is_user_in_company_true(self, db, company_id, user_id):
        db.query().scalar.return_value = True
        result = CompanyUserRepository.is_user_in_company(db, company_id, user_id)
        assert result is True

    
    def test_is_user_in_company_false(self, db, company_id, user_id):
        db.query().scalar.return_value = False
        result = CompanyUserRepository.is_user_in_company(db, company_id, user_id)
        assert result is False
    
    def test_is_user_in_company_error_db_lanza_runtime(self, db, company_id, user_id):
        db.query.side_effect = SQLAlchemyError("error")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyUserRepository.is_user_in_company(db, company_id, user_id)


    def test_get_user_role_retorna_rol(self,db, fake_membership, company_id, user_id):
        db.query().filter().first.return_value = fake_membership
        result = CompanyUserRepository.get_user_role(db, company_id, user_id)
        assert result == CompanyRole.tecnicos

    def test_get_user_role_retorna_none_si_no_es_miembro(self, db, company_id, user_id):
        db.query().filter().first.return_value = None
        result = CompanyUserRepository.get_user_role(db, company_id, user_id)
        assert result is None

    def test_get_users_by_company_sin_filtro(self, db, fake_membership, company_id):
        db.query().filter().offset().limit().all.return_value = [fake_membership]
        result = CompanyUserRepository.get_user_by_company(db, company_id)
        assert len(result) == 1

        
    def test_get_users_by_company_con_rol(self, db, fake_membership, company_id):
        db.query().filter().filter().offset().limit().all.return_value = [fake_membership]
        result = CompanyUserRepository.get_user_by_company(db, company_id, role =CompanyRole.tecnicos)
        assert fake_membership in result


    def test_get_users_by_company_skip_negativo_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="negativo"):
            CompanyUserRepository.get_user_by_company(db, company_id, skip=-1)


    def test_get_users_by_company_rol_invalido_lanza_error(self, db, company_id):
        with pytest.raises(ValueError, match="Rol inválido"):
            CompanyUserRepository.get_user_by_company(db, company_id, role="rol_inventado")

    def test_get_companies_by_user(self, db, fake_membership, user_id):
        db.query().filter().all.return_value = [fake_membership]
        result = CompanyUserRepository.get_companies_by_user(db, user_id)
        assert fake_membership in result

    def test_count_active_users(self, db, company_id):
        db.query().filter().count.return_value = 5
        result = CompanyUserRepository.count_active_users(db, company_id)
        assert result == 5

    def test_count_active_users_error_bd_lanza_runtime(self, db, company_id):
        db.query.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="Error interno"):
            CompanyUserRepository.count_active_users(db, company_id)

    def test_count_active_users_sin_miembros_retorna_cero(self, db, company_id):
        db.query().filter().count.return_value = 0
        result = CompanyUserRepository.count_active_users(db, company_id)
        assert result == 0

    def test_count_active_users_retorna_entero(self, db, company_id):
        db.query().filter().count.return_value = 7
        result = CompanyUserRepository.count_active_users(db, company_id)
        assert result == 7
        

class TestAddUserToCompany:

    def test_add_exitoso_retorna_membership(self, db, company_id, user_id):
        fake = MagicMock(spec=CompanyUser)
        with patch("app.modules.compañias.repository.company_user_repository.CompanyUser") as MockMembership:
            MockMembership.return_value = fake
            result = CompanyUserRepository.add_user_to_company(db, company_id, user_id, CompanyRole.tecnicos)
        
        assert result == fake

    def test_add_llama_add_commit_refresh_en_orden(self,db, company_id, user_id):
        fake = MagicMock(spec=CompanyUser)
        manager = MagicMock()
        db.add = manager.add
        db.commit = manager.commit
        db.refresh = manager.refresh

        with patch("app.modules.compañias.repository.company_user_repository.CompanyUser") as MockMembership:
            MockMembership.return_value = fake
            CompanyUserRepository.add_user_to_company(db, company_id, user_id, CompanyRole.tecnicos)
            assert manager.mock_calls == [
                call.add(fake),
                call.commit(),
                call.refresh(fake),
            ]
    
    def test_add_with_invited_by_success(self, db, company_id, user_id):
        """
        alguien diferente al user_id, puede ser agregado a la compañia
        """
        invited_by = uuid4() # -> cualquier id
        fake = MagicMock(spec = CompanyUser)
        with patch("app.modules.compañias.repository.company_user_repository.CompanyUser") as MockMembership:
            MockMembership.return_value = fake
            result = CompanyUserRepository.add_user_to_company(db,company_id, user_id, CompanyRole.operadores, invited_by_id=invited_by)
        assert result == fake


    def test_add_rol_invitado_lanza_error(self, db, company_id, user_id):
        with pytest.raises(ValueError, match="inválido"):
            CompanyUserRepository.add_user_to_company(
                db, company_id, user_id, "rol_inventado"
            )
    
    def test_add_rol_invalido_no_toca_la_db(self,db, company_id, user_id):
        with pytest.raises(ValueError, match="rol inválido"):
            CompanyUserRepository.add_user_to_company(
                db, company_id, user_id, "rol_invitado"
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_add_usuario_duplicado_integrity_error_hace_rollback(self, db, company_id, user_id):
        db.commit.side_effect = IntegrityError(
            "uq_company_user", {}, Exception("uq_company_user")
        )
        with pytest.raises(ValueError, match="pertenece"):
            CompanyUserRepository.add_user_to_company(db, company_id, user_id, CompanyRole.tecnicos)

        db.rollback.assert_called_once()


    def test_add_sqlalchemy_error_hace_rollback(self, db, company_id, user_id):
        db.commit.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="Error interno"):
            CompanyUserRepository.add_user_to_company(
                db, company_id, user_id, CompanyRole.tecnicos
            )

        db.rollback.assert_called_once()


class TestGetActiveMembership:

    def test_retorna_membership_activo(self, db ,user_id, company_id, fake_membership):
        mock_query  = db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = fake_membership
        result = CompanyUserRepository._get_active_user_is_part_of_the_company(db ,company_id, user_id)
        assert result == fake_membership

    def test_retorna_none_si_no_existe(self, db, user_id, company_id):
        db.query().filter().first.return_value = None
        result = CompanyUserRepository._get_active_user_is_part_of_the_company(db,company_id,user_id)
        assert result is None


    def test_retorna_none_si_membresi_no_esta_activa(self, db, fake_membership, company_id, user_id):
        """ is active == False no debe aparecer comno activo, no es membership de la compañia """
        fake_membership.is_active = False
        db.query().filter().first.return_value = None
        result = CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)
        assert result is None
    

    def test_error_db_lanza_runtime_error(self, db, company_id, user_id):
        db.query.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)

class TestUpdateUserRole:

    def test_update_exitoso_cambia_rol(self, db, fake_membership, company_id, user_id):
        fake_membership.role = CompanyRole.operadores
        db.query().filter().first.return_value = fake_membership

        result = CompanyUserRepository.update_user_role(
            db, company_id, user_id, CompanyRole.supervisor
        )

        assert result == fake_membership
        assert fake_membership.role == CompanyRole.supervisor
        db.commit.assert_called_once()

    
    def test_update_retorna_membership_actualizada(self, db, fake_membership, company_id, user_id):
        fake_membership.role = CompanyRole.operadores
        db.query().filter().first.return_value = fake_membership

        result = CompanyUserRepository.update_user_role(
            db, company_id, user_id, CompanyRole.tecnicos
        )

        assert result is not None
        assert result == fake_membership

    
    def test_update_rol_invalido_lanza_error(self, db, company_id, user_id):
        with pytest.raises(ValueError, match="Rol inválido"):
            CompanyUserRepository.update_user_role(
                db, company_id, user_id, "rol inventado"
            )
     
    def test_update_rol_invalido_no_consulta_bd(self, db, company_id, user_id):
        with pytest.raises(ValueError):
            CompanyUserRepository.update_user_role(
                db, company_id, user_id, "rol inventado"
            )
        db.query.assert_not_called()


    def test_update_usuario_no_miembro_retorna_none(self, db ,company_id, user_id):
        with patch.object(
            CompanyUserRepository,
            "_get_active_user_is_part_of_the_company",
            return_value = None
        ):
            result = CompanyUserRepository.update_user_role(
                db, company_id, user_id, CompanyRole.supervisor
            )

        assert result is None

    
    def test_update_mismo_rol_lanza_error(self, db, fake_membership, company_id, user_id):
        """ intenta cambiar el rol actual al mismo rol ej: tecnico cambia a tecnico """

        fake_membership.role = CompanyRole.tecnicos
        db.query().filter().first.return_value = fake_membership
        with pytest.raises(ValueError, match="El usuario ya tiene el rol"):
            CompanyUserRepository.update_user_role(
                db, company_id, user_id, CompanyRole.tecnicos
            )
    
    def test_update_mismo_rol_no_hace_commit(self, db, fake_membership, company_id, user_id):
        fake_membership.role = CompanyRole.tecnicos
        db.query().filter().first.return_value = fake_membership

        with pytest.raises(ValueError):
            CompanyUserRepository.update_user_role(
                db, company_id, user_id , CompanyRole.tecnicos
            )
        
        db.commit.assert_not_called()


    def test_update_sqlalchemy_error_hace_rollback(self, db, fake_membership, company_id, user_id):
        fake_membership.role = CompanyRole.operadores
        db.query().filter().first.return_value = fake_membership
        db.commit.side_effect = SQLAlchemyError("timeout")
 
        with pytest.raises(RuntimeError, match="Error interno"):
            CompanyUserRepository.update_user_role(
                db, company_id, user_id, CompanyRole.supervisor
            )
        db.rollback.assert_called_once()

    

class TestRemoveUserFromCompany:

    def test_remove_exitoso_retorna_true(self, db, fake_membership, company_id, user_id):
        db.query().filter().first.return_value = fake_membership
        result = CompanyUserRepository.remove_user_from_company(db, company_id, user_id)
        assert result is True

    
    def test_remove_hace_soft_delete(self, db, fake_membership, company_id, user_id):
        """
        no se elimina del registro de la db, solo queda desactivado y no se muestra en consultas
        de usuario, solo visible por el sistema por detras
        CompanyUser = is_active = False
        """
        db.query().filter().first.return_value = fake_membership
        CompanyUserRepository.remove_user_from_company(db, company_id, user_id)
        assert fake_membership.is_active is False


    def remove_sqlalchemy_error_hace_rollback(self, db, fake_membership, company_id, user_id):
        db.query().filter().first.return_value = fake_membership
        db.commit.side_effect = SQLAlchemyError("timeout")
        with pytest.raises(RuntimeError, match="error interno"):
            CompanyUserRepository.remove_user_from_company(db, company_id, user_id)
        db.rollback.assert_called_once()

    def test_remove_usuario_ya_inactivo_retorna_false(self, db, company_id, user_id):
        """ usuario ya removido - is_active = False ya no puede volver a removerse """
        db.query().filter().first.return_value = None  # el filtro is_active=True no lo encuentra
        result = CompanyUserRepository.remove_user_from_company(db, company_id, user_id)
        assert result is False