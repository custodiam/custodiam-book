---
title: ADR-024 — Patrol como framework E2E unificado
description: >-
  Custodiam adopta Patrol 4.6+ como framework único de tests end-to-end para
  custodiam-app, sustituyendo integration_test y unificando mobile + web bajo
  la misma API de Dart.
---

# ADR-024 — Patrol como framework E2E unificado

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 22 de mayo de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

El refactor del flujo OAuth web (ADR-023, pendiente de publicación) cerró cuatro capas de asimetría móvil/web y dejó la PWA pública operativa, pero los tres escenarios del DoD (login feliz end-to-end, llegada huérfana a `/callback`, `sessionStorage` deshabilitado) quedaron cubiertos exclusivamente en **verificación manual**. Los tests automatizados del repositorio (`flutter test` puro contra `InMemorySessionStorageGateway`) se acercaban al flujo pero ninguno corría dentro de un browser real.

Mientras esa cobertura quede manual, cualquier regresión futura en el flujo de autenticación web —el camino de entrada principal a la PWA— pasaría inadvertida hasta el siguiente ciclo de QA manual. El riesgo no es teórico: las cuatro capas de asimetría de la propia PWA fueron silenciosamente acumulables y se descubrieron en orden estrictamente lineal porque cada una bloqueaba la siguiente. Sin red automatizada en browser real, una quinta capa se detectaría con el mismo coste (incidente en producción).

La decisión a tomar: ¿qué framework cubre ese hueco con stack Dart, compatible con AGPL-3.0 y mantenible por el equipo de dos personas?

## Decisión

