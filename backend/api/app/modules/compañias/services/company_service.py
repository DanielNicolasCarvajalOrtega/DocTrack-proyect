import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from app.modules.compañias.models import Company, CompanyRole, CompanyUser, BillingPlan, StructureType
from app.modules.compañias.repository.repository import CompanyRepository
from app.modules.compañias.repository.company_user_repository import CompanyUserRepository
from app.modules.compañias.constants import (
    BILLING_PLAN_LIMITS, PLAN_ALLOWED_STRUCTURES, PLANS_WITH_CHILDREN
)

logger = logging.getLogger(__name__)

"""
 
RESPONSABILIDADES DEL SERVICE:
  - Validar permisos (quién puede hacer qué)
  - Aplicar reglas de negocio (límites de plan, jerarquía, roles)
  - Orquestar llamadas a los repositories
  - Delegar tareas asíncronas a Celery (notificaciones, emails)

  REGLAS GENERALES:
  - El admin de una compañía gestiona solo la suya
  - El admin del parent puede gestionar sus subsidiarias
  - Los límites (max_*) los define el plan — nunca el admin directamente
  - El último admin de una compañía no puede ser degradado ni removido
  - No se puede eliminar una compañía con subsidiarias activas
"""
class CompanyService:
  
  @staticmethod
  def crear_compañia(db:Session, company_data: dict) -> Company:
    """
    1- el structure_type debe ser compantible con el plan elegido
    2- los limites se aplican automaticamente desde constants.py
    """
    plan = company_data.get("billing_plan", BillingPlan.prueba)
    if isinstance(plan, str):
      plan = BillingPlan(plan)

    # guard para validar structure_type es compatible con el plan
    structure = company_data.get("structure_type",StructureType.simple)
    if isinstance(structure, str):
      structure = StructureType(structure)

    structure_allowed = PLAN_ALLOWED_STRUCTURES[plan.value]
    if structure not in structure_allowed:
      raise ValueError(
        f"El plan {plan.value} no soporta la estructura m{structure.value}"
        f"Estructuras disponibles: {[e.value for e in structure_allowed]}"
      )
    
    # aplica limites de plan automaticamente
    limits = BILLING_PLAN_LIMITS[plan.value]
    company_data.update(
      {
        "billing_plan": plan,
        "structure_type": structure,
        "max_users_per_plant": limits["max_users_per_plant"],
        "max_plants": limits["max_plants"],
        "max_storage_gb": limits["max_storage_gb"],
        "max_children": limits["max_children"],
      }
    )

    company = CompanyRepository.create(db, company_data)
    logger.info(
      f"[CompanyService.crear_compañia] id={company.id}"
      f"plan = {plan.value} structure= {structure.value}"
    )
    return company
  

  @staticmethod
  def obtener_compañia(db:Session, company_id:UUID, requesting_user_id:UUID)-> Company:
    # el usuario debe ser miembro de la compañia o admin del parent
      company = _obtener_compania_o_error(db, company_id)
      _verificar_quien_puede_ver_compania_completa(db, company, requesting_user_id)
      return company
  

  @staticmethod
  def actualizar_compañia(db: Session, company_id: UUID, update_data: dict, requesting_user_id: UUID) -> Company:
    """
    guard clauses:
    1- Solo admin propio o admin del parent
    2- Si se cambia industry, es libre (cualquier industry es válida)
    3- Si se cambia structure_type, debe ser compatible con el plan actual
    """
    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_administrar(db, company, requesting_user_id, "modificar esta compañia")

    # guard --- si cambia structure_type, valida contra el plan actual
    if "structure_type" in update_data:
      new_structure = update_data["structure_type"]
      if isinstance(new_structure, str):
        new_structure = StructureType(new_structure)
    
      structure_allowed = PLAN_ALLOWED_STRUCTURES[company.billing_plan.value]
      if new_structure not in structure_allowed:
        raise ValueError(
          f"El plan {company.billing_plan.value} no soporta "
          f"la estructura {new_structure.value}"
        )
      
      company = CompanyRepository.update(db, company_id, update_data)
      logger.info(f"[CompanyService.actualizar_compañia] id={company_id} by={requesting_user_id}")
    return company
  
  @staticmethod
  def cambiar_plan(
    db:Session,
    company_id: UUID,
    new_plan: BillingPlan,
    requesting_user_id: UUID,
    subscriptions_ends_at=None,
  )-> Company:
    """
    cambia el plan y aplica los nuevos límites automáticamente.
    guard clauses:
      1- Solo admin propio o admin del parent
      2- No degradar si tiene subsidiarias activas
      3- No degradar si tiene structure_type incompatible con el nuevo plan
      4- No degradar si tiene más plantas activas que el nuevo límite
    """
    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_administrar(db, company, requesting_user_id,"verificar puede adminstrar")

    new_limits = BILLING_PLAN_LIMITS[new_plan.value] 

    # guard --- no degradar si tiene subcidiaria activas
    if new_plan not in PLANS_WITH_CHILDREN: 
      children_active = CompanyRepository.count_children(db, company_id) # contamos childrens
      if children_active > 0: # verifica si children es mayor a 0 si no debe crear una compañia
        raise ValueError(
          f"No se puede cambiar al plan '{new_plan.value}' porque la compañía "
          f"tiene {children_active} subsidiarias activas."
        )

    if new_limits["max_children"] < CompanyRepository.count_children(db, company_id):
      raise ValueError(
        f"El plan '{new_plan.value}' permite máximo "
        f"{new_limits['max_children']} subsidiarias. "
        f"Reduce el número de subsidiarias primero."
      )
    
    company = CompanyRepository.apply_billng_plan(db, company_id, new_plan, subscriptions_ends_at)
    logger.info(
      f"[CompanyService.cambiar_plan] id={company_id}"
      f"plan='{new_plan.value}' by={requesting_user_id}"
    )
    return company

  @staticmethod
  def eliminar_compañia(db:Session, company_id: UUID, requesting_user_id: UUID) -> bool:
    """
      soft delete de una compañía.
      guard clauses:
        1- Solo admin propio o admin del parent
        2- No eliminar si tiene subsidiarias activas
        3- No eliminar si tiene miembros activos distintos al admin
    """
    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_administrar(db, company, requesting_user_id, "eliminar esta compañia")
    active_children = CompanyRepository.count_children(db, company_id)
    if active_children > 0:
      raise ValueError(
        f"No se puede eliminar la compañía porque tiene "
        f"{active_children} subsidiarias activas. Elimínalas primero.")
    
    # guard --- no se debe eliminar con usuarios activos 
    users_actives = CompanyUserRepository.count_active_users(db, company_id)
    if users_actives > 1:
      raise ValueError(
        f"No se puede eliminar la compañía porque tiene "
        f"{users_actives} usuarios activos. Retíralos primero."
      )
    
    result = CompanyRepository.deactivate(db, company_id)
    logger.info(f"[CompanyService.eliminar_compañia] id={company_id} by={requesting_user_id}")
    return result

  # SUBCIDIARIAS
  @staticmethod
  def crear_subsidiaria(db:Session,
    parent_id:UUID, 
    company_data: dict,
    child_plan:BillingPlan, 
    requesting_user_id: UUID) -> Company:
    """
    crear una subsidiaria bajo el parent
    guard clauses:
    1 - solo el admin del parent puede crear subsidiaria
    2 - el plan del parent debe soportar subsidiaria
    3 - no puede superar max_children del parent
    4 - el slug de la subsidiaria debe ser unico globalmente (manejado por la DB ya que es unique)
    """
    parent = _obtener_compania_o_error(db, parent_id)
    _verificar_es_admin(db, parent_id, requesting_user_id, "crear subsidiaria")

    # guard --- el plan del parent debe soportar subsidiarias
    if parent.billing_plan not in PLANS_WITH_CHILDREN:
      raise ValueError(
        f"El plan '{parent.billing_plan.value}' no permite crear subsidiarias. "
        f"Actualiza al plan 'pro' o 'empresas'."
      )
    
    # guard --- no debe superar max_children
    active_children = CompanyRepository.count_children(db, parent_id)
    if active_children >= parent.max_children:
      raise ValueError(
        f" {parent.name} alcanzó el límite de"
        f" {parent.max_children} subsidiarias del plan {parent.billing_plan.value}"
      )
    

    # aplicar limites de plan del hijo
    limits = BILLING_PLAN_LIMITS[child_plan.value]
    company_data.update(
      {
        "parent_id": parent_id,
        "billing_plan": child_plan,
        "structure_type": company_data.get("structure_type", StructureType.simple),
        "max_users_per_plan": limits["max_users_per_plant"],
        "max_plants": limits["max_plants"],
        "max_storage_gb": limits["max_storage_gb"],
        "max_children": limits["max_children"]
      }
    )
    child = CompanyRepository.create(db,company_data)
    logger.info(
        f"[CompanyService.crear_subsidiaria] child= {child.id}"
        f"parent = {parent_id} plan = {child_plan.value} by = {requesting_user_id}"
    )
    return child
  
  @staticmethod
  def eliminar_subsidiaria(db: Session, child_id: UUID, requesting_user_id: UUID) -> bool:
    """
    elimina una subsidiaria 
    guard: solo el admin del parent puede eliminarla
    """

    child = _obtener_compania_o_error(db, child_id)
    if not child.parent_id:
      raise ValueError("Esta compañia no es una subsidiaria")
    _verificar_es_admin(db, child.parent_id, requesting_user_id,"eliminar subsidiaria")
    active_children = CompanyRepository.count_children(db, child_id)
    if active_children > 0:
      raise ValueError(
        f"No se puede eliminar la subsidiaria porque tiene"
        f"{active_children} sub-subsidiarias activas"
      )
    
    result = CompanyRepository.deactivate(db, child_id)
    logger.info(f"[CompanyService.eliminar_subsidiaria] child = {child_id} by = {requesting_user_id}")
    return result
    

  @staticmethod
  def listar_subsidiarias(db:Session, parent_id:UUID, requesting_user_id: UUID) -> list[Company]:
    # listar las subsidiarias activas de un parent
    # solo el admin del parent puede ver la lista completa de subsidiarias

    parent = _obtener_compania_o_error(db, parent_id)
    _verificar_es_admin(db, parent_id, requesting_user_id, "ver subsidiarias")
    return CompanyRepository.get_all_children_by_parent(db, parent_id)
  

  # USUARIOS EN COMPAÑIA
  
  @staticmethod
  def agregar_usuario(db: Session, 
    company_id:UUID, 
    user_id: UUID, 
    role:CompanyRole, 
    requesting_user_id: UUID) -> CompanyUser:
    """
    agregar un usuario a una compañia
    guard clauses:
    1 - solo acciona el admin propio o admin del parent
    2 - no puede superar el limite total de usuario del plan (PlantService se encarga)
    3 - el usuario no puede ya ser un miembro activo
    """
    # guard -- solo accionan loas admin
    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_administrar(db, company, requesting_user_id, "agregar usuarios")

    # guard -- el usuario que se va a agregar no debe ser un miembro activo
    if CompanyUserRepository.is_users_in_company(db, company_id, user_id):
      raise ValueError("El usuario ya es miembro activo de esta compañia")

    membership = CompanyUserRepository.add_user_to_company(
      db, company_id, user_id, role, invited_by_id=requesting_user_id
    )
    logger.info(
       f"[CompanyService.agregar_usuario] user = {user_id}"
       f"company = {company_id} rol = {role.value} by = {requesting_user_id}"
    )
    return membership

  # metodo sujeto a pruebas y a cambios
  @staticmethod
  def remover_usuario(
      db:Session,
      company_id: UUID,
      target_user_id: UUID,
      requesting_user_id: UUID
  ) -> bool:
    
    """
    remover un usuario de la compañia - soft delete de membresia
    guard clauses:
    1 - solo admin propio o admin del parent
    2 - no puede removerse a si mismo si este es el unico admin
    3 - no puede remover al ultimo admin de la compañia
    """

    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_administrar(db, company, requesting_user_id, "remover usuario")
    
    # guard --- verifica que el target es miembro activo
    rol_target = CompanyUserRepository.get_user_role(db, company_id, target_user_id)
    if not rol_target:
      raise ValueError("El usuario no es miembro activo de esta compañia")

    if rol_target == CompanyRole.admin:
      total_admins = CompanyUserRepository.count_users_by_role(db, company_id, CompanyRole.admin)
      if total_admins <= 1:
        raise ValueError(
          "No se puede remover al unico administrador de la compañia"
          "Asigna otro administrador primero"
        )
    result = CompanyUserRepository.remove_user_from_company(db, company_id, target_user_id)
    logger.info(
      f"[CompanyService.remover_usuario] user = {target_user_id}"
      f"company = {company_id} by = {requesting_user_id}"
    )
    return result
    
  @staticmethod
  def cambiar_rol_usuario(
    db: Session,
    company_id:UUID,
    target_user_id: UUID,
    new_role: CompanyRole,
    requesting_user_id: UUID
  ) -> CompanyUser:

    """
    cambia el rol de un usuario
    guard clauses
    1 - solo el admin puede cambiar roles
    2 - no puede cambiar su propio rol
    3 - no puede degradar al otro admin
    4 - no puede cambiar al rol que ya esta asignado otro usuario
    5 - debe ser un admin activo o un usuario activo dentro del sistema
    """

    _verificar_es_admin(db, company_id, requesting_user_id, "cambiar rol a usuario")
    if requesting_user_id == target_user_id:
      raise ValueError("" \
      "Un administrador no puede cambiar su propio rol")
    
    # guard --- debe ser un rol activo o admin activo dentro del sistema
    current_role = CompanyUserRepository.get_user_role(db, company_id, target_user_id)
    if not current_role:
      raise ValueError("El usuario no es miembro activo de esta compañia")

    # guard --- no puede degradar al otro admin
    current_role == CompanyRole.admin and new_role != CompanyRole.admin:
    total_admins = CompanyUserRepository.count_users_by_role(
      db, company_id, CompanyRole.admin
    )
    if total_admins <= 1:
      raise ValueError(
          "No se puede remover al unico administrador de la compañia"
          "Asigna otro administrador primero"
        )
    membership = CompanyUserRepository.update_user_role(
      db, company_id, target_user_id, new_role
    )

    if not membership:
      raise ValueError("El usuario no es miembro activo de esta compañia")
    logger.info(
      f"[CompanyService.cambiar_rol_usuario] user = {target_user_id} "
      f"{current_role.value} > {new_role} by = {requesting_user_id}"
    )
    return membership
  
  @staticmethod
  def listar_usuarios(
    db:Session,
    company_id:UUID,
    requesting_user_id: UUID,
    role: CompanyRole = None, # corregir error (None no se puede asignar a CompanyRole como argumento)
    skip: int = 0,
    limit: int = 20,
  ) -> list[CompanyUser]:
    
    # listar los miembros activos de la compañia
    # cualquier miembro puede ver la lista 

    company = _obtener_compania_o_error(db, company_id)
    _verificar_puede_ver(db, company, requesting_user_id)

    return CompanyUserRepository.get_users_by_company(
      db, company_id, role = role, skip = skip, limit= limit
    )
  
