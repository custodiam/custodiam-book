---
title: Stack técnico
description: >-
  Tecnologías concretas que componen el stack de Custodiam por capa, con
  versiones mínimas y razones de selección.
---

# Stack técnico

Inventario completo de tecnologías del stack de Custodiam por capa, con versiones mínimas y referencias cruzadas a las ADRs que justifican cada elección.

## Frontend (`custodiam-app`)

| Componente | Versión | Decisión |
| --- | --- | --- |
| Flutter SDK | 3.x | Estándar multiplataforma del proyecto |
| Dart | 3.6+ | Sealed classes para `Result<T>` |
| `flutter_riverpod` | ^2.6 | State management — [ADR-012](../adrs/adr-012-riverpod.md) |
| `go_router` | ^17.1 | Navegación con `StatefulShellRoute.indexedStack` |
| `http` | ^1.2 | Cliente HTTP — [ADR-004](../adrs/adr-004-http-cliente.md) |
| `oauth2` | ^2.0.3 | OAuth2 + PKCE — [ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md) |
| `flutter_secure_storage` | ^10.0 | Almacenamiento de refresh tokens |
| `firebase_messaging` | ^16.x | Push notifications principales |
| `sqflite` | ^2.4 | BD local + caché offline — [ADR-005](../adrs/adr-005-sqflite.md) |

Arquitectura interna **Clean estricta + Feature-first** ([ADR-013](../adrs/adr-013-rbac-lockstep.md) y [ADR-014](../adrs/adr-014-result-failure.md)) con tres capas (`domain` / `data` / `presentation`) más `infrastructure` cross-cutting. Design System propio con prefijo `App*` ([ADR-018](../adrs/adr-018-design-system.md)) y configuración por entorno vía `String.fromEnvironment` ([ADR-015](../adrs/adr-015-env-config.md)). Versión mínima de iOS soportada: 15.0 ([ADR-022](../adrs/adr-022-ios-15.md)).

## Backend (`custodiam-api`)

| Componente | Versión | Decisión |
| --- | --- | --- |
| Python | 3.13 | Gestión vía uv |
| `uv` | 0.9+ | Package manager — [ADR-026](../adrs/adr-026-uv.md) |
| `fastapi` | ^0.115 | Web framework |
| `uvicorn[standard]` | ^0.34 | ASGI server |
| `sqlmodel` | ^0.0.22 | ORM unificado — [ADR-002](../adrs/adr-002-sqlmodel.md) |
| `sqlalchemy` | ^2.0 | Engine subyacente de SQLModel |
| `psycopg[binary]` | ^3.1 | Driver PostgreSQL — [ADR-008](../adrs/adr-008-psycopg3.md) |
| `alembic` | ^1.14 | Migraciones de schema — [ADR-003](../adrs/adr-003-alembic.md) |
| `PyJWT[crypto]` | ^2.11 | Validación local de JWT — [ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md) |
| `pydantic` | ^2.10 | Validación de schemas |
| `pydantic-settings` | ^2.7 | Configuración desde `.env` |
| `httpx` | ^0.28 | Cliente HTTP (llamadas a Keycloak Admin API) |
| `ruff` | ^0.8 | Linter + formatter |
| `pytest` | ^8.3 | Tests |

Estructura `app/{core,models,schemas,routers,services}`. Sesión SQLModel inyectada vía `Depends(get_session)`. RBAC implementado con un `Permission` enum y un factory `require_permission(Permission.X)` espejado en el cliente Flutter ([ADR-013](../adrs/adr-013-rbac-lockstep.md)).

## Infraestructura (`custodiam-infra`)

| Componente | Versión | Decisión |
| --- | --- | --- |
| Docker Compose | 2.x | Orquestador local |
| PostgreSQL | 15-alpine | BD relacional ([ADR-009](../adrs/adr-009-2-bds-separadas.md) — dos BDs lógicas) |
| Keycloak | 26+ | IdP OIDC ([ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)) |
| Resend (SMTP) | — | Emails transaccionales del realm ([ADR-021](../adrs/adr-021-smtp-resend.md)) |
| Nginx Alpine | latest | Servidor de la PWA ([ADR-006](../adrs/adr-006-nginx-alpine.md)) |
| ntfy | latest | Notificaciones de respaldo ([Notificaciones](notificaciones.md)) |
| n8n | latest | Automatización (post-MVP, profile `full`) |
| Cloudflare Tunnel | latest | Exposición HTTPS sin abrir puertos |
| Mock OIDC server | 2.1.10 | Tests del cliente OIDC en `custodiam-app` (profile `test`) |
| sops + age | latest | Gestión de secretos cifrados ([ADR-019](../adrs/adr-019-sops-age.md)) |
| `just` | 1.40+ | Command runner (interfaz preferida) |

