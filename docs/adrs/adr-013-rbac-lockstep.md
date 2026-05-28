---
title: ADR-013 — RBAC en lockstep front/back
description: >-
  La matriz rol→permisos vive en código tanto en backend (Python) como en
  cliente (Dart). El JWT solo lleva roles; el cliente y el servidor calculan
  permisos de forma local y coherente.
---

# ADR-013 — RBAC en *lockstep* front/back

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 24 de febrero de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

Custodiam tiene **doce roles** en el realm Keycloak (`voluntario_practicas`, `voluntario`, `jefe_equipo`, ..., `coordinador`, `secretario`, `tesorero`, `admin`) y **cuarenta permisos atómicos** organizados por módulo funcional (`voluntarios.crear`, `servicios.publicar`, `fichaje.fichar_propio`, etc., catalogados en el documento canónico `RBAC_v0.1.0`). Cada permiso atómico se asocia a uno o más roles según una matriz declarada.

La autorización se aplica en **dos lados independientes**:

1. **Backend**: cada endpoint REST declara qué permiso requiere (`Depends(require_permission(Permission.VOLUNTARIOS_CREAR))`).
2. **Cliente Flutter**: cada widget condicional al rol se envuelve en un *gate* declarativo (`AppPermissionGate(permission: Permission.voluntariosCrear, child: ...)`).

La decisión a tomar: ¿dónde vive la matriz rol→permisos y cómo se mantiene coherente entre las dos partes?

## Decisión

La matriz **vive en código en ambos lados, replicada en *lockstep*** (mismo orden, mismas claves, mismos valores) entre dos archivos:

- **Backend**: `app/core/permissions.py` con un `StrEnum` `Permission` y un diccionario `ROLE_PERMISSIONS: dict[str, frozenset[Permission]]`.
- **Cliente**: `lib/infrastructure/auth/permissions.dart` con un `enum Permission` y un `Map<String, Set<Permission>>` equivalente.

El **JWT emitido por Keycloak transporta solo la lista de roles** del usuario en el claim `roles`. **No transporta permisos**. El cliente y el backend resuelven la matriz de forma local consultando el diccionario hardcoded.

La regla operativa: **si la matriz cambia en un lado, cambia en el mismo Pull Request en el otro lado**. No se permite mergear cambios parciales.

```python
# Backend — app/core/permissions.py
class Permission(StrEnum):
    VOLUNTARIOS_CREAR = "voluntarios.crear"
    VOLUNTARIOS_EDITAR = "voluntarios.editar"
    # ... 40 permisos

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "voluntario": frozenset({Permission.SERVICIOS_APUNTARSE_PROPIO, ...}),
    "jefe_equipo": _BASE_JEFE_EQUIPO,
    # ... 12 roles
}

def require_permission(permission: Permission):
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if permission not in permissions_for_roles(user.roles):
            raise HTTPException(status_code=403, ...)
        return user
    return _check
```

```dart
// Cliente — lib/infrastructure/auth/permissions.dart
enum Permission {
  voluntariosCrear('voluntarios.crear'),
  voluntariosEditar('voluntarios.editar'),
  // ... 40 permisos
  ;
  final String value;
  const Permission(this.value);
}

const Map<String, Set<Permission>> rolePermissions = {
  'voluntario': {Permission.serviciosApuntarsePropio, ...},
  'jefe_equipo': _baseJefeEquipo,
  // ... 12 roles
};

// Widget gate declarativo
class AppPermissionGate extends ConsumerWidget {
  final Permission permission;
  final Widget child;
  // ...
}
```

## Justificación

1. **El JWT se mantiene pequeño y firmable.** Si el JWT incluyese los 40 permisos resueltos del usuario, el token crecería significativamente y dificultaría futuras evoluciones de la matriz (cambios en el cliente exigirían reemitir el token en caliente). Mantener solo los roles en el JWT preserva el tamaño y simplifica el ciclo de refresco.

2. **La matriz es código, no datos.** Los permisos del sistema cambian raras veces y son parte del contrato funcional del producto. Vivir como código (con type-safe enums y `frozenset` inmutable) elimina toda una clase de errores en tiempo de edición y permite revisión por *pull request*.

3. **El backend es la autoridad final.** El cliente puede mostrar u ocultar widgets según la matriz local, pero **cada petición a la API verifica el permiso de nuevo en el servidor**. Si un atacante manipulase el cliente para mostrar widgets que no debería, el backend rechazaría la operación con HTTP 403. La matriz en el cliente es UX (no mostrar afordancias inalcanzables), no seguridad.

