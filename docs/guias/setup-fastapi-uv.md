---
title: Setup FastAPI con uv — guía técnica
description: >-
  Cómo levantar el proyecto custodiam-api desde cero con uv 0.9+ como
  package manager, pyproject.toml PEP 621, Python 3.13 gestionado
  automáticamente, SQLModel como ORM, validación JWT con PyJWT,
  driver psycopg3, tests con pytest, linter ruff.
---

# Setup FastAPI con uv

Guía técnica completa para configurar el repositorio `custodiam-api` desde un clon vacío. Cubre el setup del entorno con uv, la estructura del proyecto, el código base (config, BD, main, tests), comandos de desarrollo y la configuración del linter. Aplica las decisiones del proyecto sobre toolchain Python ([ADR-026](../adrs/adr-026-uv.md)), ORM unificado ([ADR-002](../adrs/adr-002-sqlmodel.md)), driver de BD ([ADR-008](../adrs/adr-008-psycopg3.md)) y validación de JWT ([ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)).

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-026 uv](../adrs/adr-026-uv.md)**: `pyproject.toml` PEP 621 + `uv.lock` + Python 3.13 gestionado automáticamente.
    - **[ADR-002 SQLModel](../adrs/adr-002-sqlmodel.md)**: una sola clase es tabla SQL + schema Pydantic.
    - **[ADR-003 Alembic](../adrs/adr-003-alembic.md)**: migraciones con autogeneración a partir de modelos.
    - **[ADR-008 psycopg3](../adrs/adr-008-psycopg3.md)**: driver moderno PostgreSQL con prefijo `postgresql+psycopg://`.
    - **[ADR-010 OAuth + PyJWT](../adrs/adr-010-oauth-pkce-keycloak.md)**: validación JWT local con `PyJWT[crypto]`.

## Prerrequisitos

- Repositorio `custodiam-api` clonado.
- **uv 0.9+** instalado:
    - **Windows**: `winget install --id=astral-sh.uv` o `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
    - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Python 3.13 **no se requiere instalado a priori** — uv lo descarga e instala automáticamente en su caché global (`~/.local/share/uv/python/`) en el primer `uv sync` que lo necesite.

## Paso 1 — Verificar la instalación

```bash
uv --version
# uv 0.9.x o superior
```

Opcional, pre-instalar Python 3.13 antes del primer `uv sync` (rápido, ~30 s):

```bash
uv python install 3.13
```

## Paso 2 — Crear el entorno virtual

uv reemplaza el patrón histórico `python3 -m venv venv` + `source venv/bin/activate` + `pip install`. La carpeta del entorno pasa de `venv/` a **`.venv/`** (convención uv estándar). Las activaciones manuales ya no son necesarias: `uv run <cmd>` ejecuta cada comando dentro del entorno automáticamente.

```bash
cd custodiam-api

# Crear el entorno virtual local (.venv/) con Python 3.13.
# uv descarga el intérprete si no está disponible.
uv venv --python 3.13

# Verificar
uv run python --version
# Python 3.13.x
```

!!! warning "Gotcha — `VIRTUAL_ENV` heredado"
    Si tu terminal hereda `VIRTUAL_ENV=...` de otro venv padre (por ejemplo, un venv en la raíz del workspace), uv lo respeta por defecto y NO crea el `.venv/` local del repo. Solución: `unset VIRTUAL_ENV` antes del primer `uv venv` o `uv sync` en una terminal nueva.

## Paso 3 — Estructura del proyecto

El repo `custodiam-api` sigue esta estructura:

```text
custodiam-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Entry point FastAPI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings con pydantic-settings
│   │   ├── database.py            # SQLModel engine + session
│   │   ├── security.py            # Validación JWT (incluye azp check)
│   │   └── permissions.py         # Enum Permission + matriz roles → permisos
│   ├── models/                    # SQLModel models (table=True)
│   │   └── __init__.py
│   ├── schemas/                   # DTOs Pydantic para API
│   │   └── __init__.py
│   ├── repositories/              # Queries SQLModel
│   │   └── __init__.py
│   ├── services/                  # Lógica de negocio
│   │   └── __init__.py
│   └── routers/                   # Endpoints REST agrupados
│       └── __init__.py
├── alembic/
│   ├── versions/                  # Migraciones generadas
│   ├── env.py                     # Carga .env y declara metadata
│   └── script.py.mako             # Plantilla — importa sqlmodel
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures: postgres real en :5433, FakeKeycloakAdmin
│   └── test_health.py
├── alembic.ini
├── pyproject.toml                 # [project] PEP 621 + extras dev
├── uv.lock                        # Lockfile versionado para reproducibilidad
├── Dockerfile                     # Multi-stage con ghcr.io/astral-sh/uv builder
├── .github/workflows/ci.yml       # CI con astral-sh/setup-uv
├── .gitignore
├── README.md
└── LICENSE
```

Si faltan carpetas en un repo nuevo:

```bash
mkdir -p app/{core,models,schemas,repositories,routers,services}
mkdir -p alembic/versions
mkdir -p tests

