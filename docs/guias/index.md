---
title: Guías
description: >-
  Guías técnicas paso a paso para operar Custodiam — instalación de cada repo,
  configuración de Keycloak, despliegue Docker Compose, integración Flutter OIDC.
---

# Guías técnicas

Esta sección recoge **guías técnicas paso a paso** para operar el sistema. Cada guía describe un procedimiento concreto con prerrequisitos, comandos, verificaciones y troubleshooting. Las guías se publican aquí conforme alcanzan versión estable; las que están en preparación se enlistan al final con la indicación correspondiente.

## Guías disponibles

<div class="grid cards" markdown>

- :material-docker: **[Docker Compose local](docker-compose-local.md)**

    Levantar el stack completo (PostgreSQL + Keycloak + API + Web + ntfy) con Docker Compose. Tres modos mutuamente excluyentes (dev / tunnel / prod), setup desde cero, estrategia de imágenes, comandos útiles y troubleshooting completo.

- :material-key-variant: **[Configuración de Keycloak](configuracion-keycloak.md)**

    Realm `custodiam` desde cero: política HTTPS, `KC_HOSTNAME` por entorno, SMTP transaccional con Resend, los 12 roles funcionales, cliente confidencial `custodiam-api`, cliente público `custodiam-app` con PKCE S256 obligatorio, usuarios de prueba, exportación del realm. Troubleshooting completo y referencia de endpoints OIDC.

- :material-language-python: **[Setup FastAPI con uv](setup-fastapi-uv.md)**

    Configurar `custodiam-api` desde cero: entorno con uv 0.9+, estructura del proyecto, `pyproject.toml` PEP 621, código base (config, BD, main, tests), migraciones Alembic, linter ruff, variables de entorno. Comandos esenciales y troubleshooting.

- :material-flutter: **Flutter OIDC**

    Setup del cliente Flutter con `oauth2` + PKCE, asimetría móvil/web, gestión de tokens con `flutter_secure_storage`. Cubierto en **[Empezar → App Flutter](../empezar/app.md)** y formalizado en **[ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)** y **[ADR-023](../adrs/adr-023-oauth-web-asimetria.md)**.

</div>

## Estructura común

Cada guía técnica que se publique en esta sección sigue el mismo patrón:

1. **Prerrequisitos** — qué tener instalado y configurado antes de empezar.
2. **Pasos numerados** — cada paso con su comando, ejemplos de salida esperada, y verificación.
3. **Variables y configuración** — qué archivos editar y con qué valores.
4. **Troubleshooting** — errores comunes y cómo resolverlos.
5. **Próximos pasos** — qué hacer después; qué guía leer a continuación.

## Sección en construcción

Hay guías técnicas adicionales en preparación que serán publicadas conforme alcancen versión revisada:

- **Configuración de notificaciones FCM** (registro del proyecto Firebase, credenciales, integración con `firebase_messaging` en Flutter y con la HTTP v1 API desde el backend).
- **Despliegue en producción** con `prod-up.sh` (endurecimiento de Keycloak, `KC_HOSTNAME_STRICT=true`, `DEBUG=false`, cloudflared incluido vía profile).
- **Testing E2E con Patrol** (configuración del runner, browser headless, plumbing CI).
- **Backups y restauración** de PostgreSQL en operación.
- **Publicación en stores** (Google Play, App Store) con builds firmados.

Mientras tanto, los **[recorridos de Empezar](../empezar/index.md)** cubren los pasos esenciales para arrancar cada componente del stack en local.

## Referencias

- **[Empezar](../empezar/index.md)** — recorridos rápidos por cada componente.
- **[Arquitectura](../arquitectura/index.md)** — contexto técnico que las guías asumen conocido.
- **[ADRs](../adrs/index.md)** — registro de decisiones arquitectónicas que sostienen las guías.
- **[Contribuir](../contribuir/index.md)** — cómo proponer una guía nueva o sugerir mejoras a las existentes.
