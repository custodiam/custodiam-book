# Usuarios de prueba

Esta página documenta las cuentas que el script
[`scripts/seed-test-users.sh`](https://github.com/custodiam/custodiam-infra/blob/main/scripts/seed-test-users.sh)
crea automáticamente en un entorno de desarrollo o staging, junto con
la matriz de capacidades por rol del realm `custodiam`.

!!! warning "Credenciales de TEST"

    Las contraseñas listadas aquí son **públicas a propósito** porque
    solo aplican a entornos de desarrollo y staging que se levantan
    con `dev-up.sh`. **En producción nunca se ejecuta este script**;
    las cuentas reales se crean desde la consola admin de Keycloak o
    vía el endpoint `POST /api/v1/voluntarios` con un usuario que
    tenga permiso `voluntarios.crear`.

## Los dos realms de Keycloak

Custodiam usa Keycloak con dos realms separados. Es importante no
confundirlos:

| Realm | Quién vive ahí | Para qué sirve |
|---|---|---|
| `master` | Bootstrap admin de KC (credenciales en `docker/.env`) | Administrar el propio Keycloak: crear realms, configurar SSO, gestionar usuarios de cualquier realm |
| `custodiam` | Todos los usuarios humanos de la app | Login en la app (web o móvil) |

El "admin de Keycloak" del realm `master` **no es un usuario de la
app**: no se loguea en `app.custodiam.es`. Solo sirve para tocar la
configuración interna de Keycloak. Sus credenciales viven en
`docker/.env` (cifradas en `docker/.env.sops` para el equipo).

Los **usuarios de prueba documentados en esta página viven todos en
el realm `custodiam`**, no en `master`.

## Roles del realm `custodiam`

| Rol | En el mundo real | Capacidad por defecto |
|---|---|---|
| `voluntario_practicas` | Voluntario nuevo en periodo de prueba | Operativo personal; sin lista de voluntarios |
| `voluntario` | Voluntario operativo | + listar voluntarios |
| `jefe_equipo` | Jefe de un equipo en servicio | + ver ficha de otros, crear servicios, convocar |
| `jefe_grupo` | Jefe de un grupo en servicio | Equivalente operativo de `jefe_equipo` |
| `jefe_seccion` | Jefe de sección | + asignar equipamiento personal |
| `jefe_unidad` | Jefe de unidad | + registrar vehículos |
| `subjefe_agrupacion` | Sub-jefe de la agrupación | + crear / editar / dar baja voluntarios |
| `jefe_agrupacion` | Jefe de la agrupación | + logs auditoría, exportar RGPD, gestión económica y documental |
| `coordinador` | Coordinador operativo | Equivale operativamente a `jefe_agrupacion` |
| `secretario` | Secretario administrativo | Subconjunto: gestión voluntarios + algunas tareas de sistema |
| `tesorero` | Tesorero | Solo lectura del dominio + gestión económica |
| `admin` | Admin **técnico** de la app | Solo permisos `sistema.*` — no toca dominio |

La matriz canónica vive en
[`custodiam-api/app/core/permissions.py`](https://github.com/custodiam/custodiam-api/blob/main/app/core/permissions.py)
y se espeja en
[`custodiam-app/lib/infrastructure/auth/permissions.dart`](https://github.com/custodiam/custodiam-app/blob/main/lib/infrastructure/auth/permissions.dart)
(decisión [ADR-013 RBAC lockstep](../adrs/index.md)).

## Matriz de capacidades por rol

Filas = capacidad funcional (no permiso atómico), columnas = los 6
roles más representativos para QA. Una celda ✅ significa "puede
hacerlo desde la UI"; ❌ que el `AppPermissionGate` esconde la
afordancia.

|  | voluntario | jefe_equipo | tesorero | secretario | coordinador | admin |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Ver mi perfil | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Editar mis datos de contacto | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Listar voluntarios | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Ver ficha de otro voluntario | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Crear voluntario | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Editar voluntario / cambiar rol | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Dar de baja voluntario | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Anonimizar voluntario (Art. 17 RGPD) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Crear servicio preventivo | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ |
| Crear servicio de emergencia | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Convocar a un servicio | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Fichar entrada/salida | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Gestión económica | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| Panel admin técnico | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Backups | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Logs de auditoría | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

!!! note "Coordinador vs admin — el contraste clave"

    El rol **`coordinador`** maneja **todo el dominio operativo** del
    día a día (voluntarios, servicios, fichaje, inventario,
    económico) pero no toca configuración técnica. El rol
    **`admin`** es lo opuesto: solo gestiona **infraestructura
    técnica** de la app (panel admin, backups, configuración) y
    **no tiene ningún permiso del dominio operativo**. Por eso un
    usuario con solo rol `admin` que abra `/mi-perfil` ve "Sin
    acceso" — es el comportamiento correcto, no un bug.

## Los 5 usuarios que crea el seed

| Usuario | Contraseña | Rol único | Fila en BD | Lo que cubre en la UI |
|---|---|---|---|---|
| `vol1` | `Vol1Pass!` | `voluntario` | sí | `/mi-perfil` con datos, `/voluntarios` (lista), "Sin acceso" en `/voluntarios/alta` y en la ficha de otro voluntario |
| `jefe1` | `Jefe1Pass!` | `jefe_equipo` | sí | Todo lo anterior + ficha `/voluntarios/{id}` en **read-only** (ver_ficha sí, editar no) + banner "Comando operativo" en `/home` |
| `coord1` | `Coord1Pass!` | `coordinador` | sí | Admin operativo completo: `/voluntarios/alta`, ficha en modo edición, cambio de rol, todos los iconos del home |
| `tesor1` | `Tesor1Pass!` | `tesorero` | sí | Caso edge: lista y ficha sí, editar y crear no — útil para validar el split read/write |
| `admin1` | `Admin1Pass!` | `admin` | **no** | Admin técnico puro: `/mi-perfil` debe mostrar `AppEmptyState` "Sin perfil" porque no hay fila en BD vinculada al `keycloak_id` |

### Por qué `admin1` no tiene fila en BD

Es intencional. El caso "usuario en Keycloak sin fila correspondiente
en `voluntarios`" tiene que poder probarse en QA porque también
ocurre en producción de forma natural:

- Un admin técnico que solo gestiona la app sin ser voluntario.
- Un voluntario anonimizado (Art. 17 RGPD): conserva cuenta KC para
  no romper FKs históricas, pero su `keycloak_id` se borra de la
  fila BD.

La pantalla `/mi-perfil` para `admin1` debe mostrar `AppEmptyState`
con el copy "No hay un voluntario en BD vinculado a tu usuario. Pide
al administrador que te dé de alta" en lugar de un error genérico.
Si ves un error genérico, hay un bug en el manejo del 404
(`VoluntariosFailure.notFound`).

## Cómo ejecutar el seed

### Pre-requisitos

1. **Stack levantado en modo dev** (con Keycloak expuesto en `localhost:8080`):

    ```bash
    cd custodiam-infra
    ./scripts/dev-up.sh
    ```

2. **Migraciones aplicadas** en la API:

    ```bash
    cd ../custodiam-api
    uv run alembic upgrade head
    ```

    El script verifica antes de empezar que la tabla `roles` tiene
    los 12 roles canónicos. Si no los tiene, aborta indicando que
    ejecutes las migraciones primero (la migración `f76feacaf399`
    siembra el catálogo).

3. **Variable `KEYCLOAK_PASSWORD`** disponible:
   - O bien exportada en la sesión actual.
   - O bien definida en `custodiam-infra/docker/.env`.

### Ejecución

```bash
cd custodiam-infra
./scripts/seed-test-users.sh
```

Salida esperada:

```
==> Checking that the 'roles' catalog has been seeded
    catálogo OK (12 roles disponibles)
==> Requesting admin token from http://localhost:8080
==> Ensuring KC user 'vol1' exists
    creating user
    resetting password (non-temporary)
    granting realm role 'voluntario'
==> Ensuring BD row for kc_id <uuid> (rol voluntario)
...
==> Done. 5 test users seeded.
```

### Idempotencia

El script es seguro de re-ejecutar:

- Si un usuario ya existe en Keycloak, se refresca su perfil y se
  resetea su contraseña (útil si alguien la cambió manualmente).
- Si ya hay fila en `voluntarios` para ese `keycloak_id`, no se
  inserta otra (`WHERE NOT EXISTS`).
- Si ya hay asignación de rol activa en `voluntario_roles` para esa
  pareja voluntario/rol, no se duplica.

### Borrar y empezar de cero

Si necesitas un estado completamente limpio:

```bash
# ⚠️ Destruye TODOS los datos: BD de la API, BD de Keycloak, etc.
cd custodiam-infra
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down -v
./scripts/dev-up.sh
cd ../custodiam-api && uv run alembic upgrade head
cd ../custodiam-infra && ./scripts/seed-test-users.sh
```

## Casos edge documentados que el seed no cubre

Estos escenarios requieren acciones manuales adicionales si quieres
verificarlos:

- **409 email duplicado al editar `/me`** — necesitas dos voluntarios
  con emails distintos. Crea un `vol2` adicional desde la UI con
  `coord1` o ejecuta el script manualmente con otro usuario.
- **502 KeycloakSyncFailed** — solo se dispara si el cliente
  `KeycloakAdminClient` del backend está habilitado
  (`KEYCLOAK_ADMIN_PASSWORD` definida) y Keycloak está caído. En el
  setup local con esa variable vacía, el cliente es no-op y nunca
  devuelve 502.
- **Historial de cambios del voluntario** — requiere la tabla
  `voluntario_evento` (audit log) que aún no existe en BD; está
  planificado en EN-02-04 para Sprint 5.

## Referencias

- Script de seed:
  [`custodiam-infra/scripts/seed-test-users.sh`](https://github.com/custodiam/custodiam-infra/blob/main/scripts/seed-test-users.sh)
- Matriz RBAC del backend:
  [`custodiam-api/app/core/permissions.py`](https://github.com/custodiam/custodiam-api/blob/main/app/core/permissions.py)
- Espejo de la matriz en el cliente:
  [`custodiam-app/lib/infrastructure/auth/permissions.dart`](https://github.com/custodiam/custodiam-app/blob/main/lib/infrastructure/auth/permissions.dart)
- Decisión arquitectónica que mantiene ambos sincronizados: [ADR-013
  RBAC lockstep](../adrs/index.md)
