from fastapi import APIRouter, Depends, HTTPException,  Query ,status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.modules.users.repository.repository import UserRepository
from app.modules.users.schemas import (
    UserResponse,
    UserDetailResponse,
    UserCreateRequest,
    UserUpdateRequest,
    UserPasswordUpdateRequest,
    UserStatsResponse,
    UserListResponse,
    AssignPlantsRequest,
    AddPlantAccessRequest,
    MessageResponse
)
from app.modules.users.models import UserRole
from app.shared.exceptions import NotFoundException, ConflictException


router = APIRouter()

@router.get("/", response_model=UserListResponse)
def get_users(
    role: Optional[UserRole] = Query(None, description="Filtrar por rol"),
    plant_id: Optional[UUID] = Query(None, description="Filtrar por planta"),
    include_inactive: bool = Query(False, description="Incluir inactivos"),
    db: Session = Depends(get_db)
):
    """ 
    Obtener lista de usuarios con filtros opcionales
    rol
    id de planta
    inactivos incluidos
    """

    repo = UserRepository(db)
    users = repo.get_all(
        include_inactive=include_inactive,
        role=role,
        plant_id=plant_id
    )
    return UserListResponse(total=len(users), users=users)

@router.get("/search", response_model=list[UserResponse])
def search_users(
    query: str = Query(..., min_length=2, description="Texto a buscar"),
    plant_id: Optional[UUID] = Query(None, description="Filtrar por planta"),
    role: Optional[UserRole] = Query(None, description="Filtrar por rol"),
    db: Session = Depends(get_db)
):
    """ 
    buscar usuarios por nombre o email
    busca en first_name , last_name, email
    """
    repo = UserRepository(db)
    return repo.search(query=query, plant_id=plant_id, role=role)

