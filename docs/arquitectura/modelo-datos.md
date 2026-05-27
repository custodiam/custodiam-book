---
title: Modelo de datos
description: >-
  Esquema relacional de Custodiam — patrón "catálogo extensible + instancias +
  JSONB" aplicado al módulo voluntarios y replicable a futuros módulos.
---

# Modelo de datos

Custodiam usa **PostgreSQL 15** como base de datos principal y **SQLModel** ([ADR-002](../adrs/adr-002-sqlmodel.md)) como ORM unificado (SQLAlchemy 2.0 + Pydantic en una sola clase). El esquema se evoluciona con [Alembic](https://alembic.sqlalchemy.org/), incluyendo data migrations para pre-poblar catálogos.

## Patrón estructural del proyecto

Las entidades del dominio que admiten **tipos predefinidos pero ampliables** (acreditaciones, equipamiento, tipos de servicio, tipos de inventario, tipos de notificación) siguen un patrón único formalizado en [ADR-025](../adrs/adr-025-modelo-extensible.md): **catálogo + tabla de instancias + JSONB para campos específicos + enum discriminador**.

Esto permite:

- Añadir un tipo nuevo es un **INSERT en el catálogo**, sin ALTER TABLE.
- Consultas atómicas por familia (`WHERE categoria = 'FORMACION_INTERNA'`) y mixtas (`EXISTS` correlacionado) sobre la misma estructura.
- Campos específicos por tipo en `JSONB` documentados por `campos_schema` del catálogo (schema-on-read).
- Catálogos canónicos versionados en Git como data migrations.

## Diagrama ER — módulo voluntarios

```d2
direction: right

voluntarios: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  keycloak_id: varchar {constraint: unique}
  nombre: varchar
  dni: varchar {constraint: unique}
  email: varchar {constraint: unique}
  telefono: varchar
  municipio: varchar
  fecha_nacimiento: date
  direccion: varchar
  conductor_habilitado: bool
  estado: enum
  created_at: timestamptz
  updated_at: timestamptz
}

tipos_acreditacion: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  codigo: varchar {constraint: unique}
  nombre: varchar
  categoria: enum
  campos_schema: jsonb
  activo: bool
}

acreditaciones: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  tipo_id: uuid {constraint: foreign_key}
  categoria: enum
  fecha_obtencion: date
  fecha_caducidad: date
  numero: varchar
  entidad_emisora: varchar
  datos_especificos: jsonb
  documento_url: varchar
}

tipos_equipamiento: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  codigo: varchar {constraint: unique}
  nombre: varchar
  sistema_tallas: varchar
}

tallas_voluntario: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  tipo_id: uuid {constraint: foreign_key}
  valor: varchar
}

contactos_emergencia: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  nombre: varchar
  telefono: varchar
  parentesco: varchar
  orden_preferencia: int
}

voluntarios.id -> acreditaciones.voluntario_id: "tiene" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios.id -> tallas_voluntario.voluntario_id: "tiene" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios.id -> contactos_emergencia.voluntario_id: "tiene" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
tipos_acreditacion.id -> acreditaciones.tipo_id: "clasifica" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
tipos_equipamiento.id -> tallas_voluntario.tipo_id: "clasifica" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
```

## Catálogos pre-poblados

Los catálogos `tipos_acreditacion` y `tipos_equipamiento` se cargan con datos canónicos mediante **Alembic data migrations** ejecutadas al desplegar. Esto los versiona en Git como parte del esquema, no como configuración volátil.

### `tipos_acreditacion` (extracto)

| codigo | nombre | categoría sugerida | `campos_schema` (ejemplo) |
| --- | --- | --- | --- |
| `CARNET_CONDUCIR` | Carnet de conducir | `LICENCIA_OFICIAL` | `{"tipo": "B\|B+E\|C\|C+E\|D", "incluye_remolque": "bool"}` |
| `ESS_SANITARIO` | ESS Sanitario | `LICENCIA_OFICIAL` | `{"nivel": "ESS\|ATS\|enfermería"}` |
| `ADR_MERCANCIAS_PELIGROSAS` | ADR Mercancías Peligrosas | `LICENCIA_OFICIAL` | `{"clases": ["I","II","III","IV","V","VI","VII","VIII","IX"]}` |
| `MANIPULADOR_ALIMENTOS` | Manipulador de alimentos | `LICENCIA_OFICIAL` | `{}` |
| `CURSO_DEA` | Curso uso de DEA | `FORMACION_INTERNA` | `{}` |
| `CURSO_PROTECCION_CIVIL` | Curso PC (genérico) | `FORMACION_INTERNA` | `{"horas": "int", "nivel": "básico\|intermedio\|avanzado"}` |
| `JORNADA_RESCATE_VEHICULOS` | Jornada rescate vehículos | `FORMACION_INTERNA` | `{}` |
| `OTRO` | Otra acreditación | `OTRO` | (libre) |

### `tipos_equipamiento` (extracto)

| codigo | nombre | sistema_tallas |
| --- | --- | --- |
| `CAMISA` | Camisa de uniforme | `XS-XXXL` |
| `POLO` | Polo de uniforme | `XS-XXXL` |
| `CHAQUETA` | Chaqueta de uniforme | `XS-XXXL` |
| `PANTALON` | Pantalón de uniforme | `36-50` |
| `BOTAS` | Botas reglamentarias | `EU` |
| `CASCO` | Casco | `S-XL` |
| `GUANTES` | Guantes | `S-XL` |
| `CHALECO` | Chaleco reflectante | `XS-XXXL` |

Modificaciones futuras del catálogo (añadir un tipo nuevo, marcar uno como `activo = false`) se gestionan con **nuevas data migrations** Alembic, revisables por PR como cualquier otro cambio de schema.

## Indexación

| Tabla | Índices |
| --- | --- |
| `voluntarios` | `dni` UNIQUE, `email` UNIQUE, `keycloak_id` UNIQUE+INDEX, `estado` |
| `acreditaciones` | `voluntario_id`, `tipo_id`, `(voluntario_id, tipo_id, numero)` UNIQUE, `categoria` |
| `tallas_voluntario` | `voluntario_id`, `(voluntario_id, tipo_id)` UNIQUE |
| `contactos_emergencia` | `voluntario_id` |

El índice en `acreditaciones.categoria` soporta consultas atómicas por familia ("voluntarios con cualquier formación interna") sin recurrir a `JOIN` con el catálogo. Las consultas mixtas (`EXISTS` correlacionado por tipo) aprovechan los índices compuestos.

## Validación de `datos_especificos`

En la capa API, FastAPI + Pydantic valida `datos_especificos` contra el `campos_schema` declarado en el tipo asociado. Implementación recomendada:

- Librería [`jsonschema`](https://python-jsonschema.readthedocs.io/) (validación a partir del schema almacenado).
- Alternativa: `model_validator` Pydantic con lógica condicional por `tipo_id`.

La validación es **opcional al inicio** (los catálogos `campos_schema` pueden ser `null`) y **estricta cuando madure la UI de gestión** (panel admin para crear/editar tipos y describir su schema). El cliente puede leer el `campos_schema` para construir formularios dinámicos sin hardcodearlos.

## Aplicabilidad a otros módulos

El patrón se aplicará en módulos futuros con la misma estructura:

| Módulo futuro | Catálogo previsto | Instancias |
| --- | --- | --- |
| **Inventario** (E05) | `tipos_material`, `tipos_vehiculo` | `inventario`, `vehiculos` |
| **Servicios** (E03) | `tipos_servicio` (preventivo, emergencia, formación, jornada) | `servicios` |
| **Notificaciones** (E06) | `tipos_notificacion` con canales (FCM, ntfy, email) | `notificaciones` |

La elección concreta (catálogo + instancias + JSONB + enum) se documenta como **principio de proyecto** en [ADR-025](../adrs/adr-025-modelo-extensible.md): para entidades con tipos predefinidos extensibles, no usar columnas planas ni JSONB libre.

## Audit log cross-module

Todas las operaciones críticas (alta/baja/edición de voluntarios, asignación a servicios, anonimización RGPD) se registran en una tabla `audit_log` cross-module con un patrón de imports diferidos para evitar dependencias cíclicas entre módulos. Detalle en [Audit log](audit-log.md).

## Referencias

- **[ADR-002 SQLModel](../adrs/adr-002-sqlmodel.md)** — ORM unificado.
- **[ADR-025 Modelo extensible](../adrs/adr-025-modelo-extensible.md)** — patrón formal completo.
- **[PostgreSQL — JSONB](https://www.postgresql.org/docs/current/datatype-json.html)** — operadores e indexación.
- **[SQLModel — Relationships](https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/)** — patrón de relaciones.
