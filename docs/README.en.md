# U-Sarnt QR Access Control

Main English documentation for the official **U-Sarnt** project.

## Project Identity

- Public name: `U-Sarnt QR Access Control`
- Internal/reference code: `3009`
- Repository and package owner identity: **U-Sarnt**

## Description

Desktop application for QR-based access control with signed credentials. The system combines a Qt interface, camera capture, cryptographic validation and persistent SQLite audit logging.

## Core Capabilities

- HMAC-SHA256 signing to reduce trivial QR forgery.
- Automatic `entry` / `exit` alternation based on the latest access event.
- Administrative panel to create users, disable accounts and regenerate QR files.
- Helper tools for initialization, log export and backups.
- Compatibility with both legacy and current data layouts.

## Architecture

- [`run.py`](../run.py): local entry point and logging setup.
- [`src/core/config.py`](../src/core/config.py): runtime paths, identity metadata and bootstrap.
- [`src/core/database.py`](../src/core/database.py): SQLAlchemy models and engine lifecycle.
- [`src/core/qr_handler.py`](../src/core/qr_handler.py): signed QR generation and validation.
- [`src/core/access_control.py`](../src/core/access_control.py): access rules and user cache.
- [`src/core/camera.py`](../src/core/camera.py): camera opening and QR scanning through OpenCV.
- [`src/ui/main_window.py`](../src/ui/main_window.py): main operator dashboard.
- [`src/ui/admin_dialog.py`](../src/ui/admin_dialog.py): administration panel.

## Compatibility

- Windows: preferred backends `CAP_DSHOW` / `CAP_MSMF`
- Linux: preferred backends `CAP_V4L2` / `CAP_GSTREAMER`
- macOS: preferred backend `CAP_AVFOUNDATION`

GitHub Actions is configured to validate the project on all three operating systems.

## Installation

### Using `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
```

### Using `conda`

```bash
conda env create -f environment.yml
conda activate qrproj
```

## Run

```bash
python run.py
```

For headless UI validation:

```bash
QT_QPA_PLATFORM=offscreen python run.py
```

## Tooling

- Initialize sample data:

```bash
python tools/init_app.py
```

- List users and generate QR files:

```bash
python tools/generate_qr.py --list
python tools/generate_qr.py <user_uuid>
```

- Export access logs:

```bash
python tools/export_logs.py --month -f json
```

- Create or verify backups:

```bash
python tools/backup_db.py create
python tools/backup_db.py list
python tools/backup_db.py verify <archive.zip>
```

## Testing

```bash
pytest -q
```

The test suite covers:

- QR core logic
- access control rules
- database behavior
- helper tools
- importability of UI and CLI modules

## GitHub Readiness

The project already includes:

- [`pyproject.toml`](../pyproject.toml) with U-Sarnt ownership metadata
- [`NOTICE.md`](../NOTICE.md) with an explicit ownership notice
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) for CI on Windows, Linux and macOS
- [`.gitignore`](../.gitignore) to exclude secrets and runtime artifacts
