---
title: ADR-008 — psycopg3 como driver PostgreSQL
description: >-
  custodiam-api usa el paquete `psycopg[binary]` (psycopg3) como driver
  PostgreSQL, con URL `postgresql+psycopg://...` en SQLAlchemy. Driver moderno
  con mejor soporte de tipos y rendimiento que psycopg2.
---

# ADR-008 — psycopg3 como driver PostgreSQL

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 10 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El backend FastAPI + SQLAlchemy/SQLModel necesita un **driver Python para PostgreSQL** que SQLAlchemy invoca por debajo cuando ejecuta queries. El estándar histórico del ecosistema Python ha sido [`psycopg2`](https://pypi.org/project/psycopg2/) (o su variante con binarios precompilados `psycopg2-binary`). Desde 2021, su sucesor [`psycopg3`](https://www.psycopg.org/psycopg3/) está disponible como reescritura moderna con mejor soporte de tipos, asincronía nativa y compatibilidad mejorada con versiones recientes de Python.

## Decisión

**`psycopg[binary]`** (paquete unificado de psycopg3 con binarios incluidos) como driver, en `pyproject.toml`:

```toml
[project]
dependencies = [
    "psycopg[binary] >=3.1",
    # ...
]
```

URL de conexión en SQLAlchemy con el prefijo `postgresql+psycopg://`:

```python
DATABASE_URL = "postgresql+psycopg://user:pass@host:5432/custodiam"
```

El prefijo `psycopg` (sin `2`) indica a SQLAlchemy que use el driver psycopg3.

## Justificación

1. **Compatibilidad mejorada con Python 3.13 / 3.14.** `psycopg2-binary` ha tenido problemas históricos con cada release nuevo de Python (los binarios precompilados llegan con retraso, hay incidencias documentadas en Windows). `psycopg3` se mantiene activamente y soporta de forma nativa las versiones modernas del intérprete.

2. **Mejor soporte de tipos PostgreSQL-específicos.** `psycopg3` introduce adaptadores nativos para tipos modernos de PostgreSQL (rangos, JSONB con `json.dumps` integrado, `uuid` sin extension, arrays multidimensionales) y permite registrar adaptadores propios sin las gymnastics que requería `psycopg2`. Esto importa para el patrón [catálogo + JSONB](adr-025-modelo-extensible.md) del módulo de voluntarios.

3. **Compatible con SQLAlchemy 2.0 oficial.** SQLAlchemy 2.0 (la versión sobre la que se asienta SQLModel) soporta `psycopg3` de primera clase con el dialect `postgresql+psycopg`. La integración es transparente; ninguna feature de SQLModel requiere `psycopg2` específicamente.

4. **Asincronía nativa disponible.** Aunque el backend usa principalmente las APIs sync de SQLModel, `psycopg3` deja la puerta abierta a queries async sin cambiar de driver — algo que `psycopg2` no permite sin paquetes adicionales (`asyncpg`).

5. **Empaquetado `[binary]` simple.** El extra `[binary]` instala libpq precompilada como wheel binario en pip, sin necesidad de cabeceras de desarrollo del sistema (`libpq-dev`, `postgresql-server-dev`). Para Windows + uv + venv local, instalar `psycopg[binary]` funciona sin instalar el cliente PostgreSQL del sistema.

## Alternativas evaluadas y descartadas

### A. `psycopg2-binary`

El estándar histórico previo.

- **Pros**: enorme ecosistema, lleva años en producción, casi todos los tutoriales lo usan.
- **Contras**: proyecto en *maintenance mode* desde 2021 con la liberación de `psycopg3`. Sin nuevas features. Compatibilidad con Python 3.13/3.14 ha tenido latencia. Sin asincronía nativa.
- **Descartado por**: empezar un proyecto nuevo en 2026 sobre la versión legacy del driver no tiene justificación.

### B. `asyncpg`

Driver PostgreSQL puro y nativamente asíncrono, mantenido por MagicStack.

- **Pros**: rendimiento asíncrono superior a psycopg3 según benchmarks (~3x en queries simples).
- **Contras**: no soporta el protocolo DBAPI estándar que SQLAlchemy espera para sus APIs sync; integrarlo con SQLAlchemy + SQLModel obliga a usar todo el stack en modo `async`, lo que aumenta la complejidad de los endpoints FastAPI sin beneficio observable para el volumen del piloto.
- **Descartado por**: el rendimiento extra no se necesita y la complejidad operativa sí cuesta.

### C. Driver puro Python (`pg8000`)

- **Pros**: cero dependencias C, instalable en cualquier sitio.
- **Contras**: rendimiento muy inferior; soporte de tipos PostgreSQL parcial; comunidad pequeña.
- **Descartado por**: rendimiento inadecuado para producción.

## Implicaciones operativas

- **URL en `.env` con prefijo correcto**: `DATABASE_URL=postgresql+psycopg://...` (no `postgresql://...` ni `postgresql+psycopg2://...`). Si SQLAlchemy recibe solo `postgresql://`, elige `psycopg2` por defecto en versiones antiguas o falla si no está instalado.
- **Sin instalación del cliente PostgreSQL del sistema**: el wheel binario de `psycopg[binary]` incluye `libpq` precompilada. Esto simplifica el setup en CI y en máquinas de desarrollo.
- **Alembic compatible automáticamente**: Alembic ([ADR-003](adr-003-alembic.md)) lee el `DATABASE_URL` del entorno y delega en SQLAlchemy, que elige `psycopg` por el prefijo. Sin configuración adicional.
- **Imagen Docker del backend** (`custodiam-api`) instala `psycopg[binary]` via `uv sync --frozen`. El runtime `python:3.13-slim-bookworm` ya contiene las libs necesarias del SO; no hace falta `apt install libpq-dev`.
- **Sustitución potencial por `psycopg[c]`** si el extra `[binary]` causa problemas en algún SO concreto: `psycopg[c]` instala el módulo C compilando contra una `libpq` del sistema. No se ha necesitado hasta hoy.

## Referencias

- **[psycopg3 — Documentación oficial](https://www.psycopg.org/psycopg3/docs/)** — guía completa, diferencias con psycopg2.
- **[SQLAlchemy — Dialect postgresql+psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)** — integración oficial.
- **[ADR-002 SQLModel](adr-002-sqlmodel.md)** y **[ADR-003 Alembic](adr-003-alembic.md)** — capas que delegan en este driver.
