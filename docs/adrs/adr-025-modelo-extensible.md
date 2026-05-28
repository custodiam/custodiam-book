---
title: ADR-025 — Modelo de datos extensible (catálogo + instancias + JSONB)
description: >-
  Custodiam adopta el patrón "catálogo extensible + tabla de instancias + JSONB
  de campos específicos" como diseño de proyecto para entidades con tipos
  predefinidos ampliables. Materializado en el módulo voluntarios (Sprint 4).
---

# ADR-025 — Modelo de datos extensible (catálogo + instancias + JSONB)

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 10 de marzo de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

El módulo de voluntarios (Epic E02) modela entidades cuya **estructura compartida pero variable por tipo** es central al dominio:

- **Acreditaciones**: carnet de conducir (tipo B, B+E, C, C+E, D), ESS sanitario (nivel ESS, ATS, enfermería), ADR mercancías peligrosas (clases I–IX), manipulador de alimentos, cursos internos de Protección Civil, certificaciones externas, **futuros tipos que aún no existen**.
- **Equipamiento con tallas**: camisa, polo, chaqueta, pantalón, botas, casco, guantes, chaleco; el catálogo evoluciona con el inventario.
- **Contactos de emergencia**: nombre + teléfono + parentesco; un voluntario puede tener varios contactos ordenados por preferencia de llamada.

Las tres entidades comparten un patrón estructural común: **catálogo finito pero ampliable de tipos predefinidos, cada uno con su esquema de datos específico, sobre el que las instancias concretas del voluntario "se cuelgan"**. Las consultas operativas previsibles incluyen tanto **atómicas por familia** ("voluntarios con cualquier curso interno de Protección Civil") como **mixtas** ("conductores con carnet C+E **Y** ADR clase II").

La decisión a tomar: ¿qué patrón de modelado de datos cubre extensibilidad, consultas mixtas eficientes y separación semántica entre familias sin sacrificar ninguna?

## Decisión

Adoptar el patrón **"catálogo extensible + tabla de instancias + JSONB para campos específicos + enum discriminador"** como diseño de proyecto. Materializado en el módulo voluntarios mediante tres bloques:

### Bloque 1 — Acreditaciones (catálogo + enum discriminador)

```text
tipos_acreditacion (catálogo, pre-poblado vía Alembic data migration)
─────────────────────────────────────────────────────────────────────
id              UUID PK
codigo          VARCHAR(50) UNIQUE      ("CARNET_CONDUCIR", "ESS_SANITARIO", ...)
nombre          VARCHAR(255)
categoria       ENUM(LICENCIA_OFICIAL, FORMACION_INTERNA, OTRO)  — sugerida
campos_schema   JSONB?                  — documenta la forma de datos_especificos
activo          BOOLEAN DEFAULT true

acreditaciones (instancias)
───────────────────────────
id                  UUID PK
voluntario_id       UUID FK → voluntarios.id  INDEX
tipo_id             UUID FK → tipos_acreditacion.id  INDEX
categoria           ENUM(LICENCIA_OFICIAL, FORMACION_INTERNA, OTRO)  — discriminador real
fecha_obtencion     DATE
fecha_caducidad     DATE?
numero              VARCHAR(100)?
entidad_emisora     VARCHAR(255)?
datos_especificos   JSONB?              — campos específicos del tipo
documento_url       VARCHAR(500)?

UNIQUE (voluntario_id, tipo_id, numero)
INDEX (categoria)                         — filtros atómicos por familia
```

### Bloque 2 — Equipamiento + tallas (catálogo + 1:N)

```text
tipos_equipamiento (catálogo, pre-poblado)
──────────────────────────────────────────
id              UUID PK
codigo          VARCHAR(50) UNIQUE      ("CAMISA", "PANTALON", "BOTAS", ...)
nombre          VARCHAR(255)
sistema_tallas  VARCHAR(50)?            ("XS-XXXL", "36-50")

tallas_voluntario (instancias)
──────────────────────────────
id              UUID PK
voluntario_id   UUID FK → voluntarios.id  INDEX
tipo_id         UUID FK → tipos_equipamiento.id  INDEX
valor           VARCHAR(20)             ("M", "42", "L")

UNIQUE (voluntario_id, tipo_id)
```

