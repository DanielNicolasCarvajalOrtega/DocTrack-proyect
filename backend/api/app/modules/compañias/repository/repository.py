import logging
import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import exists
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.models import Company, CompanyRole, BillingPlan

logger = logging.getLogger(__name__)

COMPANY_ALLOWED_UPDATE_FIELDS = {
    "name", "slug", "billing_plan", "max_users",
    "max_plants", "max_storage_gb", "trial_ends_at", "subscription_ends_at",
    "contact_email", "contact_phone", "address","logo_url","primary_color",
}

COMPANY_USER_ALLOWED_UPDATE_FIELDS = {
    "role",
}

_COMPANY_FIELD_VALIDATORS = {
    "slug":          _validate_slug,
    "primary_color": _validate_color,
    "contact_email": _validate_email,
    "name":          _validate_name,
    "max_users":     lambda v: _validate_positive_int(v, "max_users"),
    "max_plants":    lambda v: _validate_positive_int(v, "max_plants"),
    "max_storage_gb":lambda v: _validate_positive_int(v, "max_storage_gb"),
}
        
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
    
def _validate_email(email:str)- > None:
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
    


class CompanyRepository:

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
                Company.is_active == True
            ).first()
        
        except SQLAlchemyError as err:
            logger.error(f"slug = {slug} - {err}")
            raise RuntimeError("error interno al consultar la base de datos")
    
    @staticmethod
    def get_by_email(db:Session, contact_email:str) -> Optional[Company]:
        _validate_email(contact_email)
        try:
            db.query(Company).filter(
                Company.contact_email == contact_email,
                Company.is_active == True
            ).first()

        except SQLAlchemyError as err:
            logger.error(f"contact email = {contact_email} - {err}")
            raise RuntimeError("error interno al consultar la base de datos")
    
    @staticmethod
    def get_all_active(db:Session, skip:int = 0, limit: int = 40) -> list[Company]:
        if skip < 0:
            raise ValueError(" skip no puede ser negativo ")
        limit = min(max(limit, 1), 100)
        try:
            return db.query(Company).filter(
                Company.is_active == True,
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f" company active = [Company.get_all_active] - {err}")
            raise RuntimeError("error interno al consultar la base de datos")
        
    @staticmethod
    def get_all_billing_plan(db:Session, billing_plan: BillingPlan, skip:int=0, limit:int = 20)-> list[Company]:
        """ compañias con planes de pago activoas """
        if not isinstance(billing_plan, BillingPlan):
            raise ValueError(f"plan invalido - planes validos: {[p.value for p in BillingPlan]}")
        limit = min(max(limit,1), 100)
        try:
            return db.query(Company).filter(
                Company.billing_plan == billing_plan,
                Company.is_active == True
            ).offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"plan = {billing_plan} -- {err}")
            raise RuntimeError("error interno al consultar la base de datos")

    @staticmethod
    def get_trials_expiring_soon(db:Session, before: datetime) -> list[Company]:
        """ planes de prueba que van a vencer antes de la fecha """
        if not isinstance(before, datetime):
            raise ValueError("before debe ser un datetime valido")
        try:
            return db.query(Company).filter(
                Company.billing_plan == BillingPlan,
                Company.trial_ends_at <= before,
                Company.trial_ends_at.isnot(None),
                Company.is_active == True,
            ).all()
        
        except SQLAlchemyError as err:
            logger.error(f"[Company.get_trials_expiring_soon] before={before} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
        

    @staticmethod
    def get_subscriptions_expiring_soon(db:Session, before:datetime) -> list[Company]:
        """ proximas subscripciones a vencer"""
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
    
    

