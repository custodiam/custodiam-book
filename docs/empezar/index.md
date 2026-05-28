---
title: Empezar
description: >-
  Guías de instalación y arranque rápido para los tres repositorios de
  Custodiam.
---

# Empezar

Esta sección reúne las guías para levantar cada uno de los tres repositorios de Custodiam en una máquina nueva. El proyecto sigue un patrón **polyrepo** ([ADR-001](../adrs/adr-001-polyrepo.md)) con tres repositorios independientes que se desarrollan en paralelo y se orquestan en local con Docker Compose desde `custodiam-infra`.

## Recorridos

<div class="grid cards" markdown>

- :material-server: **[Backend (API)](api.md)**

    Levantar `custodiam-api` (FastAPI + SQLModel + PostgreSQL) en local con `uv` y Docker.

- :material-cellphone-link: **[App (Flutter)](app.md)**

    Levantar `custodiam-app` (Flutter móvil + web) con `flutter pub get` y `flutter run`.

- :material-docker: **[Infraestructura completa](infra.md)**

    Levantar todo el stack (PostgreSQL + Keycloak + API + Web + ntfy) en un solo comando con `custodiam-infra`.

- :material-account-key: **[Usuarios de prueba](usuarios-prueba.md)**

    Credenciales seed, matriz de capacidades por rol y protocolo de prueba para validar el RBAC de un vistazo.

</div>

## Requisitos previos comunes

| Herramienta | Versión mínima | Cómo instalar |
|---|---|---|
| Git | 2.40+ | `winget install Git.Git` (Windows) · `brew install git` (macOS) · gestor de paquetes (Linux) |
| Docker Desktop | 4.x | [docker.com](https://www.docker.com/products/docker-desktop/) — usa WSL2 internamente en Windows |
| `uv` (para `custodiam-api`) | 0.9+ | `winget install --id=astral-sh.uv` (Windows) · `curl -LsSf https://astral.sh/uv/install.sh \| sh` (macOS/Linux) |
| Flutter SDK (para `custodiam-app`) | 3.x | [flutter.dev/docs/get-started/install](https://docs.flutter.dev/get-started/install) |
| `just` (recomendado para `custodiam-infra`) | 1.40+ | `winget install Casey.Just` · `brew install just` · `cargo install just` |

## Recomendación de orden

Si vas a contribuir o evaluar el proyecto entero:

1. Empieza por la **[Infraestructura completa](infra.md)** — un solo comando levanta todo, ideal para tener una base funcional en minutos.
2. Si vas a tocar **backend**, después clona `custodiam-api` y sigue su [recorrido API](api.md) (con `uv sync` para desarrollar fuera de Docker).
3. Si vas a tocar **frontend**, clona `custodiam-app` y sigue su [recorrido App](app.md) (Flutter ejecutándose en local contra el backend del Docker Compose).
