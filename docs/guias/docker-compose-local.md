---
title: Docker Compose local — guía técnica
description: >-
  Cómo levantar el stack completo de Custodiam (PostgreSQL + Keycloak + API
  + Web + ntfy) con Docker Compose en cualquiera de los tres modos
  (dev / tunnel / prod). Pasos completos, decisiones explicadas, comandos
  útiles y troubleshooting.
---

# Docker Compose local

Guía técnica completa de cómo levantar el stack de Custodiam con Docker Compose. Cubre los tres modos de despliegue mutuamente excluyentes, el setup de archivos desde cero, los pasos hasta tener el stack operativo en local, los comandos de mantenimiento habituales y los problemas comunes con sus soluciones.

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-007 GHCR](../adrs/adr-007-ghcr.md)**: las imágenes propias se publican en GitHub Container Registry y los modos `tunnel`/`prod` las consumen.
    - **[ADR-009 Dos BDs separadas](../adrs/adr-009-2-bds-separadas.md)** dentro de una única instancia PostgreSQL.
    - **[ADR-019 sops + age](../adrs/adr-019-sops-age.md)** para gestión de secretos (alternativa al `.env` plano).
    - **[ADR-020 Tres modos de despliegue](../adrs/adr-020-tres-modos-despliegue.md)** mutuamente excluyentes con guard de cross-mode.

## Prerrequisitos

- **Repositorios clonados**: los tres repos de código (`custodiam-app`, `custodiam-api`, `custodiam-infra`) clonados en una carpeta padre común. Recomendado el layout descrito en [Empezar](../empezar/index.md).
- **Docker Desktop** o Docker Engine + Docker Compose instalados.
- **Dominio configurado** en Cloudflare (opcional para desarrollo local; necesario para modo `tunnel` y `prod`).

Verificación rápida:

```bash
docker --version
# Docker version 27.x.x o superior

docker compose version
# Docker Compose version v2.x.x o superior
```

### Estructura de workspace

Los tres repos viven hermanos:

```text
custodiam-workspace/
├── custodiam-app/       # Flutter (Android + iOS + Web)
├── custodiam-api/       # FastAPI + SQLModel + PostgreSQL
└── custodiam-infra/     # Docker Compose (donde se trabaja en esta guía)
```

## Estructura de archivos

Todos los archivos de la orquestación viven en `custodiam-infra/`:

```text
custodiam-infra/
├── docker/
│   ├── docker-compose.yml          # Compose principal (base)
│   ├── docker-compose.dev.yml      # Override desarrollo (hot reload, puertos expuestos)
│   ├── docker-compose.prod.yml     # Override producción (endurecimiento)
│   ├── init-db.sh                  # Crea BD de Keycloak en primer arranque
│   ├── .env.example                # Plantilla pública de variables
│   ├── .env                        # Variables locales (gitignored, fallback)
│   └── .env.sops                   # Variables cifradas (versionado, ADR-019)
├── keycloak/
│   └── realm-custodiam.json        # Config exportada del realm
├── nginx/
│   └── default.conf                # Config Nginx para la PWA Flutter
└── scripts/
    ├── dev-up.sh                   # Wrapper modo dev
    ├── tunnel-up.sh                # Wrapper modo tunnel
    ├── prod-up.sh                  # Wrapper modo prod
    ├── down.sh                     # Bajar el stack
    └── seed-test-users.sh          # Sembrar usuarios de prueba en Keycloak
```

## Paso 1 — Variables de entorno

El archivo `docker/.env` contiene las variables que `docker compose` lee al levantar el stack. Existen dos formas de mantenerlo:

1. **`docker/.env` en `.gitignore`** (fallback): copia de `.env.example` con los valores reales. Cada miembro del equipo mantiene su copia.
2. **`docker/.env.sops` cifrado y versionado** ([ADR-019](../adrs/adr-019-sops-age.md)): fuente de verdad del equipo, descifrada al vuelo por los wrappers.

Para empezar con `.env` plano:

```bash
cd custodiam-infra
cp docker/.env.example docker/.env
```

Edita `docker/.env` con valores reales:

