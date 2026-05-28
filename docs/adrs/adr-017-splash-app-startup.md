---
title: ADR-017 — SplashPage Flutter + AppStartupUseCase
description: >-
  La app tiene una SplashPage como primera ruta que ejecuta un
  AppStartupUseCase: restaura tokens, refresca si expiró, valida sesión y
  decide destino (home o login). Sin "doble splash", sin redirect frágil en
  el router.
---

# ADR-017 — SplashPage Flutter + `AppStartupUseCase`

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 28 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Cuando la app arranca hay que decidir **a qué pantalla llevar al usuario**:

- Si tiene una sesión válida (tokens en almacenamiento seguro, no expirados o refrescables) → `home`.
- Si no tiene sesión o los tokens son irrecuperables → `login`.

Esta decisión requiere operaciones asíncronas (leer `flutter_secure_storage`, posiblemente refrescar tokens contra Keycloak, posiblemente comprobar el endpoint `/me`). El usuario no puede ver una pantalla en blanco durante esos 1-3 segundos.

Hay además un detalle de UX importante: **Android e iOS tienen su propio splash nativo** que se muestra antes de que Flutter arranque. Si la app no añade nada propio, el usuario ve:

1. Splash nativo (logo del SO o del fabricante).
2. **Flash blanco** mientras Flutter inicializa.
3. Pantalla destino (home o login).

Ese flash blanco es feo y delata que el arranque tiene varios pasos sin coordinar.

## Decisión

**Una `SplashPage` Flutter como primera ruta (`/`)** que se renderiza inmediatamente al arrancar Flutter (después del splash nativo) y ejecuta un **`AppStartupUseCase`** que decide a dónde navegar.

```dart
enum StartupDestination { home, login }   // MVP: 2 destinos
```

Flujo:

```text
1. Splash nativo Android/iOS    → mismo color de marca + icono
2. Flutter arranca              → SplashPage visible (logo Custodiam)
3. AppStartupUseCase ejecuta:
   - Restaura tokens del Secure Storage
   - Refresca access token si expiró
   - Valida sesión contra Keycloak (si es necesario)
4. Decide destino:
   - Sesión válida → context.go('/home')
   - Sin sesión   → context.go('/login')
```

**Mitigación del "doble splash"**: el `launch_background.xml` de Android y el `LaunchScreen.storyboard` de iOS usan el **mismo color de fondo** que la `SplashPage` Flutter. El paquete `flutter_native_splash` genera los recursos nativos consistentes con la SplashPage. El usuario percibe una sola pantalla de carga, no dos.

## Justificación

1. **UX uniforme entre fabricantes.** El splash nativo de Android 12+ se renderiza distinto en cada fabricante (MIUI, EMUI, OneUI) — algunos respetan el color de marca, otros le ponen un anillo de iconos, otros redimensionan el icono raro. La `SplashPage` Flutter es **idéntica en todos los dispositivos** porque la pinta el motor Flutter.

2. **Ventana de restauración con branding.** La operación de restaurar la sesión tarda entre 1 y 3 segundos en condiciones normales (más si Keycloak responde lento). Esos segundos se llenan con el logo de Custodiam centrado sobre fondo de marca, en lugar de un flash de pantalla blanca o un flash de la pantalla de login que después es reemplazada por home.

3. **Lógica testeable en use case.** El `AppStartupUseCase` es una clase aislada: recibe `TokenStore`, `AuthService` y `KeycloakClient` por DI ([ADR-012](adr-012-riverpod.md)) y devuelve `StartupDestination`. Es trivialmente testeable sin levantar widget tree. Compárese con la alternativa de poner la lógica en el `redirect` de GoRouter, donde el test requiere widget tests completos.

4. **UI de error de arranque sin crash.** Si la restauración falla (Firebase no inicializa, token corrupto, Keycloak no responde), la SplashPage puede mostrar un mensaje de error con botón de "reintentar" o "ir a login". Un router con redirect en el critical path no tiene un sitio natural para mostrar UI de error.

