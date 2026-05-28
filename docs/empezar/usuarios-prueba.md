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

## Protocolo de prueba

Esta sección propone un recorrido para validar visualmente que el
RBAC funciona en cada rol. Pensado para QA del equipo y para
terceros que quieran evaluar la app sin tener que cruzar varios
documentos.

### Recorrido rápido (≈15 min)

El orden importa: empieza por la cuenta con menos privilegios y
sube. Así cada cuenta nueva añade afordancias visibles respecto a la
anterior y es trivial detectar regresiones del estilo "permiso
filtrado donde no debería".

1. **`Voluntario1@test.com`** — voluntario operativo básico.
    - Login, llegada a `/home`.
    - `/mi-perfil` debe mostrar los datos del propio voluntario y
      permitir editar los campos de contacto.
    - `/voluntarios` debe mostrar la lista (lectura permitida).
    - Intentar abrir una ficha ajena → "Sin acceso".
    - Intentar abrir `/voluntarios/alta` por URL directa → "Sin
      acceso".

2. **`Jefeequipo1@test.com`** — comando operativo.
    - Home muestra el banner "Comando operativo".
    - La ficha de otro voluntario abre en modo lectura (sin botón
      Editar).
    - Acceso al alta de servicios preventivos disponible.
    - Sigue sin poder dar de alta voluntarios.

3. **`Coordinador1@test.com`** — admin operativo completo.
    - Home con todos los iconos del dominio visibles.
    - `/voluntarios/alta` accesible y funcional.
    - La ficha ajena abre en modo edición; el selector de rol está
      activo.
    - La acción "Anonimizar" (Art. 17 RGPD) está disponible en la
      ficha.

4. **`Tesorero1@test.com`** — split read/write (caso edge).
    - Ve la lista de voluntarios y abre la ficha ajena.
    - Los botones de crear, editar y dar de baja están **ocultos** en
      todo el dominio operativo.
    - El acceso a gestión económica está visible.
    - Útil para confirmar que el `AppPermissionGate` no se "rompe" en
      perfiles solo-lectura.

5. **`Admin1@test.com`** — admin técnico puro.
    - Panel admin técnico accesible (configuración, backups, logs).
    - `/mi-perfil` y `/voluntarios` muestran "Sin acceso": `admin`
      no es un rol del dominio operativo.
    - Sirve para validar el contraste con `coordinador` documentado
      más arriba.

6. **`Reviewstore1@test.com`** — cobertura total.
    - Última cuenta del recorrido. Tiene la unión de todos los
      permisos operativos y técnicos.
    - Si esta cuenta NO ve algo que debería ver, hay un bug de RBAC
      en la matriz o en el `AppPermissionGate`.

### Smoke test por feature

Si solo quieres validar una feature concreta sin recorrer todo, esta
tabla mapea cada flujo crítico a la cuenta mínima necesaria:

| Feature | Cuenta sugerida | Qué validar |
|---|---|---|
| Login OIDC (web) | Cualquiera | Redirección a Keycloak, callback a `/callback`, tokens persistidos |
| Login OIDC (móvil) | Cualquiera | El custom scheme dispara el browser embed, callback OK |
| Ver mi perfil | `Voluntario1` | `/mi-perfil` muestra los datos del propio voluntario |
| Listar voluntarios | `Voluntario1` | `/voluntarios` muestra lista, **sin** botón "Nuevo" |
| Ficha ajena en lectura | `Jefeequipo1` | Abre `/voluntarios/{id}`, **sin** botón Editar |
| Crear voluntario | `Coordinador1` | `/voluntarios/alta` accesible, alta crea usuario en Keycloak + fila en BD |
| Editar voluntario | `Coordinador1` | La ficha abre en modo edición y persiste cambios |
| Cambiar rol | `Coordinador1` | Selector de rol en la ficha, asignación persistente |
| Dar de baja (soft delete) | `Coordinador1` | `deleted_at` se setea; el voluntario desaparece de la lista |
| Anonimizar (Art. 17 RGPD) | `Coordinador1` o `Admin1` | PII pisada con valores neutros, `keycloak_id` se conserva |
| Crear servicio preventivo | `Jefeequipo1` | Formulario "Nuevo servicio", tipo preventivo, convocatoria |
| Panel admin técnico | `Admin1` | `/admin/*` accesible; dominio operativo NO accesible |
| Logs de auditoría | `Coordinador1` o `Admin1` | Tabla de eventos con búsqueda por usuario y fecha |
| Cobertura total | `Reviewstore1` | Cualquier afordancia debe estar visible |