```bash title=".env (no subir a Git)"
# ============ BASE DE DATOS ============
POSTGRES_USER=custodiam
POSTGRES_PASSWORD=<password seguro generado>
POSTGRES_DB=custodiam
KEYCLOAK_DB=custodiam_kc

# ============ KEYCLOAK ADMIN ============
KEYCLOAK_ADMIN=admin
KEYCLOAK_PASSWORD=<password seguro>

# ============ CLOUDFLARE TUNNEL (solo modo tunnel / prod) ============
# CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoixxxxxxxxxx...

# ============ KEYCLOAK SMTP (transaccional) ============
# Ver ADR-021 — provider: Resend
# KEYCLOAK_SMTP_USERNAME=resend
# KEYCLOAK_SMTP_PASSWORD=re_xxxxxxxxxxx

# ============ FIREBASE (opcional MVP) ============
# FIREBASE_CREDENTIALS={"type":"service_account",...}

# ============ N8N (opcional, profile full) ============
# N8N_USER=admin
# N8N_PASSWORD=<password n8n>

# ============ DOMINIO ============
DOMAIN=localhost
# Para producción: DOMAIN=custodiam.es

# ============ VERSIONES DE IMÁGENES (modos tunnel/prod) ============
API_VERSION=latest
APP_VERSION=latest
```

### Generar passwords seguros

```bash
# Unix / macOS
openssl rand -base64 32

# Windows con git bash
openssl rand -base64 32
```

## Paso 2 — `docker-compose.yml` (base)

El compose base define los servicios productivos del stack. Los overrides añaden o modifican según el modo.

```yaml title="docker/docker-compose.yml"
name: custodiam

services:
  # ============ BASE DE DATOS ============
  # Una instancia PostgreSQL con DOS bases de datos lógicas (ADR-009):
  #   - custodiam     → API (FastAPI + Alembic)
  #   - custodiam_kc  → Keycloak (sus ~70 tablas internas)
  postgres:
    image: postgres:15-alpine
    container_name: custodiam-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-custodiam}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-custodiam}
      KEYCLOAK_DB: ${KEYCLOAK_DB:-custodiam_kc}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-custodiam}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks: [custodiam-net]

  # ============ AUTENTICACIÓN ============
  keycloak:
    image: quay.io/keycloak/keycloak:26.0
    container_name: custodiam-auth
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: ${KEYCLOAK_ADMIN:-admin}
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_PASSWORD}
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/${KEYCLOAK_DB:-custodiam_kc}
      KC_DB_USERNAME: ${POSTGRES_USER:-custodiam}
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
      KC_PROXY_HEADERS: xforwarded
      KC_HOSTNAME: auth.${DOMAIN:-localhost}
      KC_HOSTNAME_STRICT: "false"
      KC_HTTP_ENABLED: "true"
      KC_HEALTH_ENABLED: "true"
    volumes:
      - ../keycloak/realm-custodiam.json:/opt/keycloak/data/import/realm-custodiam.json:ro
    command: start --import-realm
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/8080'"]
      interval: 10s
      timeout: 5s
      retries: 15
      start_period: 90s
    restart: unless-stopped
    networks: [custodiam-net]

  # ============ BACKEND API ============
  api:
    image: ghcr.io/custodiam/custodiam-api:${API_VERSION:-latest}
    container_name: custodiam-api
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-custodiam}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-custodiam}
      KEYCLOAK_URL: http://keycloak:8080
      KEYCLOAK_PUBLIC_URL: https://auth.${DOMAIN:-localhost}
      KEYCLOAK_REALM: custodiam
      NTFY_URL: http://ntfy:80
      FIREBASE_CREDENTIALS: ${FIREBASE_CREDENTIALS:-}
    depends_on:
      postgres: { condition: service_healthy }
      keycloak: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks: [custodiam-net]

  # ============ PWA WEB ============
  web:
    image: ghcr.io/custodiam/custodiam-app:${APP_VERSION:-latest}
    container_name: custodiam-web
    depends_on: [api]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks: [custodiam-net]

  # ============ NOTIFICACIONES ============
  ntfy:
    image: binwiederhier/ntfy:latest
    container_name: custodiam-ntfy
    command: serve
    environment:
      NTFY_BASE_URL: https://ntfy.${DOMAIN:-localhost}
      NTFY_BEHIND_PROXY: "true"
    volumes:
      - ntfy_data:/var/lib/ntfy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks: [custodiam-net]

  # ============ AUTOMATIZACIONES (POST-MVP, profile full) ============
  n8n:
    image: n8nio/n8n:latest
    container_name: custodiam-n8n
    environment:
      N8N_HOST: n8n.${DOMAIN:-localhost}
      N8N_PROTOCOL: https
      WEBHOOK_URL: https://n8n.${DOMAIN:-localhost}
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: ${N8N_USER:-admin}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD}
    volumes: [n8n_data:/home/node/.n8n]
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks: [custodiam-net]
    profiles: [full]

  # ============ TÚNEL CLOUDFLARE (profile tunnel) ============
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: custodiam-tunnel
    command: tunnel run
    environment:
      TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on: [api, keycloak, web, ntfy]
    restart: unless-stopped
    networks: [custodiam-net]
    profiles: [tunnel]

volumes:
  postgres_data:
  ntfy_data:
  n8n_data:

networks:
  custodiam-net:
    driver: bridge
```