# HELPERS ------- PRIVADOS

def _verificar_quien_puede_ver_compania_completa(db: Session, company:Company, user_id:UUID)->None:
  """
  guard --- discriminamos metricas - datos sensibles de la compañia.
  solo pueden ver el admin de la compañia, auditor de la compañia y admin del parent.
  el parent tiene control total de la subsidiaria.
  
  los demas roles como:
  supervisor - tecnico y operador no pueden ver metricas globales.
  """
 
  role = CompanyUserRepository.get_user_role(db, company.id, user_id)
  if role in {CompanyRole.admin, CompanyRole.auditor}: # aceptamos permismo para admin y auditor
    return 
  
  # verificamos que el parent pertenezca a la compañia
  if company.parent_id: 
    parent_role = CompanyUserRepository.get_user_role(db, company.parent_id, user_id) # parent de la company
    if parent_role == CompanyRole.admin:
      return
  raise PermissionError(
    "No tienes los permisos para ver esta informacion, solo administradores y auditores"
  )


def _obtener_compania_o_error(db:Session, company_id:UUID)->Company:
  # obtiene la compañia si no lanza error
  company = CompanyRepository.get_by_id(db,company_id)
  if not company:
    raise ValueError(f"Compañia con id -> {company_id} no encontrada")
  
  return company

