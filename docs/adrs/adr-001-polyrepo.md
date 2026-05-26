---
title: ADR-001 — Estructura polyrepo
description: >-
  Custodiam adopta una estructura polyrepo con tres repositorios de código
  independientes (app, api, infra) bajo la organización GitHub custodiam.
---

# ADR-001 — Estructura polyrepo

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 25 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Custodiam comprende tres componentes técnicamente distintos:

1. **App móvil y web** — Flutter cross-platform (Android, iOS, Web). Ciclo de release ligado a stores (Google Play, App Store) con versionado semver y firmas. Tooling propio: `flutter pub`, `dart`, Gradle/CocoaPods.
2. **Backend API** — Python + FastAPI + SQLModel + PostgreSQL. Ciclo de release ligado a despliegue continuo (imagen Docker en GHCR). Tooling propio: `uv`, `pytest`, `alembic`, `ruff`.
3. **Infraestructura** — Docker Compose, configuraciones de Keycloak, scripts de operación. Ciclo de release ligado a entornos (dev, tunnel, prod). Tooling propio: `docker compose`, `just`, `sops`, `cloudflared`.

Cada componente tiene **lifecycle, herramientas, dependencias y equipo de mantenimiento distintos**. La decisión a tomar es: ¿monorepo único o tres repos independientes?

## Decisión

**Polyrepo**: tres repositorios de código independientes bajo la organización GitHub `custodiam`:

- [`custodiam-app`](https://github.com/custodiam/custodiam-app) — Flutter (Android + iOS + Web).
- [`custodiam-api`](https://github.com/custodiam/custodiam-api) — FastAPI + SQLModel + PostgreSQL.
- [`custodiam-infra`](https://github.com/custodiam/custodiam-infra) — Docker Compose + Keycloak + scripts.

Más un cuarto repositorio dedicado a la documentación pública:

- [`custodiam-book`](https://github.com/custodiam/custodiam-book) — Material for MkDocs (este sitio).

Localmente, los tres repos de código viven en hermanos dentro de un `custodiam-workspace/` que el equipo abre en un único editor:

```text
custodiam-workspace/
├── custodiam-app/
├── custodiam-api/
└── custodiam-infra/
```

Los repos NO están anidados entre sí. Cada uno se clona independientemente y mantiene su propia rama `main` + `develop` con protecciones (PR + 1 review).

## Justificación

1. **Ciclos de release desacoplados.** Una app Flutter con versionado semver para stores no encaja con un backend en despliegue continuo. Mantenerlos en repos separados permite cortar releases del backend múltiples veces al día sin afectar a versiones publicadas de la app.

2. **Tooling y CI específicos por repo.** Cada repo tiene workflow CI propio en `.github/workflows/ci.yml`. El de `custodiam-app` usa `flutter analyze`/`flutter test`/`flutter build`. El de `custodiam-api` usa `astral-sh/setup-uv@v3` + `uv run pytest`/`uv run ruff`. El de `custodiam-infra` valida composiciones Docker. Mantenerlos separados evita workflows monstruosos con condicionales por subcarpeta.

3. **Permisos finos por componente.** Aunque los dos miembros del equipo tienen Write en los tres repos, en una organización mayor cada repo podría tener equipos de mantenimiento distintos con permisos diferenciados. La estructura polyrepo lo soporta natural.

4. **Tamaño manejable.** Cada repo es legible y navegable individualmente. Un monorepo con tres componentes muy distintos (Dart + Python + YAML) genera fricción cognitiva al navegar (¿esto es del app o del api?).

5. **Patrón estándar en open source.** Numerosos proyectos open source siguen este patrón: GitLab divide su producto en backend/frontend/runner en repos distintos; Kubernetes tiene `kubernetes/kubernetes` separado de `kubernetes/website` y `kubernetes/test-infra`; Postgres tiene `postgres/postgres` (core) separado de `postgres/postgresql.org-content` (web). El patrón es defendible para audiencia técnica.

## Alternativas evaluadas y descartadas

### A. Monorepo único `custodiam`

- Pros: una sola clonación, una sola rama `develop`, navegación cruzada con búsqueda global.
- Contras: workflow CI complejo con condicionales por subcarpeta; mezcla de tooling (`uv` + `flutter` + `docker compose` en una sola raíz); cambios cross-component disparan CI de los tres aunque solo se haya tocado uno; tamaño total del repo crece más rápido.
- **Descartado** por: complejidad del CI y mezcla de tooling.

### B. Monorepo con workspace tipo Nx o Turborepo

- Pros: dependencias internas explícitas, caché compartida de builds, comandos cruzados (`nx affected`).
- Contras: Nx/Turborepo están orientados a TypeScript; Flutter + Python no encajan bien; añade un meta-tooling que el equipo de 2 personas tendría que aprender; equipo de 2 personas no necesita "comandos cruzados sobre proyectos afectados".
- **Descartado** por: ROI desfavorable para el tamaño del equipo.

### C. Repo único de código + repo separado de infra (dos repos)

- Pros: agrupa app + api juntos, separa infra.
- Contras: app y api siguen teniendo ciclos de release distintos; la mezcla Flutter + Python sigue siendo pesada; no soluciona el problema principal del monorepo.
- **Descartado** por: solución intermedia que no resuelve el problema.

### D. Cada componente en su propia organización GitHub

- Pros: máxima independencia.
- Contras: dispersión excesiva; pérdida de visibilidad cruzada; permisos más complejos; equipo de 2 personas no lo necesita.
- **Descartado** por: complejidad innecesaria.

## Implicaciones operativas

- **Clonado**: contributors clonan los tres repos en una carpeta `custodiam-workspace/` hermana. Documentado en [Empezar](../empezar/index.md).
- **Coordinación de cambios cross-component**: si un cambio en `custodiam-api` (p.ej. nuevo endpoint REST) requiere también cambio en `custodiam-app` (consumirlo), se hacen en **dos PR coordinados** uno en cada repo. La sincronía se gestiona con descripciones de PR que se referencian mutuamente.
- **Versionado independiente**: cada repo tiene tags propios. `custodiam-app` con semver para stores (`v0.1.0+1`); `custodiam-api` con semver para despliegue (`v0.1.0`); `custodiam-infra` con tags por hito (`sprint-3-cerrado`, `release-1.0`).
- **Imágenes Docker**: `custodiam-api` y `custodiam-app` publican imágenes en GHCR (`ghcr.io/custodiam/custodiam-api:latest`, `ghcr.io/custodiam/custodiam-app:latest`). `custodiam-infra` consume estas imágenes pero no produce las suyas (es solo orquestación). Esto está documentado en ADR-007.
- **Documentación interna del equipo**: el material conceptual y académico del proyecto vive en un **quinto repo privado** (`rodrigomulero/DOCUMENTACION`) con permisos del equipo. El book público (`custodiam-book`, este sitio) es una vista curada del privado apta para audiencia externa (ADR-027).

## Referencias

- **[Empezar](../empezar/index.md)** — cómo clonar y arrancar los tres repos.
- **[Arquitectura](../arquitectura/index.md)** — visión general del polyrepo y stack.
- **Estándares de la industria**: muchos proyectos open source siguen el patrón polyrepo, especialmente cuando los componentes tienen lifecycle y tooling muy distinto entre sí.
