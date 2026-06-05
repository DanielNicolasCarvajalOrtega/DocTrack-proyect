import logging
import re
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from sqlalchemy import exists
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.models import Company, BillingPlan, IndustryType, StructureType
from app.modules.compañias.constants import (BILLING_PLAN_LIMITS, COMPANY_ALLOWED_UPDATE_FIELDS) 
logger = logging.getLogger(__name__)


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ValueError("El nombre no puede estar vacío.")
    
    clean = name.strip()
    if len(clean) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres.")
    if len(clean) > 200:
        raise ValueError("El nombre no puede superar los 200 caracteres.")
    
    # Bloquea caracteres usados en XSS e inyecciones
    if re.search(r"[<>\"'`;]", clean):
        raise ValueError("El nombre contiene caracteres no permitidos.")
    
    # Solo permite letras, números, espacios y puntuación de negocio
    if not re.match(r"^[\w\s\-\.\,\&\(\)áéíóúÁÉÍÓÚñÑüÜ]+$", clean):
        raise ValueError("El nombre contiene caracteres no permitidos.")


def _validate_slug(slug : str) -> None:
    if not slug:
        raise ValueError("slug vacio error")
    if len(slug) > 100:
        raise ValueError("el slug no puede pasarse de 100 caract")
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug):
        raise ValueError("Slug inválido. Solo minúsculas, números y guiones.")
    

def _validate_color(color:str) ->None:
    if not color:
        return 
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError(f"Color inválido '{color}'. Formato esperado: #3B82F6")
    
def _validate_email(email:str) -> None:
    if not email:
        return 
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        raise ValueError(f"Email inválido: '{email}'")
    
def _validate_positive_int(value:int, field:str, min_value: int= 1)->None:
    if value is not None and value < min_value:
        raise ValueError(f"{field} debe ser como menos {min_value}")
    

def _validate_company_data(data:dict)-> None:
    for field, validator in _COMPANY_FIELD_VALIDATORS.items():
        if field in data:
            validator(data[field])


def _parse_integrity_error(origin:str, context:str = "") -> str:
    origin_lower = origin.lower()
    messages = {
        "slug": "el slug ya esta en uso",
        "name": "el nombre ya esta en uso",
        "company_user": "el usuario ya pertenece a una compañia",
        "contact_email": "el email ya esta registrado en otra compañias"
    }

    for key, msg in messages.items():
        if key in origin_lower:
            return msg
    return f"Conflicto de datos{' en ' + context if context else ''}. Verifica la información enviada."
    


COMPANY_ALLOWED_UPDATE_FIELDS = {
    "name", "slug", "billing_plan", "max_users",
    "max_plants", "max_storage_gb", "trial_ends_at", "subscription_ends_at",
    "contact_email", "contact_phone", "address","logo_url","primary_color",
}

COMPANY_USER_ALLOWED_UPDATE_FIELDS = {
    "role",
}

_COMPANY_FIELD_VALIDATORS = {
    "slug": _validate_slug,
    "primary_color": _validate_color,
    "contact_email": _validate_email,
    "name": _validate_name,
    "max_users":     lambda v: _validate_positive_int(v, "max_users"),
    "max_plants":    lambda v: _validate_positive_int(v, "max_plants"),
    "max_storage_gb":lambda v: _validate_positive_int(v, "max_storage_gb"),
}


