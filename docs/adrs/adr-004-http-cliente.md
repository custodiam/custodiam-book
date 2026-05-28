---
title: ADR-004 — Cliente HTTP del cliente Flutter
description: >-
  El cliente Flutter usa el paquete oficial `http` del SDK Dart envuelto por
  una clase `ApiClient` centralizada. Sin Dio ni Chopper, sin code generation,
  sin dependencias mantenidas por terceros para algo que el SDK ya cubre.
---

# ADR-004 — Cliente HTTP del cliente Flutter

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 28 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El cliente Flutter habla con `custodiam-api` por REST sobre HTTPS. Cada feature de la app (voluntarios, servicios, fichajes, inventario) consume varios endpoints y necesita:

- Adjuntar el JWT en `Authorization: Bearer ...`.
- Detectar `401 Unauthorized`, intentar `refresh_token` y reintentar la petición original.
- Mapear errores HTTP (`401`, `403`, `409`, `5xx`) a `Failure` específicos de la capa data ([ADR-014](adr-014-result-failure.md)).
- Centralizar la `baseUrl` para no diseminar `String.fromEnvironment` por la app ([ADR-015](adr-015-env-config.md)).

Hay que decidir **qué paquete HTTP usar** como base, y cómo organizar el wrapper de transporte.

## Decisión

**Paquete oficial [`http`](https://pub.dev/packages/http)** del equipo Dart (Google), envuelto por una clase `ApiClient` en `lib/infrastructure/network/`. El wrapper centraliza:

- Inyección de tokens JWT en cabeceras (`Authorization: Bearer ...`).
- Manejo de errores HTTP (`401 → refresh + retry`, `403`, `5xx`).
- Refresh coordinado con `AuthService.getValidAccessToken()`.
- `baseUrl` leída de `EnvConfig`.
- Conversión de respuestas a `Result<T>` antes de salir de la capa data.

```dart
class VoluntariosRepositoryImpl implements VoluntariosRepository {
  final ApiClient _api;
  VoluntariosRepositoryImpl(this._api);

  @override
  Future<Result<List<Voluntario>>> getAll() async {
    try {
      final json = await _api.get('/voluntarios');
      final list = (json['items'] as List)
          .map((e) => VoluntarioModel.fromJson(e).toDomain())
          .toList();
      return Success(list);
    } on UnauthenticatedException {
      return const Fail(AuthFailure.sessionExpired());
    } on ApiException catch (e) {
      return Fail(NetworkFailure.serverError(e.statusCode));
    }
  }
}
```

## Justificación

1. **Paquete oficial Dart.** `http` está mantenido por el equipo Dart de Google. Tiene la misma garantía de mantenimiento que el propio SDK. No depende de un mantenedor individual ni de una organización externa que pueda perder interés.

2. **API suficiente para el caso de uso.** El proyecto consume REST estándar (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) con cuerpos JSON, cabeceras estándar y cancelación opcional. Todas las features que el dominio necesita están cubiertas por `http`.

3. **Sin dependencia transitiva pesada.** `http` no arrastra `meta`, `code generation`, ni adaptadores extra. La superficie del bundle final es mínima.

4. **El wrapper `ApiClient` cubre lo específico del proyecto.** Lo que `http` no hace (interceptors, refresh automático, manejo de errores tipado) lo hace el wrapper en código del propio proyecto, donde reside la lógica de negocio relacionada con auth y errores. Esa lógica no debería vivir en un paquete externo.

5. **Testabilidad por inyección.** `ApiClient` recibe un `http.Client` por constructor — los tests pueden inyectar un `MockClient` de `package:http/testing.dart` sin necesidad de paquetes adicionales de mocking HTTP.

## Alternativas evaluadas y descartadas

### A. `dio`

Cliente HTTP de cuota relevante en Flutter, con interceptors built-in y CancelToken.

- **Pros**: API más rica que `http`, comunidad amplia, soporte de interceptors out-of-the-box.
- **Contras**: dependencia de terceros no mantenida por Google; arrastra peso al bundle; sus interceptors built-in resuelven un problema (refresh, logging) que el wrapper del proyecto cubre con código propio testable.
- **Descartado por**: dependencia opcional cuando el SDK ya cubre el caso de uso.

### B. `chopper`

Cliente con code generation tipo Retrofit (define interfaces, anotaciones, genera el cliente).

- **Pros**: type-safe, contratos REST declarativos.
- **Contras**: build_runner extra, anotaciones que el equipo no usa para otras cosas, generación de código que añade fricción en el ciclo de desarrollo (`flutter pub run build_runner watch`).
- **Descartado por**: el coste del code-gen no compensa para el tamaño del API.

### C. `dart:io` `HttpClient` directo

API nativa de bajo nivel.

- **Pros**: cero dependencias.
- **Contras**: NO funciona en Flutter Web (es API exclusiva del runtime VM/native). `http` envuelve esta API en plataforma móvil y usa `BrowserClient` en web, lo que da multiplataforma transparente.
- **Descartado por**: incompatibilidad con Flutter Web.

## Implicaciones operativas

- **Refresh + retry centralizado**: si el `ApiClient` recibe un `401`, invoca `AuthService.getValidAccessToken()` (que refresca si hace falta) y reintenta la petición original **una sola vez**. Si el segundo intento también devuelve `401`, lanza `UnauthenticatedException` que el repository convierte a `Fail(AuthFailure.sessionExpired())`.
- **Tests con `MockClient`**: cada repository tiene tests que inyectan un `MockClient` configurado para responder ciertos JSON o ciertos status codes, sin levantar servidor real ni mocks adicionales de paquetes.
- **Logging via `dev.log`** ([ADR-016](adr-016-dev-log.md)): cada petición y respuesta se loguea con `name: 'API'` para facilitar el filtrado en DevTools.
- **Cabeceras estándar**: el wrapper añade `Accept: application/json` y `Content-Type: application/json` cuando hay body. El `User-Agent` no se sobreescribe (Flutter pone uno con la versión del SDK).
- **Sin caché HTTP**: el wrapper no implementa caché propio. Las features que necesiten persistencia offline usan SQLite local ([ADR-005](adr-005-sqflite.md)), no caché HTTP.

## Referencias

- **[Paquete `http` en pub.dev](https://pub.dev/packages/http)** — documentación oficial.
- **[`package:http/testing.dart`](https://pub.dev/documentation/http/latest/testing/MockClient-class.html)** — utilidades de testing oficiales.
- **[ADR-014 `Result<T>` y `Failure`](adr-014-result-failure.md)** — tipo de retorno de los repositories.
- **[ADR-015 EnvConfig](adr-015-env-config.md)** — `baseUrl` consumida por el wrapper.
- **[ADR-016 dev.log](adr-016-dev-log.md)** — logging del wrapper.
