from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.modules.users.models import User, UserRole
from app.modules.plantas.models import UserPlantAccess, Plant
from app.shared.exceptions import NotFoundException, ConflictException

class UserRepository:
    def __init__(self,db: Session):
        self.db = db
    

    def get_all(self, include_inactive:bool=False,
                role: Optional[UserRole] = None,
                plant_id: Optional[UUID] = None
                ) -> list[User]:
        
        
        query = self.db.query(User)

        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        if role:
            query = query.filter(User.role == role)

        if plant_id:
            query = query.join(UserPlantAccess).filter(
                UserPlantAccess.plan_id == plant_id
            )
        
        query = query.order_by(User.created_at.desc()).all()




    def get_by_id(self, user_id:UUID, raise_if_not_found:bool=True)-> User | None:
        """
        Args:
            user_id 
            raise_if_not_found: Si es true , lanza exception si no existe
        """

        user = (
             self.db.query(User)
             .filter(User.id == user_id, User.is_active == True)
             .options(
                joinedload(User.plant_accesses)
                .joinedload(UserPlantAccess.plant)
             ).first()
        )
        if not user and raise_if_not_found:
            raise NotFoundException("Usuario")        
        return user


    def get_by_email(self, email:str)-> User | None:
        """
        Obtener usuario por email
        incluye usuarios inactivos para dar mensajes especificos
        """
        return (
            self.db.query(User)
            .filter(User.email == email)
            .options(
                joinedload(User.plant_accesses)
                .joinedload(UserPlantAccess.plant)
            ).first()
        ) 
        
    def get_operators(self, plant_id:Optional[UUID] = None) -> list[User]:
        """OBTENERMOS OPERARIOS FILTRADOS POR PLANTA """
        return self.get_all(role=UserRole.OPERADORES, plant_id=plant_id)
    
    def get_technicians(self, plant_id:Optional[UUID]= None)-> list[User]:
        """ OBTENEMOS TECNICOS FILTRADOS POR PLANTA"""
        return self.get_all(role=UserRole.TECNICOS, plant_id=plant_id)
    
    def get_supervisors(self,plant_id:Optional[UUID]= None) -> list[User]:
        return self.get_all(role=UserRole.SUPERVISOR, plant_id=plant_id)
    
    def get_admins(self)-> list[User]:
        return self.get_all(role=UserRole.ADMIN)
    

    def get_by_plant(self,plant_id:UUID, role: Optional[UserRole]=None) -> list[User]:
        """
        Args:
            plant_id (UUID): id de la planta
            role -> filtramos por el rol especifico.

        Returns:
            list[User]: usuarios con acceso a planta especifica
        """

        query = (
            self.db.query(User)
            .join(UserPlantAccess)
            .filter(
                UserPlantAccess.plant_id == plant_id,
                User.is_active == True
            )
        )

        if role:
            query = query.filter(User.role == role)
        return query.options(
            joinedload(User.plant_accesses)
            .joinedload(UserPlantAccess.plant)
        ).all()
    

    def has_access_to_plant(self, user_id: UUID, plant_id: UUID) -> bool:
        """
        Verificar si un usuario tiene acceso a una planta específica.
        Los ADMIN tienen acceso a todas las plantas automáticamente.
        """
        user = self.get_by_id(user_id, raise_if_not_found=False)
        
        if not user:
            return False

        # Admins tienen acceso a todo
        if user.role == UserRole.ADMIN:
            return True

        # Verificar en la tabla de accesos
        access = (
            self.db.query(UserPlantAccess)
            .filter(
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.plant_id == plant_id,
                UserPlantAccess.is_active == True
            )
            .first()
        )

        return access is not None
    
    def get_plants_for_user(self, user_id:UUID) -> list[Plant]:
        """ OBTENER TODAS LAS PLANTAS 
        A LAS QUE UN USUARIO TIENE ACCESO"""

        user = self.get_by_id(user_id)

        if user.role == UserRole.ADMIN:
            return self.db.query(Plant).filter(Plant.is_active == True).all()
        
        return [access.plant for access in user.plant_accesses if access.is_active]

    def create(
            self,
            first_name: str,
            last_name:str,
            email:str,
            password_hash: str,
            role:UserRole,
            phone: Optional[str] = None,
            plant_ids: Optional[list[UUID]] = None)-> User:
        
        existing_user = self.get_by_email(email)

        if existing_user:
            raise ConflictException(f"El email {email} ya esta registrado")
        
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash = password_hash,
            role = role,
            phone=phone
        )
        self.db.add(user)
        self.db.flush()

        if plant_ids:
            self._assign_plants(user.id, plant_ids)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(
            self,
            user_id: UUID,
            first_name: Optional[str] = None,
            last_name:Optional[str] = None,
            email:Optional[str] = None,
            role:Optional[UserRole] = None,
            phone: Optional[str] = None,
            avatar_url: Optional[str] = None
    ) -> User:
        
        user = self.get_by_id(user_id)

        if email and email != user.email:
            existing = self.get_by_email(email)
            if existing:
                raise ConflictException(f"El email {email} ya esta en uso")
            user.email = email
        
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if role is not None:
            user.role = role
        if phone is not None:
            user.phone = phone
        if avatar_url is not None:
            user.avatar_url = avatar_url

        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.flush()
        self.db.refresh(user)
        return user
    

    def update_password(self, user_id:UUID, new_password_hash: str) -> User:
        user = self.get_by_id(user_id)
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)
        return user
    
    def assing_plants(self, user_id:UUID, plant_id:list[UUID]) -> User:
        """_summary_

        Args:
            user_id (UUID): id del usuario
            plant_id (list[UUID]): lista de ids de plantas a asignar

        Returns:
            Users
        """

        user = self.get_by_id(user_id)

        self.db.query(UserPlantAccess).filter(
            UserPlantAccess.user_id == user_id
        ).delete()

        self._assing_plants(user_id, plant_id)
        self.db.commit()
        self.db.refresh(user)
        return user

    
    def add_plant_access(self,user_id: UUID, plant_id:UUID) -> UserPlantAccess:
        """_summary_

        agregar acceso a una planta adicional

        Raises:
            ConflictException -> si el acceso ya existe
        """
        existing = (
            self.db.query(UserPlantAccess)
            .filter(
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.plant_id == plant_id
            )
            .first()
        )
        if existing:
            if existing.is_active:
                raise ConflictException("El usuario ya tiene acceso a esta planta")
            else:
                existing.is_active = True
                self.db.commit()
                return existing
            
        access = UserPlantAccess(
            user_id=user_id,
            plant_id = plant_id
        )
        self.db.add(access)
        self.db.commit()
        self.db.refresh(access)
        return access


    def remove_plant_access(self, useR_id: UUID, plant_id:UUID) -> None:
        """Remover acceso de un usuario a una planta (SOFT DELETE)"""

        access = (
            self.db.query(UserPlantAccess)
            .filter(
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.plant_id == plant_id,
                UserPlantAccess.is_active == True,
            ).first()
        )
        if not access:
            raise NotFoundException("Acceso a planta")
        

        access.is_active = False
        self.db.commit()

    def _assing_plants(self,user_id:UUID, plant_ids:list[UUID]) -> None:
        """ helper interno para asignar multiples plantas"""
        for plant_id in plant_ids:
            access = UserPlantAccess(
                user_id=user_id,
                plant_id=plant_id
            )
            self.db.add(access)

    
    # SOLFT DELETE

    def deactivate(self, user_id: UUID) -> User:
        """ 
        mantiene los datos del usuario pero lo marcamos como 
        desactivado
        """
        user = self.get_by_id(user_id)
        user.is_active = False
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)
        return user
    
    def reactivate(self,user_id:UUID)-> User:
        user = (
            self.db.query(User)
            .filter(User.id == user_id)
            .first() 
        )
        if not user:
            raise NotFoundException("Usuario")
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return user
    

    def search(
            self,
            query: str,
            plant_id: Optional[UUID] = None,
            role: Optional[UserRole] = None
    ) -> list[User]:
        
        """
        busquedad por filtro -> nombre o email
        """
        
        search_filter = or_(
            User.first_name.ilike(f"%{query}%"),
            User.last_name.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%"),
        )

        db_query = (
            self.db.query(User)
            .filter(search_filter, User.is_active == True)
        )
        if role:
            db_query = db_query.filter(User.role == role)

        if plant_id:
            db_query = db_query.join(UserPlantAccess).filter(
                UserPlantAccess.plant_id == plant_id
            )
        return db_query.options(
            joinedload(User.plant_accesses).joinedload(UserPlantAccess.plant)
        ).all()
    
    def count_by_role(self,plant_id:Optional[UUID]= None) -> dict[str, int]:
        """
        contar usuarios por rol.
        util para dashboar de administracion
        """
        query = self.db.query(User).filter(User.is_active == True)

        if plant_id:
            query = query.join(UserPlantAccess).filter(
                UserPlantAccess.plant_id == plant_id
            )
        
        users = query.all()

        return {
            "total": len(users),
            "admins": len([u for u in users if u.role == UserRole.ADMIN]),
            "supervisores": len([u for u in users if u.role == UserRole.SUPERVISOR ]),
            "tecnicos": len([u for u in users if u.role == UserRole.TECNICOS]),
            "operadores": len([u for u in users if u.role == UserRole.OPERADORES]),
        }
