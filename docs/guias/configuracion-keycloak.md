---
title: Configuración de Keycloak — guía técnica
description: >-
  Cómo configurar el realm Custodiam en Keycloak desde cero: política HTTPS,
  KC_HOSTNAME por entorno, SMTP transaccional con Resend, tiempos de sesión,
  políticas de contraseña, los 12 roles del realm, cliente confidencial
  custodiam-api, cliente público custodiam-app con PKCE S256 obligatorio,
  usuarios de prueba y exportación del realm.
---

# Configuración de Keycloak

Guía técnica completa de cómo configurar el Identity Provider del proyecto desde un Keycloak vacío. Cubre la creación del realm, las políticas de seguridad (HTTPS, contraseñas, sesiones), la integración SMTP transaccional, los doce roles funcionales, los dos clientes OIDC (`custodiam-api` confidencial y `custodiam-app` público con PKCE), los usuarios de prueba y la exportación del realm para reproducibilidad.

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-010 OAuth + PKCE + Keycloak + PyJWT](../adrs/adr-010-oauth-pkce-keycloak.md)**: dos clientes (`custodiam-api` confidencial + `custodiam-app` público con PKCE) y validación JWT local en el backend.
    - **[ADR-011 Deep links](../adrs/adr-011-deep-links.md)**: custom scheme `es.custodiam://callback` para OAuth + App Links HTTPS para emails.
    - **[ADR-013 RBAC lockstep](../adrs/adr-013-rbac-lockstep.md)**: matriz rol → permisos espejada en código backend y cliente.
    - **[ADR-021 SMTP Resend](../adrs/adr-021-smtp-resend.md)**: proveedor SMTP transaccional para los emails del realm.

## Prerrequisitos

- Stack Docker Compose levantado con el contenedor `keycloak` `healthy` ([Guía Docker Compose local](docker-compose-local.md)).
- Variable `DOMAIN` definida en el `.env` (o `.env.sops`) de `custodiam-infra`.
- Acceso al admin de Keycloak con las credenciales bootstrap del `.env` (`KEYCLOAK_ADMIN` + `KEYCLOAK_PASSWORD`).

!!! note "Sin túnel"
    Si trabajas en entorno 100 % local sin Cloudflare Tunnel, sustituye `https://auth.custodiam.es` por `http://localhost:8080` en toda la guía. Los pasos son idénticos; solo cambian las URLs.

## Conceptos previos

### Realm

Un realm en Keycloak es un "reino" aislado con sus propios usuarios, roles y configuración. Custodiam tiene su propio realm `custodiam` separado del realm `master`, que es el de administración interna de Keycloak:

```text
Keycloak
├── master (admin de Keycloak — NO tocar)
└── custodiam (realm del proyecto)
    ├── Clientes (custodiam-api, custodiam-app)
    ├── Roles (12 roles funcionales + admin)
    ├── Usuarios (voluntarios de la agrupación)
    └── Client scopes (mappers JWT)
```

### Client

Una aplicación que usa Keycloak para autenticar usuarios. Custodiam usa **dos clientes** ([ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)):

| Cliente | Tipo | Uso |
| --- | --- | --- |
| `custodiam-api` | **Confidencial** (con secret) | Backend FastAPI — valida tokens JWT, puede hacer introspection si llegase a ser necesario |
| `custodiam-app` | **Público** (sin secret) | Cliente Flutter Android + iOS + Web — usa Authorization Code + PKCE |

Un solo codebase Flutter equivale a un solo cliente. La misma app compila para Android, iOS y Web. Cada plataforma usa su propio `redirect_uri` dentro del mismo cliente `custodiam-app`.

### PKCE

Proof Key for Code Exchange ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) es la extensión de OAuth 2.0 para clientes públicos (apps móviles, SPAs) que no pueden guardar un `client_secret` de forma segura:

```text
Sin PKCE:
  App → Keycloak → código → App envía código → Token
  (cualquiera que intercepte el código puede usarlo)

Con PKCE:
  App genera code_verifier → envía hash code_challenge → Keycloak
  Keycloak devuelve código → App envía código + code_verifier → Keycloak verifica → Token
  (el código sin code_verifier es inútil)
```

En este proyecto el cliente `custodiam-app` tiene **PKCE S256 obligatorio**: Keycloak rechaza cualquier intercambio code → token que no incluya el `code_verifier` original.

### `KC_HOSTNAME`

El `docker-compose.yml` del proyecto configura Keycloak con:

```yaml
KC_HOSTNAME: auth.${DOMAIN:-localhost}
```

Con `DOMAIN=custodiam.es` en el `.env`, Keycloak emite tokens con:

```text
iss: https://auth.custodiam.es/realms/custodiam
```

Esto es **crítico** porque el backend FastAPI valida el `iss` del JWT contra este valor. Cualquier desalineamiento (por ejemplo, dejar `KC_HOSTNAME=localhost` cuando el cliente entra por `auth.custodiam.es`) rompe la validación silenciosamente.

## Paso 1 — Acceder al admin de Keycloak