**Adoptar [Patrol](https://patrol.leancode.co/) 4.6+ como framework E2E unificado** para `custodiam-app`, reemplazando el patrón `flutter_test` + `integration_test` allá donde se necesite ejercicio en plataforma real (browser o emulator). La pirámide de tests del proyecto pasa a tener **tres capas explícitas**:

1. **Unit + widget** (`test/`): Dart VM, sin plataforma, ejecución sub-segundo. Sigue siendo el grueso de la cobertura (~200 tests al cierre de Sprint 4).
2. **Integración con flavor externo** (`patrol_test/auth/`): Dart VM contra mock OIDC server levantado con `docker compose --profile test`. Skip automático sin variable de entorno.
3. **E2E sobre plataforma real** (`patrol_test/web/`, `patrol_test/mobile/`): browser headless (Chromium vía Playwright) o emulator/device, ejercicio del bundle real. Cubre los escenarios del DoD de ADR-023 y los flows críticos futuros.

`integration_test/` queda vacío. El paquete del SDK se mantiene como dependencia transitiva por compatibilidad pero no se escriben tests allí.

## Justificación

1. **Stack Dart preservado.** Patrol expone una API que reusa la sintaxis de `flutter_test` (matchers, finders, `WidgetTester`) y se programa en Dart. El equipo (Marcos y Rodrigo) no necesita aprender TypeScript ni un DSL declarativo. La curva de adopción es mínima sobre el conocimiento de `testWidgets` que el repo ya tiene.

2. **Unifica mobile + web.** La misma API (`patrolTest` para E2E, `patrolWidgetTest` para widget tests con finders enriquecidos) sirve para Android, iOS y Web. Esto importa porque los flows críticos de Custodiam (login, fichaje, notificación de emergencia) se ejercitan en todas las plataformas y duplicar el framework por plataforma multiplicaría el coste de mantenimiento.

3. **Licencia compatible.** Patrol es Apache-2.0, compatible con AGPL-3.0 del proyecto. Mantenido activamente por [LeanCode](https://leancode.co/) con releases mensuales y trazabilidad pública del changelog.

4. **Verificación funcional previa a la adopción.** El spike SP-08 levantó un smoke test en Windows + Flutter 3.41.8 + Node 22 + `patrol_cli` 4.4.0 + `patrol` 4.6.0 que pasó en **17 segundos verde**. La primera iteración había fallado con `Total: 0` y exit 1, pero la causa raíz era la capa 4 de asimetría OAuth web (resuelta en commit `dcfec25` con `usePathUrlStrategy()`), no un defecto de Patrol. La adopción se decide sobre evidencia experimental, no sobre expectativa.

5. **Web cubierta por Playwright + Chromium.** Patrol delega web a Playwright, que tiene madurez industrial probada (Microsoft, multitud de proyectos). La capa de browser real no es código de LeanCode sino infraestructura ampliamente verificada en producción.

## Trade-offs aceptados

### `patrolTest` y `patrolWidgetTest` NO son intercambiables

Patrol expone dos wrappers que parecen similares pero corren bajo runners distintos:

- **`patrolTest`** (de `package:patrol`) requiere `patrol test --device <…>` (CLI con Playwright + Chromium en web o instrumentation en mobile). Construye un `PlatformAutomator` al cargar el archivo. **No se ejecuta bajo `flutter test`**.
- **`patrolWidgetTest`** (de `package:patrol_finders`) es un wrapper de `testWidgets` con finders `$('text')` enriquecidos. Diseñado para `flutter test`. La CLI no lo descubre como caso E2E.

**Regla operativa del proyecto**: los tests bajo `patrol_test/web/` y `patrol_test/mobile/` son E2E por diseño y usan `patrolTest` exclusivamente. Los tests bajo `test/` que necesiten finders Patrol pueden usar `patrolWidgetTest` (uso secundario; el grueso de `test/` sigue usando `testWidgets` clásico).

**Errata operativa documentada honestamente**: la primera iteración de la migración escribió los tres tests del DoD con `patrolWidgetTest` pensando que mantenían doble ejecutabilidad VM + CLI. El CI falló con `Total: 0 + exit 1` silencioso porque la CLI no cuenta esos casos como E2E. La corrección fue cambiar el wrapper a `patrolTest` y aceptar que viven únicamente en el plano E2E. La distinción entre los dos wrappers no está claramente señalizada en la documentación oficial; esta ADR la deja escrita para futuras decisiones.

### Override Riverpod en vez de inyección JS

El plan inicial sugería inyectar `Storage.prototype.setItem = function() { throw ... }` vía `await $.native.runJsInBrowser(...)` para reproducir el escenario "sessionStorage deshabilitado". **Patrol 4.6 no expone ningún primitive de evaluación JS arbitraria**: el `WebAutomator` cubre `tap`, `enterText`, `pressKey`, `addCookie`, `acceptNextDialog`, navegación back/forward y poco más.

La traducción a la realidad fue usar **override de provider Riverpod** que inyecta el `SessionStorageGateway`:

```dart
authServiceProvider.overrideWithValue(
  KeycloakWebAuthService(
    tokenStore: ...,
    sessionStorage: InMemorySessionStorageGateway(available: false),
    launcher: _LauncherSpy().call,
  ),
)
```

El mismo `Fail(AuthFailure.sessionStorageUnavailable)` recorre el mismo camino productivo (probe → ViewModel → `ref.listen` → `showAuthFailure` → `AppSnackbar`) y la aserción del copy se hace contra el `ScaffoldMessenger` real. **Ventaja colateral**: el patrón es más reproducible que la inyección JS (no depende del estado interno del Storage API ni del orden de inyección + arranque) y es aplicable también a futuros gateways (`localStorage`, `IndexedDB`, FCM tokens).

### Node.js + Chromium en CI

Patrol web descarga Playwright (~100 MB) + Chromium (~150 MB) automáticamente en la primera ejecución y los cachea. Esto añade ~5 minutos al primer `patrol test` en un runner CI fresco. **Aceptado** porque los runs subsiguientes son ~17-30 s para los tres tests del DoD, GitHub Actions cachea node_modules entre jobs con `actions/cache@v4` si hace falta optimizar, y Node 22 LTS es una herramienta que el equipo ya usa.

Trade-off implícito: dependencia operativa de un runtime no-Dart. Mitigación: el job `patrol-web` está aislado del job `test` (Dart puro). Una caída del ecosistema npm o de los CDNs de Playwright no rompe `flutter test`, solo `patrol test`. La pirámide unit + widget sigue siendo la red principal.

### Patrol Web no controla la navegación top-level del browser

El `WebAutomator` permite interactuar con elementos dentro del documento cargado (tap, enterText, cookies, dialogs) pero **no controla `window.location`**. No se puede simular `window.location.assign('https://auth.custodiam.es/...')` ni la vuelta cross-origin desde Keycloak. **Consecuencia operativa**: el "happy path end-to-end" real (ida + vuelta de Keycloak + intercambio del code) sigue siendo verificación manual. Patrol Web cubre el **primer tramo** (verifier persistido + launcher disparado con `_self` + URL Keycloak válida), que es lo testeable sin redirect. El segundo tramo (callback con code real + token exchange) sigue cubierto en unit tests con grant stubbeado.

Aceptado porque las cuatro capas de asimetría documentadas en ADR-023 se manifestaban en el primer tramo (que ahora SÍ está automatizado), cubrir el redirect cross-origin requeriría un framework full-browser-control como Cypress o Playwright puro, y el segundo tramo está cubierto por `keycloak_web_auth_service_test.dart` con `oauth2.Client` directamente construido.

## Alternativas evaluadas y descartadas

### A. Mantener `integration_test` puro + verificación manual web

- **Pros**: cero coste de adopción, es lo que el proyecto ya tenía.
- **Contras**: no automatiza los escenarios del DoD que requieren browser real (`sessionStorage`, interacción cross-origin, redirect lifecycle); cualquier regresión del flujo OAuth web se detecta solo en QA manual.
- **Descartado por**: insuficiente como red de seguridad ante el patrón de asimetría documentado en ADR-023.

### B. Playwright puro en sub-repo `custodiam-app-e2e`

- **Pros**: técnicamente sólido y muy maduro; comunidad enorme.
- **Contras**: stack TypeScript/JavaScript separado del lenguaje del proyecto (Dart) → coste de mantenimiento doble; curva de aprendizaje para el equipo; divergencia conceptual con la pirámide de testing que ya vive en Dart.
- **Descartado por**: ROI desfavorable para equipo de dos personas con stack Dart.

### C. Cypress

- **Pros**: experiencia de desarrollador muy pulida en web.
- **Contras**: mismo trade-off que Playwright puro (stack JS). Adicionalmente, su arquitectura "in-browser" (corre dentro del frame de la app, no como browser externo) tiene limitaciones documentadas con OAuth + redirect cross-origin.
- **Descartado por**: stack JS + limitaciones documentadas con OAuth.

### D. Maestro (mobile.dev)

- **Pros**: excelente para mobile, sintaxis YAML declarativa muy ergonómica.
- **Contras**: soporte web limitado y declarativo. Para Custodiam es relevante que mobile y web compartan API expresiva del mismo flujo (RBAC, sesión, persistencia local). YAML declarativo deja menos espacio para inyectar overrides Riverpod y mockear servicios.
- **Descartado por**: web limitado + asimetría mobile/web no resuelta.

### E. Esperar madurez de Patrol web 1-2 meses

- **Pros**: opción conservadora.
- **Contras**: la versión 4.6 de Patrol se publicó el 21 de mayo de 2026, cinco días antes del cierre del spike SP-08, con Playwright + Chromium ya estable.
- **Descartado por**: tras el retry verde en 17 segundos, no hay razón para esperar.

## Implicaciones operativas

- **`pubspec.yaml`** declara `patrol: ^4.6.0` + `patrol_finders: ^3.4.0` como `dev_dependencies` y `environment.sdk: ^3.8.0`. `patrol_cli` se instala globalmente vía `dart pub global activate patrol_cli` (no se versiona en `pubspec.yaml` para no atar a una versión exacta de CLI).
- **CI** del repo `custodiam-app` gana un job `patrol-web` (Linux, Flutter stable + Node 22 + Chromium con `--no-sandbox --disable-dev-shm-usage`) ejecutado en paralelo con `test`. `build-docker` espera a ambos antes de publicar la imagen GHCR. Tres detalles de plumbing **obligatorios** (sin ellos el job aborta con `Total: 0 + exit 1` silencioso):
    - Step previo `sudo npx playwright@latest install-deps chromium` para instalar las dependencias `.deb` de Linux que `patrol_cli` no pide vía `npx playwright install`.
    - `--web-locale=es-ES` y `--web-timezone=Europe/Madrid` para que el `intl` de Dart Flutter Web no aborte al inicializar.
    - `--web-browser-args='["--no-sandbox", "--disable-dev-shm-usage"]'` como **array JSON serializado** literal (el flag se pasa por `process.env.PATROL_WEB_BROWSER_ARGS` y `playwright.config.ts` lo `JSON.parse`).
- **`.gitignore`** ignora los artefactos del runner (`playwright-report/`, `test-results/`, `test_bundle.dart`). El reporte HTML se sube como artifact CI (retención 14 días) para diagnosticar fallos sin reproducir localmente.
- **Pirámide del repo al cierre de Sprint 4**: 200 + 4 + 3 + 0 = **207 tests** distribuidos por capa.

## Referencias

- **[Patrol — sitio oficial](https://patrol.leancode.co/)**
- **[Patrol Web — superficie del WebAutomator](https://patrol.leancode.co/web)**
- **[Patrol GitHub](https://github.com/leancodepl/patrol)** — código fuente, issues, changelog.
- **[Playwright](https://playwright.dev/)** — herramienta que Patrol usa para web.
- **ADR-023 Asimetría OAuth web vs móvil** (pendiente de publicación) — patrón que motivó la necesidad de E2E real.
