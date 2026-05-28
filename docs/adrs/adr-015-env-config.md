---
title: ADR-015 — Configuración por entorno con `String.fromEnvironment`
description: >-
  La clase `EnvConfig` lee las URLs de cada entorno (API, Keycloak) con
  `String.fromEnvironment` y se inyectan en build con `--dart-define`. Sin
  archivos JSON ni hardcoded URLs en el código.
---

# ADR-015 — Configuración por entorno con `String.fromEnvironment`

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 26 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

La app Flutter consume al menos dos servicios externos cuyas URLs cambian entre entornos:

- `API_BASE_URL` — host de `custodiam-api` (en local: `http://localhost:8000/api/v1`; en producción: `https://api.custodiam.es/api/v1`).
- `KEYCLOAK_BASE_URL` — host de Keycloak (en local: `http://localhost:8080`; en producción: `https://auth.custodiam.es`).

Las URLs no pueden vivir hardcoded en el código fuente. Hay que decidir **dónde residen** y **cómo se inyectan** en cada build.

## Decisión

**Clase `EnvConfig` en `lib/core/config/env_config.dart` con `String.fromEnvironment`** + inyección por `--dart-define` en el build.

```dart
class EnvConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  static const String keycloakBaseUrl = String.fromEnvironment(
    'KEYCLOAK_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );
}
```

Builds:

```bash
# Desarrollo local (usa defaults a localhost)
flutter run

# Build release a stores
flutter build apk \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es

flutter build ios --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es

# Build web producción
flutter build web \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es
```

**No** se hardcodean URLs ni identificadores de entorno en `lib/`, `AndroidManifest.xml`, `Info.plist` ni `Runner.entitlements`.

## Justificación

1. **Mínimo viable, sin JSON files innecesarios.** En MVP, los dos entornos relevantes son "local" y "producción". Un sistema con archivos JSON por entorno (`dev.json`, `staging.json`, `prod.json`) tiene sentido cuando hay 3-5 entornos con configuración rica. Para 2 entornos con 2 variables cada uno, `--dart-define` directo es suficiente.

2. **Cero dependencias.** `String.fromEnvironment` viene en `dart:core`. No requiere paquetes adicionales ni runtime para leer un `.env`.

3. **Compile-time constants.** `String.fromEnvironment` se resuelve **en tiempo de compilación**, no en runtime. El compilador conoce el valor exacto y puede aplicar inlining y dead code elimination. Esto también significa que el valor compilado **no puede cambiarse después** — no hay riesgo de que un atacante modifique un `.env` en el dispositivo para apuntar la app a un endpoint diferente.

4. **Visible en CI con sintaxis estándar.** El workflow de CI define las URLs de producción como secretos de GitHub Actions y los inyecta con `--dart-define=KEY=$VALUE`. No hay archivos extra que mantener sincronizados.

5. **Migrable a sistemas más ricos en fases futuras.** Si en una fase posterior aparece la necesidad de configuración compleja (dev / qa / staging / prod con secrets distintos, feature flags, A/B testing remoto), se migra a `--dart-define-from-file` con JSON files versionados. La superficie de cambio queda contenida en `env_config.dart`: el resto del código sigue consumiendo `EnvConfig.apiBaseUrl`.

## Alternativas evaluadas y descartadas

### A. `--dart-define-from-file` con JSON por entorno

```bash
flutter build apk --dart-define-from-file=config/prod.json
```

- **Pros**: separa la configuración del comando, escala mejor a muchas variables.
- **Contras**: en MVP solo hay 2 variables; un archivo JSON por entorno es papelería desproporcionada. Los JSON tienen que versionarse o no versionarse; si se versionan, tienen que enmascarar los valores secretos; si no, hay que coordinarlos por canal aparte. Complica el flujo sin beneficio.
- **Descartado por**: prematuro para MVP. Migración futura preservada.

### B. `flutter_dotenv` (paquete que lee `.env` en runtime)

- **Pros**: ergonomía tipo Node.js — pone un `.env` en la raíz y la app lo lee.
- **Contras**: lectura en **runtime** significa que el `.env` viaja en el bundle de la app y puede ser modificado en el dispositivo. Riesgo de seguridad menor pero real. Además, depende de un paquete de terceros para lo que `String.fromEnvironment` ya hace nativamente.
- **Descartado por**: lectura runtime + dependencia extra sin beneficio.

### C. URLs hardcoded por flavor

Separar Android/iOS en flavors (`dev`, `prod`) con `applicationIdSuffix` distinto y URLs hardcoded por flavor.

- **Pros**: las URLs viven en el build system nativo, no en Dart.
- **Contras**: duplica la información en `AndroidManifest.xml` + `Info.plist` + `build.gradle` + `Runner.xcodeproj`; el código Dart pierde el valor a menos que use plugins de "lectura del flavor"; soluciona el problema para Android/iOS pero **no para Web**, que no tiene flavors.
- **Descartado por**: fragmenta la configuración por plataforma sin beneficio.

### D. Llamada a `/.well-known/config.json` del backend en arranque

La app pide la configuración al backend al arrancar.

- **Pros**: rota URLs sin recompilar.
- **Contras**: paradoja del huevo y la gallina: ¿desde qué URL pide la configuración inicial? Pide redirección a esa URL en `String.fromEnvironment` igualmente. Añade una llamada de red en el critical path del splash.
- **Descartado por**: complejidad sin beneficio para los entornos actuales del proyecto.

## Implicaciones operativas

- **`EnvConfig` es la única superficie de acceso a configuración** desde el código Dart. Si alguna feature necesita leer `apiBaseUrl`, lo hace vía `EnvConfig.apiBaseUrl`, nunca con `String.fromEnvironment` directo. Esto centraliza el grep cuando un día haga falta refactorizar.
- **Defaults de localhost**: los `defaultValue:` apuntan a `localhost:8000` y `localhost:8080`. `flutter run` sin `--dart-define` arranca contra el stack local. Hacer un build release sin `--dart-define` da una app que apunta a `localhost`, lo que **falla en cualquier dispositivo real** — eso es deliberado: una build de release que no especifica URLs no se va a publicar nunca, así que es preferible que falle visiblemente.
- **Tests no consumen `EnvConfig` directo**: los tests inyectan URLs mock a través de los providers de Riverpod ([ADR-012](adr-012-riverpod.md)) que envuelven `EnvConfig`. La centralización permite override.
- **No commitear nada con URLs de producción ni secretos**. Las URLs de producción son públicas por naturaleza (dominio del proyecto), no son secretos. Pero el patrón debe permanecer estricto: las variables se inyectan en build, no se versionan en el código.

## Referencias

- **[Dart — `String.fromEnvironment`](https://api.dart.dev/stable/dart-core/String/String.fromEnvironment.html)** — documentación oficial.
- **[Flutter — Build modes](https://docs.flutter.dev/testing/build-modes)** — flags `--dart-define` y `--dart-define-from-file`.
- **[ADR-004 Cliente HTTP](adr-004-http-cliente.md)** — el cliente lee `EnvConfig.apiBaseUrl` para componer URLs.
- **[ADR-010 OAuth + PKCE + Keycloak](adr-010-oauth-pkce-keycloak.md)** — el flujo OIDC lee `EnvConfig.keycloakBaseUrl`.
