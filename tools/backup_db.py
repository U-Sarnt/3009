#!/usr/bin/env python3
"""Backup and restore utilities for project data."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

try:
    from core.config import Config
    from core.database import AccessLog, User, get_session, reset_database_engine
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from core.config import Config
    from core.database import AccessLog, User, get_session, reset_database_engine


def calculate_checksum(file_path: Path) -> str:
    """Calculate the SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for block in iter(lambda: handle.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()


def create_backup(backup_dir=None, include_logs: bool = True):
    """Create a ZIP backup with database, QR codes and optional logs."""
    backup_dir = Path(backup_dir) if backup_dir else Config.BACKUPS_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    temp_dir = backup_dir / backup_name
    temp_dir.mkdir(exist_ok=True)

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "owner": Config.ORGANIZATION_NAME,
        "project_name": Config.PROJECT_NAME,
        "project_root": str(Config.PROJECT_ROOT),
        "database": str(Config.DB_PATH),
        "files": {},
    }

    try:
        if Config.DB_PATH.exists():
            db_copy = temp_dir / "database.db"
            shutil.copy2(Config.DB_PATH, db_copy)
            metadata["files"]["database.db"] = {
                "size": db_copy.stat().st_size,
                "checksum": calculate_checksum(db_copy),
            }

        qr_backup_dir = temp_dir / "qr_codes"
        qr_backup_dir.mkdir(exist_ok=True)
        if Config.QR_OUTPUT_DIR.exists():
            for qr_file in Config.QR_OUTPUT_DIR.glob("*.png"):
                target = qr_backup_dir / qr_file.name
                shutil.copy2(qr_file, target)
                metadata["files"][f"qr_codes/{qr_file.name}"] = {
                    "size": target.stat().st_size,
                    "checksum": calculate_checksum(target),
                }

        if include_logs and Config.LOGS_DIR.exists():
            logs_backup_dir = temp_dir / "logs"
            shutil.copytree(Config.LOGS_DIR, logs_backup_dir, dirs_exist_ok=True)

        info_file = temp_dir / "backup_info.txt"
        with open(info_file, "w", encoding="utf-8") as handle:
            handle.write(f"Backup del sistema {Config.PROJECT_NAME}\n")
            handle.write("=" * 50 + "\n\n")
            handle.write(f"Owner: {Config.ORGANIZATION_NAME}\n")
            handle.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            handle.write(f"Proyecto: {Config.PROJECT_ROOT}\n")
            handle.write(f"BD: {Config.DB_PATH}\n\n")

            session = get_session()
            try:
                handle.write(f"Usuarios: {session.query(User).count()}\n")
                handle.write(f"Usuarios activos: {session.query(User).filter_by(is_active=True).count()}\n")
                handle.write(f"Accesos: {session.query(AccessLog).count()}\n")
            finally:
                session.close()

        with open(temp_dir / "backup_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False)

        zip_path = backup_dir / f"{backup_name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(temp_dir))

        shutil.rmtree(temp_dir)
        cleanup_old_backups(backup_dir)
        print(f"Backup creado: {zip_path}")
        return zip_path
    except Exception as exc:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        print(f"Error creando backup: {exc}")
        return None


def cleanup_old_backups(backup_dir: Path, max_backups: int = 10) -> None:
    """Keep only the most recent backup archives."""
    backups = sorted(backup_dir.glob("backup_*.zip"), key=lambda item: item.stat().st_mtime)
    for old_backup in backups[:-max_backups]:
        old_backup.unlink(missing_ok=True)


def verify_backup_integrity(backup_file) -> bool:
    """Verify that a backup ZIP can be extracted and contains a database."""
    backup_file = Path(backup_file)
    if not backup_file.exists():
        print(f"Archivo no encontrado: {backup_file}")
        return False

    temp_dir = backup_file.parent / f"temp_verify_{datetime.now():%Y%m%d_%H%M%S}"
    temp_dir.mkdir(exist_ok=True)

    try:
        with zipfile.ZipFile(backup_file, "r") as archive:
            if archive.testzip() is not None:
                print("El archivo ZIP esta corrupto")
                return False
            archive.extractall(temp_dir)

        db_file = temp_dir / "database.db"
        if not db_file.exists():
            print("La base de datos no existe dentro del backup")
            return False

        metadata_file = temp_dir / "backup_metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            for relative_name, file_info in metadata.get("files", {}).items():
                candidate = temp_dir / relative_name
                if candidate.exists() and file_info.get("checksum"):
                    if calculate_checksum(candidate) != file_info["checksum"]:
                        print(f"Checksum invalido para {relative_name}")
                        return False

        print("Backup verificado correctamente")
        return True
    except Exception as exc:
        print(f"Error verificando backup: {exc}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def restore_backup(backup_file) -> bool:
    """Restore project state from a backup ZIP."""
    backup_file = Path(backup_file)
    if not backup_file.exists():
        print(f"Archivo no encontrado: {backup_file}")
        return False

    if backup_file.suffix != ".zip":
        print("El backup debe ser un archivo .zip")
        return False

    if not verify_backup_integrity(backup_file):
        print("Restauracion cancelada por integridad invalida")
        return False

    temp_dir = Config.BACKUPS_DIR / f"temp_restore_{datetime.now():%Y%m%d_%H%M%S}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(backup_file, "r") as archive:
            archive.extractall(temp_dir)

        reset_database_engine()

        db_file = temp_dir / "database.db"
        if Config.DB_PATH.exists():
            shutil.copy2(Config.DB_PATH, Config.DB_PATH.with_suffix(".db.bak"))
        shutil.copy2(db_file, Config.DB_PATH)

        qr_dir = temp_dir / "qr_codes"
        if qr_dir.exists():
            if Config.QR_OUTPUT_DIR.exists():
                shutil.rmtree(Config.QR_OUTPUT_DIR)
            shutil.copytree(qr_dir, Config.QR_OUTPUT_DIR)

        logs_dir = temp_dir / "logs"
        if logs_dir.exists():
            if Config.LOGS_DIR.exists():
                shutil.rmtree(Config.LOGS_DIR)
            shutil.copytree(logs_dir, Config.LOGS_DIR)

        print("Backup restaurado correctamente")
        return True
    except Exception as exc:
        print(f"Error restaurando backup: {exc}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def list_backups() -> None:
    """List available backup archives."""
    Config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(Config.BACKUPS_DIR.glob("backup_*.zip"), reverse=True)
    if not backups:
        print("No hay backups disponibles")
        return

    print("Backups disponibles:")
    for index, backup in enumerate(backups, start=1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        print(f"{index:2}. {backup.name} - {size_mb:.2f} MB")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Gestion de backups del sistema")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    create_parser = subparsers.add_parser("create", help="Crear un backup")
    create_parser.add_argument("-d", "--dir", help="Directorio destino")
    create_parser.add_argument("--no-logs", action="store_true", help="No incluir logs")

    restore_parser = subparsers.add_parser("restore", help="Restaurar un backup")
    restore_parser.add_argument("file", help="Archivo ZIP")

    verify_parser = subparsers.add_parser("verify", help="Verificar un backup")
    verify_parser.add_argument("file", help="Archivo ZIP")

    subparsers.add_parser("list", help="Listar backups")

    args = parser.parse_args()

    if args.command == "create":
        create_backup(backup_dir=args.dir, include_logs=not args.no_logs)
    elif args.command == "restore":
        restore_backup(args.file)
    elif args.command == "verify":
        verify_backup_integrity(args.file)
    elif args.command == "list":
        list_backups()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
