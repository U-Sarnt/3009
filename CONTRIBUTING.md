# Contributing

This repository is maintained by **U-Sarnt**.

## English

External contributions are not assumed to be open for unrestricted intake.

If you want to propose a change:

1. Open an issue first and describe the purpose of the change.
2. Keep changes focused and technically justified.
3. Do not remove branding, ownership notices or legal files.
4. Do not commit secrets, runtime data, generated QR files, backups or local databases.
5. Expect review under U-Sarnt ownership and repository policy.

Before submitting:

- run `python tools/check_format.py`
- run `flake8 src tests tools run.py`
- run `pytest -q`
- keep documentation in both Spanish and English when relevant
- update docs if user-facing behavior changes

## Español

Este repositorio es mantenido por **U-Sarnt**.

Las contribuciones externas no se consideran abiertas de forma irrestricta.

Si quieres proponer un cambio:

1. Abre primero un issue y explica el objetivo del cambio.
2. Mantén los cambios acotados y técnicamente justificados.
3. No elimines branding, avisos de propiedad ni archivos legales.
4. No subas secretos, datos de ejecución, QRs generados, backups ni bases de datos locales.
5. Toda revisión queda sujeta a la política y criterio de U-Sarnt.

Antes de enviar cambios:

- ejecuta `python tools/check_format.py`
- ejecuta `flake8 src tests tools run.py`
- ejecuta `pytest -q`
- mantén documentación tanto en español como en inglés cuando aplique
- actualiza la documentación si cambia el comportamiento visible del sistema
