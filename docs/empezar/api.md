---
title: Backend API
description: >-
  Cómo levantar custodiam-api en local con uv 0.9+ y Python 3.13.
---

# Backend API — `custodiam-api`

Backend REST con **FastAPI + SQLModel + PostgreSQL + Keycloak**, gestionado con `uv` como package manager moderno.

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-026 — uv como package manager](../adrs/adr-026-uv.md)**: el repo migró de `pip + venv + requirements.txt` a `uv + pyproject.toml + uv.lock`.
    - **[ADR-002 — SQLModel](../adrs/adr-002-sqlmodel.md)** unifica SQLAlchemy 2.0 + Pydantic en un solo modelo.
    - **[ADR-003 — Alembic](../adrs/adr-003-alembic.md)** para migraciones con autogeneración.
    - **[ADR-008 — psycopg3](../adrs/adr-008-psycopg3.md)** como driver PostgreSQL (URL `postgresql+psycopg://...`).
    - **[ADR-009 — Dos BDs separadas](../adrs/adr-009-2-bds-separadas.md)** para evitar conflictos de Alembic con las tablas de Keycloak.
    - **[ADR-010 — OAuth + PKCE + Keycloak + PyJWT](../adrs/adr-010-oauth-pkce-keycloak.md)** para validación local de JWT.

## Requisitos

- `uv` 0.9+ instalado ([instrucciones aquí](index.md#requisitos-previos-comunes))
- PostgreSQL accesible (lo más cómodo es arrancarlo vía Docker Compose desde `custodiam-infra`, ver [recorrido infra](infra.md))
- Keycloak accesible (idem, viene en el stack de `custodiam-infra`)

## Clonar y arrancar

=== "Linux / macOS"

    ```bash
    git clone https://github.com/custodiam/custodiam-api.git
    cd custodiam-api

    # uv descarga Python 3.13 automáticamente si no está disponible.
    uv sync --all-extras

    # Configura las variables de entorno (DATABASE_URL, KEYCLOAK_URL, etc.)
    cp .env.example .env
    # Edita .env con valores reales o los del docker-compose del repo infra.

    # Aplica migraciones de BD
    uv run alembic upgrade head

    # Arranca el servidor de desarrollo con hot reload
    uv run uvicorn app.main:app --reload --port 8000
    ```

=== "Windows (Git Bash)"

    ```bash
    git clone https://github.com/custodiam/custodiam-api.git
    cd custodiam-api

    uv sync --all-extras

    cp .env.example .env
    # Editar .env con valores reales

    uv run alembic upgrade head

    uv run uvicorn app.main:app --reload --port 8000
    ```

Abre `http://localhost:8000/docs` para acceder a la documentación Swagger UI interactiva de la API.

## Comandos esenciales

```bash
# Sincronizar deps con el lockfile (idempotente)
uv sync --all-extras

# Ejecutar tests
uv run pytest tests/ -v
uv run pytest --cov=app --cov-report=term-missing

# Linter y formato
uv run ruff check app/ tests/
uv run ruff check --fix app/ tests/
uv run ruff format app/ tests/

# Migraciones Alembic
uv run alembic revision --autogenerate -m "descripción"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current

# Añadir una dependencia nueva (actualiza pyproject.toml + uv.lock)
uv add nombre-paquete            # runtime
uv add --dev nombre-paquete      # extras dev
```

!!! warning "Gotcha — `VIRTUAL_ENV` heredado"
    Si tu terminal hereda `VIRTUAL_ENV=...` de otro venv padre (por ejemplo, de un proyecto Python distinto que tenías abierto), `uv` lo respeta por defecto y NO usa el `.venv/` local del repo. Solución: `unset VIRTUAL_ENV` antes del primer `uv sync` en una terminal nueva.

## Variables de entorno relevantes

| Variable | Valor por defecto (dev) | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://custodiam:password@localhost:5432/custodiam` | URL de PostgreSQL. **Prefijo `+psycopg` es obligatorio** (psycopg3, no psycopg2). |
| `KEYCLOAK_URL` | `http://localhost:8080` | URL base de Keycloak |
| `KEYCLOAK_REALM` | `custodiam` | Nombre del realm |
| `DEBUG` | `false` | Activa CORS abierto + logging extra |

## Estructura del repo

```text
custodiam-api/
├── app/
│   ├── core/              # config, database, security, permissions
│   ├── models/            # SQLModel (tabla=True)
│   ├── schemas/           # Pydantic para API
│   ├── routers/           # Endpoints REST agrupados
│   └── services/          # Lógica de negocio
├── alembic/
│   ├── versions/          # Migraciones generadas
│   └── env.py             # Carga .env antes de leer DATABASE_URL
├── tests/                 # pytest con fixtures de cliente autenticado
├── .github/workflows/
│   └── ci.yml             # CI con astral-sh/setup-uv
├── pyproject.toml         # [project] PEP 621 + ruff + pytest config
├── uv.lock                # Lockfile reproducible
└── Dockerfile             # Multi-stage con ghcr.io/astral-sh/uv builder
```

## Siguientes pasos

- Para tener BD + Keycloak + ntfy corriendo a la vez, ve al recorrido **[Infraestructura completa](infra.md)**.
- Para entender el modelo de datos y las decisiones de diseño, revisa **[Arquitectura](../arquitectura/index.md)** y **[ADRs](../adrs/index.md)**.
