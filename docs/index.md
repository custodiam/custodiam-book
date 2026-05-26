---
title: Custodiam — Documentación
description: >-
  Sistema multiplataforma de gestión para agrupaciones de Protección Civil.
  Documentación pública del proyecto.
---

# Custodiam

**Custodiam** es un sistema multiplataforma de gestión para agrupaciones de Protección Civil. Cubre el ciclo operativo completo: voluntarios, servicios, fichaje, inventario y notificaciones de emergencia.

!!! info "Estado del proyecto"
    El proyecto está en desarrollo activo durante el curso académico 2025-2026 como Trabajo de Fin de Grado del ciclo DAM (Salesianos Zaragoza). El cliente piloto es **Protección Civil Bajo Gállego**. Licencia [AGPL-3.0](https://github.com/custodiam/custodiam-book/blob/main/LICENSE).

## Qué incluye

- **App móvil y web** (Flutter) para voluntarios y mandos: ver servicios, marcar disponibilidad, fichar entradas y salidas, consultar material asignado, recibir alertas push de emergencia.
- **Backend API** (FastAPI + PostgreSQL) que orquesta autenticación con Keycloak, RBAC con 12 roles jerárquicos y 40 permisos, y gestión del modelo de datos.
- **Infraestructura local y de producción** (Docker Compose, Cloudflare Tunnel) reproducible en cualquier máquina con un solo comando.
- **Notificaciones redundantes**: Firebase Cloud Messaging como canal principal + ntfy como backup.

## Por dónde empezar

<div class="grid cards" markdown>

- :material-rocket-launch: **[Empezar](empezar/index.md)**

    Cómo levantar el stack completo en local en minutos.

- :material-sitemap: **[Arquitectura](arquitectura/index.md)**

    Visión general del polyrepo, stack técnico y decisiones de diseño.

- :material-history: **[ADRs](adrs/index.md)**

    Registro de decisiones arquitectónicas tomadas durante el desarrollo.

- :material-handshake: **[Contribuir](contribuir/index.md)**

    Cómo aportar al proyecto, código de conducta y proceso de pull request.

</div>

## Repositorios del proyecto

| Repo | Tecnología | Descripción |
|------|------------|-------------|
| [custodiam-app](https://github.com/custodiam/custodiam-app) | Flutter (Android + iOS + Web) | App cliente para voluntarios y mandos |
| [custodiam-api](https://github.com/custodiam/custodiam-api) | FastAPI + SQLModel + PostgreSQL | Backend REST con auth Keycloak + RBAC |
| [custodiam-infra](https://github.com/custodiam/custodiam-infra) | Docker Compose + Keycloak + Cloudflare Tunnel | Orquestación del stack local y de producción |
| [custodiam-book](https://github.com/custodiam/custodiam-book) | Material for MkDocs | Esta documentación pública |

## Equipo

- **Marcos Val Sanz** — PO, UX, DEV-FE
- **Rodrigo Mulero García** — SM, TL, DEV-BE, OPS

## Licencia

Custodiam se distribuye bajo licencia [GNU Affero General Public License v3.0](https://github.com/custodiam/custodiam-book/blob/main/LICENSE) (AGPL-3.0). Los cuatro repositorios del proyecto usan la misma licencia.
