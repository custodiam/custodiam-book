---
title: Audit log cross-module
description: >-
  Registro persistente de operaciones críticas a través de los módulos del
  backend, implementado con imports diferidos para evitar dependencias
  cíclicas entre módulos del dominio.
---

# Audit log cross-module

El backend de Custodiam mantiene un **registro persistente de operaciones críticas** (`audit_log`) que cruza los límites de los módulos del dominio: voluntarios, servicios, fichajes, inventario y notificaciones. La tabla está pensada para auditoría operativa (¿quién hizo qué y cuándo?) y para cumplir obligaciones de trazabilidad RGPD (¿se anonimizó este voluntario? ¿quién lo decidió?).

## Por qué necesita una solución cuidadosa

El módulo de voluntarios escribe en `audit_log` al dar de baja un voluntario. El módulo de servicios escribe en `audit_log` al expulsar un voluntario de un servicio. El módulo de fichajes escribe en `audit_log` al validar manualmente un fichaje. Etc.

La tentación inicial es que **`audit_log` sea un módulo más** del que dependen todos los demás. Esto funciona hasta que un módulo de auditoría necesita leer información del propio módulo para construir el registro (por ejemplo: el módulo de servicios anota en `audit_log` qué voluntarios fueron expulsados, y ese registro luego se consulta desde un endpoint de auditoría que pertenece al módulo de voluntarios). Resultado: **dependencia cíclica** `voluntarios → audit_log → voluntarios`. El intérprete Python lanza `ImportError` y el endpoint de auditoría no carga.

## Patrón aplicado: imports diferidos + helper privado

El backend usa dos mecanismos en combinación:

1. **Tabla `audit_log` genérica** sin foreign keys hacia módulos del dominio. Almacena claves textuales (`entity_type = "voluntario"`, `entity_id = "<uuid>"`) y `metadata` JSONB con el contexto operativo. Esto rompe la dependencia estructural: `audit_log` no "conoce" los módulos que escriben en ella.
2. **Helper privado `_log_audit_event(...)`** en `app/services/audit.py` que recibe los datos como argumentos sueltos y los persiste. **Cada módulo invoca este helper con `from app.services.audit import _log_audit_event` dentro de la función**, no al top-level del archivo. Esto se llama "import diferido" y posterga la resolución del módulo hasta el momento de ejecución, evitando que el grafo de imports cíclicos se evalúe en el arranque.

```python
# app/services/voluntarios.py

async def dar_de_baja(voluntario_id: UUID, motivo: str, user: CurrentUser):
    # Lógica de negocio
    voluntario = await repo.soft_delete(voluntario_id)

    # Audit log con import diferido
    from app.services.audit import _log_audit_event
    await _log_audit_event(
        actor_id=user.id,
        action="voluntario.baja",
        entity_type="voluntario",
        entity_id=str(voluntario_id),
        metadata={"motivo": motivo, "estado_previo": voluntario.estado_anterior},
    )

    return voluntario
```

```python
# app/services/audit.py

async def _log_audit_event(
    *,
    actor_id: UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    # No imports hacia módulos del dominio aquí
    async with get_session() as session:
        evento = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        session.add(evento)
        await session.commit()
```

## Esquema de la tabla

```text
audit_log
─────────
id              UUID PK
actor_id        UUID                — usuario que ejecuta la acción
action          VARCHAR(100)        — "voluntario.baja", "servicio.expulsion", ...
entity_type     VARCHAR(50)         — "voluntario", "servicio", "fichaje", ...
entity_id       VARCHAR(100)        — id textual de la entidad afectada
metadata        JSONB               — contexto operativo (motivo, estado previo, ...)
created_at      TIMESTAMP WITH TIME ZONE  DEFAULT now()

INDEX (actor_id)
INDEX (entity_type, entity_id)
INDEX (action)
INDEX (created_at)
```

**`entity_id` como VARCHAR** (no UUID con foreign key): permite registrar eventos sobre entidades que se eliminan más tarde sin perder la traza. Cuando un voluntario se anonimiza (RGPD art. 17), su `id` en `voluntarios` queda con datos placeholder pero el `audit_log` conserva el registro de la operación.

## Qué se registra

| Acción | Origen | Metadata típica |
| --- | --- | --- |
| `voluntario.alta` | Aprobación del coordinador | `keycloak_id`, `email_verificado` |
| `voluntario.baja` | Solicitud de baja | `motivo`, `estado_previo` |
| `voluntario.anonimizar` | Solicitud RGPD | `motivo`, `acepta_legal_id` |
| `servicio.crear` | Creación servicio | `tipo`, `municipio`, `plazas` |
| `servicio.expulsion` | Jefe quita voluntario | `voluntario_id`, `motivo` |
| `fichaje.validar_manual` | Validación manual fuera de ventana | `fichaje_id`, `motivo` |
| `permiso.elevacion` | Cambio de rol | `rol_anterior`, `rol_nuevo` |

## Consulta operativa

El endpoint `GET /audit-log?entity_type=X&entity_id=Y` devuelve la trazabilidad completa de una entidad. Está protegido por permiso `sistema.auditoria_leer` (rol `admin` + `coordinador`). El cliente Flutter ofrece pantallas de auditoría en el panel admin para responder consultas concretas ("¿quién dio de baja a este voluntario?", "¿qué pasó con la expulsión de X del servicio Y?").

## Trazabilidad RGPD

El audit log es **el mecanismo de cumplimiento del derecho de acceso del RGPD art. 15** sobre datos personales: cuando un voluntario solicita conocer qué se ha hecho con sus datos, el `audit_log` filtrado por `entity_id = <uuid_voluntario>` produce el listado completo de operaciones que le afectaron. La exportación se hace mediante endpoint dedicado `GET /voluntarios/{id}/rgpd-export` que adjunta el bloque de `audit_log` al volcado de sus datos.

## Lección operativa registrada

El patrón "tabla genérica + helper privado con imports diferidos" se aplicó por primera vez al implementar el módulo de voluntarios. Antes había una tentación de hacer `audit_log` "un módulo dependiente de cada uno" o "un módulo del que dependen todos", con resultados igualmente malos (dependencias cíclicas en el primer caso, acoplamiento fuerte en el segundo). El patrón actual se aplica por defecto en los siguientes módulos del backend (servicios, fichajes, inventario, notificaciones).

## Referencias

- **[Modelo de datos](modelo-datos.md)** — esquema general.
- **[Flujos de negocio](flujos-negocio.md)** — operaciones que se registran en el audit log.
- **[ADR-013 RBAC lockstep](../adrs/adr-013-rbac-lockstep.md)** — el permiso `sistema.auditoria_leer` que protege la consulta.
- **[GDPR Art. 17 — Right to erasure](https://gdpr-info.eu/art-17-gdpr/)** y **[Art. 15 — Right of access](https://gdpr-info.eu/art-15-gdpr/)** — obligaciones legales que motivan la trazabilidad.
