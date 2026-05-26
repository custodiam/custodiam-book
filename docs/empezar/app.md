---
title: App Flutter
description: >-
  Cómo levantar custodiam-app (Flutter móvil + web) en local.
---

# App — `custodiam-app`

App cliente Flutter multiplataforma: **Android + iOS + Web**. Arquitectura **Clean estricta + Riverpod + `Result<T>`**, con autenticación OAuth2 + PKCE contra Keycloak.

!!! info "Decisiones arquitectónicas relevantes"
    - **ADR-013 — Clean Architecture estricta** con tres capas (`domain` / `data` / `presentation`).
    - **ADR-012 — Riverpod** como state management (no `bloc`, no `setState` global).
    - **ADR-014 — `Result<T>` sealed** para error handling sin excepciones cross-layer.
    - **ADR-010 — OAuth2 + PKCE** con paquete `oauth2` de pub.dev.
    - **ADR-023 — Dos `AuthService` seleccionados por `kIsWeb`** (asimetría móvil/web).
    - **ADR-018 — Design System propio** con prefijo `App*` y `ThemeExtensions`.

## Requisitos

- Flutter SDK 3.x ([instalación aquí](index.md#requisitos-previos-comunes))
- Backend `custodiam-api` accesible en `http://localhost:8000` (ver [recorrido API](api.md)) o el stack completo de [infra](infra.md)
- Keycloak accesible en `http://localhost:8080` (idem)
- Para Android: Android Studio + emulador o dispositivo con USB debug
- Para iOS: macOS + Xcode + simulador o dispositivo (no aplica en Windows/Linux)
- Para Web: Chrome o Edge

## Clonar y arrancar

```bash
git clone https://github.com/custodiam/custodiam-app.git
cd custodiam-app

# Verifica que Flutter ve tus dispositivos disponibles
flutter doctor
flutter devices

# Instala las dependencias
flutter pub get

# Genera código de json_serializable (necesario tras pull si hay nuevos modelos)
dart run build_runner build --delete-conflicting-outputs

# Arranca en el dispositivo conectado por defecto
flutter run

# O específico:
flutter run -d chrome              # Web (puerto aleatorio)
flutter run -d chrome --web-port=3000   # Web con puerto fijo (requerido para OAuth callback)
flutter run -d <device-id>         # Android/iOS específico
```

!!! warning "Web + OAuth — puerto 3000 obligatorio en dev"
    El flujo OAuth + PKCE en web exige que el `redirect_uri` registrado en Keycloak coincida exactamente con el puerto en el que corre la app Flutter. El cliente OIDC tiene registrado `http://localhost:3000/callback`. Si arrancas Flutter Web con un puerto distinto (por ejemplo el aleatorio que asigna `flutter run -d chrome`), el callback fallará. Solución: `flutter run -d chrome --web-port=3000`.

## Builds de release

Builds parametrizados con `--dart-define` para apuntar a producción:

```bash
# APK release (Android)
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es

# AAB para Google Play
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es

# iOS (requiere macOS)
flutter build ios --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es

# Web (producción)
flutter build web --release \
  --dart-define=API_BASE_URL=https://api.custodiam.es/api/v1 \
  --dart-define=KEYCLOAK_BASE_URL=https://auth.custodiam.es
```

La PWA de producción se sirve en `https://app.custodiam.es` (Cloudflare Pages, ADR-022).

## Comandos esenciales

```bash
# Análisis estático
flutter analyze

# Tests unit + widget
flutter test
flutter test --coverage

# Tests E2E (integration_test/)
flutter test integration_test/all_tests.dart

# Code generation (json_serializable + freezed si se usara)
dart run build_runner build --delete-conflicting-outputs
dart run build_runner watch       # modo continuo en desarrollo
```

## Estructura del repo

```text
custodiam-app/
├── lib/
│   ├── main.dart              # ProviderScope → CustodiamApp
│   ├── app/                   # MaterialApp, router
│   ├── core/                  # ui/ (Design System App*), helpers/, services/, config/
│   ├── features/              # auth/, splash/, settings/, voluntarios/, ...
│   ├── infrastructure/        # auth/, network/, di/, theme/
│   └── l10n/                  # localizaciones (solo es-ES en MVP)
├── test/                      # unit + widget tests
├── integration_test/          # E2E tests (requiere emulador o web headless)
├── android/
├── ios/
├── web/
└── pubspec.yaml
```

## Siguientes pasos

- **[Infraestructura completa](infra.md)** — levantar BD + Keycloak + API + Web + ntfy de una sola vez.
- **[Arquitectura](../arquitectura/index.md)** — diagramas del flujo OAuth, capas Clean, asimetría móvil/web.
