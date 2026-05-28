---
title: ADR-002 — SQLModel como ORM unificado
description: >-
  custodiam-api usa SQLModel para unificar el modelo de tabla de base de datos
  y el esquema de validación de la API en una sola clase.
---

# ADR-002 — SQLModel como ORM unificado

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 5 de febrero de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

El backend `custodiam-api` necesita un ORM para hablar con PostgreSQL y un mecanismo de validación de los datos que entran y salen por la API HTTP. La práctica habitual en Python con FastAPI desacopla ambos componentes: SQLAlchemy 2.0 para el ORM y Pydantic v2 para la validación de la API. Esa separación obliga a mantener **dos clases por entidad**: una `Voluntario(Base)` en `app/models/` con las columnas de la tabla y una `VoluntarioSchema(BaseModel)` en `app/schemas/` con la misma forma pero como DTO. Cada cambio en el modelo de datos exige tocar dos archivos coherentemente; cualquier divergencia produce *bugs* sutiles en serialización.

## Decisión

Adoptar **[SQLModel](https://sqlmodel.tiangolo.com/)** como capa unificada. Una clase con `table=True` es simultáneamente tabla de base de datos y esquema de validación. Los DTOs específicos de la API (variantes `Create`, `Update`, `Response`) se declaran como subclases ligeras de la misma jerarquía cuando difieren del modelo persistido.

```python
from sqlmodel import SQLModel, Field

class VoluntarioBase(SQLModel):
    nombre: str = Field(max_length=255)
    telefono: str = Field(max_length=20)
    municipio: str = Field(max_length=100)

class Voluntario(VoluntarioBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    keycloak_id: str | None = Field(default=None, unique=True, index=True)
    # ... más campos
```

`Voluntario` es a la vez tabla `voluntarios` en PostgreSQL y modelo validable por FastAPI.

## Justificación

1. **Mismo autor que FastAPI.** SQLModel está mantenido por [Sebastián Ramírez](https://github.com/tiangolo), el mismo autor de FastAPI y Typer. Esto garantiza coherencia idiomática y mantenimiento conjunto del ecosistema. Las novedades de FastAPI llegan a SQLModel sin desfase.

2. **Eliminación de duplicación.** Una sola clase por entidad reduce el código en un 30-40 % aproximado comparado con el patrón clásico SQLAlchemy + Pydantic separados. Las variantes (`Create`, `Update`, `Response`) viven como subclases en el mismo archivo o cerca, no en repositorios separados.

3. **Sigue siendo SQLAlchemy 2.0 por debajo.** SQLModel no es un ORM alternativo: es una capa sobre SQLAlchemy 2.0. Todas las features avanzadas (relaciones, `selectinload`, transacciones, sesiones) siguen disponibles sin abstracciones añadidas. Migraciones gestionadas con Alembic estándar.

4. **Type safety reforzada.** Las anotaciones de tipo son a la vez metadatos de columna SQL y validación Pydantic. El IDE muestra errores en tiempo de edición que con SQLAlchemy clásico solo aparecen en `runtime`.

5. **Comunidad activa.** Más de 14.000 estrellas en GitHub, releases regulares, documentación oficial extensa. No es un proyecto de un solo mantenedor abandonado.

## Alternativas evaluadas y descartadas

### A. SQLAlchemy 2.0 + Pydantic v2 separados (patrón clásico)

- **Pros**: máxima flexibilidad, separación estricta entre persistencia y API, comunidad enorme.
- **Contras**: duplicación de clases, mantenimiento doble, fricción al evolucionar modelos.
- **Descartado por**: el coste de mantenimiento doble no se compensa con la flexibilidad teórica para un proyecto de este tamaño.

### B. Tortoise ORM + Pydantic

- **Pros**: ORM async nativo, integración natural con FastAPI async.
- **Contras**: comunidad más pequeña, menos features que SQLAlchemy, migraciones (Aerich) menos maduras que Alembic.
- **Descartado por**: ROI desfavorable, pierde el ecosistema SQLAlchemy/Alembic.

### C. Django ORM

- **Pros**: ORM maduro, admin panel gratuito, migraciones internas.
- **Contras**: arrastra Django entero (framework monolítico) cuando solo se necesita el ORM, no encaja con FastAPI.
- **Descartado por**: imposible casarlo con FastAPI sin perder lo que aporta FastAPI.

### D. Peewee

- **Pros**: ligero, API simple.
- **Contras**: comunidad muy pequeña, sin async nativo, sin integración Pydantic.
- **Descartado por**: ecosistema insuficiente para producción.

## Implicaciones operativas

- **Estructura del repo**: `app/models/` contiene clases SQLModel con `table=True` (tablas BD); `app/schemas/` contiene variantes Pydantic puras (sin `table=True`) cuando la API necesita una forma distinta del modelo persistido (ej. `VoluntarioCreate` sin `id` ni `created_at`).
- **Migraciones**: Alembic con autogenerate funciona normal. La plantilla `script.py.mako` debe importar `sqlmodel` para que las migraciones autogeneradas resuelvan tipos como `sqlmodel.sql.sqltypes.AutoString`.
- **Tests**: las tablas se crean con `SQLModel.metadata.create_all(engine)` en lugar de `Base.metadata.create_all`.
- **Compatibilidad con el patrón Repository + Service + Router**: las clases SQLModel se manejan exclusivamente desde la capa Repository (queries puras); el Service trabaja sobre instancias devueltas; el Router consume DTOs de `app/schemas/` para serialización HTTP.

## Referencias

- **[Documentación oficial de SQLModel](https://sqlmodel.tiangolo.com/)**
- **[ADR-001 polyrepo](adr-001-polyrepo.md)** — contexto general del proyecto.
- **[ADR-026 uv como package manager](adr-026-uv.md)** — toolchain Python del backend.
