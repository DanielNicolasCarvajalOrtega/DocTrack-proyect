from app.core.cache.cache_redis import CacheManager
from app.modules.plantas.models import Plant
from app.modules.plantas.repository.repository import PlantRepository
from uuid import UUID
from sqlalchemy.orm import Session


class PlantService:
    def get_plants(self, company_id: UUID, db:Session)->list[Plant]:
        cache = CacheManager.get(company_id, "plants")
        if cache:
            return cache
        
        plant_repo = PlantRepository(db, company_id)

        plants = plant_repo.get_all(company_id)

        CacheManager.set(
            company_id,
            "plants",
            [plant.to_dict() for plant in plants],
            ttl=600
        )




        