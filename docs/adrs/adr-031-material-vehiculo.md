---
title: ADR-031 — Modelo de asignación de material a vehículo
description: >-
  La asignación de material relaja su CheckConstraint binario a "exactamente
  uno de tres destinos" (voluntario, servicio o vehículo) para representar la
  dotación fija de un vehículo sin duplicar estructuras ni perder trazabilidad.
---

# ADR-031 — Modelo de asignación de material a vehículo

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 28 de mayo de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

El modelo de asignación de material, materializado en `asignacion_material.py`, descansa sobre un `CheckConstraint` con semántica XOR: cada asignación apunta a un voluntario **o** a un servicio, nunca a un tercer destino. No existe relación que vincule el material a un vehículo. El desarrollo del módulo de inventario introduce dos casos de negocio que ese modelo no cubre:

- **Dotación fija**: material que vive permanentemente con el vehículo —una radio, un kit de intervención— y que no depende de ningún servicio concreto.
- **Material asignado al vehículo para un servicio**: de naturaleza temporal, se incorpora al vehículo durante una intervención y se libera al cerrarla.

Ambos casos comparten el eje de pertenencia "material que está en un vehículo", pero difieren en su ciclo de vida: la dotación fija es permanente y no se libera al cerrar un servicio, mientras que el material temporal sigue la vida del servicio. El reto de diseño es representar los dos casos sin duplicar estructuras ni perder la trazabilidad temporal de las asignaciones, que es la que sostiene el flujo de reasignación de recursos.

## Decisión

Relajar el `CheckConstraint` XOR binario a **"exactamente uno de tres destinos"** (`voluntario_id`, `servicio_id`, `vehiculo_id`), añadir la clave foránea opcional `vehiculo_id` y un nuevo valor de enum `DOTACION_VEHICULO` para representar la dotación fija. El invariante de "exactamente un destino" se expresa como una suma tipada de predicados con casting a entero:

```sql
(voluntario_id IS NOT NULL)::int
+ (servicio_id IS NOT NULL)::int
+ (vehiculo_id IS NOT NULL)::int = 1
```

La **dotación fija** se modela como una fila de asignación de tipo `DOTACION_VEHICULO` con `vehiculo_id` informado y `servicio_id`, `voluntario_id` y `fecha_devolucion` a `NULL`, de carácter permanente. El **material temporal** asignado a un vehículo para un servicio no requiere ningún modelo nuevo: se infiere cruzando las asignaciones de material y de vehículo por `servicio_id`, responsabilidad de la capa de servicio y no del esquema.

La clave foránea `vehiculo_id` se declara con `ON DELETE RESTRICT` —no `ON DELETE SET NULL`—, porque anular el destino al borrar el vehículo dejaría la fila con cero destinos y rompería el propio invariante ternario.

## Justificación

1. **Reutiliza el patrón ya consolidado.** La solución se apoya en la tabla de asignaciones 1:N existente y en su discriminador enum, en línea con el patrón "catálogo + tabla de instancias + enum discriminador" establecido como decisión de proyecto en [ADR-025](adr-025-modelo-extensible.md). No introduce una tabla nueva ni un eje de relación paralelo.

2. **Separa la dotación fija del material temporal.** La auto-liberación que ocurre al cerrar un servicio filtra por `servicio_id`, de modo que no afecta a la dotación fija: una fila `DOTACION_VEHICULO` carece de `servicio_id` y permanece intacta. Los dos ciclos de vida conviven sin interferencias en la misma tabla.

3. **Preserva la trazabilidad temporal.** Al modelar la pertenencia como una asignación con sus fechas, y no como una clave foránea plana en `Material`, se conserva el historial de cuándo cada recurso entró y salió de un destino, que es la información que sostiene el flujo de reasignación.