5. **Separa decisión de navegación del routing.** El router (`go_router`) decide rutas. La SplashPage decide cuándo está listo el estado de la app. Mezclarlos en un `redirect` global obliga al router a tener referencias a `AuthService`, lo que crea acoplamiento que dificulta el testing del propio router.

## Alternativas evaluadas y descartadas

### A. Solo splash nativo, sin SplashPage Flutter

El splash nativo se mantiene visible hasta que Flutter pinta la primera frame.

- **Pros**: cero código Flutter.
- **Contras**: variación entre fabricantes documentada arriba; flash blanco al transicionar; sin UI de error si algo falla en el arranque. Si los tokens tardan en restaurarse, el usuario ve la pantalla de login que después salta a home — peor que ver branding.
- **Descartado por**: UX inferior.

### B. Redirect en el `GoRouter`

```dart
GoRouter(
  redirect: (context, state) async {
    final isAuthenticated = await authService.checkSession();
    if (!isAuthenticated && state.location != '/login') return '/login';
    return null;
  },
  ...
)
```

- **Pros**: lógica centralizada en el router.
- **Contras**: `redirect` no soporta operaciones async limpiamente (se llama en cada navegación, no solo al arranque); acoplamiento del router con `AuthService`; sin lugar para UI de error; difícil de testear sin construir el árbol de widgets entero.
- **Descartado por**: el `redirect` no es el lugar adecuado para lógica de arranque.

### C. SplashScreen plugin (paquete externo)

Hay paquetes que pintan un splash personalizable.

- **Pros**: componente listo.
- **Contras**: dependencia externa para algo que es una `Scaffold` con un `Image` centrado; el componente externo añade su propio modelo mental encima del de Flutter.
- **Descartado por**: la solución es trivial sin dependencia.

### D. Pantalla blanca con `CircularProgressIndicator` mientras se carga

- **Pros**: muy simple.
- **Contras**: ninguna identidad visual; transmite "está cargando" pero no "esta app es Custodiam". Mala primera impresión.
- **Descartado por**: UX inferior.

## Implicaciones operativas

- **`flutter_native_splash` configurado** en `pubspec.yaml` con la imagen del logo y el color de fondo de marca. `flutter pub run flutter_native_splash:create` genera los recursos nativos (`launch_background.xml`, `LaunchScreen.storyboard`).
- **`SplashPage` vive en `lib/features/splash/presentation/`** y consume `appStartupUseCaseProvider` ([ADR-012](adr-012-riverpod.md)).
- **`AppStartupUseCase` en `lib/features/splash/domain/use_cases/`**: clase pura sin dependencias de Flutter. Recibe sus colaboradores por constructor. Devuelve `Future<Result<StartupDestination>>` ([ADR-014](adr-014-result-failure.md)).
- **Tests del use case** con mocks de `TokenStore` y `AuthService`. Cubren los caminos: sesión válida → `home`, sesión expirada refrescable → `home`, sesión expirada no refrescable → `login`, sin tokens → `login`, error de red → estado de error visible.
- **`go_router` inicial apunta a `/`** que renderiza la SplashPage. Tras decidir, la SplashPage hace `context.go('/home')` o `context.go('/login')`. El router no tiene `redirect` global.

## Referencias

- **[`flutter_native_splash` en pub.dev](https://pub.dev/packages/flutter_native_splash)** — genera splash nativos.
- **[Android — Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen)** — splash nativo Android 12+.
- **[Apple — Launch Screen](https://developer.apple.com/design/human-interface-guidelines/launching)** — launch screen iOS.
- **[ADR-012 Riverpod](adr-012-riverpod.md)** — DI del use case.
- **[ADR-014 `Result<T>`](adr-014-result-failure.md)** — tipo de retorno del use case.