## Paso 3 — `init-db.sh`

Crea la segunda base de datos (Keycloak) en el primer arranque del volumen. El mecanismo `docker-entrypoint-initdb.d/` de la imagen oficial de PostgreSQL ejecuta cualquier script `.sh` o `.sql` montado en esa carpeta **solo si el volumen de datos está vacío**.

```bash title="docker/init-db.sh"
#!/bin/bash
set -e

echo "Creando base de datos para Keycloak: ${KEYCLOAK_DB:-custodiam_kc}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ${KEYCLOAK_DB:-custodiam_kc}
        OWNER = ${POSTGRES_USER:-custodiam}
        ENCODING = 'UTF8'
        LC_COLLATE = 'en_US.utf8'
        LC_CTYPE = 'en_US.utf8';

    COMMENT ON DATABASE ${KEYCLOAK_DB:-custodiam_kc}
        IS 'Keycloak internal tables - do NOT use for application data';
EOSQL

echo "Base de datos ${KEYCLOAK_DB:-custodiam_kc} creada correctamente"
```

Hacer ejecutable:

```bash
chmod +x docker/init-db.sh
```

## Paso 4 — Override `docker-compose.dev.yml`

Modo desarrollo local: puertos expuestos al host, hot reload de la API, build local de las imágenes (sin tirar de GHCR).

```yaml title="docker/docker-compose.dev.yml"
services:
  postgres:
    ports: ["5432:5432"]

  keycloak:
    command: start-dev --import-realm
    ports: ["8080:8080"]

  ntfy:
    ports: ["8090:80"]

  # API: build local en vez de imagen GHCR
  api:
    build:
      context: ../../custodiam-api
      dockerfile: Dockerfile
    image: custodiam-api:dev
    ports: ["8000:8000"]
    volumes:
      - ../../custodiam-api/app:/app/app:ro
    environment:
      DEBUG: "true"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Web: build local en vez de imagen GHCR
  web:
    build:
      context: ../../custodiam-app
      dockerfile: Dockerfile
    image: custodiam-app:dev
    ports: ["3000:80"]
```

## Paso 5 — Override `docker-compose.prod.yml`

Modo producción: endurece Keycloak (`KC_HOSTNAME_STRICT=true`) y la API (`DEBUG=false`). `cloudflared` se levanta vía `--profile tunnel` igual que en modo `tunnel` (el wrapper `prod-up.sh` añade el flag por dentro).

```yaml title="docker/docker-compose.prod.yml"
services:
  keycloak:
    environment:
      KC_HOSTNAME_STRICT: "true"

  api:
    environment:
      DEBUG: "false"
```

## Paso 6 — Configuración Nginx de la PWA

El contenedor `custodiam-web` ([ADR-006](../adrs/adr-006-nginx-alpine.md)) sirve la PWA Flutter como bundle estático con cache busting diferenciado.

```nginx title="nginx/default.conf"
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Compresión gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types
        text/plain text/css text/xml text/javascript
        application/javascript application/json application/xml application/xml+rss;

    # SPA: cualquier ruta no encontrada vuelve a index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache largo para assets con hash en el nombre
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # No cachear los bootstrap files (no se hashean)
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
```

