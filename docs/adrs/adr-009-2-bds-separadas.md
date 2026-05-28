---
title: ADR-009 — Dos bases de datos PostgreSQL separadas
description: >-
  El contenedor `postgres` aloja dos bases de datos lógicas distintas:
  `custodiam` (datos de negocio, gestionada por la API + Alembic) y
  `custodiam_kc` (interna de Keycloak). Separar las dos elimina el conflicto
  de Alembic --autogenerate con las ~70 tablas internas de Keycloak.
---

# ADR-009 — Dos bases de datos PostgreSQL separadas

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 11 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El stack del proyecto incluye dos servicios que necesitan persistencia relacional:

- **`custodiam-api`** — backend FastAPI con SQLModel + Alembic ([ADR-002](adr-002-sqlmodel.md), [ADR-003](adr-003-alembic.md)) — gestiona las entidades de negocio (voluntarios, servicios, acreditaciones, fichajes, inventario, etc.).
- **Keycloak** — Identity Provider que gestiona el realm `custodiam`, usuarios, roles, sesiones, tokens emitidos. Internamente Keycloak crea **~70 tablas** propias para su modelo (realms, clients, users, credentials, federated_identity, refresh tokens, sessions, etc.).

Una sola instancia de PostgreSQL puede alojar las dos cargas. Hay que decidir si las dos comparten una sola base de datos lógica o si cada una vive en su propia base de datos lógica dentro del mismo cluster.

## Decisión

**Dos bases de datos lógicas separadas dentro del mismo contenedor `postgres`:**

```text
postgres (contenedor)
├── BD: custodiam       ← gestionada por custodiam-api + Alembic
└── BD: custodiam_kc    ← gestionada internamente por Keycloak
```

El init-script `init-db.sh` montado en `/docker-entrypoint-initdb.d/` del contenedor crea ambas bases al primer arranque del volumen. Las cadenas de conexión son distintas:

- API: `postgresql+psycopg://custodiam:<password>@postgres:5432/custodiam`
- Keycloak: `jdbc:postgresql://postgres:5432/custodiam_kc`

Ambas bases comparten el cluster (mismo proceso, mismo volumen `postgres_data`, mismo backup), pero son **independientes a nivel de schema, tablas y usuarios SQL**.

## Justificación

1. **Elimina el conflicto de Alembic `--autogenerate`.** Si la API y Keycloak compartieran base de datos, `alembic revision --autogenerate` detectaría las ~70 tablas de Keycloak como "tablas no declaradas en el modelo Python" e intentaría incluirlas en la migración como `DROP TABLE`. Cualquier desarrollador que no se diese cuenta y aplicara la migración con `alembic upgrade head` destruiría el realm completo de Keycloak. Separar las bases de datos hace que `--autogenerate` solo vea las tablas de la API.

2. **Separación de responsabilidades.** El esquema de Keycloak es **opaco** para el equipo: cambia con cada versión mayor de Keycloak, no se documenta a nivel de tablas, y solo Keycloak mismo debe operarlo. Ponerlo junto a las tablas de negocio mezcla dos modelos mentales distintos en un solo namespace SQL.

3. **Backup y restore granulares.** Es perfectamente posible hacer `pg_dump` solo de la base `custodiam` (datos de negocio) sin arrastrar el estado de sesiones de Keycloak, que es información volátil y puede regenerarse. Esto facilita compartir snapshots de desarrollo / pruebas sin filtrar datos de sesión potencialmente sensibles.

4. **Diferentes patrones de mantenimiento.** La base `custodiam` evoluciona con migraciones Alembic versionadas en el repo. La base `custodiam_kc` la migra el propio Keycloak en cada arranque con su versión mayor. Tener una sola base mezclaría dos lifecycles de schema management que el sistema no debe coordinar.

5. **Costo cero.** PostgreSQL aloja N bases de datos en una sola instancia sin sobrecosto significativo de recursos. No se necesita un segundo contenedor de Postgres. La diferencia frente a "una sola BD compartida" es operativa, no de infraestructura.

## Alternativas evaluadas y descartadas

### A. Una sola base de datos compartida con prefijos en nombres de tablas

API en tablas `app_voluntarios`, `app_servicios`, etc.; Keycloak en sus tablas habituales sin prefijo.

- **Pros**: una sola conexión, una sola URL en `.env`.
- **Contras**: requiere reconfigurar todas las queries de la API para usar prefijos; **no resuelve el problema fundamental** de `--autogenerate` (Alembic sigue detectando las tablas de Keycloak como ajenas); ensucia el namespace para una ganancia mínima.
- **Descartado por**: no resuelve el conflicto principal.

### B. Una sola base de datos compartida con schemas PostgreSQL separados

API en schema `app.*`, Keycloak en schema `auth.*`.

- **Pros**: separación lógica explícita, una sola BD.
- **Contras**: Keycloak no soporta correr en un schema distinto al `public` por defecto (se puede forzar pero requiere configuración avanzada y se han reportado bugs); Alembic sigue necesitando configuración explícita para limitar `--autogenerate` a un schema. La complejidad operativa supera el beneficio.
- **Descartado por**: complejidad innecesaria.

### C. Dos contenedores PostgreSQL independientes

Uno para la API, otro para Keycloak.

- **Pros**: aislamiento absoluto.
- **Contras**: duplica recursos (dos procesos Postgres, dos volúmenes, dos pares de healthchecks); duplica la complejidad de backups y de monitorización; sin beneficio observable sobre dos BDs en el mismo cluster.
- **Descartado por**: sobreingeniería para el aislamiento que dos BDs lógicas ya proporcionan.

## Implicaciones operativas

- **`init-db.sh` montado en `docker-entrypoint-initdb.d/`**: el script crea las dos bases en el primer arranque del contenedor (cuando el volumen `postgres_data` está vacío). En arranques posteriores no se ejecuta, así que ambas BDs persisten.
- **Credenciales separadas en el `.env.sops`**: dos pares user/password distintos (`CUSTODIAM_DB_PASSWORD` para la API, `KC_DB_PASSWORD` para Keycloak). Permite rotarlas independientemente.
- **Backups**: `pg_dumpall` con el contenedor parado captura ambas bases. Para snapshots selectivos: `pg_dump -U custodiam -d custodiam > custodiam.sql` desde fuera del contenedor.
- **Migración de versión mayor de Keycloak**: Keycloak migra automáticamente sus tablas internas al arrancar con una versión nueva (es operación idempotente). No interfiere con `custodiam-api` porque las dos bases son independientes.
- **`docker-compose.yml`** declara ambas variables de entorno en el servicio Keycloak (`KC_DB_URL=jdbc:postgresql://postgres:5432/custodiam_kc`) y en el servicio API (`DATABASE_URL=postgresql+psycopg://custodiam:...@postgres:5432/custodiam`). Sin acoplamiento entre ellas.

## Referencias

- **[PostgreSQL — Database Roles and Authentication](https://www.postgresql.org/docs/current/user-manag.html)** — modelo de usuarios, roles y permisos sobre BDs lógicas separadas.
- **[Keycloak — Configuring the database](https://www.keycloak.org/server/db)** — variables de entorno aceptadas (`KC_DB`, `KC_DB_URL`, etc.).
- **[ADR-002 SQLModel](adr-002-sqlmodel.md)** y **[ADR-003 Alembic](adr-003-alembic.md)** — capa que toca la BD `custodiam`.
- **[ADR-008 psycopg3](adr-008-psycopg3.md)** — driver con el que la API conecta.