4. **Stock bruto coherente con el catálogo.** Una dotación fija de `N` unidades se representa como una única fila con `cantidad = N`, no como `N` filas independientes. La cantidad de `Material` se mantiene como stock bruto que incluye lo dotado, de modo que la disponibilidad real se calcula como `cantidad − dotado` en la capa de servicio. Solo el tipo de material **prestable** admite ser dotación fija, lo que acota la regla de negocio a un único discriminador de catálogo y evita que material consumible o de un solo uso entre en el flujo de dotación.

## Alternativas evaluadas y descartadas

### A. Clave foránea plana `Material.vehiculo_id`

Una clave foránea directa en la entidad `Material` apuntando al vehículo al que pertenece.

- **Pros**: simplicidad, consulta directa "qué material pertenece a este vehículo".
- **Contras**: mezcla dos ejes que el modelo mantiene separados —el de stock y catálogo (qué material existe y en qué cantidad) y el de pertenencia temporal (a quién está asignado y desde cuándo)—. Una clave foránea plana no tiene fecha de inicio ni de fin, por lo que pierde la trazabilidad temporal que el flujo de reasignación necesita.
- **Descartado por**: pérdida de la trazabilidad temporal y mezcla de ejes que deben permanecer separados.

### B. Inferencia pura vía servicios

No añadir relación material↔vehículo y deducir siempre el material de un vehículo cruzando las asignaciones por `servicio_id`.

- **Pros**: cero cambios de esquema.
- **Contras**: resuelve el material temporal por servicio, pero no cubre la dotación fija: la dotación permanente del vehículo no está ligada a ningún servicio, de modo que no hay nada por lo que cruzar. El caso permanente quedaría sin representar.
- **Descartado por**: no cubre el caso de la dotación fija.

## Implicaciones operativas

- **Migración en dos revisiones.** PostgreSQL no permite usar un valor de enum recién añadido en la misma transacción que lo crea. La primera revisión ejecuta `ALTER TYPE ... ADD VALUE 'DOTACION_VEHICULO'` aislada; la segunda añade la columna `vehiculo_id`, realiza el DROP+ADD del constraint para incorporar la forma ternaria y crea la clave foránea con `ON DELETE RESTRICT`. La migración se prueba en upgrade y downgrade, verificando que el constraint rechaza dos destinos simultáneos y acepta exactamente uno de tres, y que la dotación fija sobrevive a la auto-liberación de servicios.
- **Pruebas contra PostgreSQL real.** El casting `(... IS NOT NULL)::int` del invariante y la sentencia `ALTER TYPE ADD VALUE` son específicos de PostgreSQL y no se reproducen en SQLite, de modo que las pruebas de este modelo se ejecutan contra un PostgreSQL real.
- **Permiso RBAC nuevo.** Se introduce el permiso `inventario.gestionar_dotacion_vehiculo`, con rol mínimo `jefe_seccion`, espejado en backend y cliente según la matriz de permisos del proyecto (ver [ADR-013](adr-013-rbac-lockstep.md)).
- **Reglas de negocio fijadas.** La dotación fija de más de una unidad se cuadra con el catálogo mediante stock bruto; solo el material prestable admite ser dotación fija; y el material temporal que recorre varios vehículos se representa solo a nivel de servicio —se muestra en la ficha del servicio y nunca en la de un vehículo concreto, que únicamente expone su dotación fija—.

## Referencias

- **[ADR-025 — Modelo de datos extensible](adr-025-modelo-extensible.md)** — patrón "catálogo + tabla de instancias + enum discriminador" que esta decisión aplica y extiende al eje material↔vehículo.
- **[ADR-013 — RBAC en lockstep front/back](adr-013-rbac-lockstep.md)** — matriz de permisos donde se incorpora `inventario.gestionar_dotacion_vehiculo`.
- **[PostgreSQL — ALTER TYPE](https://www.postgresql.org/docs/current/sql-altertype.html)** — restricciones sobre `ADD VALUE` en enums.
- **[PostgreSQL — CHECK constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS)** — base del invariante ternario.
