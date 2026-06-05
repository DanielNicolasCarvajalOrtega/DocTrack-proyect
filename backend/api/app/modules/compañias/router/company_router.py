import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.users.models import User
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.compañias.services.company_service import CompanyService
from app.modules.compañias.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyUserResponse,
    SubsidiaryCreate,
    UserInvite,
    RoleUpdate,
    PlanUpdate
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compania", tags=["Compañias"])

# crud

@router.post(
    "/",
    response_model=CompanyResponse,
    status_code= status.HTTP_201_CREATED,
    summary="Crear compañia raiz",
)
def crear_compañia_raiz(company_data:CompanyCreate, 
        db:Session = Depends(get_db),
        current_user: User= Depends(get_current_user)) -> Company:

    # la estructura y limites se aplican automaticamente segun el plan seleccionado
    try:
        company = CompanyService.crear_compañia(db, company_data.model_dump())
        logger.info(f"[Router] compañia creada id={company.id} by= {current_user.id}")
        return company
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[Router.crear_compañia_raiz] error inesperado - {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    

@router.get(
        "/{company_id}",
        response_model= CompanyResponse,
        summary= "Obtener Compañia",
)
def obtener_detalles_de_una_compañia(company_id:UUID,
                      db: Session = Depends(get_db), 
                      current_user: User = Depends(get_current_user)
                    ) -> Company:

    """
    obtiene los detalles de una compañia

    Solo admin, auditor o admin del parent pueden ver metricas 
    y datos sensibles
    """
    try:
         return CompanyService.obtener_compañia(db, company_id, current_user.id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    

@router.patch(
    "/{company_id}",
    response_model= CompanyResponse,
    summary= "Actualizar compañia",
)
def actualizar_una_compañia(
    company_id:UUID,
    update_data: CompanyUpdate,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Company:
    
    """
    actualiza solamente campos editables de la compañia

    solo el admon de la compañia o admin del parent pueden modificar
    los limites "max_*" no son editales - se modifican automatiamente al cambiar el plan
    """
    try:
        return CompanyService.actualizar_compañia(
            db, 
            company_id, 
            update_data.model_dump(exclude_unset=True), 
            current_user.id
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail = str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403 , detail=str(err))
    

@router.put(
    "/{company_id}/planes",
    response_model= CompanyResponse,
    summary= "Cambiar plan de pago",
)
def cambiar_plan_de_una_compañia_no_puede_degradar(
    company_id:UUID,
    new_plan: BillingPlan,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Company:
    
    """
    combiar las preferencias de plan de pago este
    aplica nuevos limites nuevamente

    guard clauses:
    no degradar si tiene subsidiarias activas
    no degradar si tiene estructura incompatible con el nuevo plan
    no degradar si tiene mas plantas que el limite del nuevo plan
    
    NO DEGRADAR = si su cuenta actual tiene características o
      datos que el plan más barato no soporta.
    """

    try:
        return CompanyService.cambiar_plan(db, company_id, new_plan, current_user.id)
    except ValueError as err:
        raise HTTPException(status_code= 400, detail=str(err))
    except PermissionError as err:
        raise  HTTPException(status_code = 403, detail = str(err))
    

@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=" Eliminar compañia",
)
def eliminar_una_compañia(
    company_id:UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    
    # soft delete de una compañia
    # no se puede eliminar si tine subsidiaria activas o multiples usuarios

    try:
        CompanyService.eliminar_compañia(db, company_id, current_user.id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail= str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail = str(err))



# downgrades y bloqueos

@router.get(
        "/{company_id}/downgrade-check",
        summary= "Verificar bloqueos antes de degradar el plan"
)

def verificar_bloqueos_downgrade(
    company_id:UUID,
    new_plan: BillingPlan,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    retorna exactamente que es lo que bloquea la degradacion 
    al plan objetivo.
    llama este endpoint antes de intentar degradar para que el 
    admin sepa que debe limpiar dinero.

    respuesta:
    puede degradar? = true or false
    bloqueos = lista de mensajes con cada problema
    subsidiarias_activas = cuantas tiene vs cnuentas permite el nuevo plan
    estructura_incompatible = si la estructura actual es compatible
    """

    try:
        return CompanyService.verificar_bloqueo_downgrade(db, company_id, new_plan, current_user.id)

    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    

@router.delete(
        "/{company_id}/subsidiarias/cascade",
        summary= "Eliminar todas las subsidiarias para habilitar downgrade"
)
def eliminar_subsidiarias_de_una_compañia_en_cascada(
    company_id:UUID, 
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user)) -> dict:

    """
    elimina las subsidiarias en cascada si estan activas
    solo elimina subsidiarias que no tengan:
    - sus propias sub-subsidiarias activas
    - usuarios activos

    retorna cuantas se eliminaron y cuales no se pudieron eliminar, muestra el motivo
    """
    try:
        return CompanyService.eliminar_subsidiarias_de_una_compañia_en_cascada(db, company_id, current_user.id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
        
@router.put(
        "/{company_id}/plan/downgrade",
        response_model=CompanyResponse,
        summary= "Degradar plan de pago"
)
def degradar_plan_de_una_compañia(
    company_id: UUID,
    plan_update:PlanUpdate,
    db:Session = Depends(get_db),
    current_user:User = Depends(get_current_user)
) -> Company:
    # degrada el plan aplicando los nuevos limites

    try:
        CompanyService.degradar_plan_de_una_compañia(
            db, company_id, plan_update.new_plan, current_user.id, plan_update.subscription_ends_at
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail=str(err))
    

# subsidiarias
@router.post(
    "/{parent_id}/subsidiarias",
    response_model= SubsidiaryCreate,
    status_code= status.HTTP_201_CREATED,
    summary= "Crear subsidiaria",
)
def crear_subsidiaria(
    parent_id:UUID,
    subsidiary_data : SubsidiaryCreate,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Company:
    
    """
    crea una compañia bajo el parent
    solo el admin del parent puede crear subsidiarias
    el plan del parent debe soportar subsidiarias como -> pro o empresas
    """
    try:
        return CompanyService.crear_subsidiaria(
            db, 
            parent_id, 
            subsidiary_data.model_dump(exclude={"child_plan"}), # pasa el dict sin child_plan
            subsidiary_data.child_plan, # lo pasa de forma independiente
            current_user.id)
    
    except ValueError as err:
        raise HTTPException(status_code= 400, detail= str(err))
    except PermissionError as err:
        raise HTTPException(status_code=403, detail = str(err))
    
@router.delete(
        "/{company_id}/subsidiarias/{child_id}",
        status_code= status.HTTP_204_NO_CONTENT,
        summary="Eliminar subsidiaria"
)
def eliminar_subsidiaria_de_una_compañia(
    parent_id:UUID,
    child_id:UUID, 
    db:Session= Depends(get_db), 
    current_user:User= Depends(get_current_user)) -> None:
    """
    elimina una subsidiaria
    no se puede eliminar si tiene sus propias subsidiarias activas
    """

    try: 
        CompanyService.eliminar_subsidiaria(db,child_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
 

@router.get(
    "/{parent_id}/tus-subsidiarias",
    response_model= list[CompanyResponse],
    summary= "Listar subsidiarias"
)
def listar_subsidiarias_de_una_compañia(
    parent_id:UUID, 
    db:Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
)-> list[Company]:

    """
    lista las subsidiaras activas de un parent
    solo el admin del parent puede ver la lista completa
    """
    try:
        return CompanyService.listar_subsidiarias(db,parent_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    

@router.post(
    "/{company_id}/users",
    response_model = CompanyUserResponse,
    status_code= status.HTTP_201_CREATED,
    summary = "Agregar usuario a compañia"
)
def agregar_usuario(
    company_id:UUID,
    invite: UserInvite,
    db:Session = Depends(get_db),
    current_user:User = Depends(get_current_user)
) -> CompanyUser:
    
    """
    agrega usuario a la compañia
    solo admin de la compañia o admin del parent puede agregar usuarios
    no puede superar el limite del plan actual
    """

    try:
        return CompanyService.agregar_usuario(
            db, company_id, invite.user_id, invite.role,current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    

@router.get(
    "/{company_id}/users",
    response_model= list[CompanyUserResponse],
    summary = "Listar usuarios de la compañia"
)
def listar_usuarios(
    company_id:UUID,
    role: Optional[CompanyRole] = Query(None, description="Filtrar por rol"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20,ge=0, le=100),
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    # listar los usuarios activos de la compañia
    # solo admin y auditor pueden ver la lista completa

    try:
        return CompanyService.listar_usuarios(
            db, company_id, current_user.id ,role=role, skip=skip, limit= limit
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
@router.patch(
    "/{company_id}/users/{user_id}/role",
    response_model= CompanyUserResponse,
    summary = "Cambiar el rol de usuario"
)

def cambiar_el_rol_del_usuario(
    company_id: UUID,
    user_id: UUID,
    role_update: RoleUpdate,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CompanyUser:
    """
    cambiar el rol de un usuario en la compañia

    solo el admin puede cambiar roles
    no puede cambiar su propio rol ni degradar al ultimo admin
    """
    try:
         return CompanyService.cambiar_rol_usuario(
             db, 
             company_id, 
             user_id, 
             role_update.new_role, 
             current_user.id
        )
    except ValueError as err:
        raise HTTPException(status_code= 400, detail = str(err))
    except PermissionError as err:
        raise HTTPException(status_code= 403, detail = str(err))

@router.delete(
    "/{company_id}/users/{users_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover usuarios de compañia"
)
def eliminar_usuario_de_compañia(
    company_id:UUID,
    user_id:UUID,
    db:Session= Depends(get_db),
    current_user: User = Depends(get_current_user)
)-> None:

    """
    remueve un usuario de la compañia (soft-delete)
    solo el admin puede remover usuarios
    no se puede remover al ultimo admin
    """

    try:
        CompanyService.remover_usuario(db, company_id, user_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

