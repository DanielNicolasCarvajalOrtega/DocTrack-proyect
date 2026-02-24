import uuid
import random
import sys
from pathlib import Path

# Agregar backend/api al path para encontrar el módulo 'app'
sys.path.insert(0, str(Path(__file__).parent.parent / 'api'))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from api.app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.compañias.models import Company, CompanyUser, CompanyRole, BillingPlan
from app.modules.plantas.models import Plant, Area
from app.modules.maquinas.models import Machine, MachineStatus
from app.modules.documentos.models import Document, DocumentStatus, DocumentType, DocumentReadConfirmation
from app.modules.mantenimiento.models import (
    MaintenanceType, MaintenanceTask, MaintenanceActivityLog, TaskPriority, TaskStatus
)


def run_seed():
    db: Session = SessionLocal()
    try:
        print("🌱 Iniciando semilla de datos masiva de nivel corporativo...")
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

        estadisticas = {"empresas": 0, "usuarios": 0, "plantas": 0, "maquinas": 0, "tareas": 0}

        # Generar todo el ecosistema por cada empresa
        for idx, emp_data in enumerate(empresas_data):
            print(f"🏢 Construyendo ecosistema para: {emp_data['name']}...")
            
            # crear empresa
            company = _crear_empresa_completa(db, emp_data)
            estadisticas["empresas"] += 1
            
            # crear usuarios de la empresa
            users_dict = _crear_usuarios_completos(db, company, emp_data['domain'], is_first=(idx==0))
            estadisticas["usuarios"] += len(users_dict)
            
            # crear plantas y áreas
            plantas = _crear_plantas_completas(db, company)
            estadisticas["plantas"] += len(plantas)
            
            # crear maquinas para esas áreas
            maquinas = _crear_maquinas_completas(db, plantas)
            estadisticas["maquinas"] += len(maquinas)
            
            #  generar documentos y mantenimientos
            _generar_comportamiento_operativo(db, maquinas, users_dict)
            estadisticas["tareas"] += len(maquinas) * 2 # aprox 2 tareas por maquina

        print("-" * 60)
        print("✅ Seed corporativo completado exitosamente!")
        print("\n📊 Resumen de Base de Datos:")
        print(f"   🏢 Empresas creadas: {estadisticas['empresas']}")
        print(f"   👥 Usuarios activos: {estadisticas['usuarios']}")
        print(f"   🏭 Plantas operativas: {estadisticas['plantas']}")
        print(f"   ⚙️  Máquinas registradas: {estadisticas['maquinas']}")
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
        max_users=500,
        max_plants=20,
        max_storage_gb=100,
        trial_ends_at=now - timedelta(days=10), # ya pasaron la prueba
        subscription_ends_at=now + timedelta(days=365), # suscripción de 1 año
        contact_email=f"contacto@{data['domain']}",
        contact_phone=f"+569{random.randint(11111111, 99999999)}", # debe validarse el largo y codigo
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
        db.commit()
        db.refresh(u)
        
        cu = CompanyUser(
            company_id=company.id,
            user_id=u.id,
            role=ud["role"],
            joined_at=now - timedelta(days=random.randint(30, 300))
        )
        db.add(cu)
        db.commit()
        
        creados[ud["role"].value] = u
        
    return creados

