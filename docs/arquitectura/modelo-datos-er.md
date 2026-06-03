---
title: Modelo de datos — diagrama ER completo
description: >-
  Diagrama entidad-relación de toda la base de datos de negocio de Custodiam:
  las dieciocho tablas organizadas por módulo y el mapa de relaciones entre
  módulos.
---

# Modelo de datos — diagrama ER completo

Esta página presenta el **esquema relacional completo** de Custodiam: las dieciocho tablas de la base de datos de negocio, agrupadas por módulo, más un mapa de las relaciones que cruzan los límites de un módulo a otro.

Es el complemento del [Modelo de datos](modelo-datos.md), que explica el **patrón de diseño** (catálogo + instancias + JSONB + enum discriminador, [ADR-025](../adrs/adr-025-modelo-extensible.md)); aquí el foco es el **mapa entidad-relación** de todo el esquema.

!!! note "Alcance del diagrama"
    El esquema corresponde a la base de datos de negocio (`custodiam`), gestionada con [SQLModel](../adrs/adr-002-sqlmodel.md) y migrada con [Alembic](../adrs/adr-003-alembic.md). La base de datos de Keycloak (`custodiam_kc`, ~70 tablas internas del servidor de identidad) es independiente y queda fuera de este diagrama, coherente con la separación de [ADR-009](../adrs/adr-009-2-bds-separadas.md).

## Convenciones del diagrama

- **Clave primaria** (`primary_key`): `id` de tipo `uuid`, generado en la capa de aplicación (no en la base de datos).
- **Clave foránea** (`foreign_key`): referencia a la clave primaria de otra tabla.
- **`unique`**: columna con restricción de unicidad.
- Las relaciones se dibujan en notación *crow's foot* desde el lado "uno" (clave primaria) hacia el lado "muchos" (clave foránea).
- Por legibilidad, los índices compuestos, los valores por defecto y las cláusulas `ON DELETE` no se representan en el diagrama; se describen en las [notas de modelado](#notas-de-modelado).

## Módulo Voluntarios

El núcleo del dominio de personas. La tabla `voluntarios` es la raíz; a su alrededor cuelgan los roles (con vigencia temporal), las disponibilidades por día, las acreditaciones y tallas (patrón catálogo + instancias de [ADR-025](../adrs/adr-025-modelo-extensible.md)), los contactos de emergencia y el historial de actividad.

```d2
direction: down

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
  foto_url: varchar
  conductor_habilitado: bool
  fecha_alta: date
  fecha_baja: date
  estado: enum
  created_at: timestamptz
  updated_at: timestamptz
}

roles: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  nombre: varchar {constraint: unique}
  nivel: int
  descripcion: varchar
  permisos: jsonb
}

voluntario_roles: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  rol_id: uuid {constraint: foreign_key}
  fecha_desde: date
  fecha_hasta: date
}

disponibilidades: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  fecha: date
  disponible: bool
}

tipos_acreditacion: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  codigo: varchar {constraint: unique}
  nombre: varchar
  descripcion: varchar
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
  activo: bool
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

voluntario_eventos: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  tipo_evento: enum
  payload: jsonb
  actor_keycloak_id: varchar
  created_at: timestamptz
}

voluntarios.id -> voluntario_roles.voluntario_id: "tiene" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios.id -> disponibilidades.voluntario_id: "declara" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
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
voluntarios.id -> voluntario_eventos.voluntario_id: "registra" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
roles.id -> voluntario_roles.rol_id: "asignado en" {
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

`voluntario_roles` es una tabla intermedia con vigencia (`fecha_desde`/`fecha_hasta`): permite reasignar el mismo rol en periodos distintos. `voluntario_eventos` es el historial de actividad del voluntario (altas, bajas, cambios de rol, fichajes, asignaciones), con `payload` en `JSONB` para el contexto de cada evento.

## Módulo Servicios y fichaje

Un servicio (preventivo, emergencia, formación u otro) recorre una máquina de estados `borrador → publicado → activo → cerrado`. Los voluntarios se asocian a un servicio mediante `inscripciones_servicio` (con un discriminador que distingue *inscrito* de *convocado*) y registran su presencia en `fichajes`.

```d2
direction: right

servicios: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  titulo: varchar
  descripcion: varchar
  tipo: enum
  estado: enum
  fecha_inicio: timestamp
  fecha_fin: timestamp
  ubicacion: varchar
  ubicacion_lat: float
  ubicacion_lng: float
  numero_voluntarios: int
  creado_por_keycloak_id: varchar
  fecha_cierre: timestamp
  created_at: timestamptz
  updated_at: timestamptz
}

