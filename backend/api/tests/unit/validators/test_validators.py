import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.modules.compañias.repository.repository import (
    CompanyRepository, _validate_color, _validate_company_data,
    _validate_email, _validate_positive_int, _validate_slug , _parse_integrity_error)
from app.modules.compañias.repository.company_repository import CompanyUserRepository
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan



class TestValidators:
    # validacion de SLUGS
    def test_slug_valido(self):
        _validate_slug("carozzi-chile")

    def test_slug_valido_con_numeros(self):
        _validate_slug("empresa-2026")

    def test_slug_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="vacio"):
            _validate_slug("")

    def test_slug_muy_largo_lanza_error(self):
        with pytest.raises(ValueError, match="100 caracteres"):
            _validate_slug("a"*100)

    def test_slug_con_mayuscula_lanza_error(self):
        with pytest.raises(ValueError, match="Slug Vacio"):
                _validate_slug("Carozzi-CompaÑia")
    
    def test_slug_con_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="Slug invalido"):
            _validate_slug("mi compañia")

    def test_slug_con_caracteres_especiales_lanza_error(self):
        with pytest.raises(ValueError, match="Slug invalido"):
            _validate_slug("empresa-/1")

    # validamos email

    def test_email_valido(self):
         _validate_email("contacto@carozzi.cl")

    def test_validate_none_no_lanza_(self):
        _validate_email(None)

    def test_validate_sin_arroba_lanza_error(self):
        _validate_email("contacto11.carozzi.cl")

    def test_validate_sin_dominio_lanza_error(self):
         _validate_email("contacto@")

    # validamos numero entero positivo

    def test_validate_numero_entero(self):
        _validate_positive_int(10, "max_users")
    
    def test_validate_cero_entero_lanza_error(self):
        with pytest.raises(ValueError, match="max_users"):
            _validate_positive_int(0, "max_users")

    def test_entero_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="max_users"):
            _validate_positive_int(-5, "max_users")

    def test_entero_none_no_lanza(self):
        _validate_positive_int(None, "max_users")

    
    # validamos 
    def test_parse_slug_duplicados(self):
        message = _parse_integrity_error("Unique constraint on slug")
        assert "slug" in message.lower()

    def test_parse_name_duplicated(self):
        message = _parse_integrity_error("Unique constraint on name")
        assert "name" in message.lower()
    
    def test_parse_uq_company_user(self):
        message = _parse_integrity_error("violates uq_company_user constraint")
        assert "pertenece" in message.lower()

    def test_parse_unknown_error(self):
        message = _parse_integrity_error("some unknown constraint", context="Company")
        assert "Conflicto" in message.lower()


    
