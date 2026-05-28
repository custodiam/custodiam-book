---
title: Infraestructura completa
description: >-
  Cómo levantar el stack completo de Custodiam en local con Docker Compose
  desde custodiam-infra.
---

# Infraestructura completa — `custodiam-infra`

Orquestación del stack completo: **PostgreSQL + Keycloak + API + Web + ntfy**, con tres modos mutuamente excluyentes (dev / tunnel / prod) y `just` como interfaz preferida.

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-007 — GHCR](../adrs/adr-007-ghcr.md)**: las imágenes propias se publican en GitHub Container Registry y los modos `tunnel` y `prod` las consumen.
    - **[ADR-009 — Dos bases de datos](../adrs/adr-009-2-bds-separadas.md)** (`custodiam` para API, `custodiam_kc` para Keycloak) en una sola instancia PostgreSQL.
    - **[ADR-019 — Gestión de secretos con sops + age](../adrs/adr-019-sops-age.md)** — `docker/.env.sops` cifrado y versionado en el repo.
    - **[ADR-020 — Tres modos de despliegue](../adrs/adr-020-tres-modos-despliegue.md)** mutuamente excluyentes (dev / tunnel / prod) con guard de cross-mode.
    - **[ADR-006 — Nginx Alpine](../adrs/adr-006-nginx-alpine.md)**: contenedor `custodiam-web` sirve la PWA Flutter Web.
    - **[ADR-021 — SMTP transaccional con Resend](../adrs/adr-021-smtp-resend.md)** para los emails que Keycloak emite.

## Requisitos

- Docker Desktop 4.x ([instalación aquí](index.md#requisitos-previos-comunes))
- `just` 1.40+ (recomendado; los scripts shell siguen funcionando sin `just`)
- Clave age en `~/.config/sops/age/keys.txt` para descifrar el `.env.sops` del repo (opcional; existe fallback con `.env` plano)

## Clonar y arrancar

```bash
git clone https://github.com/custodiam/custodiam-infra.git
cd custodiam-infra

# Opción A — recomendada: usa el .env.sops cifrado del repo (requiere clave age)
# Los wrappers descifran al vuelo, sin acción manual.

# Opción B — fallback sin sops: copia la plantilla plana
cp docker/.env.example docker/.env
# Edita docker/.env con tus passwords (POSTGRES_PASSWORD, KEYCLOAK_PASSWORD, DOMAIN, ...)

# Levanta el stack de DESARROLLO local (puertos expuestos al host + hot reload)
just dev
# Equivalente sin just: ./scripts/dev-up.sh

# Siembra los usuarios de test del realm custodiam
just seed
# Equivalente: ./scripts/seed-test-users.sh
```

Tras `just dev`, los servicios quedan disponibles en:

| Servicio | URL local | Profile |
|---|---|---|
| API (FastAPI) | <http://localhost:8000> | (default) |
| Swagger UI | <http://localhost:8000/docs> | (default) |
| App Web (Flutter PWA) | <http://localhost:3000> | (default) |
| Keycloak (admin console) | <http://localhost:8080> | (default) |
| ntfy (web UI) | <http://localhost:8090> | (default) |
| PostgreSQL | `localhost:5432` | (default) |
| Mock OIDC server (testing) | <http://localhost:8888> | `test` (opt-in) |

## Tres modos de despliegue

```bash
just dev        # Desarrollo local: puertos expuestos, hot reload, sin túnel
just tunnel     # Staging vía Cloudflare Tunnel: puertos internos, KC_HOSTNAME=auth.${DOMAIN}
just prod       # Producción: tunnel + KC_HOSTNAME_STRICT=true + DEBUG=false
just down       # Bajar el stack (los volúmenes con datos sobreviven)
```

!!! tip "Política de cross-mode"
    Los tres modos son **mutuamente excluyentes** ([ADR-020](../adrs/adr-020-tres-modos-despliegue.md)). Cada wrapper hace un guard: si detecta que ya hay un modo distinto activo, lo aborta con un mensaje claro y pide ejecutar `just down` primero. Esto evita escenarios mixtos como "estoy en dev pero también tengo el túnel activo".

## Comandos esenciales

```bash
# Ver estado de servicios
just status
# o: docker compose ps

# Ver logs de un servicio
just logs-api
just logs-keycloak
just logs-tunnel

# Entrar a la BD desde dentro del contenedor
docker compose exec postgres psql -U custodiam custodiam      # BD de la API
docker compose exec postgres psql -U custodiam custodiam_kc   # BD de Keycloak

# Wipe destructivo de volúmenes (¡destruye BD!)
./scripts/down.sh --volumes
```

## Estructura del repo

```text
custodiam-infra/
├── docker/
│   ├── docker-compose.yml         # Base (postgres, keycloak, api, web, ntfy)
│   ├── docker-compose.dev.yml     # Override desarrollo (puertos + hot reload)
│   ├── docker-compose.prod.yml    # Override producción (tunnel + endurecimiento)
│   ├── .env.sops                  # Secretos cifrados con sops + age (versionado)
│   ├── .env.example               # Plantilla plana (fallback)
│   └── init-db.sh                 # Crea las 2 BDs al inicializar el volumen
├── keycloak/
│   └── realm-custodiam.json       # Export del realm con clientes preconfigurados
├── scripts/
│   ├── dev-up.sh                  # Wrapper modo desarrollo
│   ├── tunnel-up.sh               # Wrapper modo tunnel
│   ├── prod-up.sh                 # Wrapper modo producción
│   ├── down.sh                    # Wrapper de parada
│   └── seed-test-users.sh         # Siembra usuarios de test
└── justfile                       # Atajos a los scripts (interfaz recomendada)
```

## Gestión de secretos con sops + age

El archivo `docker/.env.sops` es la **fuente de verdad** para los secretos del entorno del equipo (passwords de PostgreSQL, Keycloak, tokens de Cloudflare Tunnel, etc.). Vive **cifrado** en el repo con [sops](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age); los destinatarios autorizados están listados en `.sops.yaml`.

Los wrappers (`dev-up.sh`, `tunnel-up.sh`) detectan `.env.sops` automáticamente, lo descifran a un tempfile con `trap` de limpieza y lo pasan a Docker Compose vía `--env-file`. Si solo existe `.env` plano, lo usan como fallback.

Operaciones canónicas:

```bash
# Rotar un secret
sops docker/.env.sops                # abre editor, edita el valor, guarda

# Añadir destinatario nuevo (otro dev)
# 1. Editar .sops.yaml y añadir la clave pública age
# 2. Re-cifrar reconociendo el nuevo destinatario
sops updatekeys docker/.env.sops
```

## Siguientes pasos

- **[Backend API](api.md)** — desarrollar fuera de Docker contra el PostgreSQL y Keycloak del stack.
- **[App Flutter](app.md)** — arrancar la app Flutter contra el backend del stack.
- **[Arquitectura](../arquitectura/index.md)** — diagrama del sistema, polyrepo, decisiones de infraestructura.
