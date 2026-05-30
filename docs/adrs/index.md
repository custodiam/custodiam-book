---
title: ADRs
description: >-
  Registro de decisiones arquitectónicas (Architecture Decision Records)
  públicas del proyecto Custodiam.
---

# ADRs — Architecture Decision Records

Los ADRs son el registro permanente de las decisiones arquitectónicas tomadas durante el desarrollo. Cada uno documenta el contexto, la decisión, las alternativas evaluadas y las implicaciones operativas.

## Patrón estructural común

Todas las ADRs siguen el mismo esquema:

1. **Contexto** — qué problema operativo motiva la decisión.
2. **Decisión** — qué se eligió concretamente.
3. **Justificación** — argumentos a favor (típicamente 3-5 razones).
4. **Alternativas evaluadas y descartadas** — qué se consideró y por qué no se eligió.
5. **Implicaciones operativas** — qué cambia para el equipo, el código y la infra.
6. **Referencias** — enlaces a estándares, otros ADRs relacionados, documentación oficial.

## ADRs publicados

| ID | Título | Decisión clave | Fecha |
| --- | --- | --- | --- |
| **[ADR-001](adr-001-polyrepo.md)** | Estructura polyrepo | Tres repos de código independientes (app, api, infra) bajo organización GitHub `custodiam` | 25-ene-2026 |
| **[ADR-003](adr-003-alembic.md)** | Alembic para migraciones de BD | Alembic con autogeneración a partir de modelos SQLModel; data migrations versionadas en repo | 27-ene-2026 |
| **[ADR-004](adr-004-http-cliente.md)** | Cliente HTTP del cliente Flutter | Paquete oficial `http` + wrapper `ApiClient` con interceptors propios; sin `dio` ni code generation | 28-ene-2026 |
| **[ADR-005](adr-005-sqflite.md)** | sqflite como BD local de la app | SQLite nativo vía plugin oficial para Android/iOS; cola offline + caché de listas grandes | 28-ene-2026 |
| **[ADR-006](adr-006-nginx-alpine.md)** | Nginx Alpine como servidor de la PWA | `nginx:alpine` ligero (~25 MB) con cabeceras de cache diferenciadas para bootstrap files y assets hasheados | 29-ene-2026 |
| **[ADR-007](adr-007-ghcr.md)** | GitHub Container Registry para imágenes Docker | GHCR para `custodiam-api` y `custodiam-web`; integración nativa con Actions, sin rate limits, gratuito en repos públicos | 30-ene-2026 |
| **[ADR-002](adr-002-sqlmodel.md)** | SQLModel como ORM unificado | Una sola clase es tabla SQL + schema Pydantic; elimina duplicación entre `app/models/` y `app/schemas/` | 05-feb-2026 |
| **[ADR-008](adr-008-psycopg3.md)** | psycopg3 como driver PostgreSQL | `psycopg[binary]` ≥3.1 con prefijo `postgresql+psycopg://`; sucesor moderno de psycopg2 con asincronía nativa | 10-feb-2026 |
| **[ADR-009](adr-009-2-bds-separadas.md)** | Dos bases de datos PostgreSQL separadas | `custodiam` (negocio, Alembic) y `custodiam_kc` (Keycloak); evita que `--autogenerate` toque las ~70 tablas de Keycloak | 11-feb-2026 |
| **[ADR-010](adr-010-oauth-pkce-keycloak.md)** | OAuth 2.0 + PKCE + Keycloak + PyJWT | Authorization Code + PKCE para clientes públicos; validación JWT local con `azp` check (RFC 9068) | 12-feb-2026 |
| **[ADR-011](adr-011-deep-links.md)** | Estrategia de deep links | Custom scheme `es.custodiam://callback` para OAuth + App Links / Universal Links HTTPS para emails y notificaciones | 18-feb-2026 |
| **[ADR-012](adr-012-riverpod.md)** | Riverpod como state management | `flutter_riverpod` ≥2.6 para DI + estado reactivo; reglas duras de uso (Provider/StateProvider/Notifier/AsyncNotifier) | 20-feb-2026 |
| **[ADR-013](adr-013-rbac-lockstep.md)** | RBAC en lockstep front/back | Matriz rol→permisos replicada en código (Python + Dart); JWT solo transporta roles | 24-feb-2026 |
| **[ADR-014](adr-014-result-failure.md)** | `Result<T>` sealed + jerarquía `Failure` | Repositorios devuelven `Result<T>`, nunca lanzan cross-layer; pattern matching exhaustivo en consumidor | 25-feb-2026 |
| **[ADR-015](adr-015-env-config.md)** | Configuración por entorno con `String.fromEnvironment` | Clase `EnvConfig` + `--dart-define` en build; sin JSON files ni hardcoded URLs | 26-feb-2026 |
| **[ADR-016](adr-016-dev-log.md)** | Logging estructurado con `dev.log` | `dart:developer` con `name:` por subsistema (`'API'`, `'Auth'`, ...); cero dependencias externas | 27-feb-2026 |
| **[ADR-017](adr-017-splash-app-startup.md)** | SplashPage Flutter + `AppStartupUseCase` | Primera ruta con branding consistente; use case testeable decide destino tras restaurar sesión | 28-feb-2026 |
| **[ADR-018](adr-018-design-system.md)** | Design System propio con prefijo `App*` | Componentes en `lib/core/ui/` que envuelven Material 3; tokens + `ThemeData` + `ThemeExtension` separados por responsabilidad | 02-mar-2026 |
| **[ADR-025](adr-025-modelo-extensible.md)** | Modelo de datos extensible | Patrón "catálogo + instancias + JSONB + enum discriminador" para entidades con tipos predefinidos ampliables | 10-mar-2026 |
| **[ADR-019](adr-019-sops-age.md)** | Gestión de secretos con sops + age | `docker/.env.sops` cifrado con sops + age multidestinatario; clave personal por miembro, archivo versionado en repo | 08-abr-2026 |
| **[ADR-020](adr-020-tres-modos-despliegue.md)** | Tres modos de despliegue | Stack en exactamente uno de `dev` / `tunnel` / `prod`; tres scripts simétricos con guard de cross-mode | 05-may-2026 |
| **[ADR-021](adr-021-smtp-resend.md)** | SMTP transaccional con Resend | Resend (AWS SES eu-west-1) para emails transaccionales del realm Keycloak; tracking opt-in OFF preserva los App Links | 12-may-2026 |
| **[ADR-022](adr-022-ios-15.md)** | Versión mínima de iOS soportada | iOS 15.0 como mínimo (`Podfile` + `project.pbxproj`); forzado por Firebase iOS SDK 12.x | 15-may-2026 |
| **[ADR-023](adr-023-oauth-web-asimetria.md)** | OAuth + PKCE en SPA web vs móvil | Dos implementaciones de `AuthService` por `kIsWeb` + persistencia del `code_verifier` en `sessionStorage` | 20-may-2026 |
| **[ADR-024](adr-024-patrol-e2e.md)** | Patrol como framework E2E unificado | Patrol 4.6+ sustituye `integration_test`; pirámide en tres capas (unit / integración / E2E) | 22-may-2026 |
| **[ADR-026](adr-026-uv.md)** | uv como gestor de paquetes Python | `pyproject.toml` PEP 621 + `uv.lock` + Python 3.13 gestionado por uv; ~10× más rápido que pip | 24-may-2026 |
| **[ADR-027](adr-027-mkdocs-pages.md)** | Material for MkDocs + GitHub Pages | Book público en repo separado; hosting GitHub Pages directo + dominio `docs.custodiam.es` vía Cloudflare DNS modo `DNS only` | 26-may-2026 |
| **[ADR-028](adr-028-valuekeys-tests.md)** | Catálogo central de ValueKeys para tests | Clase `K` en `lib/app/test_keys.dart` como fuente única del string de cada key; importable desde producción, tests de widget y E2E | 28-may-2026 |
| **[ADR-031](adr-031-material-vehiculo.md)** | Modelo de asignación de material a vehículo | `CheckConstraint` ternario ("exactamente uno de tres destinos") + FK `vehiculo_id` + enum `DOTACION_VEHICULO` para la dotación fija; material temporal inferido por servicio | 28-may-2026 |

!!! info "Sobre la numeración"
    La numeración de los ADRs sigue el orden cronológico en que se tomaron las decisiones. Algunos números pueden corresponder a decisiones cuyo diseño está cerrado pero cuya implementación llega en fases posteriores; cada uno se publica cuando se materializa. Las decisiones futuras se añaden siguiendo el mismo patrón estructural.

## Para contribuidores

Si quieres proponer una decisión arquitectónica que afecte al proyecto, abre primero un **issue** en el repo relevante con la propuesta y el análisis de alternativas. Tras discusión, redacta el ADR siguiendo el patrón común y abre PR. El proceso de aceptación está descrito en [Contribuir](../contribuir/index.md).