inscripciones_servicio: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  servicio_id: uuid {constraint: foreign_key}
  voluntario_id: uuid {constraint: foreign_key}
  tipo: enum
  fecha: timestamp
}

fichajes: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  servicio_id: uuid {constraint: foreign_key}
  voluntario_id: uuid {constraint: foreign_key}
  hora_entrada: timestamp
  hora_salida: timestamp
  automatico: bool
  created_at: timestamptz
  updated_at: timestamptz
}

servicios.id -> inscripciones_servicio.servicio_id: "tiene" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
servicios.id -> fichajes.servicio_id: "registra" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
```

Tanto `inscripciones_servicio` como `fichajes` referencian además al voluntario (`voluntario_id`); esas relaciones cruzan al módulo Voluntarios y se ven en el [mapa global](#mapa-global-de-relaciones).

## Módulo Inventario y ubicaciones

El inventario separa `materiales` y `vehiculos` en tablas distintas (campos divergentes y distinto corte de permisos), ambos ubicados opcionalmente en un catálogo común de `ubicaciones` con coordenadas. La asignación de material se modela con `asignaciones_material`, que apunta a **exactamente uno** de tres destinos (voluntario, servicio o vehículo); la asignación de vehículos a servicios va en `asignaciones_vehiculo`. La "devolución" es un borrado lógico: una asignación está activa mientras `fecha_devolucion` sea nula.

```d2
direction: down

ubicaciones: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  nombre: varchar {constraint: unique}
  descripcion: varchar
  lat: float
  lng: float
  created_at: timestamptz
  updated_at: timestamptz
}

materiales: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  nombre: varchar
  descripcion: varchar
  codigo: varchar {constraint: unique}
  numero_serie: varchar
  tipo: enum
  categoria: varchar
  estado: enum
  cantidad: int
  ubicacion_base: varchar
  ubicacion_base_id: uuid {constraint: foreign_key}
  fecha_adquisicion: date
  fecha_proxima_revision: date
  foto_url: varchar
  created_at: timestamptz
  updated_at: timestamptz
}

vehiculos: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  codigo_interno: varchar {constraint: unique}
  matricula: varchar
  tipo: enum
  marca_modelo: varchar
  fecha_itv: date
  estado: enum
  ubicacion_base: varchar
  ubicacion_base_id: uuid {constraint: foreign_key}
  foto_url: varchar
  created_at: timestamptz
  updated_at: timestamptz
}

asignaciones_material: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  material_id: uuid {constraint: foreign_key}
  voluntario_id: uuid {constraint: foreign_key}
  servicio_id: uuid {constraint: foreign_key}
  vehiculo_id: uuid {constraint: foreign_key}
  tipo: enum
  cantidad: int
  fecha_asignacion: timestamp
  fecha_devolucion: timestamp
}

asignaciones_vehiculo: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  vehiculo_id: uuid {constraint: foreign_key}
  servicio_id: uuid {constraint: foreign_key}
  fecha_asignacion: timestamp
  fecha_devolucion: timestamp
}

