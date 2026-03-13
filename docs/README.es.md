# U-Sarnt QR Access Control

Documentación principal en español del proyecto oficial de **U-Sarnt**.

## Identidad del proyecto

- Nombre público: `U-Sarnt QR Access Control`
- Código interno/referencia: `3009`
- Propietario identificado en repositorio y metadatos: **U-Sarnt**

## Descripción

Aplicación de escritorio para control de acceso mediante códigos QR firmados. El sistema combina una interfaz Qt, captura de cámara, validación criptográfica de credenciales y registro persistente de accesos sobre SQLite.

## Capacidades principales

- Firma HMAC-SHA256 para evitar falsificaciones triviales de QR.
- Alternancia automática entre `entry` y `exit` según el último acceso.
- Panel administrativo para crear usuarios, desactivar cuentas y regenerar QRs.
- Herramientas auxiliares para inicialización, exportación de logs y backups.
- Compatibilidad con layouts de datos heredados y nuevos.

## Arquitectura

- [`run.py`](../run.py): arranque local y configuración de logging.
- [`src/core/config.py`](../src/core/config.py): rutas, identidad del proyecto y bootstrap.
- [`src/core/database.py`](../src/core/database.py): modelos y manejo del engine SQLAlchemy.
- [`src/core/qr_handler.py`](../src/core/qr_handler.py): generación y validación de QRs firmados.
- [`src/core/access_control.py`](../src/core/access_control.py): reglas de acceso y caché de usuarios.
- [`src/core/camera.py`](../src/core/camera.py): apertura de cámara y lectura de QR con OpenCV.
- [`src/ui/main_window.py`](../src/ui/main_window.py): dashboard principal.
- [`src/ui/admin_dialog.py`](../src/ui/admin_dialog.py): panel administrativo.

## Compatibilidad

- Windows: backend preferente `CAP_DSHOW`/`CAP_MSMF`.
- Linux: backend preferente `CAP_V4L2`/`CAP_GSTREAMER`.
- macOS: backend preferente `CAP_AVFOUNDATION`.

La integración continua está preparada para validar el proyecto en los tres sistemas desde GitHub Actions.

## Instalación

### Con `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para desarrollo:

```bash
pip install -r requirements-dev.txt
```

### Con `conda`

```bash
conda env create -f environment.yml
conda activate qrproj
```

## Ejecución

```bash
python run.py
```

En entornos sin pantalla para pruebas:

```bash
QT_QPA_PLATFORM=offscreen python run.py
```

## Herramientas

- Inicializar datos de ejemplo:

```bash
python tools/init_app.py
```

- Listar usuarios y regenerar QR:

```bash
python tools/generate_qr.py --list
python tools/generate_qr.py <uuid_usuario>
```

- Exportar registros:

```bash
python tools/export_logs.py --month -f json
```

- Crear o verificar backups:

```bash
python tools/backup_db.py create
python tools/backup_db.py list
python tools/backup_db.py verify <archivo.zip>
```

## Testing

```bash
pytest -q
```

La suite cubre:

- núcleo de QR
- control de acceso
- base de datos
- herramientas auxiliares
- importabilidad de UI y CLI

## Publicación en GitHub

El proyecto ya incluye:

- [`pyproject.toml`](../pyproject.toml) con autoría y metadatos de U-Sarnt
- [`NOTICE.md`](../NOTICE.md) con aviso explícito de propiedad
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) para CI en Windows, Linux y macOS
- [`.gitignore`](../.gitignore) para evitar subir secretos y artefactos de ejecución
