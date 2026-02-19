from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.modules.plantas.models import Plant, Area, UserPlantAccess
from app.modules.users.models import User, UserRole
from app.shared.exceptions import NotFoundException, ConflictException
from app.modules.maquinas.models import Machine, MachineStatus
from app.modules.plantas.repository.repository import PlantRepository

class AreaRepository:
    """areas -> sectores dentro de planta """

    def __init__(self, db:Session):
        self.db = db

    def get_all(self,plant_id: Optional[UUID] = None) -> list[Area]:
        """" obtener todas las areas
            filtrados por planta
           """
        
        query = self.db.query(Area).filter(Area.is_active == True)
        if plant_id:
            query = query.filter(Area.plant_id == plant_id)

        return query.options(joinedload(Area.plant)).all()


    def get_by_id(
            self,
            area_id: UUID,
            raise_if_not_found: bool = True

    )-> Area | None:
        
        # obtener area por id

        area = (
            self.db.query(Area)
            .filter(Area.id == area_id , Area.is_active == True)
            .options(
                joinedload(Area.plant),
                joinedload(Area.machines)
            )
            .first()
        )

        if not area and raise_if_not_found:
            raise NotFoundException("Area")
        return area
    
    def get_by_plant(self, plant_id: UUID)-> list[Area]:
        
        # obtener todas las areas de una planta

        return (
            self.db.query(Area)
            .filter(Area.plant_id == plant_id, Area.is_active == True)
            .options(joinedload(Area.machines))
            .order_by(Area.nombre)
            .all()
        )
    

    def create(
        self,
        name: str,
        plant_id: UUID,
        description: Optional[str] = None
    ) -> Area:
    
        """
        Crear nueva área.
        
        Raises:
            NotFoundException: Si la planta no existe
            ConflictException: Si ya existe un área con ese nombre en la planta
        """


        plant_repo = PlantRepository(self.db)
        plant = plant_repo.get_by_id(plant_id)

        existing = (
            self.db.query(Area)
            .filter(
                Area.plant_id == plant_id,
                Area.name == name
            )
            .first()
        )

        if existing:
            raise ConflictException(
                f"Ya existe un area {name} en la planta {plant.name}"
            )

        area = Area (
            name = name,
            plant_id =plant_id,
            description = description
        )

        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)

        return area
    
    def update(
            self,
            area_id: UUID,
            name: Optional[str] = None,
            description: Optional[str] = None

    ) -> Area: 
        area = self.get_by_id(area_id)

        if name and name != area.name:
            existing = (
                self.db.query(Area)
                .filter(Area.plant_id == area.plant_id,
                        Area.anem == name,
                        Area.id != area_id
                ).first()
            )

            if existing:
                raise ConflictException(
                    f"Ya existe un area {name} en esta planta"
                )
        
        if name is not None:
            area.name = name

        if description is not None:
            area.description = description

        area.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(area)
        return area
    
    # soft delete
    def deactivate(self, area_id :UUID) -> Area:
        """
        Desactivar área.
        
        IMPORTANTE: También desactiva todas las máquinas del área.
        """
        area = self.get_by_id(area_id)

        area.is_active = False
        area.updated_at = datetime.utcnow()

        # desactiva las maquinas

        self.db.query(Machine).filter(Machine.area_id == area_id).update({
            "is_active": False,
            "updated_at": datetime.utcnow()
        })
        self.db.commit()
        self.db.refresh(area)

        return area


    def reactivate(self, area_id: UUID) -> Area:
        """ reactivar area previamente desactivado """

        area = self.db.query(Area).filter(Area.id == area_id).first()

        if not area:
            raise NotFoundException("Area")
        
        area.is_active = True
        area.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(area)

        return area


        
    def get_stats(self,area_id:UUID) -> dict:
        # obtenemos estadisticas de un area en especifico

        area = self.get_by_id(area_id)

        machines = (
            self.db.query(Machine)
            .filter(Machine.area_id == area_id, Machine.is_active == True)
            .all()
        )

        machines_by_status = {
            "total": len(machines),
            "operativa": len([m for m in machines if m.status == MachineStatus.OPERATIVA]),
            "mantenimiento": len([m for m in machines if m.status == MachineStatus.MANTENIMIENTO]),
            "fallas": len([m for m in machines if m.status == MachineStatus.FALLAS]),
            "debaja": len([m for m in machines if m.status == MachineStatus.DEBAJA]),
        }

        return {
            "area_id": area_id,
            "area_name": area.name,
            "plant_name": area.plant if area.plant else None,
            "machines": machines_by_status
        }