ubicaciones.id -> materiales.ubicacion_base_id: "ubica" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
ubicaciones.id -> vehiculos.ubicacion_base_id: "ubica" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
materiales.id -> asignaciones_material.material_id: "se asigna en" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
vehiculos.id -> asignaciones_vehiculo.vehiculo_id: "se asigna en" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
vehiculos.id -> asignaciones_material.vehiculo_id: "se dota con" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
```

La restricción de "exactamente un destino" de `asignaciones_material` (un material se asigna a un voluntario **o** a un servicio **o** como dotación fija de un vehículo, nunca a más de uno) se garantiza con una restricción de tabla, detallada en [ADR-031](../adrs/adr-031-material-vehiculo.md). Las columnas `voluntario_id` y `servicio_id` de las asignaciones cruzan a otros módulos: ver el [mapa global](#mapa-global-de-relaciones).

## Módulo Notificaciones

Cada voluntario registra sus tokens de envío (`dispositivos`, uno por plataforma) y cada emisión de aviso queda registrada en `notificaciones` con sus contadores de envío.

```d2
direction: right

dispositivos: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  voluntario_id: uuid {constraint: foreign_key}
  fcm_token: varchar {constraint: unique}
  plataforma: enum
  activo: bool
  created_at: timestamptz
  ultima_actualizacion: timestamptz
}

notificaciones: {
  shape: sql_table
  id: uuid {constraint: primary_key}
  servicio_id: uuid {constraint: foreign_key}
  titulo: varchar
  cuerpo: varchar
  tipo: enum
  prioridad: enum
  enviada_at: timestamptz
  enviadas_count: int
  entregadas_count: int
}
```

Ambas tablas se enlazan con otros módulos: `dispositivos` pertenece a un voluntario y `notificaciones` referencia opcionalmente al servicio que la motivó. Esas relaciones se ven en el mapa global.

## Mapa global de relaciones

Las siete claves foráneas que **cruzan los límites de un módulo** son las que cosen el esquema. El módulo Voluntarios y el módulo Servicios actúan como destinos comunes; los módulos Inventario y Notificaciones apuntan hacia ellos.

```d2
direction: down

voluntarios_mod: "Voluntarios" {
  voluntarios: {
    shape: sql_table
    id: uuid {constraint: primary_key}
  }
}

servicios_mod: "Servicios y fichaje" {
  servicios: {
    shape: sql_table
    id: uuid {constraint: primary_key}
  }
  inscripciones_servicio: {
    shape: sql_table
    voluntario_id: uuid {constraint: foreign_key}
    servicio_id: uuid {constraint: foreign_key}
  }
  fichajes: {
    shape: sql_table
    voluntario_id: uuid {constraint: foreign_key}
    servicio_id: uuid {constraint: foreign_key}
  }
}

inventario_mod: "Inventario y ubicaciones" {
  asignaciones_material: {
    shape: sql_table
    voluntario_id: uuid {constraint: foreign_key}
    servicio_id: uuid {constraint: foreign_key}
  }
  asignaciones_vehiculo: {
    shape: sql_table
    servicio_id: uuid {constraint: foreign_key}
  }
}

notificaciones_mod: "Notificaciones" {
  dispositivos: {
    shape: sql_table
    voluntario_id: uuid {constraint: foreign_key}
  }
  notificaciones: {
    shape: sql_table
    servicio_id: uuid {constraint: foreign_key}
  }
}

