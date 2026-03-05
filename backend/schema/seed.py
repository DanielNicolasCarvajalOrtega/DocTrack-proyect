import sys
import os
import hashlib
from pathlib import Path

# 1. INYECTAR LA RUTA
BASE_DIR = Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(BASE_DIR))

import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

# Importaciones de Modelos
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
        print("🌱 Iniciando semilla MASIVA: Compliance, Seguridad LOTO y Auditoría...")
        _clear_data(db)
        
        empresas_data = [
            {"name": "Carozzi S.A.", "slug": "carozzi", "plan": BillingPlan.empresas, "color": "#E3000F", "domain": "carozzi.cl"},
            {"name": "Nestlé Chile", "slug": "nestle", "plan": BillingPlan.empresas, "color": "#005A9C", "domain": "nestle.com"},
            {"name": "Coca-Cola Andina", "slug": "coca-cola", "plan": BillingPlan.pro, "color": "#F40009", "domain": "koandina.com"},
            {"name": "Siemens Energy", "slug": "siemens", "plan": BillingPlan.empresas, "color": "#009999", "domain": "siemens.com"},
        ]

        estadisticas = {"empresas": 0, "usuarios": 0, "plantas": 0, "areas": 0, "maquinas": 0, "maquinas_seguras": 0, "firmas_legales": 0}

        for idx, emp_data in enumerate(empresas_data):
            print(f"🏢 Construyendo ecosistema seguro para: {emp_data['name']}...")
            
            company = _crear_empresa_completa(db, emp_data)
            estadisticas["empresas"] += 1
            
            users_dict = _crear_usuarios_jerarquicos(db, company, emp_data['domain'], is_first=(idx==0))
            estadisticas["usuarios"] += len(users_dict)
            
            plantas, total_areas = _crear_plantas_y_accesos(db, company, users_dict)
            estadisticas["plantas"] += len(plantas)
            estadisticas["areas"] += total_areas
            
            maquinas, maquinas_seguras = _crear_maquinas_seguras(db, plantas, users_dict)
            estadisticas["maquinas"] += len(maquinas)
            estadisticas["maquinas_seguras"] += maquinas_seguras
            
            firmas = _generar_comportamiento_operativo(db, company, maquinas, users_dict)
            estadisticas["firmas_legales"] += firmas

        print("-" * 60)
        print("✅ Seed corporativo con Accesos, LOTO y Compliance completado!")
        print("\n📊 Resumen de Volumen Inyectado:")
        print(f"   🏢 Empresas creadas: {estadisticas['empresas']}")
        print(f"   👥 Usuarios activos: {estadisticas['usuarios']}")
        print(f"   🏭 Plantas operativas: {estadisticas['plantas']}")
        print(f"   📍 Áreas generadas: {estadisticas['areas']}")
        print(f"   ⚙️  Máquinas registradas: {estadisticas['maquinas']}")
        print(f"   🔒 Máquinas con PIN Activo: {estadisticas['maquinas_seguras']}")
        print(f"   🛡️ Firmas Digitales (Escudo Legal): {estadisticas['firmas_legales']}")
        
        print("\n🔐 CREDENCIALES DE PRUEBA (Carozzi):")
        print("   Email Admin (Ve todo):     manuelesD@gmail.com")
        print("   Email Auditor (ISO):       auditor@carozzi.cl")
        print("   Email Jefe Planta:         jefe.planta@carozzi.cl")
        print("   Email Supervisor Área:     jefe.area@carozzi.cl")
        print("   Email Técnico Fijo:        tecnico.fijo@carozzi.cl")
        print("   Email Operario:            operador@carozzi.cl")
        print("   🔑 Password para todos:    DocTrack2027@@")
        print("   🛡️ PIN DE MÁQUINAS:        1234 (Para las que exigen código)")

    except Exception as e:
        print(f"\n❌ Error en seed corporativo: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def _clear_data(db: Session):
    print("🧹 Purgando registros y bitácoras anteriores...")
    db.execute(text("DELETE FROM machine_pin_audit_logs"))
    db.execute(text("DELETE FROM user_area_access"))
    db.execute(text("DELETE FROM user_plant_access"))
    db.commit()
    
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
    company = Company(
        name=data["name"],
        slug=data["slug"],
        billing_plan=data["plan"],
        max_users=5000,
        max_plants=50,
        contact_email=f"contacto@{data['domain']}",
        is_active=True
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def _crear_usuarios_jerarquicos(db: Session, company: Company, domain: str, is_first: bool) -> dict:
    admin_email = "manuelesD@gmail.com" if is_first else f"admin@{domain}"
    password = "DocTrack2027@@"
    now = datetime.utcnow()
    
    users_data = [
        {"role": CompanyRole.admin, "type": "admin", "email": admin_email, "fname": "Director", "lname": company.name},
        {"role": CompanyRole.auditor, "type": "auditor", "email": f"auditor@{domain}", "fname": "Auditor", "lname": "Externo ISO"},
        {"role": CompanyRole.supervisor, "type": "jefe_planta", "email": f"jefe.planta@{domain}", "fname": "Gerente", "lname": "Planta"},
        {"role": CompanyRole.supervisor, "type": "jefe_area", "email": f"jefe.area@{domain}", "fname": "Supervisor", "lname": "Área"},
        {"role": CompanyRole.tecnicos, "type": "tecnico_libre", "email": f"tecnico.libre@{domain}", "fname": "Técnico", "lname": "Comodín"},
        {"role": CompanyRole.tecnicos, "type": "tecnico_fijo", "email": f"tecnico.fijo@{domain}", "fname": "Técnico", "lname": "Línea"},
        {"role": CompanyRole.operadores, "type": "operador", "email": f"operador@{domain}", "fname": "Operario", "lname": "Base"}
    ]

    creados = {}
    for ud in users_data:
        u = User(
            first_name=ud["fname"],
            last_name=ud["lname"],
            email=ud["email"],
            password_hash=hash_password(password),
            email_verified=True,
            is_active=True
        )
        db.add(u)
        db.flush()
        
        cu = CompanyUser(
            company_id=company.id,
            user_id=u.id,
            role=ud["role"],
            joined_at=now - timedelta(days=random.randint(30, 300))
        )
        db.add(cu)
        db.flush()
        creados[ud["type"]] = u
        
    db.commit()
    return creados

def _crear_plantas_y_accesos(db: Session, company: Company, users: dict) -> tuple[list[Plant], int]:
    plantas = []
    total_areas = 0
    jefe_planta = users["jefe_planta"]
    tecnico_libre = users["tecnico_libre"]
    jefe_area = users["jefe_area"]
    tecnico_fijo = users["tecnico_fijo"]

    for i in range(1, 4):
        p = Plant(
            name=f"Planta Procesadora {company.name} - 0{i}",
            company_id=company.id,
            location=f"Sector Industrial, Lote {random.randint(1,500)}",
            is_active=True
        )
        db.add(p)
        db.flush()
        
        db.execute(text("INSERT INTO user_plant_access (user_id, plant_id) VALUES (:u, :p)"), {"u": jefe_planta.id, "p": p.id})
        db.execute(text("INSERT INTO user_plant_access (user_id, plant_id) VALUES (:u, :p)"), {"u": tecnico_libre.id, "p": p.id})

        tipos_areas = ["Línea de Envasado", "Sala de Máquinas", "Refrigeración"]
        for j, tipo in enumerate(tipos_areas, 1):
            a = Area(name=f"{tipo} {j}-{p.name[-2:]}", plant_id=p.id, is_active=True)
            db.add(a)
            db.flush()
            total_areas += 1
            
            db.execute(text("INSERT INTO user_area_access (user_id, area_id) VALUES (:u, :a)"), {"u": jefe_area.id, "a": a.id})
            db.execute(text("INSERT INTO user_area_access (user_id, area_id) VALUES (:u, :a)"), {"u": tecnico_fijo.id, "a": a.id})
            
        plantas.append(p)
        
    db.commit()
    return plantas, total_areas

def _crear_maquinas_seguras(db: Session, plantas: list[Plant], users: dict) -> tuple[list[Machine], int]:
    maquinas = []
    maquinas_seguras = 0
    jefe_area = users["jefe_area"]
    default_pin_hash = hash_password("1234")

    for planta in plantas:
        for area in planta.areas:
            for i in range(1, 10):
                serial = f"SN-{uuid.uuid4().hex[:8].upper()}"
                req_pin = random.choice([True, False, False]) 
                sec_pin = default_pin_hash if req_pin else None

                m = Machine(
                    name=f"Equipo {random.choice(['Extrusora', 'Motor', 'Horno', 'Compresor'])}",
                    model=f"MOD-{random.randint(1000, 9999)}",
                    serial_number=serial,
                    status=random.choices(list(MachineStatus), weights=[70, 10, 15, 5])[0],
                    qr_code=f"QR-{serial}",
                    area_id=area.id,
                    requires_pin=req_pin,
                    security_pin=sec_pin,
                    is_active=True
                )
                db.add(m)
                db.flush() 

                if req_pin:
                    maquinas_seguras += 1
                    db.execute(
                        text("INSERT INTO machine_pin_audit_logs (machine_id, changed_by_id, action) VALUES (:m, :u, 'PIN_CREATED')"),
                        {"m": m.id, "u": jefe_area.id}
                    )
                maquinas.append(m)
                
    db.commit()
    return maquinas, maquinas_seguras

def _generar_comportamiento_operativo(db: Session, company: Company, maquinas: list[Machine], users: dict) -> int:
    now = datetime.utcnow()
    admin = users["admin"]
    supervisor_area = users["jefe_area"]
    tecnico = users["tecnico_fijo"]
    operador = users["operador"]
    firmas_creadas = 0

    for m in maquinas:
        # 1. Documento de Seguridad
        doc = Document(
            title=f"Manual de Riesgos LOTO - {m.serial_number}",
            doc_type=DocumentType.instrucciones_seguridad,
            status=DocumentStatus.activo,
            file_url=f"https://storage.provider.com/docs/{m.id}.pdf",
            file_name=f"seguridad_{m.model}.pdf",
            uploaded_by_id=admin.id,
            machine_id=m.id,
            company_id=company.id,
            is_active=True
        )
        db.add(doc)
        db.flush()

        # 2. ESCUDO LEGAL: El operario acepta los riesgos y firma
        hash_str = f"{doc.id}-{operador.id}-{now.timestamp()}".encode('utf-8')
        firma_hash = hashlib.sha256(hash_str).hexdigest()
        
        firma = DocumentReadConfirmation(
            document_id=doc.id,
            user_id=operador.id,
            read_at=now - timedelta(days=2),
            confirmed_at=now - timedelta(days=2),
            risks_accepted =True,
            signature_hash=firma_hash
        )
        db.add(firma)
        firmas_creadas += 1

        # 3. REPORTE RÁPIDO (Falla) vs LOTO (Mantenimiento)
        if m.status == MachineStatus.fallas:
            # Operario reporta en 3 clics con foto
            tarea = MaintenanceTask(
                title=f"Reporte Visual: Fuga en {m.serial_number}",
                maintenance_type=MaintenanceType.reporte_falla,
                status=TaskStatus.pendiente,
                priority=TaskPriority.alto,
                machine_id=m.id,
                created_by_id=operador.id,
                evidence_photo_url=f"https://storage.provider.com/photos/falla_{m.id}.jpg",
                completion_notes="Fuga de presión detectada. Adjunto foto de la válvula."
            )
            db.add(tarea)

        elif m.status == MachineStatus.mantenimiento:
            # Mantenimiento seguro exigiendo candado LOTO
            tarea = MaintenanceTask(
                title=f"Reparación Crítica (Protocolo LOTO) - {m.serial_number}",
                maintenance_type=MaintenanceType.,
                status=TaskStatus.en_progreso,
                priority=TaskPriority.critico,
                machine_id=m.id,
                assigned_to_id=tecnico.id,
                created_by_id=supervisor_area.id,
                is_loto_required=True,
                loto_applied_at=now - timedelta(minutes=45),
                loto_applied_by_id=tecnico.id
            )
            db.add(tarea)

    db.commit()
    return firmas_creadas

if __name__ == "__main__":
    run_seed()