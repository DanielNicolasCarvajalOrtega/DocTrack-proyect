from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.modules.compañias.models import Company
from app.modules.plantas.models import Plant, Area, UserPlantAccess
from app.modules.users.models import User, UserRole
from app.shared.exceptions import NotFoundException, ConflictException
from app.modules.maquinas.models import Machine

class PlantRepository:
    """
    - Gestión de plantas y sus áreas
    - Asignación de usuarios a plantas
    - Validaciones de integridad
    """

    def __init__(self, db: Session, company_id:UUID):
        self.db = db
        self.company_id = company_id


    def get_all(self, include_inactive: bool = False)-> list[Plant]:
        
        query = self.db.query(Plant).filter(
            Plant.company_id == self.company_id #<- hace aislamiento
        )

        if not include_inactive:
            query = self.db.query(Plant.is_active == True)

        return query.all()

    def get_by_id(self, plant_id:UUID) -> Plant:
        """
        obtener planta por ID con areas y usuarios
        """

        plant = (
            self.db.query(Plant)
            .filter(
                Plant.id == plant_id,
                    Plant.company_id == self.company_id,
                    Plant.is_active == True
                ).first()
            )
        
        if not plant:
            raise NotFoundException("Planta")
        return plant


    def get_by_name(self, name:str, company:str) -> Plant | None:
        return (
            self.db.query(Plant)
            .filter(
                Plant.name == name, 
                Plant.company == company
            ).first()
        ) 
    
    def get_by_user(self, user_id: UUID)-> list[Plant]:

        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            raise NotFoundException("Usuario")
        
        # admin ven todas las plantas

        if user.role == UserRole.ADMIN:
            return self.get_all()
        
        return (
            self.db.query(Plant)
            .join(UserPlantAccess)
            .filter(
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.is_active == True,
                Plant.is_active == True
            )
            .options(joinedload(Plant.areas))
            .all()
        )

    def get_users_with_access(self, plant_id:UUID, role:Optional[UserRole] = None) -> list[User]:
        """
        Obtener usuarios que tienen acceso a una planta.
        
        Args:
            plant_id: ID de la planta
            role: Opcional, filtrar por rol
        """

        query = (
            self.db.query(User)
            .join(UserPlantAccess)
            .filter(
                UserPlantAccess.plant_id == plant_id,
                UserPlantAccess.is_active == True,
                User.is_active == True
            )
        )

        if role:
            query = query.filter(User.role == role)

        return query.all()
    


    def create(self,name:str, company_name:str ,location: Optional[str]) -> Plant:
        
        """
            crear nueva planta simpre con - company_id
            Raises : 
                ConflictException: Si ya existe una planta con ese nombre y empresa
        """
        existing = self.get_by_name(name, company_name)
        if existing:
                raise ConflictException(
                    f" Ya existe una planta {name} para la empresa {company_name}"
                )
        plant = Plant(
            name = name,
            location=location,
            company_id = self.company_id # asignacion automatica
        )

        self.db.add(plant)
        self.db.commit()
        self.db.refresh(plant)

        return plant
      

    def update(
            self,
            plant_id: UUID,
            name: Optional[str] = None,
            company: Optional[str] = None,
            location: Optional[str] = None,
            description: Optional[str] = None,
            logo_url: Optional [str] = None
    ) -> Plant:
        
        """
        Actualizar informacion fde una planta
        """
        plant = self.get_by_id(plant_id)

        if name and company:
            if name != plant.name or company != plant.company:
                existing = self.get_by_name(name, company)
                if existing and existing.id != plant_id:
                    raise ConflictException(
                        f"Ya existe otra planta {name} para {company}"
                    )
                
        if name is not None:
            plant.name = name
        if company is not None:
            plant.company = company
        if location is not None:
            plant.location = location
        if description is not None:
            plant.description = description
        if logo_url is not None:
            plant.logo_url = logo_url

        plant.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(plant)
        return plant
    
    def assign_users(self, plant_id:UUID, user_ids: UUID) -> Plant:
        """
        Asignar usuarios a una planta (REEMPLAZA los existentes).

        Esta operación elimina todos los accesos actuales
        y crea nuevos con los user_ids proporcionados.
        """
        plant = self.get_by_id(plant_id)

        self.db.query(UserPlantAccess).filter(
            UserPlantAccess.plant_id == plant_id
        ).delete()

        for user_id in user_ids:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundException(f"Usuario con ID {user_id}")
            access = UserPlantAccess(
            user_id = user_id,
            plant_id = plant_id
            )
            self.db.add(access)

        self.db.commit()
        self.db.refresh(plant)
        
        return plant
    
    def add_user_access(self, plant_id: UUID, user_id: UUID) -> UserPlantAccess:
        
        """
        Agregar acceso de un usuario a una planta (sin afectar otros).
        
        Si el usuario ya tiene acceso activo, lanza ConflictException.
        """

        plant = self.get_by_id(plant_id)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("Usuario")
        
        existing = (
            self.db.query(UserPlantAccess)
            .filter(
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.plant_id == plant_id
            ).first()
        )
    
        if existing:
            if existing.is_active:
                raise ConflictException(
                    f"El usuario {user.first_name + " " + user.last_name} ya tiene acceso a {plant.name}"
                )

            else:
                existing.is_active = True
                self.db.commit()
                return existing
            
        access = UserPlantAccess(
            user_id = user_id,
            plant_id = plant_id
        )
        self.db.add(access)
        self.db.commit()
        self.db.refresh(access)

        return access
    
    
    def user_has_access(self,plant_id: UUID, user_id: UUID) -> bool:
        """
        Verificar si un usuario tiene acceso a una planta.
        Los ADMIN tienen acceso automático a todas.
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return False
        
        if user.role == UserRole.ADMIN:
            return True
        
        access = (
            self.db.query(UserPlantAccess)
            .filter(
                UserPlantAccess.plant_id == plant_id,
                UserPlantAccess.user_id == user_id,
                UserPlantAccess.is_active == True
            )
            .first()
        )

        return access is not None
    

    def deactivate(self,plant_id:UUID) ->Plant:
        """
        Desactivar planta (soft delete).
        
        IMPORTANTE: También desactiva todas sus áreas y accesos de usuarios.
        """

        plant = self.get_by_id(plant_id)

        plant.is_active = False
        plant.updated_at = datetime.utcnow()

        # desactivar areas 
        self.db.query(Area).filter(Area.plant_id == plant_id).update(
            {
            "is_active":False,
            "updated_at": datetime.utcnow()
            }
        )

        # desactivar accesos de usuarios

        self.db.query(UserPlantAccess).filter(
            UserPlantAccess.plant_id == plant_id
        ).update(
            {
                "is_active": False,
                "updated_at": datetime.utcnow()
            }
        )
        self.db.commit()
        self.db.refresh(plant)

        return plant
    
    def reactivate(self, plant_id: UUID) -> Plant:
        """Reactivar planta previamente desactivada"""
        plant = (
            self.db.query(Plant)
            .filter(Plant.id == plant_id)
            .first()
        )

        if not plant:
            raise NotFoundException("Planta")

        plant.is_active = True
        plant.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(plant)

        return plant

    def search(self, query: str, company:Optional[str] = None)-> list[Plant]:
        """
        buscar plantas por nombre o ubicacion
        """

        search_filter = or_(
            Plant.name.ilike(f"%{query}%"),
            Plant.location.ilike(f"%{query}%")
        )

        db_query = (
            self.db.query(Plant)
            .filter(search_filter, Plant.is_active == True)
        )
        if company:
            db_query = db_query.filter(Plant.company.ilike(f"%{company}%"))

        return db_query.options(joinedload(Plant.areas)).all()
    
    

    def get_stats(self, plant_id:UUID) -> dict:
        """
        Obtener estadísticas de una planta.
        
        Retorna:
        - Total de áreas
        - Total de máquinas
        - Total de usuarios con acceso
        - Usuarios por rol
        """

        plant = self.get_by_id(plant_id)

        total_areas = (
            self.db.query(
                func.count(Area.id)
                .filter(Area.plant_id == plant_id, Area.is_active == True)
                .scalar()
            )
        )

        total_machines = (
            self.db.query(func.count(Machine.id))
            .join(Area)
            .filter(
                Area.plant_id == plant_id,
                Area.is_active == True,
                Machine.is_active == True
            )
            .scalar()
        )


        users = self.get_users_with_access(plant_id)

        users_by_role = {
            "total": len(users),
            "administradores": len([u for u in users if u.role == UserRole.ADMIN]),
            "supervisores": len([u for u in users if u.role == UserRole.SUPERVISOR ]),
            "tecnicos": len([u for u in users if u.role == UserRole.TECNICOS]),
            "operadores": len([u for u in users if u.role == UserRole.OPERADORES]),
        }

        return {
            "plant_id": plant_id,
            "plant_name" : plant.name,
            "total_areas": plant.areas,
            "total_maquinas": total_machines,
            "users": users_by_role
        }


    


    