touch app/__init__.py app/core/__init__.py app/models/__init__.py \
      app/schemas/__init__.py app/repositories/__init__.py \
      app/routers/__init__.py app/services/__init__.py \
      tests/__init__.py
```

## Paso 4 — `pyproject.toml` con dependencias

El `pyproject.toml` declara dependencias de runtime en `[project.dependencies]` y dependencias de desarrollo (tests + lint) en `[project.optional-dependencies.dev]`. Si el repo viene vacío:

```toml title="pyproject.toml"
[project]
name = "custodiam-api"
version = "0.1.0"
description = "Backend FastAPI de Custodiam"
readme = "README.md"
requires-python = ">=3.13"
license = { text = "AGPL-3.0-or-later" }
authors = [
    { name = "Rodrigo Mulero García" },
    { name = "Marcos Val Sanz" },
]
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",

    # Database — SQLModel unifica SQLAlchemy + Pydantic
    "sqlmodel>=0.0.22",
    "sqlalchemy>=2.0.0",
    "psycopg[binary]>=3.1.0",
    "alembic>=1.14.0",

    # Auth — JWT offline validation con PyJWT
    "PyJWT[crypto]>=2.11.0",
    "httpx>=0.28.0",

    # Validation — pydantic viene con sqlmodel; declararlo explícito
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",

    # Utils
    "python-dotenv>=1.0.0",
    "python-multipart>=0.0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

Sincronizar el entorno con el `pyproject.toml`. En el primer `uv sync` se genera `uv.lock` (versionado en Git):

```bash
# Instala runtime + extras dev en .venv/
uv sync --all-extras

# En CI o cuando el lockfile no debe regenerarse:
uv sync --all-extras --frozen
```

Para añadir dependencias más adelante:

```bash
uv add nombre-paquete            # runtime — actualiza pyproject.toml + uv.lock
uv add --dev nombre-paquete      # solo extras.dev
```

`uv add` actualiza `pyproject.toml` y `uv.lock` en el mismo paso. Nunca hace falta editar a mano la lista de dependencias.

## Paso 5 — Código base

### Configuración con pydantic-settings

```python title="app/core/config.py"
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración centralizada vía variables de entorno."""

    # Base de datos
    database_url: str = (
        "postgresql+psycopg://custodiam:password@localhost:5432/custodiam"
    )

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "custodiam"
    keycloak_public_url: str = "http://localhost:8080"
    keycloak_authorized_party: str = "custodiam-app"

    # ntfy
    ntfy_url: str = "http://localhost:8090"

    # App
    debug: bool = False
    api_version: str = "v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

`pydantic-settings` lee automáticamente las variables del entorno y del `.env` (en ese orden de precedencia). Cualquier campo del modelo `Settings` es accesible como `settings.database_url` con tipado fuerte.

### Engine y sesión de SQLModel

```python title="app/core/database.py"
from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url)


