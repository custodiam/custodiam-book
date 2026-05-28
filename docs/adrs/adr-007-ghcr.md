---
title: ADR-007 — GitHub Container Registry para imágenes Docker propias
description: >-
  Las imágenes propias de Custodiam (custodiam-api, custodiam-web) se publican
  en GHCR. Permisos heredados de la organización GitHub, gratuito para repos
  públicos, integración nativa con GitHub Actions.
---

# ADR-007 — GitHub Container Registry para imágenes Docker propias

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 30 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Custodiam publica dos imágenes Docker propias como artefacto de cada merge a `main`:

- **`custodiam-api`** — backend FastAPI + Python 3.13 + uv.
- **`custodiam-web`** — bundle estático Flutter Web servido con Nginx Alpine ([ADR-006](adr-006-nginx-alpine.md)).

Las imágenes las consume el `docker-compose.yml` del repo `custodiam-infra` en los modos `tunnel` y `prod` ([ADR-020](adr-020-tres-modos-despliegue.md)). En modo `dev` se construyen localmente; en los otros dos modos se hace `docker compose pull` y se descarga la versión publicada por el último CI.

Hay que decidir **dónde se publican las imágenes**. Las opciones plausibles son Docker Hub (estándar de facto histórico) o GitHub Container Registry (GHCR).

## Decisión

**GitHub Container Registry (GHCR)** bajo la organización `custodiam`:

- `ghcr.io/custodiam/custodiam-api`
- `ghcr.io/custodiam/custodiam-web`

Las imágenes son **públicas** (visibility `public` en la página de cada package de GHCR). Cualquier `docker pull ghcr.io/custodiam/custodiam-api:latest` funciona sin `docker login`. Esto permite que un nuevo contributor levante el stack en modo `tunnel` o `prod` sin necesitar credenciales adicionales.

El CI de cada repo (`custodiam-api/.github/workflows/ci.yml` y `custodiam-app/.github/workflows/ci.yml`) tiene un job `build-docker` que se ejecuta solo en merges a `main` (no en PRs) y publica la imagen con tag `:latest`.

## Justificación

1. **Integración nativa con GitHub Actions.** El registry vive en el mismo proveedor que el código. El job `build-docker` autentica con `${{ secrets.GITHUB_TOKEN }}` (token efímero del workflow) sin necesidad de gestionar secretos adicionales. Push y pull funcionan en CI sin configuración extra.

2. **Permisos heredados de la organización.** Cualquier miembro del equipo con acceso de escritura al repo `custodiam-api` puede publicar imágenes a `ghcr.io/custodiam/custodiam-api` sin permisos específicos del registry. La gestión de accesos se hace una sola vez en la organización GitHub, no en otro panel separado.

3. **Coste cero para repos públicos.** GHCR es gratuito sin límite de pulls ni de almacenamiento para imágenes públicas asociadas a repos públicos. Custodiam es AGPL-3.0 con repos públicos, por lo que aplica el plan gratuito indefinido.

4. **Sin rate limits de Docker Hub.** Docker Hub introdujo en 2020 un rate limit de 100 pulls anónimos cada 6 horas por IP, que se ha endurecido sucesivamente desde entonces. Para un piloto que opere desde una IP residencial compartida, esto es un riesgo real (un build local que pulle varias imágenes base puede consumir el cupo). GHCR no aplica rate limits a sus imágenes.

5. **Patrón estándar en open source moderno.** Proyectos serios que viven en GitHub publican sus imágenes en GHCR: SQLModel, FastAPI, Pydantic, Material for MkDocs, uv (Astral), entre otros. Es el comportamiento que un colaborador externo espera al ver un proyecto GitHub público.

## Alternativas evaluadas y descartadas

### A. Docker Hub

- **Pros**: estándar histórico, los `docker pull mysql:8` o equivalentes ya van ahí, búsqueda integrada en Docker Desktop.
- **Contras**: registro separado del repo de código (cuenta aparte, permisos aparte, autenticación aparte); rate limits desde 2020 que empeoran con cada revisión; coste si las imágenes pasan a privadas.
- **Descartado por**: separa el registry del código sin beneficio + riesgo de rate limit.

### B. Self-hosted Docker Registry

- **Pros**: control total, cero dependencia de terceros.
- **Contras**: añade otro contenedor al stack (`registry:2`), requiere mantener su almacenamiento, su disponibilidad y su backup; sin valor diferencial sobre GHCR para un proyecto público.
- **Descartado por**: complejidad operativa sin retorno.

### C. AWS ECR / Google Artifact Registry / Azure Container Registry

- **Pros**: integración con sus respectivos ecosistemas cloud.
- **Contras**: vendor lock-in con un cloud específico que el proyecto no usa para nada más. Coste por almacenamiento + transferencia.
- **Descartado por**: el stack del proyecto es autoalojado, no en cloud.

## Implicaciones operativas

- **Permisos `packages: write` en el workflow.** El job `build-docker` necesita `permissions: { packages: write }` en su definición para poder hacer `docker push` con el `GITHUB_TOKEN`. Documentado en la guía técnica de setup del polyrepo.
- **Visibilidad pública obligatoria al primer push.** GHCR no infiere la visibilidad del repo al crear un package por primera vez — la crea como privada por defecto. Tras el primer `docker push` exitoso hay que ir a la página del package y cambiar visibility a `public` manualmente. Solo una vez por package.
- **Tag actual `:latest`** — cada merge a `main` sobreescribe `:latest`. En el futuro se puede añadir tagueado por SHA (`:sha-<7>`) o por semver (`:vX.Y.Z`) para permitir pineo a versiones exactas, pero el MVP usa `:latest` por simplicidad.
- **Las protecciones de rama de `main`** (PR + review obligatorios) son las que aseguran que solo entran a `main` cambios revisados — y por extensión, solo cambios revisados acaban como `:latest` en el registry. Esto hace seguro que el modo `prod` consuma `:latest` directamente sin pineo.

## Referencias

- **[GitHub Container Registry — Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)** — documentación oficial.
- **[Docker — Docker Hub rate limits](https://docs.docker.com/docker-hub/download-rate-limit/)** — el rate limit que GHCR evita.
- **[ADR-020 Tres modos de despliegue](adr-020-tres-modos-despliegue.md)** — modos `tunnel` y `prod` consumen las imágenes de GHCR.
