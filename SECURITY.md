# Security Policy

## English

If you discover a security issue in this repository, please report it **privately** by emailing **u.sarnt@proton.me** — do not open a public issue with exploit or attack details.

Include in your report:

1. Reproduction steps and affected area.
2. Impact assessment if known.
3. Any proof-of-concept needed to validate the report safely.

You will receive a response within 72 hours.

Security-sensitive material that should never be committed:

- secret keys
- local databases
- generated QR credentials
- logs containing personal or operational data
- backup archives

This repository already excludes common runtime artifacts through [`.gitignore`](.gitignore), but contributors remain responsible for reviewing their changes before pushing.

---

## Español

Si descubres un problema de seguridad en este repositorio, repórtalo **de forma privada** enviando un correo a **u.sarnt@proton.me** — no abras un issue público con detalles del exploit o del ataque.

Incluye en tu reporte:

1. Pasos de reproducción y área afectada.
2. Evaluación del impacto si lo conoces.
3. Prueba de concepto necesaria para validar el reporte de forma segura.

Recibirás respuesta en un plazo de 72 horas.

Material sensible que nunca debe subirse al repositorio:

- claves secretas
- bases de datos locales
- credenciales QR generadas
- logs con datos personales u operativos
- archivos de backup

Este repositorio ya excluye artefactos comunes de ejecución mediante [`.gitignore`](.gitignore), pero cada contribuyente sigue siendo responsable de revisar sus cambios antes de hacer push.
