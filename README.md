# U-Sarnt QR Access Control

![CI](https://github.com/U-Sarnt/3009/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green?logo=opencv&logoColor=white)

Official repository of **U-Sarnt** for project `3009`.

Repositorio oficial de **U-Sarnt** para el proyecto `3009`.

## Overview / Descripción

Desktop access-control system based on signed QR credentials, with:

- PySide6 desktop interface
- OpenCV camera capture and QR scanning
- SQLite persistence through SQLAlchemy
- Administrative user management
- Audit log export and backup tooling

Sistema de control de acceso de escritorio basado en credenciales QR firmadas, con:

- interfaz de escritorio en PySide6
- captura de cámara y escaneo QR con OpenCV
- persistencia SQLite mediante SQLAlchemy
- administración de usuarios
- exportación de bitácoras y herramientas de backup

## Core Features / Funcionalidades

- Signed QR payloads using HMAC-SHA256
- Automatic `entry` / `exit` alternation per user
- Active / inactive user management from the admin panel
- Recent-access dashboard and access statistics
- QR generation utilities for registered users
- Backup and log export tools for operators

## Stack

- Python 3.9+
- PySide6
- OpenCV
- SQLAlchemy
- qrcode + Pillow
- pytest / black / flake8

## Quick Start / Inicio Rápido

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python run.py
```

For headless validation:

```bash
QT_QPA_PLATFORM=offscreen python run.py
```

## Tooling / Herramientas

Initialize generic demo data:

```bash
python tools/init_app.py
```

List users and generate a QR for an existing user:

```bash
python tools/generate_qr.py --list
python tools/generate_qr.py <user_uuid>
```

Export access logs:

```bash
python tools/export_logs.py --month -f json
```

Create, list and verify backups:

```bash
python tools/backup_db.py create
python tools/backup_db.py list
python tools/backup_db.py verify <backup.zip>
```

## Development Checks / Validaciones

```bash
python tools/check_format.py
flake8 src tests tools run.py
pytest -q
```

CI is configured in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and runs on Linux, Windows and macOS.

## Repository Notes / Notas del Repositorio

- Runtime artifacts, local databases, generated QR files, secrets and backups are excluded through [`.gitignore`](.gitignore).
- Documentation is available in English and Spanish.
- The project supports both legacy and current local data layouts.

## Documentation

- English: [`docs/README.en.md`](docs/README.en.md)
- Español: [`docs/README.es.md`](docs/README.es.md)
- Ownership notice: [`NOTICE.md`](NOTICE.md)
- Contribution policy: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)

## License / Licencia

This repository is published under the proprietary terms described in [`LICENSE`](LICENSE).

Este repositorio se publica bajo los términos propietarios descritos en [`LICENSE`](LICENSE).