def get_session() -> Generator[Session, None, None]:
    """Sesión SQLModel para inyectar en endpoints FastAPI.

    Uso en routers:
        @router.get("/voluntarios")
        def listar(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session
```

SQLModel ([ADR-002](../adrs/adr-002-sqlmodel.md)) unifica SQLAlchemy + Pydantic en una sola clase. Un modelo con `table=True` es tabla de BD **y** schema de validación. Esto elimina la duplicación entre `app/models/` (tablas) y `app/schemas/` (DTOs), reduciendo el código por entidad ~30-40 %.

### Entry point FastAPI

```python title="app/main.py"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="Custodiam API",
    description="API para gestión de agrupaciones de Protección Civil",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — en producción se restringe a dominios conocidos
allowed_origins = ["*"] if settings.debug else [
    "https://app.custodiam.es",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Endpoint raíz con info básica."""
    return {
        "status": "ok",
        "app": "Custodiam API",
        "version": "0.1.0",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck para Docker y monitorización."""
    return {"status": "healthy"}


# Routers se incluirán según se desarrollen:
# from app.routers import voluntarios, servicios, inventario
# app.include_router(
#     voluntarios.router,
#     prefix=f"/api/{settings.api_version}",
# )
```

### Fixtures de tests

```python title="tests/conftest.py"
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Cliente de test para la API."""
    return TestClient(app)
```

```python title="tests/test_health.py"
def test_root(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

!!! note "Tests reales contra Postgres"
    Esta guía muestra solo el smoke test con `TestClient`. Los tests reales del proyecto usan una **instancia PostgreSQL en el puerto 5433** levantada con un contenedor auxiliar, `create_all` del schema en el `conftest`, seed de catálogos y `TRUNCATE` entre tests para asilamiento. La razón: SQLite + `factory_boy` no cubre operadores PostgreSQL específicos (JSONB, arrays, ranges) que sí usa el dominio del proyecto.

## Paso 6 — Ejecutar en desarrollo

```bash
# uv run usa el .venv/ del repo automáticamente, sin activación manual.
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acceder a:

| URL | Qué es |
| --- | --- |
| `http://localhost:8000` | Endpoint raíz |
| `http://localhost:8000/health` | Healthcheck |
| `http://localhost:8000/docs` | Swagger UI interactivo |
| `http://localhost:8000/redoc` | ReDoc (documentación alternativa) |

El `--reload` recarga el servidor automáticamente al detectar cambios en `app/`. Útil en desarrollo, **no usar en producción**.

## Paso 7 — Tests

```bash
uv run pytest tests/ -v
```

Salida esperada:

```text
tests/test_health.py::test_root     PASSED
tests/test_health.py::test_health   PASSED
```

Cobertura con report en terminal:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

Para tests específicos:

```bash
uv run pytest tests/test_voluntarios.py -v
uv run pytest tests/test_voluntarios.py::test_crear_voluntario -v
```

## Paso 8 — Linter y formato con ruff

La configuración de ruff y pytest vive en el mismo `pyproject.toml`:

```toml title="pyproject.toml (continuación)"
[tool.ruff]
target-version = "py313"
line-length = 100
src = ["app", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

Comandos:

```bash
uv run ruff check app/ tests/             # solo reporta
uv run ruff check --fix app/ tests/       # autofix
uv run ruff format app/ tests/            # formateo
```

`ruff` ya está instalado como parte del extra `dev` de `pyproject.toml` y se resuelve automáticamente vía `uv sync --all-extras`.

## Paso 9 — Migraciones con Alembic

Alembic ([ADR-003](../adrs/adr-003-alembic.md)) gestiona los cambios de schema con autogeneración a partir de los modelos SQLModel.

### Crear una migración nueva

```bash
# Tras añadir o modificar modelos en app/models/
uv run alembic revision --autogenerate -m "add municipio column to voluntarios"
```

Alembic compara los modelos declarados en Python contra el estado real de la BD y genera un archivo en `alembic/versions/` con las operaciones `op.add_column`, `op.create_table`, etc. **Revisar siempre** el archivo generado antes de aplicarlo — las constraints complejas (`UNIQUE`, `CHECK`, índices parciales) suelen requerir edición manual.

### Aplicar migraciones

```bash
uv run alembic upgrade head        # aplica todas las migraciones pendientes
uv run alembic upgrade +1          # aplica solo la siguiente
uv run alembic downgrade -1        # deshace la última
uv run alembic current             # qué revisión está aplicada
uv run alembic history             # historial completo
```

### Plantilla `script.py.mako`

La plantilla debe importar `sqlmodel` para que las migraciones autogeneradas resuelvan tipos como `sqlmodel.sql.sqltypes.AutoString`:

```python title="alembic/script.py.mako (fragmento)"
import sqlalchemy as sa
import sqlmodel       # ← necesario para SQLModel-specific types
${imports if imports else ""}
```

## Paso 10 — Variables de entorno

El archivo `.env` (gitignored) contiene los valores reales:

```bash title=".env"
# Base de datos
DATABASE_URL=postgresql+psycopg://custodiam:<password>@localhost:5432/custodiam

# Keycloak (para validación JWT y, opcionalmente, Admin API)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=custodiam
KEYCLOAK_PUBLIC_URL=http://localhost:8080
KEYCLOAK_AUTHORIZED_PARTY=custodiam-app

# ntfy (notificaciones de respaldo)
NTFY_URL=http://localhost:8090

# App
DEBUG=true
API_VERSION=v1
```

El prefijo `postgresql+psycopg://` en `DATABASE_URL` es **obligatorio** ([ADR-008](../adrs/adr-008-psycopg3.md)). Sin él, SQLAlchemy elige `psycopg2` por defecto y falla.

## Comandos esenciales — resumen

```bash
# Entorno
uv sync --all-extras               # instala runtime + dev (regenera lockfile si es necesario)
uv sync --all-extras --frozen      # CI: no regenera lockfile

# Dependencias
uv add fastapi-pagination          # añade runtime
uv add --dev httpx-mock            # añade dev
uv remove paquete                  # quita una dep

# Ejecución
uv run uvicorn app.main:app --reload
uv run python -c "from app.core.config import settings; print(settings)"

# Tests
uv run pytest tests/ -v
uv run pytest --cov=app --cov-report=term-missing
uv run pytest tests/test_voluntarios.py::test_crear -v

# Linter
uv run ruff check app/ tests/
uv run ruff check --fix app/ tests/
uv run ruff format app/ tests/

# Migraciones
uv run alembic revision --autogenerate -m "descripción"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic current
```

## Verificación final

- [ ] `uv sync --all-extras --frozen` audita el lockfile sin resolver versiones nuevas.
- [ ] `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` arranca sin errores.
- [ ] GET `http://localhost:8000/` retorna 200 con JSON `{"status": "ok", ...}`.
- [ ] GET `http://localhost:8000/health` retorna `{"status": "healthy"}`.
- [ ] GET `http://localhost:8000/docs` muestra Swagger UI con los dos endpoints.
- [ ] `uv run pytest tests/ -v` pasa con los dos tests verdes.
- [ ] `uv run ruff check app/` sin errores.
- [ ] Estructura de carpetas completa; `pyproject.toml` y `uv.lock` versionados; sin `requirements.txt` ni `venv/` en el repo.

## Problemas comunes

### `VIRTUAL_ENV` apunta a otro venv del workspace

Síntoma: `uv sync` no crea `.venv/` local, instala paquetes en un venv padre o falla con permisos.

```bash
unset VIRTUAL_ENV
uv sync --all-extras
```

### `uv sync` falla al descargar Python 3.13

uv descarga binarios de Python desde `python.org`. Si tu red bloquea ese host:

```bash
# Forzar uso de Python del sistema (debe ser ≥3.13)
uv venv --python $(which python3.13)
```

### `psycopg.errors.OperationalError: could not connect to server`

- Verifica que PostgreSQL esté `healthy`: `docker compose ps`.
- Verifica el prefijo `postgresql+psycopg://` en `DATABASE_URL`.
- En desarrollo local, el host debe ser `localhost`. Desde dentro de Docker, debe ser `postgres` (nombre del servicio).

### Alembic detecta tablas de Keycloak como `removed`

Significa que la BD `custodiam` y la BD `custodiam_kc` no están separadas. Ver el [troubleshooting de la guía Docker Compose local](docker-compose-local.md#alembic-detecta-tablas-de-keycloak-como-removed) ([ADR-009](../adrs/adr-009-2-bds-separadas.md)).

### `ImportError: cannot import name 'X' from 'sqlmodel'`

Versión de SQLModel desincronizada con SQLAlchemy. Asegurar `sqlmodel>=0.0.22` y `sqlalchemy>=2.0.0` en `pyproject.toml`. Tras cambiar, `uv sync --all-extras` regenera `.venv/`.

### Plantilla Alembic no resuelve `AutoString`

Asegurar que `alembic/script.py.mako` tiene `import sqlmodel` al inicio. Las migraciones autogeneradas usan `sqlmodel.sql.sqltypes.AutoString` para columnas `str` y sin el import fallan en `upgrade head`.

### `uv add paquete` no actualiza el lockfile

Verifica que `pyproject.toml` no esté en modo solo lectura. Si el lockfile parece corrupto, regenerar con `uv lock --upgrade`.

## Referencias

- **[FastAPI Documentation](https://fastapi.tiangolo.com/)** — referencia oficial del framework.
- **[SQLModel Documentation](https://sqlmodel.tiangolo.com/)** — ORM unificado.
- **[SQLAlchemy 2.0](https://docs.sqlalchemy.org/)** — motor subyacente.
- **[Pydantic v2](https://docs.pydantic.dev/)** — validación subyacente de SQLModel.
- **[Alembic](https://alembic.sqlalchemy.org/)** — migraciones.
- **[uv documentation](https://docs.astral.sh/uv/)** — package manager.
- **[Ruff](https://docs.astral.sh/ruff/)** — linter y formatter.
- **[ADR-002](../adrs/adr-002-sqlmodel.md)**, **[ADR-003](../adrs/adr-003-alembic.md)**, **[ADR-008](../adrs/adr-008-psycopg3.md)**, **[ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)**, **[ADR-026](../adrs/adr-026-uv.md)** — decisiones que esta guía implementa.
