---
title: ADR-005 — sqflite como base de datos local de la app
description: >-
  El cliente Flutter usa `sqflite` para persistencia local en SQLite cuando una
  feature necesita modo offline o caché. Plugin oficial maduro de la comunidad
  Flutter; alternativas modernas (drift, isar) no compensan el coste de
  adopción.
---

# ADR-005 — sqflite como base de datos local de la app

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 28 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Algunas features del cliente Flutter necesitan persistencia local en el dispositivo:

- **Fichaje offline**: si el voluntario está sin cobertura al fichar (situación habitual en zonas rurales o eventos masivos), el fichaje debe persistir localmente y sincronizar al volver online.
- **Caché de listas grandes**: el panel de voluntarios o el inventario pueden mostrar listados largos que no es razonable rebajar del servidor en cada navegación.
- **Cola de operaciones offline**: acciones que el usuario realiza sin conexión (apuntarse a un servicio, marcar un fichaje, modificar un dato) se encolan localmente para sincronizar después.

PostgreSQL del backend es la fuente de verdad. La BD local es **caché y buffer** del cliente: nada que viva solo localmente debe ser irrecuperable.

## Decisión

**[`sqflite`](https://pub.dev/packages/sqflite)** (Plugin Flutter sobre SQLite nativo) como base de datos local para Android e iOS. En Flutter Web, las features que necesiten persistencia local usarán IndexedDB con un wrapper específico o ninguna persistencia (sesión efímera), porque `sqflite` no soporta Web. El alcance de la persistencia web en MVP es deliberadamente mínimo.

## Justificación

1. **SQLite nativo, no reimplementación.** `sqflite` invoca SQLite directamente del SO (la versión empaquetada con Android e iOS). No hay capa de abstracción que reinvente SQL. El equipo escribe sentencias SQL estándar.

2. **Plugin maduro de la comunidad Flutter.** Mantenido por [Alex Tekartik](https://github.com/tekartik) durante años. Cuota de adopción muy alta: la mayoría de apps Flutter con persistencia local lo usan.

3. **Migraciones simples.** El plugin gestiona versiones de schema con un callback `onCreate` y `onUpgrade(db, oldVersion, newVersion)` donde se ejecutan los `ALTER TABLE` o `CREATE TABLE` necesarios. Es manual pero predecible.

4. **Sin code generation.** A diferencia de `drift` o `isar`, no requiere `build_runner` ni anotaciones. El equipo escribe el modelo Dart, escribe el SQL, y mapea manualmente en `fromMap` / `toMap`. Para el volumen de tablas que la app necesita en MVP (cola offline + 1-2 cachés), el coste es bajo.

5. **Estándar de la industria.** Cualquier desarrollador con experiencia en Flutter conoce `sqflite`. La curva de aprendizaje es nula.

## Alternativas evaluadas y descartadas

### A. `drift` (antes `moor`)

ORM Dart sobre SQLite con code generation.

- **Pros**: queries type-safe, migraciones declarativas, soporte web vía `drift_native` y `drift_web`.
- **Contras**: build_runner permanente, anotaciones y código generado que añade fricción; ventaja real solo aparece cuando las tablas son numerosas y las queries complejas — el cliente de Custodiam no llega a ese umbral en MVP.
- **Descartado por**: ROI desfavorable. Si en una fase futura la persistencia local crece mucho, se reconsidera.

### B. `isar`

NoSQL document store nativo Flutter.

- **Pros**: muy rápido en operaciones single-row; API ergonómica con sintaxis fluida.
- **Contras**: NoSQL (sin SQL) — no encaja conceptualmente con un modelo cliente que es espejo de uno relacional en el backend; depende fuertemente de un mantenedor individual; soporte web reciente y con limitaciones.
- **Descartado por**: modelo de datos divergente con el backend + dependencia de un único mantenedor.

### C. `hive`

Key-value store NoSQL puro Dart.

- **Pros**: cero overhead, ideal para configuración o caches simples.
- **Contras**: NoSQL puro, no permite consultas relacionales. Para fichajes con timestamp, deduplicación por servicio_id, sincronización ordenada, etc., escribir manualmente todos los índices y filtros sería tedioso.
- **Descartado por**: insuficiente para el modelo relacional que la app necesita.

### D. Sin persistencia local

Cualquier acción offline pierde estado.

- **Pros**: cero infraestructura local.
- **Contras**: rompe el caso de uso "fichaje en zona sin cobertura", que es uno de los flujos críticos del producto.
- **Descartado por**: incumple un requisito funcional.

## Implicaciones operativas

- **Inicialización lazy**: la BD local se abre la primera vez que una feature la necesita, no en el arranque. Esto evita penalizar el tiempo de splash de las features que nunca tocan persistencia local.
- **Schema versionado**: `onCreate` crea las tablas iniciales con `CREATE TABLE IF NOT EXISTS`. `onUpgrade` aplica las migraciones de schema necesarias entre versiones de la app. La versión vive como constante `kDatabaseVersion` y se bumpea por PR cuando hay cambio de schema local.
- **Solo accesible desde la capa data**: la BD local vive detrás de un repository, no se expone como provider global. La presentación nunca habla directamente con SQLite.
- **Web sin sqflite**: features que requieran offline en web (caso poco frecuente en MVP) se implementan con IndexedDB envuelto en una abstracción equivalente. En MVP, web es canal secundario y no se prioriza persistencia local en navegador.
- **Cifrado opcional con `sqflite_sqlcipher`**: si en el futuro algún dato local pasa a considerarse sensible (cache de datos personales de voluntarios), `sqflite_sqlcipher` reemplaza a `sqflite` sin cambiar la API. No se aplica en MVP — los datos locales actuales son fichajes y cola de acciones, sin PII fuera de IDs.

## Referencias

- **[Paquete sqflite en pub.dev](https://pub.dev/packages/sqflite)** — documentación oficial.
- **[SQLite — Documentación oficial](https://www.sqlite.org/docs.html)** — motor subyacente.
- **[ADR-004 Cliente HTTP](adr-004-http-cliente.md)** — capa que orquesta la sincronización entre local y backend.