def _verificar_es_admin(db:Session, company_id:UUID, user_id:UUID, accion:str) ->None:
  # lanza error de permiso si no es admin de la compañia
  role = CompanyUserRepository.get_user_role(db, company_id, user_id)
  if role != CompanyRole.admin:
    raise PermissionError(f"Solamente el admin puede {accion}")
  

def _verificar_puede_administrar(db:Session, company:Company, user_id:UUID, accion: str )-> None:
  """
  pueden administrar
  1 - admin de la propia compañia -> puede administrarla
  2 - admin del parent -> puede administrar cualquier subsidiaria
  """
  role = CompanyUserRepository.get_user_role(db, company.id, user_id)
  if role == CompanyRole.admin:
    return
  
  if company.parent_id:
    parent_role = CompanyUserRepository.get_user_role(db, company.parent_id, user_id)
    if parent_role == CompanyRole.admin:
      return
    
  raise PermissionError(f"No tiene permisos para {accion}")

def _verificar_es_miembro_activo_o_no(db:Session, company_id:UUID, user_id:UUID)-> CompanyRole:
    # guard --- verificar es miembro activo
    # retorna el rol del usuario

    role = CompanyUserRepository.get_user_role(db, company_id, user_id)
    if not role:
      raise PermissionError("No eres miembro de esta compañia")
    
    return role

def _verificar_puede_ver(db: Session, company: Company, user_id:UUID)-> None:
  """
  guard clause de visibilidad
   - cualquier miembro activo puede ver su propia compañia
   - admin del parent puede ver cualquier subsidiaria
  """

  # es miebro de la compañia
  if CompanyUserRepository.get_user_role(db, company.id, user_id):
    return 
  
  # es admin del parent
  if company.parent_id:
    parent_role = CompanyUserRepository.get_user_role(db, company.parent_id, user_id)
    if parent_role == CompanyRole.admin:
      return
  
  raise PermissionError("No tienes acceso a esta compañia")