## Paso 7 — Levantar el stack

Tres scripts simétricos exponen un entry point por modo. Todos comparten `_lib-env.sh` para descifrar `.env.sops` con sops + age si está presente (sino cae al `.env` plano).

```bash
cd custodiam-infra

./scripts/dev-up.sh        # desarrollo local
./scripts/tunnel-up.sh     # staging vía Cloudflare Tunnel
./scripts/prod-up.sh       # producción (incluye --profile tunnel internamente)
./scripts/down.sh          # bajar (volúmenes sobreviven)
```

Tras `dev-up.sh`, los servicios quedan disponibles en:

| URL | Servicio |
| --- | --- |
| `http://localhost:8000` | API FastAPI |
| `http://localhost:8000/docs` | Swagger UI interactivo |
| `http://localhost:8080` | Keycloak Admin Console |
| `http://localhost:3000` | PWA Flutter Web |
| `http://localhost:8090` | ntfy Web UI |
| `localhost:5432` | PostgreSQL |

Ver estado y logs:

```bash
cd docker
docker compose ps                # estado de servicios
docker compose logs -f           # todos los logs en streaming
docker compose logs -f api       # solo un servicio
docker compose logs -f keycloak
```

## Tres modos de despliegue

El stack se levanta en **exactamente uno** de tres modos. Análisis completo en [ADR-020](../adrs/adr-020-tres-modos-despliegue.md). Resumen:

| | **dev** | **tunnel** | **prod** |
| --- | --- | --- | --- |
| **Script** | `./scripts/dev-up.sh` | `./scripts/tunnel-up.sh` | `./scripts/prod-up.sh` |
| **Composición** | `base + dev.yml` | `base` solo | `base + prod.yml` |
| **Profile extra** | — | `--profile tunnel` | `--profile tunnel` (interno) |
| **`KC_HOSTNAME`** | `http://localhost:8080` | `auth.${DOMAIN}` | `auth.${DOMAIN}` |
| **`KC_HOSTNAME_STRICT`** | `false` | `false` | **`true`** |
| **`DEBUG` (API)** | `true` | (sin definir) | **`false`** |
| **Imágenes `api`/`web`** | build local (`:dev`) | GHCR `:latest` | GHCR `:latest` |
| **Hot reload API** | sí (`uvicorn --reload`) | no | no |
| **Puertos al host** | 5432, 8080, 8000, 3000, 8090 | ninguno | ninguno |
| **`cloudflared`** | no | sí | sí |
| **Caso de uso** | iterar código local, tests, `adb reverse` | probar deep links / Universal Links / emails desde móvil real contra `auth.custodiam.es` | despliegue en el PC anfitrión del piloto |

### Guard de cross-mode

Los tres scripts **se niegan a arrancar si ya hay contenedores del proyecto `custodiam` activos**. Esto es deliberado: levantar `tunnel-up.sh` sobre un stack que sigue arriba en modo `dev` no recrea Keycloak (el `KC_HOSTNAME` aplicado sigue siendo el de `dev`) y el OIDC silenciosamente queda roto a través del túnel. El guard fuerza el patrón correcto:

```bash
./scripts/down.sh           # baja el stack actual (volúmenes sobreviven)
./scripts/tunnel-up.sh      # arranca en el modo nuevo
```

Mensaje de error literal cuando se intenta saltar de modo sin pasar por `down`:

```text
ERROR: Custodiam containers are already running:
  - custodiam-web (custodiam-app:dev)
  - custodiam-api (custodiam-api:dev)
  ...

tunnel-up.sh applies a different compose composition (no dev override,
KC_HOSTNAME=auth.${DOMAIN}, --profile tunnel) and cannot reuse a stack
that was started in dev or prod mode. Bring it down first:

  ./scripts/down.sh
```

### Pre-checks compartidos

Tanto `tunnel-up.sh` como `prod-up.sh` aplican dos verificaciones antes de invocar a `docker compose`:

1. **`CLOUDFLARE_TUNNEL_TOKEN` no vacío** en el env file descifrado por `_lib-env.sh`. Sin él, `cloudflared` arranca pero falla al registrar el túnel en silencio.
2. **`docker compose pull` explícito** antes de `up -d`. Cualquier problema de red, registry o auth aflora aquí en vez de mezclarse con la salida de `up -d`.