@router.get("/by-role/{role}", response_model=list[UserResponse])
def get_users_by_role(
    role: UserRole,
    plant_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    
    """
    obtiene usuarios por rol especificos
     admin - supervisor - operador - tecnico
    """
    repo = UserRepository(db)

    if role == UserRole.OPERADORES:
        users = repo.get_operators(plant_id)
    elif role == UserRole.TECNICOS:
        users = repo.get_technicians(plant_id)
    elif role == UserRole.SUPERVISOR:
        users = repo.get_supervisors(plant_id)
    elif role == UserRole.ADMIN:
        users = repo.get_admins()
    else:
        users = []
    
    return users


@router.get("/stats", response_model=UserStatsResponse)
def get_users_stats(
    plant_id: Optional[UUID] = Query(None, description="Filtrar por planta"),
    db: Session = Depends(get_db)
):
    
    repo = UserRepository(db)
    return repo.count_by_role(plant_id = plant_id)

@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user(user_id: UUID, db:Session = Depends(get_db)):
    """
    obtene usuarios con todos sus detalles
    """

    repo = UserRepository(db)

    try:
        user = repo.get_by_id(user_id)
        plant_accesses = []
        for access in user.plant_accesses:
            plant_accesses.append({
                "plant_id": access.plant.id,
                "plant_name": access.plant.name,
                "company": access.plant.company,
                "location": access.plant.location
            })
        return UserDetailResponse(
            **user.__dict__,
            plant_accesses=plant_accesses
        )
    
    except NotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    

@router.post("/", response_model = UserDetailResponse, status_code = status.HTTP_201_CREATED)
def create_user(data: UserCreateRequest,db: Session = Depends(get_db)):
    
    repo = UserRepository(db)
    try:
        password_hash = hash_password(data.password)

        user = repo.create(
            first_name= data.first_name,
            last_name= data.last_name,
            email = data.email,
            password_hash= password_hash,
            role = data.role,
            phone = data.phone,
            plant_ids = data.plant_ids if data.plant_ids else []
        )

        # construimos la respuesta
        plant_accesses = []
        for access in user.plant_accesses:
            plant_accesses.append({
                "plant_id": access.plant.id,
                "plant_name": access.plant.name,
                "company": access.plant.company,
                "location": access.plant.location
            })
        return UserDetailResponse(
            **user.__dict__,
            plant_accesses=plant_accesses
        )
    except ConflictException as err:
        raise HTTPException(status_code=409, detail=str(err))
    
@router.patch("/{user_id}", response_model=UserDetailResponse)
def update_user(user_id: UUID, data: UserUpdateRequest, db: Session = Depends(get_db)
):
    """
    Actualizar información de un usuario.
    
    Solo se actualizan los campos proporcionados (partial update).
    
    **No se puede cambiar la contraseña** por este endpoint (usar PATCH /users/{id}/password)
    """

    repo = UserRepository(db)
    try:
        user = repo.update(
            user_id = user_id,
            first_name= data.first_name,
            last_name= data.last_name,
            email = data.email,
            role = data.role,
            phone = data.phone,
            avatar_url= data.avatar_url
        )
        
        plant_accesses = []
        for access in user.plant_accesses:
            if access.is_active and access.plant:
                plant_accesses.append({
                    "plant_id": access.plant.id,
                    "plant_name": access.plant.name,
                    "company": access.plant.company,
                    "location": access.plant.location
                })
        return UserDetailResponse(
            **user.__dict__,
            plant_accesses=plant_accesses
        )
    except NotFoundException as err:
        raise  HTTPException(status_code=404, detail=str(err))
        
    except ConflictException as err:
        raise HTTPException(status_code=409, detail=str(err))
    

@router.patch("/{user_id}/password", response_model=MessageResponse)
def update_password(user_id:UUID, data: UserPasswordUpdateRequest, db:Session = Depends(get_db)):
    """
    Cambiar contraseña de un usuario.
    
    **Requiere:**
    - Contraseña actual (para validación)
    - Nueva contraseña
    """

    repo = UserRepository(db)
    try:
        user = repo.get_by_id(user_id)

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(status_code=400 , detail="La contrseña actual es incorrecta")

        new_password_hash = hash_password(data.new_password)
        repo.update_password(user_id, new_password_hash)
        return MessageResponse(
            message = "Contraseña actualizada correctamente",
            data =
            {
                "user_id": str(user_id)
            }
        )
    except NotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    
@router.delete("/{user_id}", response_model=MessageResponse)
def deactivate_user(user_id:UUID, db:Session = Depends(get_db)):
    """
    soft delete 
    no se elimina de la base de datos, se marca como inactivo
    puede ser reactivado mas adelante si es necesario
    """
    repo = UserRepository(db)

    try:
        user = repo.deactivate(user_id)
        return MessageResponse(
            message=f"Usuario {user.first_name} + {user.last_name} desactivado exitosamente",
            data = {
                "user_id": str(user.id), 
                "email": user.email
            }
        )
    except NotFoundException as err:
        raise HTTPException(status_code= 404, detail=str(err))

@router.post("/{user_id}/reactivate", response_model=MessageResponse)
def reactivate_user(user_id:UUID, db:Session = Depends(get_db)):
    
    repo = UserRepository(db)

    try:
        user = repo.reactivate(user_id)
        return MessageResponse(
            message = f"Usuario {user.first_name} + {user.last_name} reactivado exitosamente",
            data = {
                "user_id": str(user.id), 
                "email": user.email
            }
        )
    except NotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    

@router.get("/{user_id}/plants")
def get_user_plants(user_id:UUID, db:Session = Depends(get_db)):
    """
    Obtener todas las plantas a las que un usuario tiene acceso.
    los roles ADMIN tienen acceso a todas las plantas automaticamente
    """

    repo = UserRepository(db)

    try:
        plants = repo.get_plants_for_user(user_id)
        return {
            "user_id": user_id,
            "total_plants": len(plants),
            "plants": plants
        }
    except NotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    

@router.put("/{user_id}/plants", response_model = MessageResponse)
def assign_plants(user_id: UUID, data: AssignPlantsRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    try: 
        user = repo.assing_plants(user_id, data.plant_ids)
        return MessageResponse(
            message= f"Se asignaron {len(data.plant_ids)} plantas al usuario",
            data = {
                "user_id": str(user.id),
                "plants_id": [str(pla_id)for pla_id in data.plant_ids]
            }
        )
    
    except NotFoundException as err:
        raise HTTPException(status_code=404, detail=str(err))
    
@router.post("/{user_id}/plants/add", response_model=MessageResponse)
def add_plant_access(user_id: UUID, data:AddPlantAccessRequest , db: Session = Depends(get_db)):
    """
    agregar accesso a una planta adicional - sin afectar a las demas
    """

    repo = UserRepository(db)
    
    try:
        acccess = repo.add_plant_access(user_id, data.plant_id)
        return MessageResponse(
            message = "Acceso a planta agregado exitosamente",
            data = {
                "user_id": str(user_id),
                "plant_id": str(data.plant_id)
            }
        )
    except NotFoundException as err:
        raise HTTPException(status_code= 404, detail=str(err))
    except ConflictException as err:
        raise HTTPException(status_code= 409, detail=str(err))
    
@router.delete("/{user_id}/plants/{plant_id}", response_model=MessageResponse)
def remove_plant_access(user_id: UUID, plant_id: UUID, db: Session = Depends(get_db)):
    """
    Remover acceso de un usuario a una planta específica.
    """
    repo = UserRepository(db)
    
    try:
        repo.remove_plant_access(user_id, plant_id)
        return MessageResponse(
            message="Acceso a planta removido exitosamente",
            data={
                "user_id": str(user_id),
                "plant_id": str(plant_id)
            }
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/has-access/{plant_id}")
def check_plant_access(
    user_id: UUID,
    plant_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Verificar si un usuario tiene acceso a una planta específica.
    
    **Retorna:**
```json
    {
      "user_id": "uuid",
      "plant_id": "uuid",
      "has_access": true/false
    }
```
    """
    repo = UserRepository(db)
    has_access = repo.has_access_to_plant(user_id, plant_id)
    
    return {
        "user_id": user_id,
        "plant_id": plant_id,
        "has_access": has_access
    }    
