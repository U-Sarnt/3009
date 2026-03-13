#!/usr/bin/env python3
"""Generate QR files for existing users."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.database import User, get_session
from core.qr_handler import QRHandler


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python generate_qr.py <uuid_usuario>")
        print("\nPara listar usuarios disponibles:")
        print("  python generate_qr.py --list")
        return 1

    if sys.argv[1] == "--list":
        session = get_session()
        try:
            users = session.query(User).all()
            if not users:
                print("No hay usuarios registrados")
                return 0

            print("\nUsuarios disponibles:")
            print("-" * 60)
            for user in users:
                status = "ACTIVO" if user.is_active else "INACTIVO"
                print(f"UUID: {user.uuid}")
                print(f"  Nombre: {user.name}")
                print(f"  Email: {user.email}")
                print(f"  Estado: {status}")
                print("-" * 60)
            return 0
        finally:
            session.close()

    user_uuid = sys.argv[1]
    session = get_session()
    try:
        user = session.query(User).filter_by(uuid=user_uuid).first()
        if not user:
            print(f"Error: No se encontro usuario con UUID {user_uuid}")
            return 1

        payload = QRHandler.build_payload(user.uuid, user.name, user.email)
        qr_path, _ = QRHandler.generate_qr_file(
            payload, filename_prefix=f"qr_{user.name}"
        )
        print(f"QR generado para: {user.name}")
        print(f"Guardado en: {qr_path}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