## Estrategia de imágenes Docker

El `docker-compose.yml` orquesta servicios de **tres procedencias distintas**. La distinción importa porque cada nivel se actualiza y se versiona de forma muy diferente.

| Nivel | Imágenes | Procedencia | ¿Se publica? |
| --- | --- | --- | --- |
| **A — Terceros oficiales** | `postgres:15-alpine`, `quay.io/keycloak/keycloak:26.0`, `binwiederhier/ntfy:latest`, `n8nio/n8n:latest`, `cloudflare/cloudflared:latest` | Imágenes oficiales mantenidas por sus proveedores | No — se tira directamente del registro del proveedor, pineadas por tag |
| **B — Propias del proyecto** | `ghcr.io/custodiam/custodiam-app` (PWA + Nginx) y `ghcr.io/custodiam/custodiam-api` (FastAPI + uv) | Repos `custodiam-app` y `custodiam-api`, cada uno con su `Dockerfile` | Sí — el CI las construye y publica en GHCR ([ADR-007](../adrs/adr-007-ghcr.md)) |
| **C — Orquestación** | n/a — solo `docker-compose.yml` + scripts shell | Repo `custodiam-infra` | No — código que se clona y se ejecuta con `docker compose` |

El total de imágenes propias del proyecto es **dos**. No hay sobrecarga de mantenimiento ni "imagen-por-cosa".

### Por qué imágenes propias y no compilar en el PC anfitrión

Cinco razones operativas sostienen la decisión:

1. **Toolchain limpio en el PC anfitrión.** El PC que sirve `app.custodiam.es` y `api.custodiam.es` solo necesita Docker Engine. No hay Flutter SDK, no hay Python ni sus dependencias, no hay Node ni paquetes nativos. Reduce la superficie de ataque y elimina la categoría "funciona en mi máquina pero no en la del cliente".
2. **Reproducibilidad criptográfica.** Cada imagen tiene un digest SHA-256 inmutable. Tirar del digest concreto garantiza que el binario ejecutado en producción es bit-a-bit el que el CI probó.
3. **Rollback trivial.** Si una versión nueva rompe producción, `docker compose pull <imagen-anterior>` + restart devuelve el sistema al estado previo en segundos.
4. **Promoción dev → tunnel → prod natural.** La misma imagen puede correr en cualquier modo cambiando únicamente el `.env`.
5. **GHCR es gratuito para repos públicos.** El proyecto es AGPL-3.0 y el coste incremental sobre lo que ya se paga por GitHub es cero. Sin rate limits de pulls anónimos como Docker Hub.

### Estado del CI

| Repo | Workflow | Publica | Notas |
| --- | --- | --- | --- |
| `custodiam-app` | `ci.yml` | `ghcr.io/custodiam/custodiam-app:latest` | Job `test` (analyze + test + build web) + `build-docker` (push a `main`) |
| `custodiam-api` | `ci.yml` | `ghcr.io/custodiam/custodiam-api:latest` | Job `test` (ruff + pytest contra Postgres real) + `build-docker` (push a `main`) |
| `custodiam-infra` | — | n/a | Orquestación; no produce imagen propia |

### Permiso `packages: write`

El job `build-docker` necesita escribir el paquete en `ghcr.io/<org>/<repo>` con el `GITHUB_TOKEN` automático. La configuración por defecto del repo (`default_workflow_permissions: read`) impide crear el paquete por primera vez con el error `denied: installation not allowed to Create organization package`.

Solución limpia: conceder `packages: write` **únicamente al job** (no al repo ni a la organización), añadiendo este bloque dentro de `jobs.build-docker:`:

```yaml
permissions:
  contents: read
  packages: write
```

Mantiene el principio de mínimo privilegio.

### Visibilidad pública de las imágenes

Las imágenes `ghcr.io/custodiam/custodiam-{app,api}` están publicadas como **públicas**, alineado con la licencia AGPL-3.0. Consecuencia operativa: `docker pull` desde el PC anfitrión, scripts y cualquier consumidor anónimo funciona sin `docker login ghcr.io`.

Verificación:

```bash
docker pull ghcr.io/custodiam/custodiam-app:latest
docker pull ghcr.io/custodiam/custodiam-api:latest
# Esperado: "Status: Downloaded newer image"
# Si devuelve "denied: requested access to the resource is denied",
# el paquete está privado — cambiar visibilidad desde la UI o por API:
#   gh api -X PATCH 'orgs/custodiam/packages/container/<nombre>' -f visibility=public
```

!!! warning "No usar `curl -sI` para verificar visibilidad"
    Docker Registry v2 responde `401` a peticiones anónimas sin token aunque la imagen sea pública (cabecera `WWW-Authenticate: Bearer realm=...` que invita al "bearer challenge dance" para obtener un token anónimo). `curl -sI` daría falso negativo. Verificar siempre con `docker pull` real.

### Estrategia de tags futura

La estrategia operativa propuesta usa **cuatro tipos de tag complementarios**:

| Tag | Cuándo se asigna | Propósito | Sobrescribe |
| --- | --- | --- | --- |
| `:sha-<7-chars>` | En cada push a `develop` o `main`. Siempre. | Reproducibilidad criptográfica; base del rollback. | No (cada SHA es único) |
| `:develop` | Push a `develop` | Canal pre-release / staging | Sí (puntero rolling) |
| `:latest` | Push a `main` | Producción (default cuando `APP_VERSION` no se fija) | Sí (puntero rolling) |
| `:vX.Y.Z` | Git tag semver en commit de `main` | Releases formales | No (tags semver inmutables) |

Implementación recomendada con `docker/metadata-action` en GitHub Actions:

```yaml
- name: Extract metadata
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: ghcr.io/${{ github.repository }}
    tags: |
      type=raw,value=latest,enable={{is_default_branch}}
      type=raw,value=develop,enable=${{ github.ref == 'refs/heads/develop' }}
      type=sha,prefix=sha-,format=short
      type=semver,pattern={{version}}
```

### Procedimiento de rollback por SHA

Si `:latest` rompe producción, el rollback no requiere recompilación ni `git revert`:

```bash
# 1. Identificar el SHA del último build estable
gh api '/orgs/custodiam/packages/container/custodiam-app/versions' \
  | jq '.[] | {tags: .metadata.container.tags, created_at}'

# 2. Fijar APP_VERSION al SHA bueno en el .env del PC anfitrión:
APP_VERSION=sha-abc1234

# 3. Pull + restart del servicio web:
docker compose pull web
docker compose up -d web

# Tiempo total: ~30 segundos.
```

Esto es muy superior a "revertir el commit, esperar al CI, volver a desplegar" en términos de Mean Time To Recovery.

## Comandos útiles

```bash
cd custodiam-infra/docker

# ============ Básicos ============
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d   # dev
docker compose -f docker-compose.yml --profile tunnel up -d            # tunnel
docker compose down                                                    # parar (volúmenes sobreviven)
docker compose down -v                                                 # parar + borrar volúmenes (destructivo)

# ============ Logs ============
docker compose logs -f
docker compose logs -f api
docker compose logs -f keycloak

# ============ Mantenimiento ============
docker compose restart api
docker compose build api
docker compose up -d api
docker compose exec api bash
docker compose exec postgres psql -U custodiam

# ============ Base de datos ============
# BD de la API
docker compose exec postgres psql -U custodiam -d custodiam

# BD de Keycloak
docker compose exec postgres psql -U custodiam -d custodiam_kc

# Listar todas las BDs
docker compose exec postgres psql -U custodiam -c "\l"

# Backup
docker compose exec postgres pg_dump -U custodiam custodiam > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U custodiam -d custodiam
```

## Verificación final

- [ ] Archivo `.env` (o `.env.sops`) con passwords seguros.
- [ ] Servicios levantados (`docker compose ps`).
- [ ] Las dos BDs creadas: `docker compose exec postgres psql -U custodiam -c "\l"` muestra `custodiam` y `custodiam_kc`.
- [ ] API responde en `http://localhost:8000/health`.
- [ ] Swagger accesible en `http://localhost:8000/docs`.
- [ ] Keycloak accesible en `http://localhost:8080`.
- [ ] PWA Flutter accesible en `http://localhost:3000`.
- [ ] ntfy accesible en `http://localhost:8090`.

