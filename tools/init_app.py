#!/usr/bin/env python3
"""Inicializa la base de datos con usuarios de ejemplo."""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.access_control import AccessController
from core.database import init_database, get_session, User
from core.qr_handler import QRHandler
from core.config import Config
import uuid

def main():
    print("=== Inicialización del Sistema de Control de Acceso ===\n")
    
    # Crear directorios necesarios
    print("1. Creando directorios...")
    Config.ensure_dirs()
    print(f"   ✓ Directorio de datos: {Config.DATA_DIR}")
    print(f"   ✓ Directorio de QR: {Config.QR_OUTPUT_DIR}")
    
    # Inicializar base de datos
    print("\n2. Inicializando base de datos...")
    init_database()
    print(f"   ✓ Base de datos creada: {Config.DB_PATH}")
    
    # Crear usuarios de ejemplo
    print("\n3. Creando usuarios de ejemplo...")
    
    sample_users = [
        {"name": "Juan Pérez", "email": "juan@example.com"},
        {"name": "María García", "email": "maria@example.com"},
        {"name": "Carlos López", "email": "carlos@example.com"},
    ]
    
    session = get_session()
    try:
        for user_data in sample_users:
            # Verificar si ya existe
            existing = session.query(User).filter_by(email=user_data["email"]).first()
            if existing:
                print(f"   ⚠ Usuario {user_data['name']} ya existe")
                continue
            
            # Crear usuario
            user_uuid = str(uuid.uuid4())
            user = User(
                uuid=user_uuid,
                name=user_data["name"],
                email=user_data["email"]
            )
            session.add(user)
            session.flush()
            
            # Generar QR - MÉTODO CORREGIDO ✅
            payload = {
                "uuid": user_uuid,
                "name": user_data["name"],
                "email": user_data["email"]
            }
            qr_path, _ = QRHandler.generate_qr_file(
                payload=payload,
                filename_prefix=f"qr_{user_data['name'].replace(' ', '_')}"
            )
            session.commit()
            AccessController.invalidate_user_cache(user.uuid)
            
            print(f"   ✓ Usuario creado: {user_data['name']}")
            print(f"     QR guardado en: {qr_path}")
    
    finally:
        session.close()
    
    Config.save_default_config()
    print("\n=== Inicialización completada ===")
    print("\nPara ejecutar la aplicación:")
    print("  python run.py")
    print("\nLos códigos QR están en:", Config.QR_OUTPUT_DIR)

if __name__ == "__main__":
    main()