def _crear_plantas_completas(db: Session, company: Company) -> list[Plant]:
    plantas = []
    # 2 Plantas por empresa
    for i in range(1, 3):
        p = Plant(
            name=f"Planta Principal {company.name} - 0{i}",
            company_id=company.id,
            location=f"Sector Industrial {random.choice(['Norte', 'Sur', 'Centro'])}, Lote {random.randint(1,50)}",
            description=f"Planta dedicada a la producción y ensamblaje central de la corporación {company.name}.",
            logo_url=company.logo_url,
            is_active=True
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        
        # 2 Áreas por planta
        for area_name in ["Línea de Producción A", "Sala de Máquinas Críticas"]:
            a = Area(
                name=area_name,
                description=f"Área operativa de alta demanda en {p.name}.",
                plant_id=p.id,
                is_active=True
            )
            db.add(a)
            db.commit()
            
        plantas.append(p)
    return plantas

def _crear_maquinas_completas(db: Session, plantas: list[Plant]) -> list[Machine]:
    maquinas = []
    marcas = ["Siemens", "Bosch", "Caterpillar", "ABB", "General Electric"]
    
    for planta in plantas:
        for area in planta.areas:
            # 2 Máquinas por área
            for i in range(2):
                serial = f"SN-{uuid.uuid4().hex[:8].upper()}"
                m = Machine(
                    name=f"Equipo Industrial Tipo {random.choice(['A', 'B', 'X'])}",
                    model=f"MOD-{random.randint(1000, 9000)}",
                    brand=random.choice(marcas),
                    serial_number=serial,
                    description=f"Equipo de alto tonelaje para procesamiento en línea continua. Mantenimiento requerido cada 500 horas.",
                    location_detail=f"Pasillo {random.randint(1,5)}, Estación {random.randint(1,20)}",
                    status=random.choice(list(MachineStatus)), # Status aleatorio
                    qr_code=f"QR-{serial}",
                    image_url=f"https://via.placeholder.com/500x300.png?text=Maquina+{serial}",
                    area_id=area.id,
                    is_active=True
                )
                db.add(m)
                db.commit()
                db.refresh(m)
                maquinas.append(m)
    return maquinas

def _generar_comportamiento_operativo(db: Session, maquinas: list[Machine], users: dict):
    now = datetime.utcnow()
    admin = users[CompanyRole.admin.value]
    supervisor = users[CompanyRole.supervisor.value]
    tecnico = users[CompanyRole.tecnicos.value]
    operador = users[CompanyRole.operadores.value]

    for m in maquinas:
        #crear un documento técnico sin campos nulos
        doc = Document(
            title=f"Manual de Operación Segura - {m.serial_number}",
            description="Documento oficial del fabricante con normativas ISO-9001 para operación y riesgos.",
            doc_type=DocumentType.manuales,
            status=DocumentStatus.activo,
            version="2.1",
            version_number=2,
            file_url=f"https://storage.provider.com/docs/{m.id}.pdf",
            file_name=f"manual_seguridad_{m.model}.pdf",
            file_size=random.randint(1024, 15000), # Tamaño en KB
            file_type="application/pdf",
            valid_from=now - timedelta(days=100),
            valid_until=now + timedelta(days=365),
            uploaded_by_id=admin.id,
            machine_id=m.id,
            is_active=True
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # simular que el operador leyó el documento
        lectura = DocumentReadConfirmation(
            document_id=doc.id,
            user_id=operador.id,
            read_at=now - timedelta(days=2),
            confirmed_at=now - timedelta(days=1),
            notes="He leído y comprendido los riesgos de operación del equipo."
        )
        db.add(lectura)

        # tarea completada en el pasado
        tarea_pasada = MaintenanceTask(
            title="Calibración de Sensores Térmicos",
            description="Revisión mensual obligatoria de temperatura del motor principal.",
            maintenance_type=MaintenanceType.preventivo,
            status=TaskStatus.completado,
            priority=TaskPriority.mediano,
            scheduled_date=now - timedelta(days=15),
            started_at=now - timedelta(days=15, hours=2),
            completed_at=now - timedelta(days=15),
            due_date=now - timedelta(days=10),
            completion_notes="Sensores calibrados a 45°C. Se reemplazó filtro de aire secundario.",
            estimated_hours=4,
            actual_hours=5,
            machine_id=m.id,
            assigned_to_id=tecnico.id,
            created_by_id=supervisor.id
        )
        db.add(tarea_pasada)
        db.commit()
        db.refresh(tarea_pasada)

        # log de actividad para la tarea completada
        log = MaintenanceActivityLog(
            task_id=tarea_pasada.id,
            user_id=tecnico.id,
            previous_status=TaskStatus.en_progreso,
            new_status=TaskStatus.completado,
            notes="Pruebas de estrés exitosas, máquina liberada para producción."
        )
        db.add(log)

        # tarea pendiente o crítica hacia el futuro
        tarea_futura = MaintenanceTask(
            title="Cambio de Rodamientos Eje Central",
            description="Vibración anómala reportada por el operador. Requiere intervención profunda.",
            maintenance_type=MaintenanceType.correctivo,
            status=TaskStatus.pendiente if m.status is MachineStatus.operativa else TaskStatus.en_progreso,
            priority=TaskPriority.critico,
            scheduled_date=now + timedelta(days=2),
            started_at=now if m.status is not  MachineStatus.operativa else None,
            completed_at=None,
            due_date=now + timedelta(days=3),
            completion_notes="A la espera de repuestos importados.", # Nota aunque no esté completada
            estimated_hours=12,
            actual_hours=2 if m.status is not MachineStatus.operativa else None,
            machine_id=m.id,
            assigned_to_id=tecnico.id,
            created_by_id=supervisor.id
        )
        db.add(tarea_futura)
        
    db.commit()

if __name__ == "__main__":
    run_seed()