**Con túnel activo (modo `tunnel` o `prod`):**

1. Abrir `https://auth.custodiam.es`.
2. Click en **Administration Console**.
3. Login con:
    - **Usuario**: `admin` (o el valor de `KEYCLOAK_ADMIN` en `.env`).
    - **Password**: el valor de `KEYCLOAK_PASSWORD` en `.env`.

**Sin túnel (modo `dev`):**

1. Abrir `http://localhost:8080`.
2. Mismas credenciales.

Si ves la página del realm `master` con el mensaje "Welcome to Keycloak", todo funciona.

## Paso 2 — Crear el realm `custodiam`

1. Esquina superior izquierda → click en **master** (desplegable de realm).
2. Click **Create Realm**.
3. Configurar:
    - **Realm name**: `custodiam`.
    - **Enabled**: `ON`.
4. Click **Create**.

Tras crear el realm, Keycloak te lleva automáticamente al realm `custodiam`. Verifica que en la esquina superior izquierda diga **custodiam**, no **master**.

## Paso 2.5 — Política HTTPS del realm (`sslRequired`)

Cuando el realm se crea desde cero, Keycloak deja el campo `sslRequired` en `"external"`. **El proyecto lo fija a `"none"`** y el `realm-custodiam.json` versionado ya lo refleja.

### Por qué `"none"` y no `"external"`

`"external"` debería permitir HTTP solo para clientes en IPs privadas (RFC 1918: `127.0.0.1`, `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`). En la práctica, Keycloak 26 **no identifica como privada la cadena de proxy `adb reverse → host → bridge Docker → container`**: un device físico Android que alcanza `localhost:8080` mediante `adb reverse tcp:8080 tcp:8080` recibe la pantalla "We are sorry... HTTPS required" al intentar autenticar. El modo `external` asume cabeceras `Forwarded` / `X-Forwarded-*` previsibles que `adb reverse` no genera.

`"none"` evita el rechazo. Y es **seguro en este proyecto** por dos motivos:

1. **HTTPS lo termina Cloudflare en el edge.** El único punto público (`auth.custodiam.es`, etc.) llega por **Cloudflare Tunnel**. El túnel hace TLS hasta el edge de Cloudflare y reenvía HTTP plano hacia el container Keycloak por la red Docker privada `custodiam-net`. El `sslRequired` del realm es redundante en ese flujo.
2. **Keycloak no se expone directo a Internet.** No hay regla de puerto en el router público que apunte a `keycloak:8080`. Solo el contenedor `cloudflared` puede alcanzarlo, y solo para los hostnames mapeados en el Zero Trust dashboard.