## Problemas comunes

### `Cannot connect to Docker daemon`

```bash
# Linux: añadir usuario al grupo docker
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar
```

### Keycloak no arranca

- Verifica que PostgreSQL esté `healthy` primero.
- Keycloak tarda ~60-90 s en arrancar la primera vez (crea ~148 changesets de BD).
- Logs: `docker compose logs keycloak`.
- Causa común: password de BD incorrecto en `.env`.
- El endpoint `/health/ready` está en el **puerto 9000** (management), no en 8080:

    ```bash
    docker compose exec keycloak bash -c \
      'exec 3<>/dev/tcp/localhost/9000 && \
       echo -e "GET /health/ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3 && \
       head -20 <&3'
    ```

### `Port already in use`

```bash
# Linux/macOS
sudo lsof -i :8080
sudo kill -9 <PID>

# Windows
netstat -ano | findstr :8080
taskkill /F /PID <PID>
```

O cambiar el puerto del host en `docker-compose.dev.yml`.

### Alembic detecta tablas de Keycloak como "removed"

Si `alembic revision --autogenerate` muestra `Detected removed table` para tablas de Keycloak (`admin_event_entity`, `realm`, `client`, ...), significa que la API y Keycloak están usando la **misma** BD lógica — no las dos separadas ([ADR-009](../adrs/adr-009-2-bds-separadas.md)).

```bash
# Verificar que hay 2 BDs separadas
docker compose exec postgres psql -U custodiam -c "\l" | grep custodiam
# Debe mostrar: custodiam (API) y custodiam_kc (Keycloak)

# Si solo hay una BD, recrear el volumen:
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

!!! warning "`down -v` borra volúmenes"
    En desarrollo es seguro. En producción hacer `pg_dump` antes.

### Conflicto del puerto 5432 (PostgreSQL local en Windows)

Si hay un PostgreSQL instalado localmente en Windows, compite por el puerto 5432 con Docker. Síntoma: la conexión falla con `password authentication failed`.

```bash
# Verificar
netstat -ano | findstr :5432
# Si hay dos PIDs diferentes, hay conflicto

# Parar el servicio local
net stop postgresql-x64-18
```

### Hyper-V reserva el puerto 3000 en Windows

En algunos sistemas Windows con Hyper-V activo, el puerto 3000 queda reservado por Windows aunque ningún proceso lo use. El contenedor `custodiam-web` falla al arrancar con `bind: An attempt was made to access a socket in a way forbidden by its access permissions`.

```powershell
# Verificar puertos reservados por Windows
netsh interface ipv4 show excludedportrange protocol=tcp

# Solución (requiere admin): desactivar el rango excluido
netsh int ipv4 set dynamic tcp start=49152 num=16384
# Reiniciar Windows
```

Como mitigación temporal, cambiar el mapeo del host: `ports: ["3001:80"]` en `docker-compose.dev.yml`.

### API no conecta con Keycloak

- Verifica que Keycloak esté `healthy`.
- Dentro de Docker, la URL para servicio-a-servicio es `http://keycloak:8080` (nombre del servicio en la red interna), no `http://localhost:8080`.
- Comprobar `KEYCLOAK_URL` en variables de entorno del servicio `api`.

### Build de la PWA Flutter falla

```bash
cd ../custodiam-app
flutter clean
flutter pub get
flutter build web

cd ../custodiam-infra/docker
docker compose build web
```

## Referencias

- **[Docker Compose Documentation](https://docs.docker.com/compose/)** — referencia oficial.
- **[FastAPI in Containers](https://fastapi.tiangolo.com/deployment/docker/)** — guía oficial.
- **[Keycloak — Running in a container](https://www.keycloak.org/server/containers)** — variables de entorno y configuración.
- **[GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)** — Docker Registry de GitHub.
- **[ADR-007 GHCR](../adrs/adr-007-ghcr.md)**, **[ADR-009 Dos BDs separadas](../adrs/adr-009-2-bds-separadas.md)**, **[ADR-019 sops + age](../adrs/adr-019-sops-age.md)**, **[ADR-020 Tres modos de despliegue](../adrs/adr-020-tres-modos-despliegue.md)** — decisiones arquitectónicas que esta guía implementa.
