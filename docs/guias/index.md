---
title: Guías
description: >-
  Guías técnicas paso a paso para operar Custodiam — instalación de cada repo,
  configuración de Keycloak, despliegue Docker Compose, integración Flutter OIDC.
---

# Guías técnicas

Esta sección recoge **guías técnicas paso a paso** para operar el sistema. Cada guía describe un procedimiento concreto con prerrequisitos, comandos, verificaciones y troubleshooting. Cubren las cuatro decisiones operativas fundamentales del proyecto: levantar el stack con Docker Compose, configurar el realm Keycloak, montar el backend FastAPI con uv y desarrollar el cliente OIDC en Flutter.

## Guías disponibles

<div class="grid cards" markdown>

- :material-docker: **[Docker Compose local](docker-compose-local.md)**

    Levantar el stack completo (PostgreSQL + Keycloak + API + Web + ntfy) con Docker Compose. Tres modos mutuamente excluyentes (dev / tunnel / prod), setup desde cero, estrategia de imágenes, comandos útiles y troubleshooting completo.

- :material-key-variant: **[Configuración de Keycloak](configuracion-keycloak.md)**

    Realm `custodiam` desde cero: política HTTPS, `KC_HOSTNAME` por entorno, SMTP transaccional con Resend, los 12 roles funcionales, cliente confidencial `custodiam-api`, cliente público `custodiam-app` con PKCE S256 obligatorio, usuarios de prueba, exportación del realm. Troubleshooting completo y referencia de endpoints OIDC.

- :material-language-python: **[Setup FastAPI con uv](setup-fastapi-uv.md)**

    Configurar `custodiam-api` desde cero: entorno con uv 0.9+, estructura del proyecto, `pyproject.toml` PEP 621, código base (config, BD, main, tests), migraciones Alembic, linter ruff, variables de entorno. Comandos esenciales y troubleshooting.

- :material-flutter: **[Cliente OIDC en Flutter](flutter-oidc.md)**

    OAuth 2.0 + PKCE con Keycloak en Android + iOS + Web. Configuración nativa por plataforma, dos implementaciones de `AuthService` por `kIsWeb`, persistencia del `code_verifier` en `sessionStorage`, refresh automático, integración con `ApiClient`, router con `/callback`, `AppPermissionGate` para RBAC.

</div>

## Estructura común

Cada guía técnica que se publique en esta sección sigue el mismo patrón:

1. **Prerrequisitos** — qué tener instalado y configurado antes de empezar.
2. **Pasos numerados** — cada paso con su comando, ejemplos de salida esperada, y verificación.
3. **Variables y configuración** — qué archivos editar y con qué valores.
4. **Troubleshooting** — errores comunes y cómo resolverlos.
5. **Próximos pasos** — qué hacer después; qué guía leer a continuación.

## Más guías en preparación

Hay guías técnicas adicionales planificadas que se publicarán conforme alcancen versión revisada:

- **Configuración de notificaciones FCM** (registro del proyecto Firebase, credenciales, integración con `firebase_messaging` en Flutter y con la HTTP v1 API desde el backend).
- **Despliegue en producción** con `prod-up.sh` (endurecimiento de Keycloak, `KC_HOSTNAME_STRICT=true`, `DEBUG=false`, `cloudflared` incluido vía profile).
- **Testing E2E con Patrol** (configuración del runner, browser headless, plumbing CI — complementa [ADR-024](../adrs/adr-024-patrol-e2e.md)).
- **Backups y restauración** de PostgreSQL en operación.
- **Publicación en stores** (Google Play, App Store) con builds firmados.

Para el día a día, los **[recorridos de Empezar](../empezar/index.md)** cubren los pasos esenciales para arrancar cada componente del stack en local.

## Referencias

- **[Empezar](../empezar/index.md)** — recorridos rápidos por cada componente.
- **[Arquitectura](../arquitectura/index.md)** — contexto técnico que las guías asumen conocido.
- **[ADRs](../adrs/index.md)** — registro de decisiones arquitectónicas que sostienen las guías.
- **[Contribuir](../contribuir/index.md)** — cómo proponer una guía nueva o sugerir mejoras a las existentes.