### Cómo reportar un fallo de RBAC

Si una cuenta ve algo que **no** debería, o **no** ve algo que sí
debería, abre issue en
[`custodiam-app`](https://github.com/custodiam/custodiam-app/issues)
si es el UI quien filtra mal, o en
[`custodiam-api`](https://github.com/custodiam/custodiam-api/issues)
si es el backend quien devuelve 200 cuando debería devolver 403.
Adjunta:

- Cuenta con la que reprodujiste (`<Rol>1@test.com`).
- Ruta o pantalla.
- Afordancia esperada vs la observada.
- Captura de pantalla si aplica.

La matriz canónica de permisos por rol vive en el código (los dos
archivos enlazados arriba en "Roles del realm `custodiam`");
cualquier divergencia entre lo que el código dice y lo que el UI
ofrece es un bug del UI o del backend, no de la matriz.

## Los 7 usuarios que crea el seed

Todas las cuentas siguen el patrón triple-igual **username = password = email = `<Rol>1@test.com`**. Es deliberadamente débil porque las credenciales aparecen en esta página pública y, en el caso de `Reviewstore1@test.com`, en la submission de Google Play y Apple App Store. No es una postura sobre seguridad real de producción: estas cuentas son **sacrificables** y solo se usan para QA del equipo, evaluación interna y review de las stores. Las cuentas humanas de una agrupación que adopte Custodiam se crean por el flujo normal de alta de voluntario, no por este seed.

El patrón concreto cumple la `passwordPolicy` del realm `custodiam` (`length(8) and upperCase(1) and digits(1)`) sin necesidad de relajarla: la mayúscula inicial cubre `upperCase(1)`, el dígito `1` cubre `digits(1)` y la longitud del string sobra para `length(8)`. Usar el mismo string en los tres campos (username, password, email) reduce errores de copia/pega en QA y deja a los reviewers de las stores con un dato único que recordar por cuenta.

| Usuario (= contraseña = email) | Roles en Keycloak | Fila en BD | Lo que cubre en la UI |
|---|---|---|---|
| `Voluntario1@test.com` | `voluntario` | sí · asignación `voluntario` | `/mi-perfil` con datos, `/voluntarios` (lista), "Sin acceso" en `/voluntarios/alta` y en la ficha de otro voluntario |
| `Jefeequipo1@test.com` | `jefe_equipo` | sí · asignación `jefe_equipo` | Todo lo anterior + ficha `/voluntarios/{id}` en **read-only** (ver_ficha sí, editar no) + banner "Comando operativo" en `/home` |
| `Coordinador1@test.com` | `coordinador` | sí · asignación `coordinador` | Admin operativo completo: `/voluntarios/alta`, ficha en modo edición, cambio de rol, todos los iconos del home |
| `Tesorero1@test.com` | `tesorero` | sí · asignación `tesorero` | Caso edge: lista y ficha sí, editar y crear no — útil para validar el split read/write |
| `Admin1@test.com` | `admin` | sí · asignación `admin` | Flujos del admin técnico (permisos `sistema.*`): panel admin, configuración, logs, backups, exportar RGPD |
| `Reviewstore1@test.com` | `coordinador` + `admin` | sí · asignación `coordinador` | **Cuenta para revisión de Google Play y Apple App Store.** Cobertura total: union de todos los permisos operativos del coordinador con los `sistema.*` del admin |
| `Superadmin1@test.com` | `coordinador` + `admin` | sí · asignación `coordinador` | Cuenta de emergencia del equipo: misma cobertura que `Reviewstore1@test.com` pero distinta audiencia, para administración interna del piloto |

### Por qué dos cuentas con `coordinador` + `admin`

`Reviewstore1@test.com` y `Superadmin1@test.com` tienen capacidades idénticas pero distinta **audiencia**. Esa separación permite rotar credenciales o eliminar una sin afectar a la otra:

- **`Reviewstore1@test.com`** es visible a los revisores externos de Google Play y Apple. Su existencia y su password aparecen en la submission ("Sign-in Info" de App Store Connect y "Acceso a la aplicación" de Google Play Console). Si en algún momento los reviewers reportan algo o cambiamos a otro mecanismo de review (test track, internal testing con cuentas reales), `Reviewstore1@test.com` se borra de Keycloak sin tocar nada más.
- **`Superadmin1@test.com`** es para uso interno del equipo durante la fase piloto. Permite que un miembro del equipo pueda entrar a administrar el sistema en cualquier momento sin depender de las credenciales que se le pasaron a los reviewers.

### Por qué `admin` SÍ tiene fila en BD

A diferencia de versiones anteriores de este seed, ahora el usuario `admin` tiene su fila en `voluntarios` con la asignación de rol `admin`. El rol `admin` está en el catálogo canónico de los 12 roles del sistema (sembrado por la migración Alembic `f76feacaf399`), así que es coherente que el usuario `admin` lo tenga materializado en BD igual que cualquier otro rol.

El caso edge "usuario Keycloak sin fila vinculada en BD" sigue cubierto **por código** (`AppEmptyState` con copy "Pide al administrador que te dé de alta") y **por tests E2E** del mock OIDC server. No necesita un usuario seed específico para reproducirlo: cualquier persona que se autentique en Keycloak sin que un admin la haya dado de alta en BD primero cae en ese estado de forma natural, exactamente como en producción.

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
==> Ensuring KC user 'Voluntario1@test.com' exists
    creating user
    resetting password (non-temporary)
    granting realm role 'voluntario'
==> Ensuring BD row for kc_id <uuid> (rol voluntario)
...
==> Done. 7 test users seeded.
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
  con emails distintos. Crea un `Voluntario2@test.com` adicional desde
  la UI con `Coordinador1@test.com` o ejecuta el script manualmente con
  otro usuario.
- **502 KeycloakSyncFailed** — solo se dispara si el cliente
  `KeycloakAdminClient` del backend está habilitado
  (`KEYCLOAK_ADMIN_PASSWORD` definida) y Keycloak está caído. En el
  setup local con esa variable vacía, el cliente es no-op y nunca
  devuelve 502.
- **Historial de cambios del voluntario** — requiere la tabla
  `voluntario_evento` (audit log) que aún no existe en BD; está
  planificado para una iteración posterior del módulo de Voluntarios.

## Referencias

- Script de seed:
  [`custodiam-infra/scripts/seed-test-users.sh`](https://github.com/custodiam/custodiam-infra/blob/main/scripts/seed-test-users.sh)
- Matriz RBAC del backend:
  [`custodiam-api/app/core/permissions.py`](https://github.com/custodiam/custodiam-api/blob/main/app/core/permissions.py)
- Espejo de la matriz en el cliente:
  [`custodiam-app/lib/infrastructure/auth/permissions.dart`](https://github.com/custodiam/custodiam-app/blob/main/lib/infrastructure/auth/permissions.dart)
- Decisión arquitectónica que mantiene ambos sincronizados: [ADR-013
  RBAC lockstep](../adrs/index.md)
