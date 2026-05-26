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
|---|---|---|---|
| **[ADR-001](adr-001-polyrepo.md)** | Estructura polyrepo | Tres repos de código independientes (app, api, infra) bajo organización GitHub `custodiam` | 25-ene-2026 |

!!! info "Más ADRs en camino"
    El proyecto tiene **27 ADRs documentados internamente** (ADR-001 a ADR-027 al cierre del Sprint 4). Se irán publicando aquí progresivamente conforme alcancen versión final y se confirme que son aptas para audiencia externa.
    
    ADRs publicadas próximamente (en orden de prioridad):
    
    - ADR-002 — SQLModel como ORM unificado (SQLAlchemy + Pydantic).
    - ADR-010 — OAuth2 + PKCE + Keycloak + PyJWT.
    - ADR-013 — Clean Architecture estricta en Flutter.
    - ADR-020 — Tres modos de despliegue (dev / tunnel / prod).
    - ADR-022 — iOS 15 como deployment target mínimo.
    - ADR-026 — uv como package manager Python.
    - ADR-027 — Material for MkDocs para esta documentación pública.

## Para contribuidores

Si quieres proponer una decisión arquitectónica que afecte al proyecto, abre primero un **issue** en el repo relevante con la propuesta y el análisis de alternativas. Tras discusión, redacta el ADR siguiendo el patrón común y abre PR. El proceso de aceptación está descrito en [Contribuir](../contribuir/index.md).
