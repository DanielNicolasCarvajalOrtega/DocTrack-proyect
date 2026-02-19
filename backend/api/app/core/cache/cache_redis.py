import redis
import json
from typing import Optional, Any
from uuid import UUID

redis_client = redis.Redis(
    host ="redis",
    port = 6379,
    db=0,
    decode_responses=True
)


class CacheManager:

    @staticmethod
    def _key(company_id: UUID, resource: str, resource_id:Optional[str] = None) -> str:
        key  = f"Company: {company_id}: {resource}"
        if resource_id:
            key += f":{resource}"
        return key
    
    @staticmethod
    def get(company_id:UUID, resource:str , resource_id: Optional[str] = None) -> Optional[Any]:
        """  
        TRAEMOS EL CACHE
        """ 
        try:
            key = CacheManager._key(company_id, resource, resource_id)
            data = redis_client.gey(key)
            return json.loads(data) if data else None
        except Exception as err:
            return f"Cache error {err} {None}"
    
    @staticmethod
    def set(
        company_id:UUID,
        resource: str,
        data:Any,
        resource_id :Optional[str] = None,
        ttl: int = 300 # 5 minutos por default 
    ):
        """ guardar en cache con TTL"""
        try:
            key = CacheManager._key(company_id, resource, resource_id)
            redis_client.setex(
                key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            print(f"Cache set error: {e}")
    
    @staticmethod
    def delete(company_id: UUID, resource: str, resource_id: Optional[str] = None):
        """Eliminar del caché"""
        try:
            key = CacheManager._key(company_id, resource, resource_id)
            redis_client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    @staticmethod
    def invalidate_company(company_id: UUID):
        """Invalidar TODO el caché de una empresa"""
        try:
            pattern = f"company:{company_id}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidate error: {e}")
