import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from app.modules.compañias.models import (
    BillingPlan, Company, CompanyRole, CompanyUser, StructureType
)
from app.modules.compañias.services.company_service import CompanyService

class TestCrearCompañia:
    
    def test_strucutra_divisional_con_plan_prueba_lanza_error(self,db):
        with pytest.raises(ValueError, match="no soporta"):
            CompanyService.crear_compañia(
                db,    
                {
                    "name": "Test",
                    "slug": "test",
                    "billing_plan": BillingPlan.prueba,
                    "structure_type": StructureType.divisional,
                }
            )
    
    @patch("app.modules.compañias.repository.CompanyRepository.create")
    def test_plan_prueba_aplica_limites_correctos(self, mock_create,db):
        mock_create.return_value = MagicMock(spec=Company)
        CompanyService.crear_compañia(
            db,
            {
                "name":"Test",
                "slug":"test",
                "billing_plan": BillingPlan.prueba,
                "structure_type": StructureType.simple,
            }
        )
        datos_enviados = mock_create.call_args[0][1]
        assert datos_enviados["max_users_per_plant"] == 5 

    @patch("app.modules.compañias.repository.CompanyRepository.create")
    def test_plan_pro_aplica_max_plants_correcto(self, mock_create, db):
        mock_create.return_value = MagicMock(spec=Company)
        CompanyService.crear_compañia(
            db,
            {
                "name":"Test",
                "slug": "slug",
                "billing_plan": BillingPlan.pro,
                "structure_type": StructureType.divisional,

            }    
        )
        datos_enviados = mock_create.call_args[0][1]
        assert datos_enviados["max_plans"] == 20


    @patch("app.modules.compañias.repository.CompanyRepository.create")
    def test_plan_empresas_aplica_max_children_correcto(self,mock_create, db):
        mock_create.return_value = MagicMock(spec=Company)
        CompanyService.crear_compañia(
            db, 
                {
                    "name":"Test",
                    "slug":"test",
                    "billing_plan": BillingPlan.empresas,
                    "structure_type": StructureType.corporativo,
                }
        )

        datos_enviados = mock_create.call_args[0][1]
        assert datos_enviados["max_children"] == 22

class TestObtenerCompañia:

    @patch("app.modules.compañias.repository.get_by_id", return_value=None)
    def test_compañia_inexistente_lanza_error(self, mock_get, db, admin_id):
        with pytest.raises(ValueError, match="no encontrada"):
            CompanyService.obtener_compañia(db, uuid4(), admin_id)
    
    @patch("app.modules.compañias.repository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.supervisor)
    def test_el_supervisor_no_puede_ver_metricas_de_la_compañia(
        self, 
        mock_role, 
        mock_get, 
        db,
        fake_company_pro,
        user_id):

        mock_get.return_value = fake_company_pro
        with pytest.raises(PermissionError):
            CompanyService.obtener_compañia(db,fake_company_pro.id, user_id)
    
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role",
            return_value=CompanyRole.tecnicos)
    def test_tecnicos_no_pueden_ver_metricas_de_la_compañia(
        self,
        mock_role,
        mock_get, db,
        fake_company_pro, 
        user_id
    ):
        mock_get.return_value = fake_company_pro
        with pytest.raises(PermissionError):
            CompanyService.obtener_compañia(db, fake_company_pro.id, user_id)
    

    @patch("app.modules.compañias.repository.CompanyRepository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.admin)
    def test_el_admin_puede_obtener_la_compañia(
        self,
        mock_role,
        mock_get,
        db,
        fake_company_pro,
        admin_id
    ):
        mock_get.return_value = fake_company_pro
        result = CompanyService.obtener_compañia(db, fake_company_pro.id, admin_id)
        assert result == fake_company_pro


    @patch("app.modules.compañias.repository.CompanyRepository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.auditor)
    def test_el_auditor_puede_obtener_compañia(
        self,
        mock_role,
        mock_get,
        db, 
        fake_company_pro,
        user_id
    ):
        mock_get.return_value = fake_company_pro
        result = CompanyService.obtener_compañia(db, fake_company_pro.id, user_id)
        assert result == fake_company_pro


class TestCambiarPlan:

    @patch("app.modules.compañias.repository.CompanyRepository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.supervisor)
    
    def test_si_no_es_admin_no_puede_cambiar_plan(
        self,
        mock_role,
        mock_get,
        db,
        fake_company_pro,
        user_id
    ):
        mock_get.return_value = fake_company_pro
        with pytest.raises(PermissionError):
            CompanyService.cambiar_plan(db, fake_company_pro.id, BillingPlan.basico, user_id)

    @patch("app.modules.compañias.repository.CompanyRepository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.admin)
    @patch("app.modules.compañias.repository.CompanyRepostory.count_children", return_value=1)
    def test_intenta_degradar_a_prueba_el_plan_y_contiene_hijos_lanza_error(
        self,
        mock_count,
        mock_role,
        mock_get,
        db,
        fake_company_pro,
        admin_id
    ):
        
        mock_get.return_value = fake_company_pro
        with pytest.raises(ValueError, match="Contiene subsidiarias activas"):
            CompanyService.cambiar_plan(db, fake_company_pro.id, BillingPlan.prueba, admin_id)


    @patch("app.modules.compañias.repository.CompanyRepository.get_by_id")
    @patch("app.modules.compañias.repository.CompanyUserRepository.get_user_role", 
           return_value=CompanyRole.admin)
    @patch("app.modules.compañias.repository.CompanyRepostory.count_children", return_value=0)
    def test_structure_corporatvo_contiene_plan_pro_debe_lanzar_error(
        self,
        mock_count,
        mock_role,
        mock_get,
        db,
        fake_company_pro,
        admin_id
    ):
        pass
         