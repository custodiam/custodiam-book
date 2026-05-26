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

Existe además un **quinto repositorio privado** (`rodrigomulero/DOCUMENTACION`) con la documentación interna del equipo: backlog operativo, seguimiento de sprints, memoria académica del TFG y lecciones operativas. El book público es una vista curada del material de ese repo apta para el público; el sync es manual y controlado ([ADR-027](../adrs/index.md)).

## Recorridos por la arquitectura

<div class="grid cards" markdown>

- :material-stack-overflow: **[Stack técnico](stack.md)**

    Tecnologías concretas por capa: Flutter, FastAPI, SQLModel, PostgreSQL, Keycloak, Docker, Cloudflare.

- :material-graph: **[Diagrama del sistema](diagramas.md)**

    Diagrama de componentes y flujos principales del sistema (auth, API, notificaciones).

</div>

## Principios de diseño

- **Polyrepo** ([ADR-001](../adrs/adr-001-polyrepo.md)): tres repos independientes evitan el "monorepo monstruo" y permiten ciclos de release desacoplados (`custodiam-app` con releases semver para stores, `custodiam-api` con su propio versionado, `custodiam-infra` con tags por entorno).
- **Clean Architecture estricta en `custodiam-app`** (ADR-013): tres capas `domain` / `data` / `presentation`. Domain es Dart puro sin dependencias de framework. Data devuelve `Result<T>` siempre, no lanza excepciones cross-layer (ADR-014).
- **SQLModel en `custodiam-api`** (ADR-002): unifica SQLAlchemy 2.0 + Pydantic en una sola clase. Una `tabla=True` es modelo de BD Y schema de API en un único punto.
- **Resiliencia documentada**: matriz de fallos del sistema con planes de degradación (FCM caído → ntfy backup, Cloudflare Tunnel caído → modo dev local, Keycloak caído → degradación graceful con error 503).
- **Notificaciones redundantes**: Firebase Cloud Messaging como canal principal + ntfy como backup. Si FCM falla, las alertas críticas se entregan vía ntfy.
- **Auth basado en estándares**: OAuth2 + PKCE (RFC 7636) contra Keycloak (ADR-010, ADR-023). JWT validación local en backend con PyJWT (ADR-010). RBAC con 12 roles jerárquicos + 40 permisos definidos en `RBAC_v0.1.0`.

## Stack resumido

| Capa | Tecnología | Versión | Decisión |
|---|---|---|---|
| App móvil/web | Flutter + Dart | 3.x | ADR-001, ADR-022 (iOS 15+) |
| State management | Riverpod | 2.6+ | ADR-012 |
| Backend | Python + FastAPI | 3.13 + 0.115+ | ADR-026 (uv) |
| ORM | SQLModel + Alembic | 0.0.22+ | ADR-002 |
| BD | PostgreSQL + psycopg3 | 15 + 3.1+ | ADR-008 (psycopg3), ADR-009 (2 BDs separadas) |
| Auth | Keycloak | 26+ | ADR-010, ADR-023 |
| Push notif | Firebase FCM + ntfy | — | ADR-005 (notif redundantes) |
| Infra local | Docker Compose | 2.x | ADR-007 |
| Tunnel + CDN | Cloudflare Tunnel + Pages | — | ADR-022, ADR-028 (pendiente) |
| Documentación pública | Material for MkDocs | 9.x | ADR-027 |

## Referencias

- **[ADRs públicos](../adrs/index.md)** — registro completo de decisiones arquitectónicas con justificación y alternativas evaluadas.
- **[Empezar](../empezar/index.md)** — cómo levantar el stack completo en local.