class TestValidateCompanyData:

    def test_dict_completo_valido_no_lanza(self):
        _validate_company_data({
            "name":          "Carozzi S.A.",
            "slug":          "carozzi-chile",
            "primary_color": "#E3000F",
            "contact_email": "contacto@carozzi.cl",
            "max_users":     100,
            "max_plants":    10,
            "max_storage_gb":50,
        })
 
    def test_dict_parcial_valido_no_lanza(self): # campos parciales se validan
        _validate_company_data( 
            {
                "name": "Nestle Chile",
                "slug": "nestle-chile"
            }
        )

    def test_dict_vacio_no_lanza(self):
        _validate_company_data({}) # <- campos vacios

    def test_campos_extras_no_conocidos_se_ignoran(self):
        _validate_company_data( # campos fuera del dispatch table no provocan error aca - lo maneja la whitelist
            {
                "descripcion": "texto texto - texto",
                "address": "Plaza de armas"
            }
        )
    
    # slug 

    def test_slug_invalido_lanza_error(self):
        with pytest.raises(ValueError, match="Slug invalido"):
            _validate_company_data(
                {
                    "slug": "carozzi/[]"
                }
            )

    def test_slug_con_mayusculas_lanza_error(self):
        with pytest.raises(ValueError, match="Slug invalido"):
            _validate_company_data(
                {
                    "slug": "CarozzI"
                }
            )
    def test_slug_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="Slug vacio"):
            _validate_company_data(
                {
                    "slug": ""
                }
            )

    def test_slug_muy_largo_lanza_error(self):
         with pytest.raises(ValueError, match="Slug 100 caracteres"):
            _validate_company_data(
                {
                    "slug": "carozzi-" * 120
                }
            )
    
    # Nombre - name

    def test_name_muy_corto_lanza_error(self):
        with pytest.raises(ValueError, match="2 caracteres"):
            _validate_company_data(
                {
                    "name": "x"
                }
            )
    
    def test_name_solo_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="2 caracteres"):
            _validate_company_data(
                {
                    "name": "   "
                }
            )
    def test_name_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="2 caracteres"):
            _validate_company_data(
                {
                    "name": ""
                }
            )
    
    def test_name_none_lanza_error(self):
        with pytest.raises(ValueError, match="2 caracteres"):
            _validate_company_data(
                {
                    "name": None
                }
            )

    def test_email_invalido_lanza_error(self):
        with pytest.raises(ValueError, match="invalido"):
            _validate_company_data(
                {
                    "contact_email": "no-no-email"
                }
            )
    
    def test_email_sin_dominio_lanza_error(self):
        with pytest.raises(ValueError, match="invalido"):
            _validate_company_data(
                {
                    "contact_email": "correo@"
                }
            )
    
    def test_email_none_no_lanza_error(self):
        _validate_company_data(
            {
                "contact_email": None
            }
        )

    def test_max_users_cero_lanza_error(self):
        with pytest.raises(ValueError, match="max_users"):
            _validate_company_data(
                {
                    "max_users": 0
                }
            )

    def test_max_users_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="max_users"):
            _validate_company_data(
                {
                    "max_user": -19
                }
            )
    
    def test_max_users_ausente_no_lanza_error(self): 
            """ si max_users no esta en el data, este no se valida"""
            _validate_company_data(
                {
                    "name": "Nestle Talca"
                }
            )
    
    # plantas

    def test_max_plants_cero_lanza_error(self):
        with pytest.raises(ValueError, match="max_plants"):
            _validate_company_data(
                {
                    "max_plants": 0
                }
            )
    
    def test_max_plants_negative_lanza_error(self):
        with pytest.raises(ValueError, match="max_plants"):
            _validate_company_data(
                {
                    "max_plants": -8
                }
            )

    # almacenamiento maximo

    def test_max_storage_gb_cero_lanza_error(self):
        with pytest.raises(ValueError, match="max_storage_gb"):
            _validate_company_data(
                {
                    "max_storage_gb": 0
                }
            )
        
    def test_max_storage_negative_lanza_error(self):
        with pytest.raises(ValueError, match="max_storage_gb"):
            _validate_company_data(
                {
                    "max_storage_gb": -2
                }
            )

    # comportamiento del dispatch table

    def test_solo_valido_campos_presentes(self):
        """
        El dispatch table solo ejecuta validadores de campos que existen en el dict.
        Un slug ausente no debe lanzar error aunque el dict tenga campos inválidos en otras claves.
        """

        with pytest.raises(ValueError, match="invalido"):
            _validate_company_data(
                {
                    "primary_color": "-no-es-un-color"
                }
            )
        
    def test_primer_campo_invalido_detiene_validacion(self):
        with pytest.raises(ValueError):
            _validate_company_data(
                {
                    "slug": "Invalido",
                    "name": "xx"
                }
            )

    def test_multiples_campos_validos_pasan_todos(self):
        _validate_company_data(
            {
                "slug": "monster-energy",
                "name": "monster energy",
                "primary_color": "#399293",
                "contact_email": "info.monster@monsterenergy.com",
                "max_users":500,
                "max_plants": 8,
                "max_storage_gb": 100
            }
        )