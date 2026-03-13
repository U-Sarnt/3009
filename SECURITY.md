# Security Policy

## English

If you discover a security issue in this repository:

1. Do not publish exploits, secrets or attack details in a public issue.
2. Report the issue privately to the repository owner or maintainer.
3. Include reproduction steps, affected area and impact if known.

Security-sensitive material that should never be committed:

- secret keys
- local databases
- generated QR credentials
- logs containing personal or operational data
- backup archives

This repository already excludes common runtime artifacts through [`.gitignore`](.gitignore), but contributors remain responsible for reviewing their changes before pushing.

## Español

Si descubres un problema de seguridad en este repositorio:

1. No publiques exploits, secretos ni detalles del ataque en un issue público.
2. Repórtalo de forma privada al propietario o mantenedor del repositorio.
3. Incluye pasos de reproducción, área afectada e impacto si lo conoces.

Material sensible que nunca debe subirse al repositorio:

- claves secretas
- bases de datos locales
- credenciales QR generadas
- logs con datos personales u operativos
- archivos de backup

Este repositorio ya excluye artefactos comunes de ejecución mediante [`.gitignore`](.gitignore), pero cada contribuyente sigue siendo responsable de revisar sus cambios antes de hacer push.
