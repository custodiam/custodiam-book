---
title: ADR-003 — Alembic para migraciones de base de datos
description: >-
  custodiam-api usa Alembic como herramienta de migraciones de base de datos
  por su integración nativa con SQLAlchemy/SQLModel y la autogeneración a
  partir de cambios en los modelos.
---

# ADR-003 — Alembic para migraciones de base de datos

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 27 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El backend `custodiam-api` necesita un mecanismo de **migraciones de base de datos versionadas** que permita evolucionar el esquema PostgreSQL conforme el modelo de dominio cambia, sin perder datos y de forma reproducible entre máquinas. La elección de [SQLModel](adr-002-sqlmodel.md) como ORM unificado (sobre SQLAlchemy 2.0 por debajo) deja abierta la decisión de la herramienta de migraciones.

## Decisión

**[Alembic](https://alembic.sqlalchemy.org/)** como herramienta de migraciones, instalada como dependencia del proyecto.

```python
# Alembic detecta cambios en modelos y genera migración automáticamente
alembic revision --autogenerate -m "add municipio column to voluntarios"

# Aplica la migración a la BD
alembic upgrade head
```

La plantilla `script.py.mako` se ajusta para importar `sqlmodel` y permitir que el `--autogenerate` resuelva correctamente tipos como `sqlmodel.sql.sqltypes.AutoString`.

## Justificación

1. **Integración nativa con SQLAlchemy/SQLModel.** Alembic es el proyecto hermano de SQLAlchemy desarrollado por el mismo autor. Lee los modelos directamente desde `SQLModel.metadata` y genera migraciones a partir del diff entre el modelo declarado en Python y el estado real de la BD.

2. **Autogeneración madura.** `alembic revision --autogenerate` produce migraciones funcionales para la mayoría de cambios (`ADD COLUMN`, `CREATE TABLE`, `CREATE INDEX`, renames con `--rename`). Los cambios delicados (data migrations, constraints complejos, downgrades) se editan a mano sobre el archivo generado.

3. **Data migrations versionadas.** Los catálogos pre-poblados ([ADR-025](adr-025-modelo-extensible.md)) viven como `INSERT INTO ... VALUES (...)` dentro de las migraciones Alembic, no como configuración volátil externa. Una restauración de BD desde el repo restaura también los datos canónicos.

4. **Integración con CI.** El workflow de CI ejecuta `alembic upgrade head` en una BD efímera al inicio de la suite de tests, garantizando que las migraciones aplican limpias sobre una BD vacía y que el estado tras aplicarlas coincide con lo que los tests esperan.

5. **Estándar histórico en Python.** Alembic es la herramienta de facto para migraciones en proyectos Python con SQLAlchemy desde aproximadamente 2010. Documentación extensa, ecosistema maduro, gran cantidad de recetas para casos avanzados (PostgreSQL-specific, particionado, JSONB, etc.).

## Alternativas evaluadas y descartadas

### A. Liquibase

- **Pros**: agnóstico al lenguaje, soporta múltiples BDs, formato declarativo con XML / YAML / SQL.
- **Contras**: escrito en Java — añade JVM al stack del backend. Sintaxis declarativa más prolija que Alembic. La integración con SQLAlchemy/SQLModel no es nativa: hay que mantener manualmente el paralelismo entre los modelos Python y los changelogs Liquibase.
- **Descartado por**: arrastra JVM al backend sin beneficio sobre Alembic para un stack 100 % Python.

### B. Flyway

- **Pros**: simple, basado en archivos SQL versionados (`V1__init.sql`, `V2__add_column.sql`).
- **Contras**: igualmente Java — mismo problema que Liquibase. Sin autogeneración a partir de modelos: cada migración se escribe a mano.
- **Descartado por**: misma razón que Liquibase, y peor ergonomía sin autogeneración.

### C. Migraciones manuales con SQL plano sin herramienta

- **Pros**: máximo control, cero dependencias.
- **Contras**: sin versionado automático, sin checks de orden, sin downgrade, sin integración con CI. Requiere escribir y mantener manualmente la tabla de versiones aplicadas.
- **Descartado por**: reinventar Alembic sin beneficios.

## Implicaciones operativas

- **Estructura del repo**: la carpeta `alembic/` vive en la raíz de `custodiam-api` con `env.py` configurado para leer el `DATABASE_URL` de las variables de entorno (no del `alembic.ini`, que se mantiene minimal). Las migraciones generadas viven en `alembic/versions/`.
- **Plantilla con `sqlmodel`**: la línea `import sqlmodel` se añade a `script.py.mako` para que los tipos `sqlmodel.sql.sqltypes.*` se resuelvan en las migraciones autogeneradas.
- **CI**: el job de tests ejecuta `alembic upgrade head` antes de correr `pytest`. Esto garantiza que cualquier cambio de schema en una PR pasa por la migración antes que por los tests.
- **Convención de nombres**: las migraciones siguen el patrón `<revision>_<descripcion_corta>.py` con descripción en snake_case y verbo imperativo (`add_municipio_column`, `create_acreditaciones_table`).

## Referencias

- **[Documentación oficial de Alembic](https://alembic.sqlalchemy.org/)** — guía completa.
- **[Alembic + SQLModel](https://sqlmodel.tiangolo.com/tutorial/migrations/)** — integración recomendada.
- **[ADR-002 SQLModel](adr-002-sqlmodel.md)** — ORM unificado sobre el que opera Alembic.
- **[ADR-008 psycopg3](adr-008-psycopg3.md)** — driver PostgreSQL que Alembic usa por debajo.