voluntarios_mod.voluntarios.id -> servicios_mod.inscripciones_servicio.voluntario_id: "se inscribe" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios_mod.voluntarios.id -> servicios_mod.fichajes.voluntario_id: "ficha" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios_mod.voluntarios.id -> inventario_mod.asignaciones_material.voluntario_id: "recibe en préstamo" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
voluntarios_mod.voluntarios.id -> notificaciones_mod.dispositivos.voluntario_id: "tiene dispositivo" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
servicios_mod.servicios.id -> inventario_mod.asignaciones_material.servicio_id: "usa material" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
servicios_mod.servicios.id -> inventario_mod.asignaciones_vehiculo.servicio_id: "usa vehículo" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
servicios_mod.servicios.id -> notificaciones_mod.notificaciones.servicio_id: "motiva aviso" {
  source-arrowhead.shape: cf-one
  target-arrowhead.shape: cf-many
}
```

## Enumerados

El esquema usa trece tipos enumerados de PostgreSQL como discriminadores y máquinas de estado:

| Enumerado | Valores | Usado en |
| --- | --- | --- |
| `estado_voluntario` | activo · baja · suspendido | `voluntarios.estado` |
| `categoria_acreditacion` | licencia_oficial · formacion_interna · otro | `tipos_acreditacion.categoria`, `acreditaciones.categoria` |
| `tipo_servicio` | preventivo · emergencia · formacion · otro | `servicios.tipo` |
| `estado_servicio` | borrador · publicado · activo · cerrado | `servicios.estado` |
| `tipo_inscripcion` | inscrito · convocado | `inscripciones_servicio.tipo` |
| `tipo_material` | personal · prestable · servicio | `materiales.tipo` |
| `estado_inventario` | operativo · averiado · perdido · en_uso | `materiales.estado`, `vehiculos.estado` |
| `tipo_vehiculo` | furgoneta · pick_up · ambulancia · remolque | `vehiculos.tipo` |
| `tipo_asignacion_material` | personal · prestamo · servicio · dotacion_vehiculo | `asignaciones_material.tipo` |
| `plataforma_dispositivo` | android · ios · web | `dispositivos.plataforma` |
| `tipo_notificacion` | emergencia · servicio · recordatorio · sistema | `notificaciones.tipo` |
| `prioridad_notificacion` | critica · alta · normal · baja | `notificaciones.prioridad` |
| `tipo_evento_voluntario` | alta · baja · anonimizacion · cambio de rol · fichajes · inscripciones · asignaciones de material | `voluntario_eventos.tipo_evento` |

## Notas de modelado

- **Claves primarias `uuid`**: todas las tablas usan `id` de tipo `uuid` generado en la capa de aplicación, no por la base de datos. No se usan secuencias ni enteros autoincrementales.
- **Marcas de tiempo**: las columnas de auditoría (`created_at`, `updated_at`, `enviada_at`, `ultima_actualizacion`) son `timestamptz` (con zona horaria); las marcas de dominio (`fecha_inicio`, `hora_entrada`, `fecha_asignacion`, etc.) son `timestamp` sin zona.
- **Borrado lógico, nunca físico**: las bajas y devoluciones no eliminan filas. Un voluntario se da de baja con `estado = baja` (o se anonimiza); una asignación se devuelve poniendo `fecha_devolucion`. No hay ninguna cláusula `ON DELETE CASCADE` en el esquema: las únicas claves foráneas con borrado restringido explícito son las de `materiales`/`vehiculos`/`asignaciones_material` hacia las tablas que referencian.
- **Columnas `JSONB`**: `roles.permisos`, `tipos_acreditacion.campos_schema`, `acreditaciones.datos_especificos` y `voluntario_eventos.payload`. La matriz real de permisos por rol no vive en `roles.permisos`, sino espejada en código backend y cliente ([ADR-013](../adrs/adr-013-rbac-lockstep.md)).
- **Catálogos pre-poblados**: `roles`, `tipos_acreditacion` y `tipos_equipamiento` se cargan con datos canónicos mediante *data migrations* de Alembic, versionados en Git como parte del esquema.
- **Valores derivados no persistidos**: algunos atributos que la API expone (como el recuento de inscritos de un servicio o la duración de un fichaje) se calculan en consulta y no son columnas físicas.

## Referencias

- **[Modelo de datos](modelo-datos.md)** — el patrón de diseño catálogo + instancias + JSONB.
- **[ADR-002 SQLModel](../adrs/adr-002-sqlmodel.md)** — ORM unificado.
- **[ADR-003 Alembic](../adrs/adr-003-alembic.md)** — migraciones de esquema.
- **[ADR-009 Dos bases de datos separadas](../adrs/adr-009-2-bds-separadas.md)** — por qué la base de negocio y la de Keycloak van aparte.
- **[ADR-025 Modelo extensible](../adrs/adr-025-modelo-extensible.md)** — el patrón formal completo.
- **[ADR-031 Modelo material↔vehículo](../adrs/adr-031-material-vehiculo.md)** — la asignación con destino único.