### Bloque 3 — Contactos de emergencia (1:N sin catálogo)

```text
contactos_emergencia
────────────────────
id                  UUID PK
voluntario_id       UUID FK → voluntarios.id  INDEX
nombre              VARCHAR(255)
telefono            VARCHAR(20)
parentesco          VARCHAR(100)?
orden_preferencia   INTEGER DEFAULT 1
```

No tiene catálogo porque no hay "tipos de contacto" predefinidos relevantes; el parentesco es texto libre.

## Justificación

1. **Extensibilidad sin schema migration.** Añadir un tipo nuevo es **una fila INSERT en el catálogo** (vía data migration o panel admin futuro), sin tocar el schema. Las acreditaciones que vendrán cuando la normativa europea introduzca nuevas categorías se incorporan sin ALTER TABLE en producción.

2. **Consultas atómicas y mixtas con la misma estructura.** Una sola tabla `acreditaciones` con `JOIN tipos_acreditacion` soporta consultas por familia (`WHERE a.categoria = 'FORMACION_INTERNA'`), por tipo concreto (`WHERE t.codigo = 'CARNET_CONDUCIR'`) y mixtas (`EXISTS` correlacionado por cada tipo requerido). Tablas separadas exigirían UNION + merge en código.

3. **Separación semántica preservada vía enum.** El enum `categoria` (`LICENCIA_OFICIAL` / `FORMACION_INTERNA` / `OTRO`) deja al usuario pensar conceptualmente en categorías distintas sin que la BD las separe físicamente. La frontera entre las dos no siempre es nítida (un curso externo reconocido puede caer en zona gris); el enum permite reclasificar una instancia sin migración.

4. **JSONB con schema-on-read documentado.** El campo `campos_schema` del catálogo documenta la forma esperada de `datos_especificos`. La validación es opcional en la capa API (Pydantic + librería `jsonschema`) y el schema sirve también como documentación viva para construir formularios dinámicos en futuras fases del cliente.

5. **Catálogos versionados con Alembic.** Los datos canónicos (tipos predefinidos) viven en el historial Git como parte del esquema, no como configuración volátil. Una restauración de BD a partir del repo restaura también los catálogos. Cambios al catálogo son revisables por PR como cualquier otro cambio de schema.

## Alternativas evaluadas y descartadas

### A. Columnas planas en `Voluntario`

(`carnet_conducir_tipo`, `talla_camisa`, `contacto_emergencia_nombre`, etc.)

- **Pros**: simplicidad, queries directos.
- **Contras**: añadir un tipo nuevo de licencia o item exige ALTER TABLE; un voluntario con N contactos de emergencia exige columnas `contacto_2_*`, `contacto_3_*` repetidas; consultas como "voluntarios con cualquier acreditación de la categoría X" se vuelven inviables.
- **Descartado por**: incompatibilidad con extensibilidad y modelado incorrecto del dominio.

### B. JSONB libre directamente en `Voluntario`

(`acreditaciones: dict`, `tallas: dict`, `contactos_emergencia: list[dict]`)

- **Pros**: máxima flexibilidad, schema completamente abierto.
- **Contras**: las consultas operativas dependen de operadores JSONB específicos de PostgreSQL (`?`, `?&`, `@>`, `jsonb_path_query_array`) cuyo plan de ejecución es opaco y no aprovecha índices clásicos; el modelo conceptual no queda explícito en el schema (onboarding pobre); la validación queda al 100% en la capa API.
- **Descartado por**: penalización de queries y opacidad del schema.

### C. Class Table Inheritance (tabla por tipo)

Tabla base `acreditaciones` + N tablas hijas (`licencias_conduccion`, `licencias_sanitarias`, ...).