Tres modos de despliegue (dev / tunnel / prod) mutuamente excluyentes con guard de cross-mode ([ADR-020](../adrs/adr-020-tres-modos-despliegue.md)). Imágenes publicadas en GHCR (`ghcr.io/custodiam/custodiam-api`, `ghcr.io/custodiam/custodiam-web`) por el workflow de CI de cada repo ([ADR-007](../adrs/adr-007-ghcr.md)).

## Documentación pública (`custodiam-book`)

| Componente | Versión | Decisión |
| --- | --- | --- |
| Material for MkDocs | ^9.5 | Theme + engine ([ADR-027](../adrs/adr-027-mkdocs-pages.md)) |
| `mkdocs-mermaid2-plugin` | ^1.2 | Renderizado nativo Mermaid |
| `mkdocs-d2-plugin` | ^1.7 | Diagramas D2 con `shape: sql_table` y crow's foot |
| `mike` | ^2.1 | Versionado de docs (instalado, sin activar de inicio) |
| `pymdown-extensions` | ^10.13 | Admonitions, tabs, code blocks |
| Python + uv | 3.13 + 0.9+ | Mismo stack que `custodiam-api` |

Hosted en **GitHub Pages directo** (vendor-lock-free) con dominio propio `docs.custodiam.es` vía CNAME en Cloudflare DNS modo `DNS only`. Workflow CI con `astral-sh/setup-uv` + `mkdocs build` + `peaceiris/actions-gh-pages@v4`.

## Diagrama del stack (alto nivel)

```d2
direction: down

clients: Clientes {
  style.fill: "#eef2ff"
  android: App Android\n(Flutter release)
  ios: App iOS\n(Flutter release)
  web: PWA\napp.custodiam.es
}

edge: Edge (Cloudflare) {
  style.fill: "#fef3c7"
  tunnel: Cloudflare Tunnel\n(api, auth, app, ntfy.custodiam.es) {
    shape: cloud
  }
  pages_legal: Cloudflare Pages\n(/privacy, /delete legales) {
    shape: page
  }
}

stack: Stack autoalojado (Docker Compose) {
  style.fill: "#ecfdf5"
  web: custodiam-web\nNginx Alpine sirviendo PWA
  api: FastAPI\ncustodiam-api
  kc: Keycloak 26\nrealm custodiam
  db: PostgreSQL 15\n2 BDs: custodiam, custodiam_kc {
    shape: cylinder
  }
  ntfy: ntfy\n(backup push)
}

external: Externos {
  style.fill: "#fef2f2"
  fcm: Firebase FCM\n(canal principal push) {
    shape: cloud
  }
  resend: Resend SMTP\n(emails transaccionales Keycloak) {
    shape: cloud
  }
}

clients.android -> edge.tunnel: HTTPS
clients.ios -> edge.tunnel: HTTPS
clients.web -> edge.tunnel: HTTPS

edge.tunnel -> stack.web
edge.tunnel -> stack.api
edge.tunnel -> stack.kc
edge.tunnel -> stack.ntfy

stack.api -> stack.db
stack.api -> stack.kc
stack.api -> external.fcm
stack.api -> stack.ntfy

stack.kc -> stack.db
stack.kc -> external.resend

clients.android -> external.fcm: push {style.stroke-dash: 3}
clients.ios -> external.fcm: push {style.stroke-dash: 3}
clients.web -> external.fcm: push {style.stroke-dash: 3}
clients.android -> stack.ntfy: fallback {style.stroke-dash: 3}
```

Diagrama detallado por flujo (autenticación OAuth, propagación de eventos, etc.) en **[Diagramas del sistema](diagramas.md)**.

## Referencias

- **[Empezar](../empezar/index.md)** — cómo levantar el stack completo.
- **[ADRs](../adrs/index.md)** — registro de decisiones técnicas con justificación.
