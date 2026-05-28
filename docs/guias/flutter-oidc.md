---
title: Cliente OIDC en Flutter — guía técnica
description: >-
  Implementar el flujo OAuth 2.0 + PKCE con Keycloak en el cliente Flutter
  (Android + iOS + Web). Configuración nativa por plataforma, dos
  implementaciones de AuthService seleccionadas por kIsWeb (mobile con
  deep links + web con sessionStorage para code_verifier), almacenamiento
  seguro de tokens, refresh automático y RBAC con AppPermissionGate.
---

# Cliente OIDC en Flutter

Guía técnica completa para implementar la autenticación OIDC con Keycloak en `custodiam-app`. Cubre la configuración nativa por plataforma (Android, iOS, Web), la asimetría móvil/web del flujo OAuth + PKCE, las dos implementaciones de `AuthService`, el almacenamiento seguro de tokens, el refresh automático, la integración con el cliente HTTP, el router con `/callback` y el sistema de gates de permiso del RBAC del proyecto.

!!! info "Decisiones arquitectónicas relevantes"
    - **[ADR-010 OAuth + PKCE + Keycloak + PyJWT](../adrs/adr-010-oauth-pkce-keycloak.md)** — stack `oauth2 + url_launcher + app_links` para móvil y SPA web.
    - **[ADR-011 Deep links](../adrs/adr-011-deep-links.md)** — custom scheme `es.custodiam://callback` para OAuth + App Links HTTPS para emails.
    - **[ADR-012 Riverpod](../adrs/adr-012-riverpod.md)** — DI + estado reactivo.
    - **[ADR-013 RBAC lockstep](../adrs/adr-013-rbac-lockstep.md)** — `Permission` enum espejo del backend, gates declarativos.
    - **[ADR-022 iOS 15 mínimo](../adrs/adr-022-ios-15.md)** — versión mínima soportada.
    - **[ADR-023 OAuth web vs móvil](../adrs/adr-023-oauth-web-asimetria.md)** — dos implementaciones de `AuthService` por `kIsWeb` + persistencia del `code_verifier` en `sessionStorage`.
    - **[ADR-024 Patrol E2E](../adrs/adr-024-patrol-e2e.md)** — framework de testing end-to-end para los tres escenarios del DoD.

## Prerrequisitos

- Realm Keycloak operativo con el cliente `custodiam-app` configurado ([Configuración de Keycloak](configuracion-keycloak.md)).
- Proyecto Flutter creado con la arquitectura interna Clean + Riverpod + `Result<T>` + `EnvConfig`.
- Docker Compose levantado con Keycloak accesible.

## Qué consigues al terminar

- Login vía Keycloak con Authorization Code + PKCE (abre navegador, el usuario se autentica, vuelve a la app).
- Logout con cierre de sesión en Keycloak.
- Almacenamiento seguro de tokens (Keychain iOS, EncryptedSharedPreferences Android, IndexedDB cifrado web).
- Refresh automático del access token cuando expira.
- Persistencia de sesión entre reinicios.
- `ApiClient` que añade el token automáticamente a cada request y maneja el refresh + retry en `401`.
- `LoginPage` construida solo con componentes `App*` del Design System.
- `SplashPage` decidiendo `/home` o `/login` según el estado real de la sesión.
- Configuración nativa para Android, iOS y Web.
- `AppPermissionGate` para mostrar/ocultar UI según los permisos del usuario actual.

## Conceptos: cómo funciona el login

```text
1. El usuario pulsa "Iniciar sesión" en la app.
2. La app abre el navegador del sistema con la URL de Keycloak.
3. El usuario escribe su usuario y contraseña EN KEYCLOAK (no en nuestra app).
4. Keycloak verifica las credenciales.
5. Keycloak redirige de vuelta a la app con un "código de autorización".
6. La app intercambia el código + code_verifier por tokens (access_token + refresh_token).
7. La app guarda los tokens de forma segura.
8. Todas las llamadas a la API llevan el access_token en el header.
```

**Por qué abrir el navegador**: para que la app **nunca vea la contraseña**. Keycloak se encarga de la autenticación y nuestra app solo recibe tokens. Es el estándar OAuth 2.0 / OIDC.