- **Pros**: máxima normalización, campos específicos con tipos correctos.
- **Contras**: añadir un tipo exige crear tabla + migration + redeploy; queries que necesitan unificar todas las acreditaciones requieren N LEFT JOINs; ORM (SQLModel) tiene soporte limitado para inheritance polimórfico.
- **Descartado por**: ROI desfavorable para datos que son fundamentalmente "campos opcionales por tipo".

### D. Tablas separadas (`licencias` + `formaciones`)

- **Pros**: separación semántica clara y explícita a nivel de schema.
- **Contras**: (1) duplicación estructural — ambas tendrían `voluntario_id`, `tipo`, `fecha_obtencion`, etc.; (2) consultas mixtas exigen UNION o queries múltiples + merge; (3) la frontera entre "licencia oficial" y "formación interna" no es nítida.
- **Descartado por**: la unificación + enum mantiene la separación semántica deseada sin penalizar consultas mixtas ni duplicar estructura.

### E. Catálogo con relación N:M sin tabla intermedia

Pivote `(voluntario_id, tipo_id)` sin campos propios.

- **Pros**: máxima simplicidad.
- **Contras**: las instancias concretas tienen datos propios (fecha obtención, número de carnet, documento adjunto) que no caben en una relación M:N pura. Forzar JSONB en la pivote nos lleva a la opción B sin sus ventajas.
- **Descartado por**: modelado incorrecto del dominio (las acreditaciones son entidades con identidad propia).

## Implicaciones operativas

- **Catálogos pre-poblados via Alembic data migration.** El primer migration tras el enabler que crea las tablas incluye `INSERT INTO tipos_acreditacion (...) VALUES (...)` y `INSERT INTO tipos_equipamiento (...) VALUES (...)` con los datos canónicos. Modificaciones futuras se gestionan vía nuevas data migrations.
- **Validación de `datos_especificos`.** En la capa API, validar `datos_especificos` contra `campos_schema` del tipo asociado con `jsonschema` o `model_validator` Pydantic. Validación opcional al inicio; estricta cuando madure la UI de gestión.
- **Indexación.** `acreditaciones` con índices en `voluntario_id`, `tipo_id`, `(voluntario_id, tipo_id)` para JOINs eficientes y en `categoria` para filtros atómicos por familia.
- **Documentación viva.** El campo `campos_schema` del catálogo permite que el cliente lea la forma esperada y construya formularios dinámicos sin hardcodearlos.

## Patrón derivado aplicable a futuros módulos

Esta ADR establece **"catálogo extensible + tabla de instancias + JSONB para campos específicos + enum discriminador"** como **decisión de proyecto**, no solo decisión local del módulo voluntarios. Es candidato natural a replicarse en:

- **Inventario** (epic E05): categorías de material, vehículos, equipamiento — mismo patrón con catálogo de tipos de material.
- **Notificaciones** (epic E06): tipos de notificación con campos específicos por canal (FCM, ntfy, email) — mismo patrón si los tipos son extensibles.
- **Servicios** (epic E03): tipos de servicio (preventivo, emergencia, formación, jornada) — mismo patrón si la lista evoluciona en fases posteriores.

Como principio de proyecto: **para entidades con tipos predefinidos extensibles, no usar columnas planas ni JSONB libre; aplicar el patrón catálogo + instancias + JSONB + enum**.

## Referencias

- **[PostgreSQL — JSONB Indexing](https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING)** — operadores e índices.
- **[SQLModel — Relationships](https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/)** — patrón de relaciones aplicado a `voluntario ↔ acreditaciones ↔ tipos_acreditacion`.
- **Patrones.** El patrón "catálogo + instancias + JSONB" es una variante del patrón EAV (Entity-Attribute-Value) con discriminador documentada en Martin Fowler, *Patterns of Enterprise Application Architecture* (Addison-Wesley, 2002).
- **[ADR-002 SQLModel](adr-002-sqlmodel.md)** — ORM unificado sobre el que se asienta este modelo.