class CompanyRepository:

    """
    Acceso a datos de Company.
    - Retorna objetos ORM o None. Nunca JsonResponse.
    - Los límites del plan (max_*) se aplican via apply_billing_plan.
      El admin nunca los modifica directamente — los define el plan.
    """
    @staticmethod
    def create(db:Session, company_data:dict) -> Company:
        """ crea nueva compañia con validacion de datos primero"""

        missing = [f for f in ("name", "slug") if not company_data.get(f)]
        if missing:
            raise ValueError(f"campos obligatorios faltantes {missing}")
        _validate_company_data(company_data)

        try:
            db_company = Company(**company_data)
            db.add(db_company)
            db.commit()
            db.refresh(db_company)
            logger.info(f"[Company.create] id={db_company.id} slug ='{db_company.slug}")
            return db_company
        except IntegrityError as err:
            db.rollback()
            logger.warning(f"[Company.create] slug= {company_data.get("slug")} -> {err.orig}")
            raise ValueError(_parse_integrity_error(str(err.orig), "Company"))
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[Company.create] SQLAlchemyError - {err}")
            raise RuntimeError("Error interno en base de datos")
        
    @staticmethod
    def update(db:Session, company_id: UUID, update_data: dict[str, Any]) -> Optional[Company]:
        """ 
        Actualiza solo los campos permitidos por la whitelist.
        Los límites del plan (max_*) NO están en la whitelist —
        solo se modifican via apply_billing_plan.
        """
        if not update_data:
            raise ValueError("no se enviaron datos para actualizar")
        
        invalid_fields = set(update_data.keys()) - COMPANY_ALLOWED_UPDATE_FIELDS
        if invalid_fields:
            raise ValueError(f"campos no permitidos: {invalid_fields}")
        _validate_company_data(update_data)

        db_company = CompanyRepository.get_by_id(db, company_id)
        if not db_company:
            return None
        
        try:
            for key, value in update_data.items():
                setattr(db_company, key, value)
            db.commit()
            db.refresh(db_company)
            logger.info(f"[Company.update] id={company_id} campos= {list(update_data.keys())}")
            return db_company
        except IntegrityError as err:
            db.rollback()
            logger.warning(f"[Company.update] IntegrityError id={company_id}: error:{ err.orig}")
            raise ValueError(_parse_integrity_error(str(err.orig), "Company"))
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[Company.update] SQLAlchemyError id={company_id} - {err}")
            raise RuntimeError("Error en la base de datos")
        
    @staticmethod
    def apply_billng_plan(
        db:Session,
        company_id:UUID,
        new_plan: BillingPlan,
        subscriptions_ends_at: Optional[datetime] = None,
    )-> Optional[Company]:
        
        """
        Cambia el plan y aplica automáticamente todos los límites.
        FIX: update_billing_plan anterior solo cambiaba billing_plan,
        no aplicaba max_users_per_plant, max_plants, max_storage_gb, max_children.
        Este método reemplaza update_billing_plan.
        """

        if not isinstance(new_plan, BillingPlan):
            raise ValueError(f"Plan inválido. Opciones: {[p.value for p in BillingPlan]}")
        
        db_company = CompanyRepository.get_by_id(db, company_id)
        if not db_company:
            return None
        
        limits = BILLING_PLAN_LIMITS[new_plan.value]

        try:
            db_company.billing_plan = new_plan
            db_company.max_users_per_plant = limits["max_users_per_plant"]
            db_company.max_plants = limits["max_plants"]
            db_company.max_storage_gb = limits["max_storage_gb"]
            db_company.max_children = limits["max_children"]
            if subscriptions_ends_at:
                db_company.subscription_ends_at = subscriptions_ends_at
            db.commit()
            db.refresh(db_company)
            logger.info(f"[Company.apply_billing_plan] id={company_id} plan='{new_plan.value}'")
            return db_company
        
        except SQLAlchemyError as err:
            db.rollback()   
            logger.error(f"[Company.apply_billing_plan] id={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos.") 

    @staticmethod
    def update_billing_plan(
        db:Session,
        company_id:UUID,
        new_plan: BillingPlan,
        subscription_ends_at: Optional[datetime] = None,
    ) -> Optional[Company]:
        
        """ actualiza el plan de facturacion de la compañia"""
        if not isinstance(new_plan, BillingPlan):
            raise ValueError(f"plan invalido. Opciones : {[p.value for p in BillingPlan]}")
        
        db_company = CompanyRepository.get_by_id(db, company_id)
        if not db_company:
            return None
        try:
            db_company.billing_plan = new_plan
            if  subscription_ends_at:
                db_company.subscription_ends_at = subscription_ends_at
            db.commit()
            db.refresh(db_company)
            logger.info(f"[Company.update_billing_plan] id={company_id} - plan={new_plan}")
            return db_company
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[Company.update_billing_plan] id={company_id} -- {err}")
            raise RuntimeError("Error interno de base de datos")

    @staticmethod
    def deactivate(db: Session, company_id:UUID) -> bool:    
        """ soft delte marca is_active=False """
        db_company = CompanyRepository.get_by_id(db,company_id)
        if not db_company:
            return False
        try:
            db_company.is_active = False
            db.commit()
            logger.info(f"[Company.deactivate] id={company_id}")
            return True
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[Company.deactivate] id={company_id} -- {err}")
            raise RuntimeError("Error interno de la base de datos")
    

    @staticmethod
    def get_by_id(db:Session, company_id:UUID) -> Optional[Company]:
        try:
            return db.query(Company).filter(
                Company.id == company_id,
                Company.is_active == True
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"id = {company_id} - {e}")
            raise RuntimeError("error interno al consultar la base de datos")

    @staticmethod
    def get_by_slug(db:Session, slug:str) -> Optional[Company]:
        _validate_slug(slug)

        try:
            return db.query(Company).filter(
                Company.slug == slug.strip(),
                Company.is_active == True,
            ).first()
        
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_by_slug] slug='{slug}' — {err}")
            raise RuntimeError("error interno al consultar la base de datos")
    
    @staticmethod
    def get_by_email(db:Session, contact_email:str) -> Optional[Company]:
        _validate_email(contact_email)
        try:
            return db.query(Company).filter(
                Company.contact_email == contact_email,
                Company.is_active == True
            ).first()

        except SQLAlchemyError as err:
            logger.error(f"[Company.get_by_email] email='{contact_email}' — {err}")
            raise RuntimeError("error interno al consultar la base de datos")
    
    @staticmethod
    def get_all_active(db:Session, skip:int = 0, limit: int = 40) -> list[Company]:
        """
        Lista paginada de compañías raíz activas.
        FIX: filtra parent_id IS NULL para no incluir subsidiarias.
        """
        if skip < 0:
            raise ValueError(" skip no puede ser negativo ")
        limit = min(max(limit, 1), 100)
        try:
            return db.query(Company).filter(
                Company.is_active == True,
                Company.parent_id == None,
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f" company active = [Company.get_all_active] - {err}")
            raise RuntimeError("error interno al consultar la base de datos")
        
    @staticmethod
    def get_all_billing_plan(db:Session, billing_plan: BillingPlan, skip:int=0, limit:int = 20)-> list[Company]:
        """ compañias con planes de pago activos """
        if not isinstance(billing_plan, BillingPlan):
            raise ValueError(f"plan invalido - planes validos: {[p.value for p in BillingPlan]}")
        limit = min(max(limit,1), 100)
        try:
            return db.query(Company).filter(
                Company.billing_plan == billing_plan,
                Company.is_active == True
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_all_billing_plan] plan='{billing_plan}' — {err}")
            raise RuntimeError("error interno al consultar la base de datos")

    @staticmethod
    def get_trials_expiring_soon(db:Session, before: datetime) -> list[Company]:
        """ planes de prueba que van a vencer antes de la fecha 
            FIX: era Company.billing_plan == BillingPlan (la clase) → nunca retornaba nada
        """
        if not isinstance(before, datetime):
            raise ValueError("before debe ser un datetime valido")
        try:
            return db.query(Company).filter(
                Company.billing_plan == BillingPlan.prueba, # FIX correjido
                Company.trial_ends_at <= before,
                Company.trial_ends_at.isnot(None),
                Company.is_active == True,
            ).all()
        
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_trials_expiring_soon] before={before} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
    
    @staticmethod
    def get_by_industry(db:Session, industry: IndustryType, skip:int=0, limit:int = 20) -> list[Company]:
        """compañias activas filtradas por industria"""
        if not isinstance(industry, IndustryType):
            raise ValueError(f"Industria invalida, Opciones: {[i.value for i in IndustryType]}")
    
        limit = min(max(limit, 1), 100)
        try:
            return db.query(Company).filter(
                Company.industry == industry,
                Company.is_active == True,
            ).offset(skip).limit(limit).all()
        
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_by_industry] industry='{industry}' — {err}")

            raise RuntimeError("Error interno en la base de datos")
    

    @staticmethod
    def get_by_structure(db:Session, structure:StructureType, skip: int = 0, limit:int =20)-> list[Company]:
        """
        compañias activas filtradas por tipo de estructura
        """

        if not isinstance(structure, StructureType):
            raise ValueError(f"Estructura inválida. Opciones: {[s.value for s in StructureType]}")
        
        limit = min(max(limit, 1), 100)
        try:
            return db.query(Company).filter(
                Company.structure_type == structure,
                Company.is_active == True,
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_by_structure] structure='{structure}' — {err}")
            raise RuntimeError("Error interno en la base de datos")


    @staticmethod
    def get_subscriptions_expiring_soon(db:Session, before:datetime) -> list[Company]:
        """ proximas subscripciones a vencer antes de la fecha  (before)"""
        if not isinstance(before,  datetime):
            raise ValueError("before debe ser un datetime valido")
        
        try:
            return db.query(Company).filter(
                Company.subscription_ends_at <= before,
                Company.subscription_ends_at.isnot(None),
                Company.is_active == True
            ).all()
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_trials_expiring_soon] before={before} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
    
   
    @staticmethod
    def get_all_children_by_parent(db:Session, parent_id: UUID) -> list[Company]:
        """  
        Subsidiarias activas de una compañía parent.
        """

        try:
            return db.query(Company).filter(
                Company.parent_id == parent_id,
                Company.is_active == True,
            ).all()
        
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_children] parent={parent_id} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")

    @staticmethod
    def count_children(db:Session, parent_id: UUID)-> int:
        """cuanta subsidiaria activas de un parent"""

        try:
            return db.query(Company).filter(
                Company.parent_id == parent_id,
                Company.is_active == True
            ).count()
        except SQLAlchemyError as err:
            logger.error(f"[Company.count_children] parent={parent_id} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
    
    @staticmethod
    def get_root_compaies(db:Session, skip:int = 0, limit:int = 20)-> list[Company]:
        """Compañías raíz activas — las que no tienen parent."""
        if skip < 0:
            raise ValueError("skip' no puede ser negativo.")
        limit = min(max(limit, 1), 100)
        try:
            return db.query(Company).filter(
                Company.parent_id == None,
                Company.is_active == True
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_root_companies] — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