4. **`AppPermissionGate` declarativo evita esparcir condicionales.** En lugar de `if (currentUser.hasPermission(...)) ShowWidget() else SizedBox.shrink()` repetido por toda la UI, el *gate* concentra la lógica en un solo widget y permite testear el comportamiento con un único patrón (`pumpRiverpod` + override del `currentUserProvider` + `find.byType(AppPermissionGate)`).

5. **Permite añadir un permiso sin migrar datos.** Un permiso nuevo se añade modificando los dos archivos en un mismo PR. No requiere migración de BD, no requiere revocar tokens emitidos (solo afecta a tokens nuevos cuyo cliente tendría que actualizar la matriz local mediante actualización de la aplicación).

## Alternativas evaluadas y descartadas

### A. Permisos en el JWT

- **Pros**: el cliente obtiene la lista de permisos efectiva sin necesidad de matriz local.
- **Contras**: token grande (40 strings adicionales por usuario), cambios en la matriz exigen reemitir tokens, riesgo de drift entre cliente y servidor si el cliente lee permisos del token sin validar.
- **Descartado por**: peor relación tamaño/utilidad; preferimos mantener el JWT mínimo.

### B. *Policy engine* dinámico (Casbin, OPA, Cedar)

- **Pros**: políticas declarativas en archivos externos, hot-reload de cambios.
- **Contras**: complejidad enorme para 40 permisos y 12 roles estáticos; introduce un nuevo runtime (Casbin Python, OPA daemon o Cedar SDK) que se compromete a mantener; el cliente seguiría necesitando alguna forma de saber qué mostrar.
- **Descartado por**: ROI desfavorable; los policy engines son apropiados cuando la matriz cambia frecuentemente o es mucho mayor.

### C. ABAC (Attribute-Based Access Control) con políticas dinámicas

- **Pros**: granularidad extrema (puede decidir según atributos del recurso, no solo del usuario).
- **Contras**: el modelo de Custodiam es plenamente RBAC: las acciones se autorizan según el rol funcional, no según atributos del recurso. ABAC sería sobreingeniería.
- **Descartado por**: el modelo del producto es RBAC, no ABAC.

### D. Backend único con UI server-rendered (sin matriz en cliente)

- **Pros**: una sola fuente de verdad.
- **Contras**: incompatible con la arquitectura del proyecto (cliente Flutter SPA, no plantillas Jinja). El cliente necesita saber qué widgets condicionales mostrar antes de cada acción.
- **Descartado por**: rompe la arquitectura del producto.

## Implicaciones operativas

- **Procedimiento de cambio**: cualquier cambio en `app/core/permissions.py` exige un cambio simétrico en `lib/infrastructure/auth/permissions.dart` en el mismo PR (o en PRs coordinados con referencias mutuas si hay separación de repos). Code review explícita la coherencia.
- **Tests**: en backend, `test_permissions.py` valida el catálogo completo de 40 permisos y su asignación a los 12 roles. En cliente, los tests de `AppPermissionGate` verifican el comportamiento del *gate* con `mocktail` sobre `CurrentUserNotifier`.
- **Catálogo canónico**: el documento `docs/trabajo/backlog/RBAC_v0.1.0.md` del repositorio privado lista los 40 permisos con su descripción funcional y la matriz exhaustiva. Este book muestra una vista resumida en [Usuarios de prueba](../empezar/usuarios-prueba.md).
- **`admin` es técnico puro**: el rol `admin` solo tiene permisos `sistema.*` (panel admin, configuración, backups, logs auditoría, exportar RGPD). **No tiene capacidades operativas por sí mismo**. Un usuario que en la práctica debe ser técnico y operativo recibe dos roles simultáneos (`admin` + `coordinador`, por ejemplo). Esto mantiene el principio de mínimo privilegio y permite delegar el rol técnico a un contratista externo sin entregarle el dominio operativo.

## Referencias

- **[RBAC_v0.1.0](https://github.com/custodiam/custodiam-api/blob/main/docs/RBAC_v0.1.0.md)** — catálogo completo (en repo privado; aquí solo vista resumida).
- **[Usuarios de prueba](../empezar/usuarios-prueba.md)** — matriz de capacidades por rol vista del usuario.
- **[ADR-010 OAuth + PKCE + Keycloak](adr-010-oauth-pkce-keycloak.md)** — IdP que emite el JWT con los roles.
