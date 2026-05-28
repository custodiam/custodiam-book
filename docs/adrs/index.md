---
title: ADRs
description: >-
  Registro de decisiones arquitectónicas (Architecture Decision Records)
  públicas del proyecto Custodiam.
---

# ADRs — Architecture Decision Records

Los ADRs son el registro permanente de las decisiones arquitectónicas tomadas durante el desarrollo. Cada uno documenta el contexto, la decisión, las alternativas evaluadas y las implicaciones operativas. Esta sección publica las ADRs aptas para audiencia externa; el repo privado del equipo conserva las versiones extendidas con material académico interno.

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
| **[ADR-002](adr-002-sqlmodel.md)** | SQLModel como ORM unificado | Una sola clase es tabla SQL + schema Pydantic; elimina duplicación entre `app/models/` y `app/schemas/` | 05-feb-2026 |
| **[ADR-010](adr-010-oauth-pkce-keycloak.md)** | OAuth 2.0 + PKCE + Keycloak + PyJWT | Authorization Code + PKCE para clientes públicos; validación JWT local con `azp` check (RFC 9068) | 12-feb-2026 |
| **[ADR-011](adr-011-deep-links.md)** | Estrategia de deep links | Custom scheme `es.custodiam://callback` para OAuth + App Links / Universal Links HTTPS para emails y notificaciones | 18-feb-2026 |
| **[ADR-013](adr-013-rbac-lockstep.md)** | RBAC en lockstep front/back | Matriz rol→permisos replicada en código (Python + Dart); JWT solo transporta roles | 24-feb-2026 |
| **[ADR-025](adr-025-modelo-extensible.md)** | Modelo de datos extensible | Patrón "catálogo + instancias + JSONB + enum discriminador" para entidades con tipos predefinidos ampliables | 10-mar-2026 |
| **[ADR-020](adr-020-tres-modos-despliegue.md)** | Tres modos de despliegue | Stack en exactamente uno de `dev` / `tunnel` / `prod`; tres scripts simétricos con guard de cross-mode | 05-may-2026 |
| **[ADR-021](adr-021-smtp-resend.md)** | SMTP transaccional con Resend | Resend (AWS SES eu-west-1) para emails transaccionales del realm Keycloak; tracking opt-in OFF preserva los App Links | 12-may-2026 |
| **[ADR-022](adr-022-ios-15.md)** | Versión mínima de iOS soportada | iOS 15.0 como mínimo (`Podfile` + `project.pbxproj`); forzado por Firebase iOS SDK 12.x | 15-may-2026 |
| **[ADR-023](adr-023-oauth-web-asimetria.md)** | OAuth + PKCE en SPA web vs móvil | Dos implementaciones de `AuthService` por `kIsWeb` + persistencia del `code_verifier` en `sessionStorage` | 20-may-2026 |
| **[ADR-024](adr-024-patrol-e2e.md)** | Patrol como framework E2E unificado | Patrol 4.6+ sustituye `integration_test`; pirámide en tres capas (unit / integración / E2E) | 22-may-2026 |
| **[ADR-026](adr-026-uv.md)** | uv como gestor de paquetes Python | `pyproject.toml` PEP 621 + `uv.lock` + Python 3.13 gestionado por uv; ~10× más rápido que pip | 24-may-2026 |
| **[ADR-027](adr-027-mkdocs-pages.md)** | Material for MkDocs + GitHub Pages | Book público en repo separado; hosting GitHub Pages directo + dominio `docs.custodiam.es` vía Cloudflare DNS modo `DNS only` | 26-may-2026 |

!!! info "Más ADRs en camino"
    El proyecto tiene 27 ADRs documentados internamente. Esta sección publica las aptas para audiencia externa conforme alcancen versión final.

    Próximas ADRs a publicar: ADR-003 a ADR-009 (decisiones de stack y registro Docker), ADR-012 a ADR-019 (arquitectura interna del cliente Flutter, gestión de secretos).

## Para contribuidores

Si quieres proponer una decisión arquitectónica que afecte al proyecto, abre primero un **issue** en el repo relevante con la propuesta y el análisis de alternativas. Tras discusión, redacta el ADR siguiendo el patrón común y abre PR. El proceso de aceptación está descrito en [Contribuir](../contribuir/index.md).
