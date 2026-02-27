import uuid
import random
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(BASE_DIR))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.modules.users.models import User
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.plantas.models import Plant, Area
from app.modules.maquinas.models import Machine, MachineStatus
from app.modules.documentos.models import Document, DocumentStatus, DocumentType, DocumentReadConfirmation
from app.modules.mantenimiento.models import (
    MaintenanceType, MaintenanceTask, MaintenanceActivityLog, TaskPriority, TaskStatus
)
from app.core.security import hash_password
from app.core.database import SessionLocal

def run_seed():
    db: Session = SessionLocal()
    try:
        print("🌱 Iniciando semilla de datos MASIVA (Stress Test) corporativo...")
        _clear_data(db)
        
        # Datos base para las 6 empresas
        empresas_data = [
            {"name": "Carozzi S.A.", "slug": "carozzi", "plan": BillingPlan.empresas, "color": "#E3000F", "domain": "carozzi.cl"},
            {"name": "Nestlé Chile", "slug": "nestle", "plan": BillingPlan.empresas, "color": "#005A9C", "domain": "nestle.com"},
            {"name": "Coca-Cola Andina", "slug": "coca-cola", "plan": BillingPlan.pro, "color": "#F40009", "domain": "koandina.com"},
            {"name": "Siemens Energy", "slug": "siemens", "plan": BillingPlan.empresas, "color": "#009999", "domain": "siemens.com"},
            {"name": "Toyota Industries", "slug": "toyota", "plan": BillingPlan.pro, "color": "#EB0A1E", "domain": "toyota.com"},
            {"name": "Bayer Agro", "slug": "bayer", "plan": BillingPlan.basico, "color": "#89D329", "domain": "bayer.com"},
        ]

        estadisticas = {"empresas": 0, "usuarios": 0, "plantas": 0, "areas": 0, "maquinas": 0, "tareas": 0, "documentos": 0}

        # Generar todo el ecosistema por cada empresa
        for idx, emp_data in enumerate(empresas_data):
            print(f"🏢 Construyendo ecosistema masivo para: {emp_data['name']}...")
            
            # crear empresa
            company = _crear_empresa_completa(db, emp_data)
            estadisticas["empresas"] += 1
            
            # crear usuarios de la empresa
            users_dict = _crear_usuarios_completos(db, company, emp_data['domain'], is_first=(idx==0))
            estadisticas["usuarios"] += len(users_dict)
            
            # crear plantas y áreas (ALTO VOLUMEN)
            plantas, total_areas = _crear_plantas_completas(db, company)
            estadisticas["plantas"] += len(plantas)
            estadisticas["areas"] += total_areas
            
            # crear maquinas para esas áreas (ALTO VOLUMEN)
            maquinas = _crear_maquinas_completas(db, plantas)
            estadisticas["maquinas"] += len(maquinas)
            
            # generar documentos y mantenimientos
            docs_creados, tareas_creadas = _generar_comportamiento_operativo(db, company, maquinas, users_dict)
            estadisticas["documentos"] += docs_creados
            estadisticas["tareas"] += tareas_creadas

        print("-" * 60)
        print("✅ Seed corporativo masivo completado exitosamente!")
        print("\n📊 Resumen de Volumen Inyectado:")
        print(f"   🏢 Empresas creadas: {estadisticas['empresas']}")
        print(f"   👥 Usuarios activos: {estadisticas['usuarios']}")
        print(f"   🏭 Plantas operativas: {estadisticas['plantas']}")
        print(f"   📍 Áreas generadas: {estadisticas['areas']}")
        print(f"   ⚙️  Máquinas registradas: {estadisticas['maquinas']}")
        print(f"   📄 Documentos inyectados: {estadisticas['documentos']}")
        print(f"   🛠️  Tareas de mantenimiento: {estadisticas['tareas']}")
        
        print("\n🔐 Credenciales de acceso principal (Carozzi - Admin):")
        print("   Email:    manuelesD@gmail.com")
        print("   Password: DocTrack2027@@")
        print("\n   (Para los demás administradores el correo es admin@[dominio] y la clave es Admin123!)")

    except Exception as e:
        print(f"\n❌ Error en seed corporativo: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def _clear_data(db: Session):
    print("🧹 Purgando registros anteriores en cascada...")
    db.query(DocumentReadConfirmation).delete()
    db.query(MaintenanceActivityLog).delete()
    db.query(MaintenanceTask).delete()
    db.query(Document).delete()
    db.query(Machine).delete()
    db.query(Area).delete()
    db.query(Plant).delete()
    db.query(CompanyUser).delete()
    db.query(User).delete()
    db.query(Company).delete()
    db.commit()

def _crear_empresa_completa(db: Session, data: dict) -> Company:
    now = datetime.utcnow()
    company = Company(
        name=data["name"],
        slug=data["slug"],
        billing_plan=data["plan"],
        max_users=5000,
        max_plants=50,
        max_storage_gb=1000,
        trial_ends_at=now - timedelta(days=10),
        subscription_ends_at=now + timedelta(days=365),
        contact_email=f"contacto@{data['domain']}",
        contact_phone=f"+569{random.randint(11111111, 99999999)}",
        address=f"Av. Corporativa {random.randint(100, 9999)}, Santiago, Chile",
        logo_url=f"https://logo.clearbit.com/{data['domain']}",
        primary_color=data["color"],
        is_active=True
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def _crear_usuarios_completos(db: Session, company: Company, domain: str, is_first: bool) -> dict:
    if is_first:
        admin_email, admin_pass = "manuelesD@gmail.com", "DocTrack2027@@"
    else:
        admin_email, admin_pass = f"admin@{domain}", "Admin123!"

    now = datetime.utcnow()
    
    users_data = [
        {"role": CompanyRole.admin, "email": admin_email, "pass": admin_pass, "fname": "Director", "lname": company.name},
        {"role": CompanyRole.supervisor, "email": f"super@{domain}", "pass": "Super123!", "fname": "Jefe", "lname": "Planta"},
        {"role": CompanyRole.tecnicos, "email": f"tecnico@{domain}", "pass": "Tecnico123!", "fname": "Especialista", "lname": "Mantenimiento"},
        {"role": CompanyRole.operadores, "email": f"operador@{domain}", "pass": "Operador123!", "fname": "Operario", "lname": "Línea"}
    ]

    creados = {}
    for ud in users_data:
        u = User(
            first_name=ud["fname"],
            last_name=ud["lname"],
            email=ud["email"],
            password_hash=hash_password(ud["pass"]),
            phone=f"+569{random.randint(10000000, 99999999)}", 
            avatar_url=f"https://ui-avatars.com/api/?name={ud['fname']}+{ud['lname']}&background=random",
            is_super_admin=False,
            email_verified=True,
            last_login_at=now - timedelta(hours=random.randint(1, 48)),
            is_active=True
        )
        
        db.add(u)
        db.flush() # Flush asigna el ID sin commitear aún
        
        cu = CompanyUser(
            company_id=company.id,
            user_id=u.id,
            role=ud["role"],
            joined_at=now - timedelta(days=random.randint(30, 300))
        )
        db.add(cu)
        db.flush()
        
        creados[ud["role"].value] = u
        
    db.commit() # Un solo commit para todos los usuarios
    return creados

def _crear_plantas_completas(db: Session, company: Company) -> tuple[list[Plant], int]:
    plantas = []
    total_areas = 0
    # AUMENTO DE VOLUMEN: 5 Plantas por empresa
    for i in range(1, 6):
        p = Plant(
            name=f"Planta Principal {company.name} - 0{i}",
            company_id=company.id,
            location=f"Sector Industrial {random.choice(['Norte', 'Sur', 'Centro', 'Este', 'Oeste'])}, Lote {random.randint(1,500)}",
            description=f"Instalación de alto rendimiento operada por {company.name}.",
            logo_url=company.logo_url,
            is_active=True
        )
        db.add(p)
        db.flush() # Obtenemos p.id
        
        # AUMENTO DE VOLUMEN: 5 Áreas por planta
        tipos_areas = ["Línea de Producción", "Sala de Máquinas", "Empaquetado", "Procesamiento Térmico", "Almacenamiento Activo"]
        for j, tipo in enumerate(tipos_areas, 1):
            a = Area(
                name=f"{tipo} {j}-{p.name[-2:]}",
                description=f"Área operativa de nivel crítico.",
                plant_id=p.id,
                is_active=True
            )
            db.add(a)
            total_areas += 1
            
        plantas.append(p)
        
    db.commit() # Guardamos en bloque
    return plantas, total_areas

def _crear_maquinas_completas(db: Session, plantas: list[Plant]) -> list[Machine]:
    maquinas = []
    marcas = ["Siemens", "Bosch", "Caterpillar", "ABB", "General Electric", "Mitsubishi", "Schneider"]
    
    for planta in plantas:
        for area in planta.areas:
            # AUMENTO DE VOLUMEN: 15 Máquinas por área
            for i in range(1, 16):
                serial = f"SN-{uuid.uuid4().hex[:8].upper()}"
                m = Machine(
                    name=f"Equipo Industrial {random.choice(['Extrusora', 'Motor', 'Banda', 'Horno', 'Compresor'])}",
                    model=f"MOD-{random.randint(1000, 9999)}",
                    brand=random.choice(marcas),
                    serial_number=serial,
                    description=f"Maquinaria pesada inyectada en semilla masiva. Operando en {area.name}.",
                    location_detail=f"Pasillo {random.randint(1,10)}, Estación {random.randint(1,50)}",
                    status=random.choices(list(MachineStatus), weights=[70, 10, 15, 5])[0], # 70% operativas
                    qr_code=f"QR-{serial}",
                    image_url=f"https://via.placeholder.com/500x300.png?text=Maquina+{serial}",
                    area_id=area.id,
                    is_active=True
                )
                db.add(m)
                maquinas.append(m)
                
    db.commit() # Solo 1 commit pesado por empresa
    return maquinas

def _generar_comportamiento_operativo(db: Session, company: Company, maquinas: list[Machine], users: dict):
    now = datetime.utcnow()
    admin = users[CompanyRole.admin.value]
    supervisor = users[CompanyRole.supervisor.value]
    tecnico = users[CompanyRole.tecnicos.value]
    operador = users[CompanyRole.operadores.value]

    docs_creados = 0
    tareas_creadas = 0

    for m in maquinas:
        # Documento corregido (company_id)
        doc = Document(
            title=f"Manual Técnico v{random.randint(1,5)} - {m.serial_number}",
            description="Documentación de seguridad operacional.",
            doc_type=random.choice(list(DocumentType)),
            status=DocumentStatus.activo,
            version=f"{random.randint(1,3)}.0",
            version_number=1,
            file_url=f"https://storage.provider.com/docs/{m.id}.pdf",
            file_name=f"doc_{m.model}.pdf",
            file_size=random.randint(2048, 25000), 
            file_type="application/pdf",
            valid_from=now - timedelta(days=100),
            valid_until=now + timedelta(days=365),
            uploaded_by_id=admin.id,
            machine_id=m.id,
            company_id=company.id,  # CORRECCIÓN APLICADA AQUÍ
            is_active=True
        )
        db.add(doc)
        db.flush()
        docs_creados += 1

        # Confirmación de lectura aleatoria (solo para el 50% de las máquinas)
        if random.choice([True, False]):
            lectura = DocumentReadConfirmation(
                document_id=doc.id,
                user_id=operador.id,
                read_at=now - timedelta(days=random.randint(1, 10)),
                confirmed_at=now - timedelta(days=random.randint(1, 5)),
                notes="Leído y aceptado."
            )
            db.add(lectura)

        # Tarea histórica completada
        tarea_pasada = MaintenanceTask(
            title=f"Revisión de rutina - {m.serial_number}",
            description="Mantenimiento preventivo mensual.",
            maintenance_type=MaintenanceType.preventivo,
            status=TaskStatus.completado,
            priority=random.choice(list(TaskPriority)),
            scheduled_date=now - timedelta(days=30),
            started_at=now - timedelta(days=30, hours=2),
            completed_at=now - timedelta(days=30),
            due_date=now - timedelta(days=25),
            completion_notes="Todo en orden operativo.",
            estimated_hours=4,
            actual_hours=random.randint(3, 6),
            machine_id=m.id,
            assigned_to_id=tecnico.id,
            created_by_id=supervisor.id
        )
        db.add(tarea_pasada)
        db.flush()
        tareas_creadas += 1

        log = MaintenanceActivityLog(
            task_id=tarea_pasada.id,
            user_id=tecnico.id,
            previous_status=TaskStatus.en_progreso,
            new_status=TaskStatus.completado,
            notes="Cierre de orden de trabajo."
        )
        db.add(log)

        # Si la máquina no está operativa, crear tarea pendiente o en progreso
        if m.status in [MachineStatus.fallas, MachineStatus.mantenimiento]:
            tarea_activa = MaintenanceTask(
                title=f"Reparación Urgente - {m.serial_number}",
                description="Falla detectada durante turno.",
                maintenance_type=MaintenanceType.correctivo,
                status=TaskStatus.en_progreso if m.status == MachineStatus.mantenimiento else TaskStatus.pendiente,
                priority=TaskPriority.critico,
                scheduled_date=now + timedelta(days=1),
                started_at=now if m.status == MachineStatus.mantenimiento else None,
                completed_at=None,
                due_date=now + timedelta(days=2),
                completion_notes=None,
                estimated_hours=8,
                actual_hours=None,
                machine_id=m.id,
                assigned_to_id=tecnico.id,
                created_by_id=supervisor.id
            )
            db.add(tarea_activa)
            tareas_creadas += 1

    db.commit() # Commit masivo al final de procesar todas las máquinas
    return docs_creados, tareas_creadas

if __name__ == "__main__":
    run_seed()