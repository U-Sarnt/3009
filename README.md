# U-Sarnt QR Access Control

Official repository of **U-Sarnt** for the `3009` project.

Repositorio oficial de **U-Sarnt** para el proyecto `3009`.

## Ownership / Propiedad

- This project, its branding, documentation and source code are identified as a U-Sarnt project.
- Este proyecto, su identidad visual, su documentación y su código fuente están identificados como un proyecto de U-Sarnt.

More details:

- English: [`docs/README.en.md`](docs/README.en.md)
- Español: [`docs/README.es.md`](docs/README.es.md)
- Ownership notice: [`NOTICE.md`](NOTICE.md)

## Summary / Resumen

- Signed QR-based desktop access control.
- Control de acceso de escritorio basado en códigos QR firmados.

- PySide6 interface, OpenCV camera capture, SQLite audit logs and admin tooling.
- Interfaz con PySide6, captura de cámara con OpenCV, bitácora SQLite y herramientas administrativas.

- Compatible project structure for Windows, Linux and macOS.
- Estructura preparada para Windows, Linux y macOS.

## Quick Start / Inicio Rápido

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python run.py
```

## Repository Notes / Notas del Repositorio

- GitHub CI is configured in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
- La integración continua para GitHub está configurada en [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

- Runtime artifacts and secrets are excluded through [`.gitignore`](.gitignore).
- Los artefactos de ejecución y secretos están excluidos mediante [`.gitignore`](.gitignore).
