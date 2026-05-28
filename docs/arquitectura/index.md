---
title: Arquitectura
description: >-
  Visión general de la arquitectura de Custodiam: polyrepo, stack, diagrama
  del sistema y decisiones clave.
---

# Arquitectura

Custodiam sigue una arquitectura **polyrepo** con tres repositorios de código independientes coordinados desde un cuarto de orquestación + un quinto de documentación pública.

## Repositorios del proyecto

```text
custodiam-workspace/
├── custodiam-app/     ← Flutter (Android + iOS + Web)         · github.com/custodiam/custodiam-app
├── custodiam-api/     ← FastAPI + SQLModel + PostgreSQL       · github.com/custodiam/custodiam-api
├── custodiam-infra/   ← Docker Compose + Keycloak + Tunnels   · github.com/custodiam/custodiam-infra
└── custodiam-book/    ← Documentación pública (este sitio)    · github.com/custodiam/custodiam-book
```

La estructura polyrepo y la separación de los tres componentes de código están justificadas en [ADR-001](../adrs/adr-001-polyrepo.md). La existencia del book como repositorio aparte (en lugar de mezclar la documentación con uno de los repos de código) está justificada en [ADR-027](../adrs/adr-027-mkdocs-pages.md).

## Recorridos por la arquitectura

<div class="grid cards" markdown>

- :material-stack-overflow: **[Stack técnico](stack.md)**

    Tecnologías concretas por capa: Flutter, FastAPI, SQLModel, PostgreSQL, Keycloak, Docker, Cloudflare.

- :material-graph: **[Diagrama del sistema](diagramas.md)**

    Topología de despliegue y secuencias OAuth + notificación de emergencia.

- :material-database: **[Modelo de datos](modelo-datos.md)**

    Esquema relacional, patrón catálogo + instancias + JSONB, diagrama ER del módulo voluntarios.

- :material-sitemap: **[Flujos de negocio](flujos-negocio.md)**

    Ciclo del voluntario, servicio preventivo, emergencia activa, fichaje, inventario.

- :material-bell-ring: **[Notificaciones redundantes](notificaciones.md)**

    Firebase Cloud Messaging como canal principal + ntfy como fallback automático.

- :material-clipboard-text-clock: **[Audit log](audit-log.md)**

    Registro cross-module de operaciones críticas con patrón de imports diferidos.

</div>

## Principios de diseño

- **Polyrepo** ([ADR-001](../adrs/adr-001-polyrepo.md)): tres repos independientes evitan el "monorepo monstruo" y permiten ciclos de release desacoplados (`custodiam-app` con releases semver para stores, `custodiam-api` con su propio versionado, `custodiam-infra` con tags por entorno).
- **Clean Architecture estricta en `custodiam-app`**: tres capas `domain` / `data` / `presentation` + `infrastructure` cross-cutting. Domain es Dart puro sin dependencias de framework. Data devuelve `Result<T>` siempre, no lanza excepciones cross-layer ([ADR-014](../adrs/adr-014-result-failure.md)).
- **SQLModel en `custodiam-api`** ([ADR-002](../adrs/adr-002-sqlmodel.md)): unifica SQLAlchemy 2.0 + Pydantic en una sola clase. Una `tabla=True` es modelo de BD y schema de API en un único punto.
- **Resiliencia documentada**: matriz de fallos del sistema con planes de degradación (FCM caído → ntfy como respaldo, Cloudflare Tunnel caído → modo dev local, Keycloak caído → degradación graceful con error 503).
- **Notificaciones redundantes**: Firebase Cloud Messaging como canal principal + ntfy como respaldo automático ([Notificaciones redundantes](notificaciones.md)).
- **Auth basado en estándares**: OAuth 2.0 + PKCE ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) contra Keycloak ([ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md), [ADR-023](../adrs/adr-023-oauth-web-asimetria.md)). JWT validación local en backend con PyJWT. RBAC con doce roles jerárquicos y cuarenta permisos atómicos espejados en código backend y cliente ([ADR-013](../adrs/adr-013-rbac-lockstep.md)).

## Stack resumido

| Capa | Tecnología | Versión | Decisión |
| --- | --- | --- | --- |
| App móvil y web | Flutter + Dart | 3.x | [ADR-001](../adrs/adr-001-polyrepo.md), [ADR-022](../adrs/adr-022-ios-15.md) (iOS 15+) |
| State management | Riverpod | 2.6+ | [ADR-012](../adrs/adr-012-riverpod.md) |
| BD local app | SQLite vía sqflite | — | [ADR-005](../adrs/adr-005-sqflite.md) |
| Backend | Python + FastAPI | 3.13 + 0.115+ | [ADR-026](../adrs/adr-026-uv.md) (uv) |
| ORM | SQLModel + Alembic | 0.0.22+ | [ADR-002](../adrs/adr-002-sqlmodel.md), [ADR-003](../adrs/adr-003-alembic.md) |
| BD servidor | PostgreSQL + psycopg3 | 15 + 3.1+ | [ADR-008](../adrs/adr-008-psycopg3.md), [ADR-009](../adrs/adr-009-2-bds-separadas.md) |
| Auth | Keycloak | 26+ | [ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md), [ADR-023](../adrs/adr-023-oauth-web-asimetria.md) |
| Push notif | Firebase FCM + ntfy | — | [Notificaciones redundantes](notificaciones.md) |
| Email transaccional | Resend | — | [ADR-021](../adrs/adr-021-smtp-resend.md) |
| Servidor PWA | Nginx Alpine | — | [ADR-006](../adrs/adr-006-nginx-alpine.md) |
| Registro Docker | GHCR | — | [ADR-007](../adrs/adr-007-ghcr.md) |
| Modos de despliegue | Docker Compose (dev / tunnel / prod) | 2.x | [ADR-020](../adrs/adr-020-tres-modos-despliegue.md) |
| Gestión de secretos | sops + age | — | [ADR-019](../adrs/adr-019-sops-age.md) |
| Documentación pública | Material for MkDocs + GitHub Pages | 9.x | [ADR-027](../adrs/adr-027-mkdocs-pages.md) |

## Referencias

- **[ADRs públicos](../adrs/index.md)** — registro completo de decisiones arquitectónicas con justificación y alternativas evaluadas.
- **[Empezar](../empezar/index.md)** — cómo levantar el stack completo en local.
