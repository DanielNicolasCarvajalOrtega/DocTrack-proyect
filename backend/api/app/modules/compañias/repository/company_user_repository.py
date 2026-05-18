import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import exists
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.modules.compañias.models import CompanyRole, CompanyUser
from app.modules.compañias.repository import repository as repo
from app.modules.compañias.repository.repository import _parse_integrity_error
from app.modules.compañias.repository.repository import (
    COMPANY_ALLOWED_UPDATE_FIELDS, COMPANY_USER_ALLOWED_UPDATE_FIELDS
)

logger = logging.getLogger(__name__)

class CompanyUserRepository:
    """
    Acceso a datos de CompanyUser.
    Gestiona membresías, roles e invitaciones.
    La validación de max_users_per_plant

    """

    @staticmethod
    def _get_active_membership(db:Session, company_id: UUID, user_id:UUID) -> Optional[CompanyUser]:
        """
        Membresía activa de un usuario en una compañía.
        Método interno reutilizado por get_user_role, update_user_role y remove.
        Solo retorna membresías con is_active=True.
        """
        try: 
            return db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
                CompanyUser.is_active == True,
            ).first()
        
        except SQLAlchemyError as err:
            logger.error(
                f"[CompanyUser._get_active_membership] "
                f"company={company_id} user={user_id} — {err}"
            )
            raise RuntimeError("Error interno al consultar la base de datos")

    
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
    def get_user_role(db:Session, company_id:UUID, user_id:UUID) -> Optional[CompanyRole]:
        """ rol activo de un usuario dentro de la compañia"""
        membership = CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)
        return membership.role if membership else None


    @staticmethod
    def is_users_in_company(db:Session, company_id:UUID, user_id:UUID) -> bool:
        """
        verifica membresia activa con exists
        mas eficiente que first - asi no trae el objeto completo
        """

        try:
            return db.query(
                exists().where(
                    CompanyUser.company_id == company_id,
                    CompanyUser.user_id == user_id,
                    CompanyUser.is_active == True
                )
            ).scalar()
        
        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.is_user_in_company] company={company_id} user={user_id} — {err}")
            raise RuntimeError("Error interno en base de datos")


    @staticmethod
    def get_users_by_company(db:Session, company_id:UUID, role:Optional[CompanyRole] = None,skip:int=0, limit:int=20) ->list[CompanyUser]:
        """ miembros activos en la compañia  filtrado por rol"""
        if skip < 0:
            raise ValueError("skip no puede ser negativo")
        if role is not None and not isinstance(role, CompanyRole):
            raise ValueError(f"Rol inválido. Opciones: {[r.value for r in CompanyRole]}")
        limit = min(max(limit,1),100)

        try:
            query = db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.is_active == True,   
            )
            if role:
                query = query.filter(CompanyUser.role == role)
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.get_user_by_company] company={company_id} - error= {err}")
            raise RuntimeError("error interno en la base de datos")
        
    
    @staticmethod
    def get_companies_by_user(db:Session, user_id:UUID) -> list[CompanyUser]:
        """ compañias activas a las que pertenece un usuario - para dashboard"""

        try:
            return db.query(CompanyUser).filter(
                CompanyUser.user_id == user_id,
                CompanyUser.is_active == True
            ).all()

        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.get_companies_by_user] user={user_id} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos")
        
    @staticmethod
    def count_active_users(db:Session, company_id:UUID)-> int:
        """
        Cuenta miembros activos.
        El Service lo compara con max_users_per_plant x max_plants
        antes de agregar un nuevo miembro.
        """
        try:
            return db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.is_active == True
            ).count()
        
        except SQLAlchemyError as e:
            logger.error(f"[CompanyUser.count_active_users] company={company_id} — {e}")
            raise RuntimeError("Error interno al consultar la base de datos")
        
    @staticmethod
    def count_users_by_role(db: Session, company_id: UUID, role: CompanyRole) -> int:
        """
        Cuenta miembros activos con un rol específico.
        Usado por el Service para verificar que no quede la compañía sin admins.
        FIX: faltaba try/except — un error de BD explotaba sin manejar.
        """
        if not isinstance(role,CompanyRole):
            raise ValueError(f"Rol inválido. Opciones: {[r.value for r in CompanyRole]}")
        
        try:
            return db.query(CompanyUser).filter(
                CompanyUser.company_id == company_id,
                CompanyUser.role == role,
                CompanyUser.is_active == True,
            ).count()
        except SQLAlchemyError as err:
            logger.error(f"[CompanyUser.count_users_by_role] company={company_id} role={role} — {err}")
            raise RuntimeError("Error interno al consultar la base de datos.")

    @staticmethod
    def add_user_to_company(db:Session, company_id: UUID, user_id:UUID, role:CompanyRole, invited_by_id:Optional[UUID]=None)-> CompanyUser:
        """
        Agrega un usuario a una compañía
        Guard clauses primero — lógica al final
        """
        # guard N1
        if not isinstance(role, CompanyRole):
            raise ValueError(f"rol inválido: opciones {[r.value for r in CompanyRole]}")
        # guard N2
        if invited_by_id and invited_by_id == user_id:
            raise ValueError("un usuario no puede invitarse o agregarse a si mismo")

        try:
            membership = CompanyUser(
                company_id = company_id,
                user_id = user_id,
                role = role,
                invited_by_id = invited_by_id,
                joined_at = datetime.utcnow(),
            )
            db.add(membership)
            db.commit()
            db.refresh(membership)
            logger.info(f"[CompanyUser.add_user_to_company]"
                        f"user={user_id} company={company_id} rol='{role}'")
            return membership
        
        except IntegrityError as err:
            db.rollback()
            logger.warning(f"[CompanyUser.add_user_to_company] IntegrityError user={user_id} company={company_id}: {err.orig}")
            raise ValueError(repo._parse_integrity_error(str(err.orig), "CompanyUser"))
        
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.add] SQLAlchemyError user={user_id} "
                         f"company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos")


    @staticmethod
    def update_user_role(db:Session, company_id:UUID, user_id: UUID, new_role: CompanyRole) -> Optional[CompanyUser]:
        """
        Actualiza el rol de un usuario.
        Guard clauses: rol válido -> es miembro -> rol diferente -> persistir.
        FIX: argumentos de _get_active_membership estaban invertidos
             (db, user_id, company_id) -> (db, company_id, user_id).
        """

        if not isinstance(new_role, CompanyRole):
            raise ValueError(f"Rol inválido, Opciones {[r.value for r in CompanyRole]}")
        
        membership = CompanyUserRepository._get_active_user_is_part_of_the_company(db,company_id, user_id)
        if not membership:
            return None
        
        if membership.role == new_role:
            raise ValueError(f"El usuario ya tiene el rol -> {new_role.value}")
        
        try:
            old_role = membership.role
            membership.role = new_role
            db.commit()
            db.refresh(membership)
            logger.info(f"[CompanyUser.update_user_role] "
                f"user={user_id} '{old_role.value}' → '{new_role.value}'")
            return membership
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.update_user_role] user={user_id} company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos.")

    @staticmethod
    def remove_user_from_company(db:Session, company_id:UUID, user_id:UUID) -> bool:
        """ soft delete de membresia - si no es miembro activo False """

        membership = CompanyUserRepository._get_active_user_is_part_of_the_company(db, company_id, user_id)
        if not membership:
            return False
        try:
            membership.is_active = False # modifica el objeto a false 
            db.commit()
            logger.info(f"[CompanyUser.remove_user_from_company] "
                        f"user={user_id} company={company_id}")
            return True # confirma que si se guardo en la base de datos 
        except SQLAlchemyError as err:
            db.rollback()
            logger.error(f"[CompanyUser.remove_user_from_company] user={user_id} company={company_id} — {err}")
            raise RuntimeError("Error interno de base de datos")
        