Referencia formal: [Keycloak — SSL modes](https://www.keycloak.org/docs/latest/server_admin/#_ssl_modes).

### Aplicar el cambio si el realm ya existe en BD

`--import-realm` es no-op cuando el realm ya existe en BD, así que cambiar el JSON y reiniciar Keycloak **no actualiza** un realm existente. Dos opciones:

#### Opción A — Apply en runtime vía Admin REST (recomendada)

No destruye datos. Aplica inmediato sin reiniciar el container.

```bash
# Obtener access token del admin del realm master
ACCESS=$(curl -s -X POST \
  "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -d "username=admin&password=${KEYCLOAK_PASSWORD}&grant_type=password&client_id=admin-cli" \
  | jq -r .access_token)

# Aplicar el cambio
curl -X PUT "http://localhost:8080/admin/realms/custodiam" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"sslRequired":"none"}'

# Verificación
curl -s "http://localhost:8080/admin/realms/custodiam" \
  -H "Authorization: Bearer $ACCESS" | jq .sslRequired
# → "none"
```

El cambio persiste en la BD `custodiam_kc` del volumen `postgres_data`.

#### Opción B — Wipe del volumen `postgres_data` (destructiva)

Pierde usuarios manuales. Solo apropiado en entornos limpios.

```bash
docker compose down
docker volume rm custodiam_postgres_data
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

Al levantar de cero, Keycloak importa `realm-custodiam.json` con `sslRequired: none` y arranca limpio. **Inconveniente**: los usuarios creados manualmente desaparecen — los partial exports no incluyen usuarios.

**Recomendación operativa**: usar la Opción A en máquinas de desarrollo activas. Reservar la Opción B para entornos limpios o cuando se cambien múltiples claims del realm a la vez.

## Paso 2.6 — `KC_HOSTNAME` por entorno (dev vs tunnel)

Tras corregir el `sslRequired` aparece un segundo síntoma cuando se prueba con device físico: el browser entra a `localhost:8080`, Keycloak responde, pero el form action y los redirects llevan al browser a `auth.custodiam.es`, donde la cookie de sesión no llega y aparece "We are sorry... Cookie not found". La causa: Keycloak emite URLs absolutas con `KC_HOSTNAME`.

### Diseño: override solo en `docker-compose.dev.yml`

El `docker-compose.yml` base mantiene:

```yaml
keycloak:
  environment:
    KC_HOSTNAME: auth.${DOMAIN:-localhost}
```

Con `DOMAIN=custodiam.es`, Keycloak emite URLs `auth.custodiam.es`. **Esto es correcto cuando el tráfico viene por el túnel**: Cloudflare resuelve `auth.custodiam.es` por DNS público, `cloudflared` reenvía a `keycloak:8080`, y como Keycloak emite URLs `auth.custodiam.es` el browser externo las puede seguir.

El `docker-compose.dev.yml` añade un override que solo aplica al modo dev local sin túnel:

```yaml
keycloak:
  command: start-dev --import-realm
  ports:
    - "8080:8080"
  environment:
    KC_HOSTNAME: "http://localhost:8080"
```

Con este override, en dev local Keycloak emite URLs absolutas con `localhost:8080` que el browser del device (vía `adb reverse`) puede seguir.

### Cuándo usar cada combinación

| Escenario | Composición | `KC_HOSTNAME` resultante |
| --- | --- | --- |
| Dev local con device USB (`adb reverse`) | `base + dev.yml` | `http://localhost:8080` |
| Tunnel Cloudflare (validación pre-piloto) | `base` con `--profile tunnel` | `auth.${DOMAIN}` |
| Producción | `base + prod.yml` con `--profile tunnel` | `auth.${DOMAIN}` |

### Conmutar entre modos

`KC_HOSTNAME` se evalúa cuando el container arranca. Cambiar de modo requiere **recrear el container** (no basta `restart`):

```bash
# Bajar el stack actual (preserva volúmenes)
./scripts/down.sh

# Levantar en el modo nuevo
./scripts/tunnel-up.sh   # o prod-up.sh / dev-up.sh
```

!!! warning "Nunca usar `down -v` para esto"
    Si el cambio de `sslRequired: none` se aplicó a runtime via Admin REST (opción A del paso 2.5) y vive en `postgres_data`, el cambio sigue vigente tras `down` + `up` porque el volumen no se borra. `down -v` lo destruiría.

### Verificación rápida del modo activo

```bash
# Qué KC_HOSTNAME tiene cargado el container
docker exec custodiam-auth printenv KC_HOSTNAME

# Discovery con el issuer correcto
curl http://localhost:8080/realms/custodiam/.well-known/openid-configuration
```

El campo `issuer` que devuelve el discovery debe coincidir con el hostname del modo en que arrancaste el stack.

## Paso 2.7 — Configurar SMTP en el realm

Keycloak emite emails transaccionales (`forgot-password`, `verify-email`, `executeActions`) pero no incluye servidor SMTP propio. Hay que enchufarle un MTA externo. La decisión del proyecto es **Resend** ([ADR-021](../adrs/adr-021-smtp-resend.md)).

### Prerrequisito SMTP

Antes de tocar el realm, tener disponibles:

- **Cuenta Resend** operativa con `custodiam.es` verificado en su panel (DKIM + MX en subdominio `send.custodiam.es` + SPF) según [`Resend — Domains introduction`](https://resend.com/docs/dashboard/domains/introduction).
- **API key** `re_...` activa con permission *Sending access* y restricción al dominio.
- **Credenciales cifradas** en `docker/.env.sops` ([ADR-019](../adrs/adr-019-sops-age.md)) con la convención:
    - `KEYCLOAK_SMTP_USERNAME=resend` (literal).
    - `KEYCLOAK_SMTP_PASSWORD=re_xxxxxxxxxxx` (la API key).
- **`AUTH OK`** en un smoke test directo contra `smtp.resend.com:587` desde tu máquina.

### Mapear las variables al contenedor Keycloak

En `custodiam-infra/docker/docker-compose.yml`, dentro de `services.keycloak.environment:` añadir:

```yaml
# SMTP credentials (Resend) consumed by realm-custodiam.json via ${env.VAR}
# placeholders. Values live encrypted in docker/.env.sops.
KEYCLOAK_SMTP_USERNAME: ${KEYCLOAK_SMTP_USERNAME}
KEYCLOAK_SMTP_PASSWORD: ${KEYCLOAK_SMTP_PASSWORD}
```

El mapeo es **provider-agnostic**: en Keycloak 26 la configuración SMTP del realm vive dentro del propio realm (BD `custodiam_kc`), no del servidor. Mapeamos las variables con su nombre original; el `realm-custodiam.json` las resuelve como `${env.KEYCLOAK_SMTP_USERNAME}` y `${env.KEYCLOAK_SMTP_PASSWORD}` al importar. Si en el futuro cambias Resend por otro proveedor, solo cambian los **valores** en `.env.sops` y el `host` en `realm-custodiam.json`.

### Configurar el bloque `smtpServer` en `realm-custodiam.json`

En `custodiam-infra/keycloak/realm-custodiam.json`, localizar la línea `"smtpServer": {},` y reemplazarla por:

```json
"smtpServer": {
  "host": "smtp.resend.com",
  "port": "587",
  "starttls": "true",
  "auth": "true",
  "from": "noreply@custodiam.es",
  "fromDisplayName": "Custodiam",
  "replyTo": "soporte@custodiam.es",
  "replyToDisplayName": "Soporte Custodiam",
  "user": "${env.KEYCLOAK_SMTP_USERNAME}",
  "password": "${env.KEYCLOAK_SMTP_PASSWORD}"
}
```

Verificar con `git diff keycloak/realm-custodiam.json`: **NO** debe aparecer la API key real, solo los placeholders `${env.KEYCLOAK_SMTP_*}`. Si aparece, deshacer y rehacer.

El único campo provider-specific en este bloque es `host: smtp.resend.com`. El resto (port, starttls, from, replyTo, displayName) lo elige el proyecto.

### Recargar el stack

Tres escenarios:

**Local con realm json modificado (placeholders vienen sin resolver)** — forzar reimport con wipe del volumen Postgres. Destructivo solo en local:

```bash
cd custodiam-infra
./scripts/down.sh
docker volume rm custodiam_postgres_data
./scripts/dev-up.sh
./scripts/seed-test-users.sh
```

**Local con cambio solo en credenciales SMTP** (no en realm json) — recrear solo el contenedor de Keycloak sin destruir BD:

```bash
cd custodiam-infra
TEMPFILE=$(mktemp)
SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -d \
  --input-type dotenv --output-type dotenv docker/.env.sops > "$TEMPFILE"
docker compose --env-file "$TEMPFILE" \
  -f docker/docker-compose.yml -f docker/docker-compose.dev.yml \
  up -d --force-recreate --no-deps keycloak
rm -f "$TEMPFILE"
```

**Producción con datos reales sin destruir BD** — actualizar `smtpServer` del realm vía Admin API (`PUT /admin/realms/custodiam`) con un body que solo contenga el bloque `smtpServer` actualizado. Keycloak hace merge sin tocar usuarios.

Tras los healthchecks verdes:

1. Abrir `http://localhost:8080/admin` → realm `custodiam` → **Realm settings** → **Email**.
2. Comprobar que los campos están rellenos (host `smtp.resend.com`, port `587`, etc.) y *Authentication* activado.
3. Botón **Test connection** (esquina superior) → introducir tu email real → "Email sent successfully" + email recibido = SMTP funcional.

### Verificar end-to-end "Recuperar contraseña"

Opción rápida vía Admin API, sin tocar la PWA:

```bash
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=${KEYCLOAK_PASSWORD}&grant_type=password&client_id=admin-cli" \
  | jq -r .access_token)

USER_ID=$(curl -s "http://localhost:8080/admin/realms/custodiam/users?username=voluntario" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

# Cambiar email del usuario a uno real y marcar verified
curl -s -X PUT "http://localhost:8080/admin/realms/custodiam/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"TU_EMAIL_REAL@dominio.com","emailVerified":true}'

# Disparar UPDATE_PASSWORD
curl -s -X PUT "http://localhost:8080/admin/realms/custodiam/users/$USER_ID/execute-actions-email" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '["UPDATE_PASSWORD"]' -w "HTTP:%{http_code}\n"
```

Esperado: `HTTP:204`. Logs de Keycloak (`docker logs custodiam-auth --since 30s | grep -iE "smtp|email|sent|failed"`) sin errores.

**Criterios de validación del email recibido**:

- **From**: `Custodiam <noreply@custodiam.es>`.
- **Reply-To**: `Soporte Custodiam <soporte@custodiam.es>`.
- **Cuerpo**: enlace `http://localhost:8080/realms/custodiam/login-actions/action-token?...`.
- **Crítico — enlace directo a Keycloak, sin wrap**. Si aparece un dominio de tracking intermedio (`sendibt3.com`, `r.bh.d.*`, etc.), revisar que el tracking esté en OFF en el dominio del panel del proveedor. Romper este requisito invalida los App Links / Universal Links del proyecto ([ADR-011](../adrs/adr-011-deep-links.md), [ADR-021](../adrs/adr-021-smtp-resend.md)).
- **Headers (`View source`)**: `received-spf: pass` desde IP AWS SES `eu-west-*.amazonses.com`. DKIM firmado con `resend._domainkey.custodiam.es`.

## Paso 3 — Tiempos de sesión

Antes de crear clientes, configurar los tiempos a nivel de realm.

1. Menú lateral → **Realm settings**.
2. Pestaña **Sessions**:

    | Campo | Valor | Motivo |
    | --- | --- | --- |
    | SSO Session Idle | 24 hours | Tiempo máximo sin actividad antes de expirar |
    | SSO Session Max | 24 hours | Tiempo máximo absoluto de la sesión SSO |

3. Pestaña **Tokens**:

    | Campo | Valor | Motivo |
    | --- | --- | --- |
    | Access Token Lifespan | 15 minutes | Ventana de revocación aceptable |
    | Client login timeout | 5 minutes | Tiempo para completar el flujo Authorization Code |

4. Click **Save**.

El access token se refresca automáticamente en el cliente Flutter con el `refresh_token`. 15 minutos es la ventana máxima en la que un token comprometido seguiría siendo válido. 24 horas para el refresh token significa que los voluntarios no tienen que hacer login más de una vez al día.

## Paso 4 — Política de contraseñas

1. Menú lateral → **Authentication**.
2. Pestaña **Policies** → **Password policy**.
3. Click **Add policy** y añadir una a una:

    | Política | Valor |
    | --- | --- |
    | Minimum Length | 8 |
    | Uppercase Characters | 1 |
    | Digits | 1 |

4. Click **Save**.

Estas políticas se aplican cuando un usuario crea o cambia su contraseña. Los usuarios de prueba creados con el script `seed-test-users.sh` también las cumplen.

## Paso 5 — Crear los 12 roles del realm

1. Asegúrate de estar en el realm **custodiam**.
2. Menú lateral → **Realm roles**.
3. Para cada rol: **Create role** → Nombre → Descripción → **Save**.

| Nombre del rol | Descripción |
| --- | --- |
| `voluntario_practicas` | Voluntario en periodo de prácticas |
| `voluntario` | Voluntario activo |
| `jefe_equipo` | Jefe de equipo |
| `jefe_grupo` | Jefe de grupo |
| `jefe_seccion` | Jefe de sección |
| `jefe_unidad` | Jefe de unidad |
| `secretario` | Secretario de la agrupación |
| `subjefe_agrupacion` | Sub-jefe de agrupación |
| `jefe_agrupacion` | Jefe de agrupación |
| `coordinador` | Máxima autoridad de la agrupación |
| `tesorero` | Rol administrativo (sin autoridad jerárquica) |
| `admin` | Administrador del sistema |

Los nombres son **exactamente** como aparecen en la tabla (minúsculas, guiones bajos). El backend y el cliente Flutter los reciben así en el JWT ([ADR-013](../adrs/adr-013-rbac-lockstep.md)).

## Paso 6 — Client scope compartido `custodiam-roles`

Antes de crear los clientes, se crea un client scope compartido que incluye los roles y los nombres en el JWT. Así los dos clientes (`custodiam-api` y `custodiam-app`) comparten la misma configuración de mappers sin duplicar.

### Crear el scope

1. Menú lateral → **Client scopes**.
2. Click **Create client scope**.
3. Configurar:
    - **Name**: `custodiam-roles`.
    - **Description**: `Incluye roles de realm y nombres en los tokens JWT de Custodiam`.
    - **Type**: Default.
    - **Protocol**: OpenID Connect.
    - **Include in token scope**: ON.
4. Click **Save**.

### Mapper de roles

1. Dentro de `custodiam-roles`, pestaña **Mappers**.
2. Click **Add mapper → By configuration**.
3. Seleccionar **User Realm Role**.
4. Configurar:

    | Campo | Valor |
    | --- | --- |
    | Name | `realm-roles` |
    | Multivalued | ON |
    | Token Claim Name | `roles` |
    | Claim JSON Type | String |
    | Add to ID token | ON |
    | Add to access token | ON |
    | Add to userinfo | ON |

5. Click **Save**.

### Mappers de nombre y apellido

Añadir `given_name` y `family_name` para que el cliente Flutter pueda mostrar el nombre del usuario sin llamar a `/userinfo` aparte.

1. **Add mapper → By configuration → User Attribute**.
2. Primer mapper:

    | Campo | Valor |
    | --- | --- |
    | Name | `given-name` |
    | User Attribute | `firstName` |
    | Token Claim Name | `given_name` |
    | Claim JSON Type | String |
    | Add to ID token | ON |
    | Add to access token | ON |

3. **Save**.
4. Repetir para apellido:

    | Campo | Valor |
    | --- | --- |
    | Name | `family-name` |
    | User Attribute | `lastName` |
    | Token Claim Name | `family_name` |
    | Claim JSON Type | String |
    | Add to ID token | ON |
    | Add to access token | ON |

5. **Save**.

Un scope compartido evita duplicar la configuración en cada cliente. Cualquier cambio se aplica automáticamente.

## Paso 7 — Cliente `custodiam-api` (confidencial)

### Crear el cliente

1. Menú lateral → **Clients** → **Create client**.

**Paso 1 — General Settings**:

| Campo | Valor |
| --- | --- |
| Client type | OpenID Connect |
| Client ID | `custodiam-api` |
| Name | Custodiam API |
| Description | Backend FastAPI — validación JWT |

Click **Next**.

**Paso 2 — Capability config**:

| Campo | Valor | Motivo |
| --- | --- | --- |
| Client authentication | **ON** | Cliente confidencial (tiene secret) |
| Authorization | OFF | No usamos Authorization Services |
| Standard flow | OFF | La API no inicia flujos OAuth, solo valida tokens |
| Direct access grants | OFF | No usamos Resource Owner Password Grant |
| Service accounts roles | ON | Permite a la API autenticarse como servicio (útil para Admin API) |

Click **Next**.

**Paso 3 — Login settings**: dejar todo vacío. La API no tiene `redirect_uri` porque no inicia flujos.

Click **Save**.

### Obtener el client secret

1. Dentro de `custodiam-api`, pestaña **Credentials**.
2. Copiar el **Client secret**.
3. Guardarlo en el gestor de secretos del equipo. En desarrollo se exporta como variable de entorno del backend.

### Asignar el client scope

1. Pestaña **Client scopes** → **Add client scope**.
2. Buscar **`custodiam-roles`** y añadirlo como **Default**.

## Paso 8 — Cliente `custodiam-app` (público + PKCE)

### Crear el cliente

1. **Clients** → **Create client**.

**Paso 1 — General Settings**:

| Campo | Valor |
| --- | --- |
| Client type | OpenID Connect |
| Client ID | `custodiam-app` |
| Name | Custodiam App |
| Description | App Flutter (Android + iOS + Web) — Authorization Code + PKCE |

Click **Next**.

**Paso 2 — Capability config**:

| Campo | Valor | Motivo |
| --- | --- | --- |
| Client authentication | **OFF** | Cliente público (app móvil, no puede guardar secret) |
| Authorization | OFF | No usamos Authorization Services |
| Standard flow | **ON** | Authorization Code + PKCE |
| Direct access grants | **OFF** | Resource Owner Password Grant desactivado; usar siempre PKCE |

Click **Next**.

**Paso 3 — Login settings**:

| Campo | Valor |
| --- | --- |
| Root URL | `https://app.custodiam.es` |
| Home URL | `https://app.custodiam.es` |
| Valid redirect URIs | ver tabla abajo |
| Valid post logout redirect URIs | ver tabla abajo |
| Web origins | `+` |

**Valid redirect URIs** (una por línea):

```text
es.custodiam://callback
http://localhost:3000/callback
https://app.custodiam.es/callback
```

**Valid post logout redirect URIs** (una por línea):

```text
es.custodiam://logout
http://localhost:3000
https://app.custodiam.es
```

Click **Save**.

Los tres `redirect_uri` cubren las tres familias documentadas en [ADR-011](../adrs/adr-011-deep-links.md):

- `es.custodiam://callback` → Android e iOS (custom URL scheme).
- `http://localhost:3000/callback` → Flutter Web en desarrollo local.
- `https://app.custodiam.es/callback` → Flutter Web en producción.

### PKCE S256 obligatorio

1. Dentro de `custodiam-app`, pestaña **Advanced**.
2. Sección **Advanced Settings** (desplegable al final).
3. Configurar:

    | Campo | Valor |
    | --- | --- |
    | Proof Key for Code Exchange Code Challenge Method | **S256** |

4. **Save**.

Con S256, Keycloak rechaza cualquier request de token que no incluya un `code_verifier` válido. Obliga a todos los clientes (Android, iOS, Web) a usar PKCE.

### Asignar el client scope

1. Pestaña **Client scopes** → **Add client scope**.
2. Buscar **`custodiam-roles`** y añadirlo como **Default**.

## Paso 9 — Usuarios de prueba

!!! tip "Atajo automatizado"
    Ejecutar `./scripts/seed-test-users.sh` desde `custodiam-infra` crea los usuarios de forma idempotente vía la Admin REST API, lee `KEYCLOAK_PASSWORD` de `docker/.env` y produce el mismo resultado que los pasos manuales de abajo. Es la opción que el equipo usa tras `down --volumes` o tras un primer `dev-up.sh` sobre un volumen `postgres_data` vacío. La página [Usuarios de prueba](../empezar/usuarios-prueba.md) documenta el conjunto exacto de cuentas que el seed crea.

Los pasos manuales siguen siendo válidos para depurar formularios o entender los campos uno a uno. Por simplicidad, esta sección muestra dos altas: `admin` y `voluntario`.

### Usuario `admin` (con rol técnico + coordinador)

1. Menú lateral → **Users** → **Add user**.
2. Configurar:

    | Campo | Valor |
    | --- | --- |
    | Username | `admin` |
    | Email | `admin@custodiam.es` |
    | Email verified | ON |
    | First name | `Admin` |
    | Last name | `Custodiam` |
    | Enabled | ON |

3. **Create**.
4. Pestaña **Credentials** → **Set password**:
    - Contraseña: `Admin1@test.com` (cumple la `passwordPolicy` del realm).
    - Temporary: OFF.
    - **Save** → confirmar.
5. Pestaña **Role mapping** → **Assign role**:
    - Buscar y seleccionar: `admin` y `coordinador`.
    - **Assign**.

`admin` es **técnico puro**: solo agrupa permisos `sistema.*` ([ADR-013](../adrs/adr-013-rbac-lockstep.md)). Por eso este usuario combina `admin` + `coordinador` para tener también capacidades operativas.

### Usuario `voluntario` (rol funcional básico)

1. **Users** → **Add user**.
2. Configurar:

    | Campo | Valor |
    | --- | --- |
    | Username | `voluntario` |
    | Email | `voluntario@custodiam.es` |
    | Email verified | ON |
    | First name | `Maria` |
    | Last name | `Garcia` |
    | Enabled | ON |

3. **Create**.
4. Pestaña **Credentials** → **Set password**: `Voluntario1@test.com`. Temporary OFF.
5. **Role mapping** → **Assign role** → seleccionar `voluntario`.

## Paso 10 — Exportar el realm

Exportar el realm permite recrearlo automáticamente en otro entorno (producción, CI, otra máquina) sin repetir todos los pasos manuales.

### Exportar desde la UI

1. Menú lateral → **Realm settings**.
2. Menú desplegable (esquina superior derecha) → **Partial export**.
3. Marcar:
    - Export groups and related permissions.
    - Export clients.
4. **Export**.
5. Guardar el JSON como `custodiam-infra/keycloak/realm-custodiam.json`.

!!! warning "Limitación: usuarios no se exportan"
    `Partial export` desde la UI **no incluye usuarios ni secrets de clientes**. Los usuarios de prueba hay que crearlos con `seed-test-users.sh` o manualmente. El secret del cliente confidencial se regenera al importar y hay que actualizarlo donde se consume.

### Importar en otro entorno

Para importar el realm en un Keycloak limpio, montar el JSON como volumen en el `docker-compose.yml`:

```yaml
keycloak:
  volumes:
    - ./keycloak/realm-custodiam.json:/opt/keycloak/data/import/realm-custodiam.json:ro
  command: start --import-realm   # o: start-dev --import-realm
```

!!! warning "`--import-realm` es idempotente"
    Solo importa si el realm no existe. Si ya existe, lo ignora. Para reimportar hay que borrar el realm primero (o el volumen Postgres con `down -v`).

## Verificación

### Comprobar el realm

```bash
curl -s https://auth.custodiam.es/realms/custodiam | jq
```

Debe mostrar `realm: "custodiam"`, `public_key`, `token-service: https://auth.custodiam.es/realms/custodiam/protocol/openid-connect`, etc.

**Verificar el `issuer`**: el `token-service` debe usar `https://auth.custodiam.es`, no `http://localhost:8080`. Si ves localhost, revisa que `DOMAIN=custodiam.es` esté en el `.env` y reinicia Keycloak.

### Obtener un token con Resource Owner Password (temporal)

!!! warning "Solo temporal"
    Este método solo funciona si se habilita temporalmente *Direct access grants* en `custodiam-app`. Es para verificación rápida. **Desactivar después.**

1. **Clients → `custodiam-app` → Settings → Authentication flow → Direct access grants ON → Save**.
2. Pedir token:

    ```bash
    TOKEN_RESPONSE=$(curl -s -X POST \
      "https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "client_id=custodiam-app" \
      -d "username=admin" \
      -d "password=Admin1@test.com" \
      -d "grant_type=password")

    echo "$TOKEN_RESPONSE" | jq
    ```

3. Decodificar el `access_token` y verificar claims:

    ```bash
    echo "$TOKEN_RESPONSE" | jq -r .access_token \
      | cut -d. -f2 | base64 -d 2>/dev/null | jq
    ```

    Buscar:

    | Claim | Valor esperado | Si falla... |
    | --- | --- | --- |
    | `iss` | `https://auth.custodiam.es/realms/custodiam` | Revisa `KC_HOSTNAME` y `DOMAIN` en `.env` |
    | `roles` | Array con `admin`, `coordinador` | Revisa el mapper `realm-roles` |
    | `given_name` | `Admin` | Revisa el mapper `given-name` |
    | `family_name` | `Custodiam` | Revisa el mapper `family-name` |
    | `email` | `admin@custodiam.es` | Verifica datos del usuario |

4. **Desactivar** *Direct access grants* después.

### JWKS endpoint

```bash
curl -s https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/certs | jq
```

Devuelve una o más claves públicas RSA. Es el endpoint que el backend FastAPI consulta vía `PyJWKClient` para descargar las claves públicas y validar firmas de JWT **sin llamar a Keycloak en cada request**.

### OpenID Configuration (discovery)

```bash
curl -s https://auth.custodiam.es/realms/custodiam/.well-known/openid-configuration | jq
```

Verificar que todos los endpoints usen `https://auth.custodiam.es` y no `localhost`.

### Login por navegador

1. Abrir `https://auth.custodiam.es/realms/custodiam/account`.
2. Login con `admin` / `Admin1@test.com`.
3. Deberías ver la consola de cuenta del usuario.

## Checklist final

- [ ] Realm `custodiam` creado y activo.
- [ ] `sslRequired: none` aplicado.
- [ ] `KC_HOSTNAME` correcto para el modo activo.
- [ ] SMTP de Resend operativo (test connection OK + email recibido sin link wrap).
- [ ] Tiempos de sesión configurados (access 15 min, SSO 24 h).
- [ ] Política de contraseñas activa (8+ chars, 1 mayúscula, 1 dígito).
- [ ] 12 roles funcionales creados.
- [ ] Client scope `custodiam-roles` con 3 mappers (roles, given_name, family_name).
- [ ] Cliente `custodiam-api` confidencial con secret guardado.
- [ ] Cliente `custodiam-app` público con PKCE S256 obligatorio y 3 redirect URIs.
- [ ] Ambos clientes tienen `custodiam-roles` como scope Default.
- [ ] Direct access grants **desactivado** en `custodiam-app`.
- [ ] Usuarios de prueba creados.
- [ ] JWT contiene `iss`, `sub`, `email`, `roles`, `given_name`, `family_name`.
- [ ] Issuer del JWT usa `https://auth.custodiam.es` (no `localhost`).
- [ ] Realm exportado a `keycloak/realm-custodiam.json` y versionado.

## Endpoints OIDC del realm

Referencia rápida (sustituir `https://auth.custodiam.es` por `http://localhost:8080` en dev local):

| Endpoint | URL |
| --- | --- |
| Authorization | `https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/auth` |
| Token | `https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/token` |
| Userinfo | `https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/userinfo` |
| Logout | `https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/logout` |
| JWKS | `https://auth.custodiam.es/realms/custodiam/protocol/openid-connect/certs` |
| Discovery | `https://auth.custodiam.es/realms/custodiam/.well-known/openid-configuration` |
| Account Console | `https://auth.custodiam.es/realms/custodiam/account` |

## Problemas comunes

### `Invalid redirect URI`

- Verifica que la URI esté **exactamente** en *Valid redirect URIs* del cliente.
- Recuerda: `es.custodiam://callback` (no `custodiam://callback`).
- Para desarrollo web local: `http://localhost:3000/callback`.

### `Client not found`

- Verifica que el Client ID sea exacto (`custodiam-app`, no `custodiam-web`).
- Asegúrate de estar en el realm correcto (`custodiam`, no `master`).

### Token no incluye roles

1. Verifica que el scope `custodiam-roles` esté asignado al cliente como **Default**.
2. Verifica que el mapper `realm-roles` exista dentro de `custodiam-roles`.
3. Verifica que el usuario tenga roles asignados en su **Role mapping**.

### Issuer dice `localhost` en vez de `auth.custodiam.es`

1. Verifica que `DOMAIN=custodiam.es` esté en el `.env`.
2. Reinicia Keycloak: `docker compose restart keycloak`.
3. Verifica `KC_HOSTNAME` en `docker-compose.yml`: debe ser `auth.${DOMAIN:-localhost}`.

### `PKCE verification failed`

- El cliente tiene PKCE S256 obligatorio. El cliente debe enviar `code_challenge` en la autorización y `code_verifier` en el intercambio de código.
- El paquete `oauth2` de Dart lo hace automáticamente para clientes públicos.
- Si pruebas con `curl`, necesitas generar manualmente `code_verifier` y `code_challenge`.

### Pantalla "We are sorry... HTTPS required"

- Aplicar `sslRequired: none` siguiendo el [Paso 2.5](#paso-25-politica-https-del-realm-sslrequired).

### Pantalla "Cookie not found" desde device físico

- Verificar `KC_HOSTNAME` para el modo en que arrancaste el stack ([Paso 2.6](#paso-26-kc_hostname-por-entorno-dev-vs-tunnel)).
- Recrear el container de Keycloak tras cambiar `KC_HOSTNAME` (no basta `restart`).

### Emails con enlaces wrap por dominio de tracking

- Comprobar el toggle de *Link click tracking* en el dominio del panel del proveedor SMTP — debe estar **OFF**.
- Resend permite desactivarlo por dominio; este paso es lo que invalida la alternativa Brevo para el caso de uso ([ADR-021](../adrs/adr-021-smtp-resend.md)).

### Keycloak no arranca

- Tarda ~60-90 s la primera vez (crea ~148 changesets de BD).
- Logs: `docker compose logs keycloak | tail -20`.
- Causa común: password de BD incorrecto en `.env`.

## Referencias

- **[Keycloak — Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/)** — referencia oficial.
- **[Keycloak — Configuring the hostname](https://www.keycloak.org/server/hostname)** — `KC_HOSTNAME` y su comportamiento.
- **[Keycloak — SSL modes](https://www.keycloak.org/docs/latest/server_admin/#_ssl_modes)** — política HTTPS del realm.
- **[Resend — Send with SMTP](https://resend.com/docs/send-with-smtp)** y **[Domains introduction](https://resend.com/docs/dashboard/domains/introduction)** — proveedor SMTP del proyecto.
- **[RFC 7636 — Proof Key for Code Exchange](https://datatracker.ietf.org/doc/html/rfc7636)** — fundamento de PKCE.
- **[ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)**, **[ADR-011](../adrs/adr-011-deep-links.md)**, **[ADR-013](../adrs/adr-013-rbac-lockstep.md)** y **[ADR-021](../adrs/adr-021-smtp-resend.md)** — decisiones arquitectónicas que esta guía implementa.
- **[Usuarios de prueba](../empezar/usuarios-prueba.md)** — credenciales y matriz de capacidades del seed.
