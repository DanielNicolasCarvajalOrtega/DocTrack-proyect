import logging
import re
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from sqlalchemy import exists
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.models import Company, CompanyRole, BillingPlan, CompanyUser
from app.modules.compañias.repository import repository as repo
from app.modules.compañias.repository.repository import CompanyRepository
from app.modules.compañias.repository.repository import (
    COMPANY_ALLOWED_UPDATE_FIELDS, COMPANY_USER_ALLOWED_UPDATE_FIELDS
)


logger = logging.getLogger(__name__)

@staticmethod
def create(db:Session, company_data:dict) -> Company:
    """ crea nueva compañia con validacion de datos primero"""

    missing = [f for f in ("nane", "slug") if not company_data.get(f)]
    if missing:
        raise ValueError(f"campos obligatorios faltantes {missing}")
    repo._validate_company_data(company_data)

    try:
        db_company = Company(**company_data)
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        logger.info(f"[Company.create] id={db_company.id} slug ='{db_company.slug}")
    except IntegrityError as err:
        db.rollback()
        logger.warning(f"[Company.create] slug= {company_data.get("slug")} -> {err.orig}")
        raise ValueError(repo._parse_integrity_error(str(err.orig), "Company"))
    except SQLAlchemyError as err:
        db.rollback()
        logger.error(f"[Company.create] SQLAlchemyError - {err}")
        raise RuntimeError("Error interno en base de datos")
    
@staticmethod
def update(db:Session, company_id: UUID, update_data: dict[str, Any]) -> Optional[Company]:
    """ guard clauses → whitelist → validar formatos → persisten """
    if not update_data:
        raise ValueError("no se enviaron datos para actualizar")
    
    invalid_fields = set(update_data.keys()) - COMPANY_ALLOWED_UPDATE_FIELDS
    if invalid_fields:
        raise ValueError(f"campos no permitidos: {invalid_fields}")
    repo._validate_company_data(update_data)

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
        logger.warning(f"[Company.update] IntegrityError id={company_id}: error:{ err.orig}")
        raise ValueError(repo._parse_integrity_error(str(err.orig), "Company"))
    except SQLAlchemyError as err:
        db.rollback()
        logger.error(f"[Company.update] SQLAlchemyError id={company_id} - {err}")
        raise RuntimeError("Error en la base de datos")
    

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
    if not company_id:
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
    

class CompanyUserRepository:

    @staticmethod
    def _get_active_user_is_part_of_the_company(db:Session, company_id:UUID, user_id: UUID) -> Optional[CompanyUser]:
        try:
            return db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
                CompanyUser.is_active == True,
            ).first()
        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser. _get_active_user_is_part_of_the_company]"
                         f"company_id ={company_id} - user={user_id} - error: {err}")
            raise RuntimeError("error interno al consultar la base de datos")
        
    @staticmethod
    def is_user_in_company(db:Session, company_id: UUID, user_id:UUID) -> bool:
        """ verifica que sea parte de la compañia
            importante -- no trae el objeto
        """
        try:
            return db.query(exists().where(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
                CompanyUser.is_active == True
            )
            ).scalar()

        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.is_user_in_company] company={company_id} user={user_id} - {err}")
            raise RuntimeError("error interno en base de datos")
        
    @staticmethod
    def get_user_role(db:Session, company_id:UUID, user_id:UUID) -> Optional[CompanyRole]:
        """ rol activo de un usuario dentro de la compañia"""
        user_is_active = CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)
        return user_is_active.rol if user_is_active else None

    
    @staticmethod
    def get_user_by_company(db:Session, company_id:UUID, role:Optional[CompanyRole] = None,skip:int=0, limit:int=20) ->list[CompanyUser]:
        """ miembros activos en la compañia  filtrado por rol"""

        if skip < 0:
            raise ValueError("skip no puede ser negarigo")
        if role is not None and not isinstance(role, CompanyRole):
            raise ValueError(f"Rol invalido. Opciones: {[r.value for r in CompanyRole]}")
        limit = min(max(limit,1),100)

        try:
            query = db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.is_active == True   
            )
            if role:
                query = query.filter(CompanyUser.role == role)
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.get_user_by_company] company={company_id} - error= {err}")
            raise RuntimeError("error interno en la base de datos")
        
    
    @staticmethod
    def get_companies_by_user(db:Session, user_id:UUID) -> list[CompanyUser]:
        """ compañias activas a las que pertenece un usuario  para dashboard"""

        try:
            return db.query(CompanyUser).filter(
                CompanyUser.user_id == user_id,
                CompanyUser.is_active == True
            ).all()

        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.get_companies_by_user] user={user_id} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")
        
    @staticmethod
    def count_active_users(db:Session, company_id:UUID)-> int:
        try:
            return db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.is_active == True
            ).count()
        
        except SQLAlchemyError as e:
            logger.error(f"[CompanyUser.count_active_users] company={company_id} — {e}")
            raise RuntimeError("Error interno al consultar la base de datos.")
        

    @staticmethod
    def add_user_to_company(db:Session, company_id: UUID, user_id:UUID, role:CompanyRole, invited_by_id:Optional[UUID]=None)-> CompanyUser:
        if not isinstance(role, CompanyRole):
            raise ValueError(f"rol invalido: opciones {[r.value for r in CompanyRole]}")
        if invited_by_id and invited_by_id == user_id:
            raise ValueError("un usuario no puede invitarse o agregarse a si mismo")

        try:
            membership = CompanyUser(
                company_id = company_id,
                user_id = user_id,
                role = role,
                invited_by_id = invited_by_id,
                joined_at = datetime.now()
            )

            db.add(membership)
            db.commit()
            db.refresh(membership)
            logger.info(f"[CompanyUser.add_user_to_company] user={user_id} company={company_id} rol='{role}'")
            return membership
        except IntegrityError as err:
            db.rollback()
            logger.warning(f"[CompanyUser.add_user_to_company] IntegrityError user={user_id} company={company_id}: {err.orig}")
            raise ValueError(repo._parse_integrity_error(str(err.orig), "CompanyUser"))
        
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.add] SQLAlchemyError user={user_id} company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos.")


    @staticmethod
    def update_user_role(db:Session, company_id:UUID, user_id: UUID, new_role: CompanyRole) -> Optional[CompanyUser]:
        """Actualiza el rol. Guard clauses: rol válido → es miembro → rol diferente → persistir"""
        if not isinstance(new_role, CompanyRole):
            raise ValueError(f"Rol invalido, Optciones {[r.value for r in CompanyRole]}")
        
        membership = CompanyUserRepository._get_active_user_is_part_of_the_company(db, user_id, company_id)
        if not membership:
            return None
        
        if membership.rol == new_role:
            raise ValueError(f"El usuario ya tiene el rol -> {new_role.value}")
        
        try:
            old_role = membership.role
            membership.rol = new_role
            db.commit()
            db.refresh(membership)
            logger.info(f"[CompanyUser.update_user_role] user={user_id} - {old_role} - {new_role} ")
            return membership
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.update_user_role] user={user_id} company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos.")

    @staticmethod
    def remove_user_from_company(db:Session, company_id:UUID, user_id:UUID) -> bool:
        """ soft delete de la compañia, si no es miebro activo False"""

        membership = CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)
        if not membership:
            return False
        try:
            membership.is_active = False
            db.commit()
            logger.info(f"[CompanyUser.remove_user_from_company] user={user_id} company={company_id}")
            return True
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.remove_user_from_company] user={user_id} company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos.")


