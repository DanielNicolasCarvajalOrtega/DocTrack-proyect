"""
Módulo de compañías

Fuente de verdad para:
  - Límites por plan de pago
  - Precios en CLP y USD
  - Planes que soportan subsidiarias
  - Whitelists de campos actualizables
  - Estructuras permitidas por plan
  - Terminología por industria
 
REGLA: Los campos max_* NUNCA son editables directamente por el admin.
El Service llama a apply_billing_plan() que lee BILLING_PLAN_LIMITS
y los aplica automáticamente al cambiar el plan.
"""

from app.modules.compañias.models import BillingPlan, StructureType

BILLING_PLAN_LIMITS: dict[str, dict] = {
    BillingPlan.prueba.value: {
        "max_users_per_plant": 5,
        "max_plants":          1,
        "max_storage_gb":      2,
        "max_children":        0,
    },
    BillingPlan.basico.value: {
        "max_users_per_plant": 20,
        "max_plants":          2,
        "max_storage_gb":      15,
        "max_children":        1,
    },
    BillingPlan.pro.value: {
        "max_users_per_plant": 60,
        "max_plants":          20,
        "max_storage_gb":      150,
        "max_children":        6,
    },
    BillingPlan.empresas.value: {
        "max_users_per_plant": 120,
        "max_plants":          30,
        "max_storage_gb":      1024,  # 1 TB
        "max_children":        22,
    },
}

BILLING_PLAN_PRICES: dict[str, dict] = {
    BillingPlan.prueba.value: {
        "clp":        0,
        "usd":        0,
        "descripcion": "Gratis — prueba sin compromiso",
    },
    BillingPlan.basico.value: {
        "clp":        54_990,
        "usd":        60,
        "descripcion": "PYME industrial — 1 subsidiaria, 2 plantas, 40 usuarios",
    },
    BillingPlan.pro.value: {
        "clp":        229_990,
        "usd":        250,
        "descripcion": "Mediana empresa — 6 subsidiarias, 20 plantas, 1.200 usuarios",
    },
    BillingPlan.empresas.value: {
        "clp":        899_990,
        "usd":        990,
        "descripcion": "Corporativo — 22 subsidiarias, 30 plantas, 3.600 usuarios, 1 TB",
    },
}


"""
simple      → Company → Plant → Area → Machine
divisional  → Company → Division → Plant → Area → Machine
corporativo → Parent → Company → Division → Plant → Area → Machine

prueba/basico → solo simple
pro           → simple o divisional
empresas      → cualquiera incluyendo corporativo

"""

PLAN_ALLOWED_STRUCTURES: dict[str, set] = {
    BillingPlan.prueba.value:   {StructureType.simple},
    BillingPlan.basico.value:   {StructureType.simple},
    BillingPlan.pro.value:      {StructureType.simple, StructureType.divisional},
    BillingPlan.empresas.value: {StructureType.simple, StructureType.divisional, StructureType.corporativo},
}

# PLANES QUE SOPORTAN SUBSIDIARIAS
# Usado en el Service para validar antes de crear una subsidiaria

PLANS_WITH_CHILDREN: set[BillingPlan] = {
    BillingPlan.basico,
    BillingPlan.pro,
    BillingPlan.empresas,
}

"""
WHITELISTS DE CAMPOS ACTUALIZABLES

    COMPANY_ALLOWED_UPDATE_FIELDS:
    Campos que el admin puede modificar directamente.
    max_users_per_plant, max_plants, max_storage_gb, max_children
    NO están aquí — los gestiona apply_billing_plan() automáticamente.
    COMPANY_USER_ALLOWED_UPDATE_FIELDS:
    Campos de membresía actualizables.

"""

COMPANY_ALLOWED_UPDATE_FIELDS: set[str] = {
    "name",
    "slug",
    "industry",
    "structure_type",
    "trial_ends_at",
    "subscription_ends_at",
    "contact_email",
    "contact_phone",
    "address",
    "logo_url",
    "primary_color",
}
 
COMPANY_USER_ALLOWED_UPDATE_FIELDS: set[str] = {
    "role",
}
 

""" 
TERMINOLOGÍA POR INDUSTRIA
Permite adaptar los labels del frontend según la industria del cliente.
Ej: "División" en alimentos -> "Faena" en minería -> "Proyecto" en construcción
El frontend consulta este dict para mostrar los labels correctos.
"""

INDUSTRY_LABELS: dict[str, dict[str, str]] = {
    "alimentos_bebidas": {
        "division": "División",
        "plant":    "Planta",
        "area":     "Línea",
    },
    "manufactura": {
        "division": "Unidad",
        "plant":    "Planta",
        "area":     "Línea de producción",
    },
    "construccion": {
        "division": "Proyecto",
        "plant":    "Obra",
        "area":     "Frente de trabajo",
    },
    "mineria": {
        "division": "Faena",
        "plant":    "Instalación",
        "area":     "Nivel",
    },
    "energia": {
        "division": "Unidad de negocio",
        "plant":    "Central",
        "area":     "Sector",
    },
    "salud": {
        "division": "Unidad clínica",
        "plant":    "Sede",
        "area":     "Pabellón",
    },
    "logistica": {
        "division": "Operación",
        "plant":    "Centro de distribución",
        "area":     "Zona",
    },
    "hoteleria": {
        "division": "Cadena",
        "plant":    "Hotel",
        "area":     "Piso",
    },
    "petroquimica": {
        "division": "Complejo",
        "plant":    "Refinería",
        "area":     "Unidad de proceso",
    },
    "agroindustria": {
        "division": "Unidad productiva",
        "plant":    "Planta",
        "area":     "Sector",
    },
    "otro": {
        "division": "División",
        "plant":    "Planta",
        "area":     "Área",
    },
}