**Qué es PKCE**: es una protección extra que evita el *scheme hijacking* en clientes públicos. Detalle conceptual en [ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md). El paquete [`oauth2`](https://pub.dev/packages/oauth2) lo gestiona automáticamente cuando se crea el `AuthorizationCodeGrant` sin secret.

## La asimetría móvil/web

El flujo OAuth + PKCE se comporta de forma distinta en móvil y en web. Es **el detalle más importante** de esta guía y la razón de tener dos implementaciones de `AuthService` ([ADR-023](../adrs/adr-023-oauth-web-asimetria.md)).

### Móvil (Android + iOS)

`launchUrl(authUrl, mode: LaunchMode.externalApplication)` abre el navegador externo. La app Flutter **sigue viva en memoria**, esperando el callback por *deep link* a través de `app_links`. Al volver del navegador, el método `_pendingGrant.handleAuthorizationResponse()` se ejecuta dentro de la misma instancia que conserva el `code_verifier` PKCE generado al inicio del flujo.

### Web (Flutter Web)

`launchUrl(authUrl, webOnlyWindowName: '_self')` **sustituye la pestaña actual** por la URL de Keycloak. Cuando Keycloak redirige de vuelta a `/callback`, el navegador carga la aplicación Flutter **completamente desde cero**: una nueva instancia de `KeycloakWebAuthService` se crea con `_pendingGrant == null`. Para que el flujo funcione, el `code_verifier` debe **persistirse en `window.sessionStorage`** antes del redirect y leerse de vuelta tras la nueva carga.

```text
Móvil: app viva → navegador → app misma instancia → code_verifier en memoria → OK
Web:   app viva → navegador → recarga app desde cero → ❌ code_verifier perdido
       ╰────────────── solución: sessionStorage ────────────────╯
```

`sessionStorage` se elige sobre `localStorage` por su semántica precisa: vida útil ligada a la pestaña del navegador (se limpia al cerrarla), no se sincroniza entre pestañas y desaparece automáticamente sin que la app tenga que limpiarlo en caminos de error.

## Mapa arquitectónico

```text
lib/
├── infrastructure/
│   ├── auth/
│   │   ├── auth_service.dart                       # interface invariante
│   │   ├── auth_failure.dart                       # AuthFailure.userCancelled, .sessionStorageUnavailable, ...
│   │   ├── keycloak_config.dart                    # endpoints derivados de EnvConfig
│   │   ├── token_store.dart                        # wrapper sobre FlutterSecureStorage
│   │   ├── keycloak_mobile_auth_service.dart       # flujo móvil con deep links
│   │   ├── keycloak_web_auth_service.dart          # flujo web con sessionStorage
│   │   ├── session_storage_gateway.dart            # interface del gateway de sessionStorage
│   │   ├── web_session_storage_gateway.dart        # impl web (importa package:web)
│   │   ├── stub_session_storage_gateway.dart       # stub VM (sin package:web)
│   │   ├── current_user.dart                       # claims decodificados del JWT
│   │   ├── jwt_claims.dart                         # decodificación segura del JWT
│   │   └── permissions.dart                        # enum Permission + matriz roles → permisos
│   ├── di/
│   │   └── providers.dart                          # authServiceProvider selecciona por kIsWeb
│   ├── network/
│   │   └── api_client.dart                         # getValidAccessToken antes de cada request
│   └── error/
│       └── failure.dart                            # AuthFailure como subtipo de Failure
├── features/
│   └── auth/
│       └── presentation/
│           ├── pages/
│           │   └── login_page.dart                 # UI con App* components
│           └── viewmodels/
│               ├── auth_di.dart                    # providers de la feature
│               └── auth_view_model.dart            # AsyncNotifier orquesta login/logout
├── core/
│   ├── config/
│   │   └── env_config.dart                         # keycloakRealm + keycloakClientId
│   └── ui/                                         # Design System App*
└── app/
    └── router.dart                                 # GoRouter con /callback para web
```

**Patrón clave**: el contrato (`AuthService`) es el mismo en las dos plataformas. La diferencia operativa (¿la app sigue viva durante el redirect a Keycloak?) es **explícita en el tipo de la implementación**, no oculta en ramas `kIsWeb` que comparten estado por accidente. Es la aplicación de Clean Architecture al problema concreto descrito en [ADR-023](../adrs/adr-023-oauth-web-asimetria.md).

## Paso 1 — Dependencias

`pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_web_plugins:
    sdk: flutter

  # State management
  flutter_riverpod: ^2.6.0

  # OAuth + PKCE
  oauth2: ^2.0.3
  url_launcher: ^6.3.1
  app_links: ^6.3.3            # solo móvil — captura deep link es.custodiam://callback

  # Storage seguro
  flutter_secure_storage: ^10.0.0

  # OIDC web — sessionStorage para code_verifier
  web: ^1.1.0                  # solo se importa desde web_session_storage_gateway.dart

  # JWT (decodificación local, sin validar firma — el backend valida)
  jwt_decoder: ^2.0.1

  # Routing
  go_router: ^17.1.0
```

Tras editar:

```bash
flutter pub get
flutter analyze   # debe quedar limpio
```

!!! warning "Regla crítica con `package:web`"
    `package:web` **solo compila para target web**. Importarlo al top level de cualquier archivo que se cargue desde código no-web (incluida la suite de tests unitarios, que corre en Dart VM) hace que el compilador VM muera sin diagnóstico útil. La implementación real va en su propio archivo (`web_session_storage_gateway.dart`) y se importa **condicionalmente** desde `providers.dart` con `if (dart.library.js_interop)`. Detalle completo en [Paso 7](#paso-7-selector-kisweb-en-authserviceprovider).

## Paso 2 — Configuración nativa por plataforma

### Android — `AndroidManifest.xml`

Edita `android/app/src/main/AndroidManifest.xml`. Dentro de `<activity android:name=".MainActivity">` **añade** este `intent-filter` (sin tocar los existentes):

```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="es.custodiam" android:host="callback" />
</intent-filter>
```

Cuando Keycloak redirige a `es.custodiam://callback`, Android sabe que tiene que devolver el control a la app pasándole la URL.

### iOS — `Info.plist`

Edita `ios/Runner/Info.plist`. Dentro del `<dict>` raíz **añade**:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLName</key>
        <string>es.custodiam</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>es.custodiam</string>
        </array>
    </dict>
</array>
```

Versión mínima de iOS: 15.0 ([ADR-022](../adrs/adr-022-ios-15.md)).

### Web — `PathUrlStrategy` obligatoria

En web, Keycloak redirige a `${Uri.base.origin}/callback`. El router de la app captura `/callback` y procesa el código. **Pero esto solo funciona si la app declara `PathUrlStrategy`** — el default de Flutter Web es `HashUrlStrategy`, que reescribe las rutas a `/#/login`, `/#/callback`, etc. y hace que `GoRouter` no matchee el path crudo que devuelve Keycloak.

```dart title="lib/main.dart"
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'package:custodiam/app/app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  usePathUrlStrategy();                  // OBLIGATORIO en web, no-op en mobile
  runApp(
    const ProviderScope(
      child: CustodiamApp(),
    ),
  );
}
```

**Por qué es necesario en web pero no en móvil**: OAuth ([RFC 6749 §3.1.2](https://datatracker.ietf.org/doc/html/rfc6749#section-3.1.2)) **prohíbe fragmentos (`#`) en `redirect_uri`** — el IdP nunca va a devolver `/#/callback`. En móvil esto no importa porque los deep links los entrega el SO directamente al listener `AppLinks` sin pasar por un router HTTP. En web, la única forma de que `/callback` matchee `GoRoute(path: '/callback')` es declarar `PathUrlStrategy` explícitamente. La función es segura en todas las plataformas; en móvil carga un stub no-op.

**Contrato implícito con el servidor**: activar `PathUrlStrategy` obliga a que el servidor que sirve la PWA haga **SPA fallback** (servir `index.html` para cualquier ruta desconocida). En desarrollo `flutter run -d chrome --web-port=3000` lo hace automáticamente. En producción, el nginx que sirve `custodiam-web` ya está configurado con `try_files $uri /index.html` ([ADR-006](../adrs/adr-006-nginx-alpine.md)).

### Puerto 3000 en dev local

Cualquier origen que sirva la app debe estar registrado como `redirect_uri` válida en el cliente `custodiam-app` de Keycloak:

| Origen | Uso |
| --- | --- |
| `es.custodiam://callback` | Móvil (Android + iOS) |
| `http://localhost:3000/callback` | Dev local — puerto fijo 3000 |
| `https://app.custodiam.es/callback` | Producción |

**Importante para dev local**: `flutter run -d chrome` asigna un **puerto random** cada arranque (`:54321`, `:48132`, …). Si tu puerto no coincide con `:3000` el redirect a Keycloak da `Invalid parameter: redirect_uri`. Solución: forzar siempre el mismo puerto.

```bash
# Liberar el puerto 3000 del contenedor web del stack dev
cd custodiam-workspace/custodiam-infra
docker compose stop custodiam-web

# Lanzar el dev server Flutter en :3000
cd ../custodiam-app
flutter run -d chrome --web-port=3000
```

Nuevos dominios (staging, preview deploys) requieren registro adicional en el realm Keycloak ([Configuración de Keycloak — Paso 8](configuracion-keycloak.md#paso-8-cliente-custodiam-app-publico-pkce)).

## Paso 3 — Ampliar `EnvConfig`

El `EnvConfig` ([ADR-015](../adrs/adr-015-env-config.md)) ya expone `apiBaseUrl` y `keycloakBaseUrl`. Añadir el realm y el client id:

```dart title="lib/core/config/env_config.dart (añadir)"
class EnvConfig {
  // ... apiBaseUrl, keycloakBaseUrl, ...

  static const String keycloakRealm = String.fromEnvironment(
    'KEYCLOAK_REALM',
    defaultValue: 'custodiam',
  );

  static const String keycloakClientId = String.fromEnvironment(
    'KEYCLOAK_CLIENT_ID',
    defaultValue: 'custodiam-app',
  );
}
```

Build de producción:

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es \
  --dart-define=KEYCLOAK_REALM=custodiam \
  --dart-define=KEYCLOAK_CLIENT_ID=custodiam-app
```

## Paso 4 — `KeycloakConfig` — endpoints derivados de `EnvConfig`

```dart title="lib/infrastructure/auth/keycloak_config.dart"
import 'package:flutter/foundation.dart' show kIsWeb;

import '../../core/config/env_config.dart';

class KeycloakConfig {
  KeycloakConfig._();

  static String get realmBase =>
      '${EnvConfig.keycloakBaseUrl}/realms/${EnvConfig.keycloakRealm}';

  static String get _oidcBase => '$realmBase/protocol/openid-connect';

  static Uri get authorizationEndpoint => Uri.parse('$_oidcBase/auth');
  static Uri get tokenEndpoint => Uri.parse('$_oidcBase/token');
  static Uri get endSessionEndpoint => Uri.parse('$_oidcBase/logout');

  /// Scopes que la app pide al hacer login.
  /// - openid: obligatorio.
  /// - profile: given_name, family_name.
  /// - email: email, email_verified.
  /// Los roles llegan vía mapper `realm-roles` del client scope
  /// `custodiam-roles`; no es un scope.
  static const List<String> scopes = ['openid', 'profile', 'email'];

  /// URI de callback según plataforma.
  /// - Móvil: deep link con custom scheme.
  /// - Web: origin actual + /callback (funciona dev y prod sin tocar código).
  static Uri get redirectUri {
    if (kIsWeb) {
      return Uri.parse('${Uri.base.origin}/callback');
    }
    return Uri.parse('es.custodiam://callback');
  }

  static Uri get postLogoutRedirectUri {
    if (kIsWeb) {
      return Uri.parse(Uri.base.origin);
    }
    return Uri.parse('es.custodiam://logout');
  }
}
```

## Paso 5 — `TokenStore`

Wrapper sobre `FlutterSecureStorage` que persiste las credenciales OAuth serializadas. El JSON incluye `access_token`, `refresh_token`, `expiry` y `scopes`; lo produce `Credentials.toJson()` y se rehidrata con `Credentials.fromJson()`.

```dart title="lib/infrastructure/auth/token_store.dart"
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStore {
  TokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'custodiam.oauth.credentials';
  final FlutterSecureStorage _storage;

  Future<String?> read() => _storage.read(key: _key);

  Future<void> write(String credentialsJson) =>
      _storage.write(key: _key, value: credentialsJson);

  Future<void> clear() => _storage.delete(key: _key);
}
```

En iOS usa Keychain, en Android `EncryptedSharedPreferences`, en web IndexedDB cifrado por el SO/navegador. Es el patrón canónico de `flutter_secure_storage`.

## Paso 6 — `AuthService` y `AuthFailure`

### Interface invariante

```dart title="lib/infrastructure/auth/auth_service.dart"
import '../error/failure.dart';

abstract class AuthService {
  /// Inicia el flujo de login. En móvil abre el navegador y espera el
  /// deep link; en web redirige a Keycloak con `_self` y persiste el
  /// code_verifier en sessionStorage.
  Future<Result<void>> login();

  /// Procesa el callback (solo relevante en web). En móvil es no-op.
  Future<Result<void>> handleWebCallback(Uri uri);

  /// Devuelve un access_token válido. Si está expirado, hace refresh
  /// transparentemente.
  Future<Result<String>> getValidAccessToken();

  /// Cierra la sesión en Keycloak y borra los tokens locales.
  Future<Result<void>> logout();

  /// Estado observable de la sesión.
  Stream<bool> get isAuthenticatedStream;
  bool get isAuthenticated;

  /// Claims decodificados del JWT — null si no hay sesión activa.
  CurrentUser? get currentUser;
}
```

### `AuthFailure` (jerarquía sellada)

```dart title="lib/infrastructure/error/auth_failure.dart"
sealed class AuthFailure extends Failure {
  const AuthFailure();

  const factory AuthFailure.sessionExpired() = _SessionExpired;
  const factory AuthFailure.userCancelled() = _UserCancelled;
  const factory AuthFailure.browserError(String message) = _BrowserError;
  const factory AuthFailure.invalidGrant() = _InvalidGrant;
  const factory AuthFailure.refreshFailed() = _RefreshFailed;
  const factory AuthFailure.sessionStorageUnavailable() = _SessionStorageUnavailable;
}
```

`sessionStorageUnavailable` es el caso de error específico de web ([ADR-023](../adrs/adr-023-oauth-web-asimetria.md)): si el navegador del usuario tiene `sessionStorage` deshabilitado (modo privado en algunos navegadores, configuración corporativa), el flujo no puede completar. La UI debe mostrar un mensaje claro en este caso.

## Paso 6.A — `KeycloakMobileAuthService`

Implementación para Android e iOS. Mantiene `_pendingGrant` en memoria porque la app sobrevive a la redirección al navegador.

```dart title="lib/infrastructure/auth/keycloak_mobile_auth_service.dart (esquema)"
class KeycloakMobileAuthService implements AuthService {
  KeycloakMobileAuthService({
    required TokenStore tokenStore,
    AppLinks? appLinks,
    LaunchUrlFn? launcher,
  })  : _tokenStore = tokenStore,
        _appLinks = appLinks ?? AppLinks(),
        _launcher = launcher ?? launchUrl;

  oauth2.AuthorizationCodeGrant? _pendingGrant;
  oauth2.Client? _client;
  // ...

  @override
  Future<Result<void>> login() async {
    _pendingGrant = oauth2.AuthorizationCodeGrant(
      EnvConfig.keycloakClientId,
      KeycloakConfig.authorizationEndpoint,
      KeycloakConfig.tokenEndpoint,
      // PKCE automático para clientes públicos (sin secret).
    );

    final authUrl = _pendingGrant!.getAuthorizationUrl(
      KeycloakConfig.redirectUri,
      scopes: KeycloakConfig.scopes,
    );

    // Escuchar el deep link es.custodiam://callback ANTES de abrir el browser.
    _deepLinkSubscription = _appLinks.uriLinkStream.listen(_handleMobileCallback);

    final launched = await _launcher(
      authUrl,
      mode: LaunchMode.externalApplication,
    );

    if (!launched) {
      return const Fail(AuthFailure.browserError('No se pudo abrir el navegador'));
    }
    return const Success(null);
  }

  Future<void> _handleMobileCallback(Uri uri) async {
    if (_pendingGrant == null) return;
    try {
      _client = await _pendingGrant!.handleAuthorizationResponse(
        uri.queryParameters,
      );
      await _tokenStore.write(_client!.credentials.toJson());
      _authStateController.add(true);
    } on oauth2.AuthorizationException catch (e) {
      // user_denied, invalid_grant, ...
      _emitFailure(e);
    } finally {
      _pendingGrant = null;
      await _deepLinkSubscription?.cancel();
    }
  }

  @override
  Future<Result<void>> handleWebCallback(Uri uri) async {
    // No-op en móvil — el deep link lo gestiona AppLinks.
    return const Success(null);
  }

  // getValidAccessToken, logout, isAuthenticated, currentUser ...
}
```

Detalle clave: `_pendingGrant` se mantiene en memoria entre `login()` y `_handleMobileCallback()` porque la app **no se reinicia** al volver del navegador externo. El `code_verifier` PKCE vive dentro del `_pendingGrant`.

## Paso 6.B — `KeycloakWebAuthService`

Implementación para Flutter Web. **El `code_verifier` se persiste en `sessionStorage`** antes del redirect porque el navegador recarga la app completa al volver del callback.

### Gateway aislado para `sessionStorage`

`package:web` solo compila para web. La implementación se aísla en su propio archivo:

```dart title="lib/infrastructure/auth/session_storage_gateway.dart"
abstract class SessionStorageGateway {
  bool get available;
  String? read(String key);
  void write(String key, String value);
  void remove(String key);
}
```

```dart title="lib/infrastructure/auth/web_session_storage_gateway.dart"
// Este archivo SOLO se importa cuando dart.library.js_interop está disponible.
import 'package:web/web.dart' as web;

import 'session_storage_gateway.dart';

class WebSessionStorageGateway implements SessionStorageGateway {
  @override
  bool get available {
    try {
      web.window.sessionStorage.setItem('__custodiam_probe', '1');
      web.window.sessionStorage.removeItem('__custodiam_probe');
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  String? read(String key) => web.window.sessionStorage.getItem(key);

  @override
  void write(String key, String value) =>
      web.window.sessionStorage.setItem(key, value);

  @override
  void remove(String key) => web.window.sessionStorage.removeItem(key);
}
```

```dart title="lib/infrastructure/auth/stub_session_storage_gateway.dart"
import 'session_storage_gateway.dart';

/// Stub para target VM (tests, build mobile). Siempre `available: false`
/// — pero los tests inyectan InMemorySessionStorageGateway por DI.
class StubSessionStorageGateway implements SessionStorageGateway {
  @override
  bool get available => false;

  @override
  String? read(String key) => null;

  @override
  void write(String key, String value) {}

  @override
  void remove(String key) {}
}
```

### Implementación web del `AuthService`

```dart title="lib/infrastructure/auth/keycloak_web_auth_service.dart (esquema)"
class KeycloakWebAuthService implements AuthService {
  KeycloakWebAuthService({
    required TokenStore tokenStore,
    required SessionStorageGateway sessionStorage,
    LaunchUrlFn? launcher,
  })  : _tokenStore = tokenStore,
        _sessionStorage = sessionStorage,
        _launcher = launcher ?? launchUrl;

  static const _codeVerifierKey = 'custodiam.oauth.code_verifier';

  @override
  Future<Result<void>> login() async {
    if (!_sessionStorage.available) {
      return const Fail(AuthFailure.sessionStorageUnavailable());
    }

    final grant = oauth2.AuthorizationCodeGrant(
      EnvConfig.keycloakClientId,
      KeycloakConfig.authorizationEndpoint,
      KeycloakConfig.tokenEndpoint,
    );

    final authUrl = grant.getAuthorizationUrl(
      KeycloakConfig.redirectUri,
      scopes: KeycloakConfig.scopes,
    );

    // CRÍTICO — persistir el code_verifier ANTES del redirect.
    _sessionStorage.write(_codeVerifierKey, grant.codeVerifier);

    final launched = await _launcher(
      authUrl,
      webOnlyWindowName: '_self',
    );

    if (!launched) {
      _sessionStorage.remove(_codeVerifierKey);
      return const Fail(AuthFailure.browserError('No se pudo redirigir'));
    }
    // El navegador ya está cargando la URL de Keycloak. Volveremos
    // a /callback en una nueva instancia de la app.
    return const Success(null);
  }

  @override
  Future<Result<void>> handleWebCallback(Uri uri) async {
    final codeVerifier = _sessionStorage.read(_codeVerifierKey);
    if (codeVerifier == null) {
      // Llegada huérfana a /callback (nunca pulsó login).
      return const Fail(AuthFailure.invalidGrant());
    }

    // Reconstruir el grant con el code_verifier persistido.
    final grant = oauth2.AuthorizationCodeGrant(
      EnvConfig.keycloakClientId,
      KeycloakConfig.authorizationEndpoint,
      KeycloakConfig.tokenEndpoint,
      codeVerifier: codeVerifier,
    );

    // El grant exige llamar a getAuthorizationUrl una vez antes de
    // handleAuthorizationResponse, aunque no se use.
    grant.getAuthorizationUrl(
      KeycloakConfig.redirectUri,
      scopes: KeycloakConfig.scopes,
    );

    try {
      final client = await grant.handleAuthorizationResponse(uri.queryParameters);
      await _tokenStore.write(client.credentials.toJson());
      _authStateController.add(true);
      return const Success(null);
    } on oauth2.AuthorizationException {
      return const Fail(AuthFailure.invalidGrant());
    } finally {
      _sessionStorage.remove(_codeVerifierKey);
    }
  }

  // getValidAccessToken, logout, ...
}
```

## Paso 7 — Selector `kIsWeb` en `authServiceProvider`

`providers.dart` selecciona la implementación correcta en runtime. El import de `WebSessionStorageGateway` es **condicional**:

```dart title="lib/infrastructure/di/providers.dart"
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_service.dart';
import '../auth/keycloak_mobile_auth_service.dart';
import '../auth/keycloak_web_auth_service.dart';
import '../auth/session_storage_gateway.dart';
import '../auth/stub_session_storage_gateway.dart'
    if (dart.library.js_interop) '../auth/web_session_storage_gateway.dart';
import '../auth/token_store.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore());

final sessionStorageProvider = Provider<SessionStorageGateway>((ref) {
  // En target web carga WebSessionStorageGateway por el conditional import;
  // en VM/mobile carga StubSessionStorageGateway sin tocar package:web.
  if (kIsWeb) {
    return WebSessionStorageGateway();
  }
  return StubSessionStorageGateway();
});

final authServiceProvider = Provider<AuthService>((ref) {
  final tokenStore = ref.read(tokenStoreProvider);
  if (kIsWeb) {
    return KeycloakWebAuthService(
      tokenStore: tokenStore,
      sessionStorage: ref.read(sessionStorageProvider),
    );
  }
  return KeycloakMobileAuthService(tokenStore: tokenStore);
});
```

El truco del `conditional import` (`import '...stub' if (dart.library.js_interop) '...real'`) es lo que permite que la suite de tests VM compile sin que `package:web` se materialice nunca en su grafo de imports.

## Paso 8 — `ApiClient` consume `AuthService`

El wrapper HTTP ([ADR-004](../adrs/adr-004-http-cliente.md)) llama a `getValidAccessToken()` antes de cada request y maneja el refresh + retry en `401`:

```dart title="lib/infrastructure/network/api_client.dart (esquema)"
class ApiClient {
  ApiClient(this._authService, this._httpClient);

  final AuthService _authService;
  final http.Client _httpClient;

  Future<Map<String, dynamic>> get(String path) async {
    return _withAuth((token) => _httpClient.get(
      Uri.parse('${EnvConfig.apiBaseUrl}$path'),
      headers: {
        'Authorization': 'Bearer $token',
        'Accept': 'application/json',
      },
    ));
  }

  Future<Map<String, dynamic>> _withAuth(
    Future<http.Response> Function(String token) request,
  ) async {
    final tokenResult = await _authService.getValidAccessToken();
    final token = switch (tokenResult) {
      Success(:final value) => value,
      Fail() => throw UnauthenticatedException(),
    };

    var response = await request(token);

    if (response.statusCode == 401) {
      // El access token podría haber expirado entre getValid() y el send.
      // Reintentar UNA vez con refresh forzado.
      final retryResult = await _authService.getValidAccessToken();
      final retryToken = switch (retryResult) {
        Success(:final value) => value,
        Fail() => throw UnauthenticatedException(),
      };
      response = await request(retryToken);
      if (response.statusCode == 401) throw UnauthenticatedException();
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
```

## Paso 9 — Router con `/callback`

`GoRouter` necesita una ruta `/callback` que delegue en `KeycloakWebAuthService.handleWebCallback`:

```dart title="lib/app/router.dart (esquema)"
GoRouter buildRouter(Ref ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginPage(),
      ),
      GoRoute(
        path: '/home',
        builder: (_, __) => const HomePage(),
      ),
      GoRoute(
        path: '/callback',
        builder: (context, state) {
          // Solo se activa en web. El uri completo viene en state.uri.
          ref.read(authViewModelProvider.notifier).handleCallback(state.uri);
          return const _CallbackHandlerPage();
        },
      ),
    ],
  );
}
```

`_CallbackHandlerPage` muestra un spinner mientras el `AuthViewModel` procesa el callback. Tras éxito redirige a `/home`; en error a `/login` con el mensaje.

## Paso 10 — `AuthViewModel`

`AsyncNotifier` que orquesta login/logout/callback ([ADR-012](../adrs/adr-012-riverpod.md)):

```dart title="lib/features/auth/presentation/viewmodels/auth_view_model.dart (esquema)"
class AuthViewModel extends AsyncNotifier<bool> {
  @override
  Future<bool> build() async {
    final authService = ref.read(authServiceProvider);
    return authService.isAuthenticated;
  }

  Future<void> login() async {
    state = const AsyncLoading();
    final result = await ref.read(authServiceProvider).login();
    state = switch (result) {
      Success() => const AsyncData(true),
      Fail(:final failure) => AsyncError(failure, StackTrace.current),
    };
  }

  Future<void> handleCallback(Uri uri) async {
    state = const AsyncLoading();
    final result = await ref.read(authServiceProvider).handleWebCallback(uri);
    state = switch (result) {
      Success() => const AsyncData(true),
      Fail(:final failure) => AsyncError(failure, StackTrace.current),
    };
    if (state.hasValue && state.value!) {
      ref.read(routerProvider).go('/home');
    }
  }

  Future<void> logout() async { /* ... */ }
}
```

## Paso 11 — `LoginPage`

UI con componentes `App*` del Design System ([ADR-018](../adrs/adr-018-design-system.md)):

```dart title="lib/features/auth/presentation/pages/login_page.dart (esquema)"
class LoginPage extends ConsumerWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authViewModelProvider);

    // Mostrar SnackBar en caso de error específico
    ref.listen(authViewModelProvider, (_, next) {
      if (next.hasError && next.error is AuthFailure) {
        AppSnackbar.error(context, failureToUserMessage(next.error as Failure));
      }
    });

    return AppPageScaffold(
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AppLogo(),
            const SizedBox(height: AppSpacing.xl),
            Text('Custodiam', style: Theme.of(context).textTheme.headlineLarge),
            const SizedBox(height: AppSpacing.md),
            AppPrimaryButton(
              label: 'Iniciar sesión',
              loading: authState.isLoading,
              onPressed: () =>
                  ref.read(authViewModelProvider.notifier).login(),
            ),
          ],
        ),
      ),
    );
  }
}
```

## Paso 12 — Tests

La pirámide de tests del repo ([ADR-024](../adrs/adr-024-patrol-e2e.md)):

- **Unit + widget** (`test/`): mocks de `AuthService`, `TokenStore`, `SessionStorageGateway`. Cubren los caminos felices y los `AuthFailure` con `mocktail`. No tocan red.
- **Integración** (`patrol_test/auth/`): contra mock OIDC server levantado con `docker compose --profile test`.
- **E2E web** (`patrol_test/web/`): tres escenarios del DoD ejercitados con Chromium real:
    1. Login feliz hasta `/home`.
    2. Llegada huérfana a `/callback` (sin pasar por login) → mensaje de error.
    3. `sessionStorage` deshabilitado → `AuthFailure.sessionStorageUnavailable` + `AppSnackbar`.

Para el caso 3, el test inyecta `InMemorySessionStorageGateway(available: false)` vía `ProviderScope.overrides`, no manipula el browser real (el `WebAutomator` de Patrol no expone `runJsInBrowser`).

## Verificación final

- [ ] Configuración nativa Android (`intent-filter` para `es.custodiam://callback`).
- [ ] Configuración nativa iOS (`CFBundleURLTypes`).
- [ ] `usePathUrlStrategy()` en `main.dart` para web.
- [ ] Las tres `redirect_uri` registradas en Keycloak (`es.custodiam://callback`, `http://localhost:3000/callback`, `https://app.custodiam.es/callback`).
- [ ] `flutter run -d chrome --web-port=3000` arranca y permite login completo.
- [ ] `flutter run` en Android device físico permite login completo via Custom Tab.
- [ ] Tras logout, los tokens del `TokenStore` quedan limpios.
- [ ] El `ApiClient` adjunta el `Authorization: Bearer <token>` en todas las requests.
- [ ] `flutter test` pasa con los mocks de `AuthService`.
- [ ] `flutter analyze` sin errores.

## Anexo — `CurrentUser` y `AppPermissionGate`

El cliente Flutter espeja la matriz rol → permisos del backend ([ADR-013](../adrs/adr-013-rbac-lockstep.md)). Los permisos se evalúan localmente desde los roles del JWT — el backend revalida en cada request.

### `Permission` enum

```dart title="lib/infrastructure/auth/permissions.dart (extracto)"
enum Permission {
  voluntariosCrear('voluntarios.crear'),
  voluntariosEditar('voluntarios.editar'),
  // ... 40 permisos en total
  ;

  final String value;
  const Permission(this.value);
}

const Map<String, Set<Permission>> rolePermissions = {
  'voluntario': {Permission.serviciosApuntarsePropio, /* ... */},
  'jefe_equipo': {Permission.voluntariosVer, Permission.serviciosCrear, /* ... */},
  // ... 12 roles
  'admin': {Permission.sistemaAdmin, /* ... */},
};

Set<Permission> permissionsForRoles(Iterable<String> roles) {
  final result = <Permission>{};
  for (final role in roles) {
    result.addAll(rolePermissions[role] ?? const {});
  }
  return result;
}
```

### `CurrentUser` decodificado del JWT

```dart title="lib/infrastructure/auth/current_user.dart (esquema)"
class CurrentUser {
  CurrentUser({
    required this.id,
    required this.username,
    required this.email,
    required this.givenName,
    required this.familyName,
    required this.roles,
  });

  final String id;            // sub del JWT
  final String username;      // preferred_username
  final String email;
  final String givenName;
  final String familyName;
  final List<String> roles;

  late final Set<Permission> permissions = permissionsForRoles(roles);

  bool hasPermission(Permission p) => permissions.contains(p);

  factory CurrentUser.fromJwt(Map<String, dynamic> claims) {
    return CurrentUser(
      id: claims['sub'] as String,
      username: claims['preferred_username'] as String,
      email: claims['email'] as String,
      givenName: claims['given_name'] as String? ?? '',
      familyName: claims['family_name'] as String? ?? '',
      roles: (claims['roles'] as List?)?.cast<String>() ?? const [],
    );
  }
}
```

### `AppPermissionGate` declarativo

```dart title="lib/core/ui/AppPermissionGate.dart (esquema)"
class AppPermissionGate extends ConsumerWidget {
  const AppPermissionGate({
    required this.permission,
    required this.child,
    this.fallback,
    super.key,
  });

  final Permission permission;
  final Widget child;
  final Widget? fallback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    if (user != null && user.hasPermission(permission)) {
      return child;
    }
    return fallback ?? const SizedBox.shrink();
  }
}
```

Uso en cualquier feature:

```dart
AppPermissionGate(
  permission: Permission.voluntariosCrear,
  child: AppPrimaryButton(
    label: 'Crear voluntario',
    onPressed: () => context.go('/voluntarios/nuevo'),
  ),
)
```

Concentra la lógica de RBAC en un solo widget, evita esparcir `if (currentUser.hasPermission(...))` por toda la UI y permite testear con un único patrón (`pumpRiverpod` + override del `currentUserProvider` + `find.byType(AppPermissionGate)`).

## Problemas comunes

### `Invalid redirect URI` al hacer login

- Verificar que la URI esté exactamente en *Valid redirect URIs* del cliente `custodiam-app` en Keycloak.
- En web local con `flutter run -d chrome`: forzar `--web-port=3000` para que coincida con el registro del cliente.
- En móvil: confirmar `es.custodiam://callback` (no `custodiam://callback`).

### En móvil el callback no llega

- Verificar el `intent-filter` en `AndroidManifest.xml` con `android:scheme="es.custodiam"` y `android:host="callback"`.
- Verificar `CFBundleURLSchemes` en `Info.plist` con `es.custodiam`.
- Comprobar que `AppLinks().uriLinkStream.listen(...)` se suscribe **antes** de abrir el navegador.

### El token no llega al backend

- Verificar que el `ApiClient` adjunta `Authorization: Bearer <token>` en las cabeceras.
- En las DevTools del navegador (web) o en `dev.log(name: 'API')` (móvil), comprobar las requests reales.
- Si el backend devuelve `401`, verificar el `azp` check ([ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)) — el cliente del token debe coincidir con `KEYCLOAK_AUTHORIZED_PARTY` del backend.

### Web: Keycloak no abre

- Comprobar que el navegador no esté bloqueando popups (debería usar `webOnlyWindowName: '_self'`, no `'_blank'`).
- Verificar `EnvConfig.keycloakBaseUrl` con `dev.log(name: 'Auth')`.

### Web: la app vuelve a `/login` tras autenticar en Keycloak

Síntoma: el browser entra a Keycloak, el usuario se autentica, vuelve a `/callback`, pero la app rebota a `/login` sin error visible. Causa más probable: `code_verifier` no se persistió o se perdió.

- Comprobar que `usePathUrlStrategy()` está en `main.dart` antes de `runApp()`.
- Comprobar que `KeycloakWebAuthService.login()` invoca `_sessionStorage.write(_codeVerifierKey, grant.codeVerifier)` antes de `_launcher(...)`.
- En DevTools → Application → Session Storage, verificar que la clave `custodiam.oauth.code_verifier` existe **antes** del redirect.

### Web: `sessionStorage` deshabilitado

Algunos navegadores en modo privado / configuración corporativa devuelven excepción al escribir en `sessionStorage`. El `WebSessionStorageGateway` lo detecta con un probe `setItem` + `removeItem` y devuelve `available: false`. El `KeycloakWebAuthService.login()` retorna `AuthFailure.sessionStorageUnavailable` y la UI muestra `AppSnackbar` con un mensaje explicativo.

### `flutter test` falla con "The Dart compiler exited unexpectedly"

Causa: algún archivo del grafo de imports importa `package:web` al top level. Solo se debe importar desde `web_session_storage_gateway.dart` y consumirlo desde `providers.dart` con conditional import. Buscar `import 'package:web/web.dart'` en `lib/` — solo debe existir en ese archivo.

### `flutter analyze` se queja por `package:web`

Comprobar el constraint `web: ^1.1.0` en `pubspec.yaml`. La rama 0.x usa nombres distintos para los símbolos.

### Tests E2E web requieren browser real

Los tests bajo `patrol_test/web/` son **E2E reales** y solo corren bajo `patrol test --target patrol_test/web/ --device chrome --web-headless=true`, no bajo `flutter test`. Detalle en [ADR-024](../adrs/adr-024-patrol-e2e.md).

## Referencias

- **[`oauth2` en pub.dev](https://pub.dev/packages/oauth2)** — librería que gestiona el flujo OAuth y PKCE.
- **[`url_launcher`](https://pub.dev/packages/url_launcher)** — abre el navegador externo.
- **[`app_links`](https://pub.dev/packages/app_links)** — captura deep links en móvil.
- **[`flutter_secure_storage`](https://pub.dev/packages/flutter_secure_storage)** — almacenamiento cifrado de tokens.
- **[`package:web`](https://pub.dev/packages/web)** — bindings web del SDK Dart.
- **[RFC 7636 — PKCE](https://datatracker.ietf.org/doc/html/rfc7636)** — fundamento de la protección.
- **[RFC 9700 — OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/rfc9700)** — recomendaciones de seguridad.
- **[ADR-010](../adrs/adr-010-oauth-pkce-keycloak.md)**, **[ADR-011](../adrs/adr-011-deep-links.md)**, **[ADR-013](../adrs/adr-013-rbac-lockstep.md)**, **[ADR-022](../adrs/adr-022-ios-15.md)**, **[ADR-023](../adrs/adr-023-oauth-web-asimetria.md)**, **[ADR-024](../adrs/adr-024-patrol-e2e.md)** — decisiones que esta guía implementa.
- **[Configuración de Keycloak](configuracion-keycloak.md)** — setup del realm y los clientes OIDC.
