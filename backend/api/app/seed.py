import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.users.models import User, UserRole
from app.modules.documentos.models import Document, DocumentStatus, DocumentType
from app.modules.plantas.models import Area, Plant, UserPlantAccess
from app.modules.mantenimiento.models import (MaintenanceType,
                                              MaintenanceTask, 
                                              MaintenanceActivityLog,
                                              TaskPriority, 
                                              TaskStatus)


def run_seed():
    db:Session = SessionLocal()

    try:
        print("iniciando semilla de datos")

        _clear_data(db)
        user = _seed_user(db)
        plantas = _seed_plantas(db)
        areas = _seed_areas(db, plantas)        
        _seed_user_plant_accesses(db, user, plantas)
        maquinas = _seed_maquinas(db, areas)
        documentos = _seed_documentos(db, maquinas, user)
        _seed_tareas_mantenimiento(db, maquinas, user)

        print("-" * 60)
        print("✅ Seed completado exitosamente!")
        print("\n📊 Resumen:")
        print(f"   👥 Usuarios: {len(user)}")
        print(f"   🏭 Plantas: {len(plantas)}")
        print(f"   📍 Áreas: {len(areas)}")
        print(f"   ⚙️  Máquinas: {len(maquinas)}")
        print(f"   📄 Documentos: {len(documentos)}")
        print("\n🔐 Credenciales de acceso:")
        print("   Admin:      admin@doctrack.com / DocTrack2024!")
        print("   Supervisor: mgonzalez@carozzi.com / DocTrack2024!")
        print("   Técnico:    jperez@carozzi.com / DocTrack2024!")
        print("   Operario:   lmorales@carozzi.com / DocTrack2024!")
        print("\n🔗 QR Codes para probar:")
        print("   Molino VDK9: QR-VDK9-001")
        print("   Molino VDK7: QR-VDK7-001")

    except Exception as e:
        print(f"\n❌ Error en seed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

def _clear_data(db:Session):
    print("limpiando datos anteriores")

    db.query(MaintenanceActivityLog).delete()
    db.query(MaintenanceTask).delete()
    db.query(Document).delete()
    db.query(Area).delete()
    db.query(Plant).delete()
    db.query(User).delete()
    db.query(UserPlantAccess).delete()

    db.commit()
    print("datos eliminados correctamente")

def _seed_user(db:Session)-> dict:
    print("creando usuarios..")

    #password_test = hash_password("DocTrack2027@@")
    
    user_data = [
        {
            
            "first_name": "Daniel Ortiz",
            "last_name": "Manueles Galvez",
            "email": "manuelesD@gmail.com",
            "password_hash": "DocTrack2027@@",
            "role": UserRole.ADMIN,
            "phone": "+56938172883",
            "is_active" : True
        },
        {
            "first_name":"Javier Cristofer",
            "last_name": "Paulina De Jesus",
            "email": "pauDCristofer23@gmail.com",
            "password_hash":"Dlasdoo20-@",
            "role": UserRole.OPERADORES,
            "phone": "+5691000291",
            "is_active": True
        },
        {
            "first_name": "Javiera Belen",
            "last_name": "Fernandez Manual",
            "password_hash": "aksdks9381",
            "role": UserRole.SUPERVISOR,
            "phone":"+56910029244",
            "is_active": False

        },
        {
            "first_name": "Lucas Fernando",
            "last_name": "Hernandez Jimenez",
            "password_hash": "Julaso3112",
            "role": UserRole.SUPERVISOR,
            "phone": "+56910209932",
            "is_active": True
        },
        {
            "first_name": "Jose Antonio",
            "last_name": "Quesada Silva",
            "password_hash": "SilvaJoseall22",
            "role": UserRole.OPERADORES,
            "phone": "+569102004452",
            "is_active":True
        },
        {
            "first_name": "Andres Cecilio",
            "last_name": "Rojas Silva",
            "password_hash": "ACrOSOA",
            "role": UserRole.TECNICOS,
            "phone": "+56982994344",
            "is_active": True
        }
    ]
