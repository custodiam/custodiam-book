---
title: ADR-014 — Result<T> sealed + jerarquía Failure como error handling
description: >-
  Los métodos de repository devuelven `Result<T>` (sealed class con Success y
  Fail) en lugar de lanzar excepciones cross-layer. Las excepciones quedan
  contenidas dentro de la capa data; las capas superiores hacen pattern
  matching exhaustivo.
---

# ADR-014 — `Result<T>` sealed + jerarquía `Failure` como error handling

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 25 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El cliente Flutter consume APIs HTTP, BD local, almacenamiento seguro y servicios externos. Cada uno puede fallar por razones distintas (red caída, token expirado, conflicto 409, error de validación, BD corrupta, permiso denegado). Hay que decidir **cómo se propagan los errores** desde la capa data hacia la capa presentation.

Dos modelos compiten:

- **Excepciones**: cualquier capa lanza, la capa superior captura con `try/catch`. Es el modelo idiomático Dart.
- **Tipo de retorno explícito**: la función devuelve un valor que representa éxito **o** fracaso (`Either`, `Result`, etc.). Pattern matching exhaustivo en el consumidor.

## Decisión

**`Result<T>` propio como `sealed class`** con dos casos (`Success<T>` y `Fail<T>`) + **jerarquía `Failure`** con subclases por tipo de error (`AuthFailure`, `NetworkFailure`, `ValidationFailure`, etc.).

```dart
sealed class Result<T> {
  const Result();
}

final class Success<T> extends Result<T> {
  final T value;
  const Success(this.value);
}

final class Fail<T> extends Result<T> {
  final Failure failure;
  const Fail(this.failure);
}
```

Todos los métodos de repository devuelven `Result<T>`. Las excepciones siguen existiendo pero **quedan contenidas dentro de la capa data**: el repository las captura, las traduce a `Failure` y devuelve `Fail(failure)`. Ninguna excepción atraviesa el límite hacia el ViewModel.

Consumo desde ViewModel con pattern matching:

```dart
return switch (result) {
  Success(:final value) => AsyncData(value),
  Fail(:final failure) => AsyncError(failure, StackTrace.current),
};
```

**Prohibido** en el código del proyecto: usar `fpdart`, `Either`, `left()`, `right()`, `.match()`. Se mantiene `Result<T>` propio (las 3 líneas de arriba) por simplicidad, testabilidad y cero dependencias externas para un concepto trivial.

## Justificación

1. **Errores como parte del contrato.** El tipo de retorno `Future<Result<List<Voluntario>>>` deja explícito en la firma que la operación puede fallar y que el llamador debe tratar el caso. Una firma `Future<List<Voluntario>>` que lanza excepciones esconde esto y obliga al llamador a recordar qué excepciones puede recibir.

2. **Pattern matching exhaustivo gracias a `sealed`.** Dart 3+ con clases `sealed` permite que el compilador verifique que el `switch` cubre todos los casos de `Result<T>` (`Success` y `Fail`). Olvidar uno produce error de compilación. Esto elimina toda una clase de bugs.

3. **Las capas superiores no necesitan saber qué excepciones existen.** El ViewModel hace `switch (result)` y trata éxito/fracaso. No necesita conocer `SocketException`, `HttpException`, `FormatException`, `KeycloakException` ni catálogos de excepciones de paquetes externos. La superficie del API de cada repository queda mínima.

4. **Testabilidad alta.** Construir un `Success(value)` o un `Fail(AuthFailure.sessionExpired())` en un test es trivial. Stubbear excepciones requiere `throw` real en un mock + `expectLater(future, throwsA(...))`, que es más ruidoso y peor legible.

5. **Sin dependencias externas para un concepto trivial.** `fpdart` añade decenas de tipos (`Either`, `Option`, `IO`, `Task`, `State`, ...) cuando el proyecto solo necesita el patrón éxito/fracaso. Tres líneas de Dart resuelven el caso de uso con cero peso transitivo.

## Alternativas evaluadas y descartadas

### A. Excepciones cross-layer

El modelo idiomático Dart: el repository lanza, el ViewModel captura.

- **Pros**: idiomático en Dart, menos código en el path feliz.
- **Contras**: las excepciones son flujo de control invisible — la firma de la función no las refleja; obliga al consumidor a saber qué excepciones puede recibir; el flujo de error no es exhaustivo verificable por el compilador; mezclar paths felices y de error en `try/catch` con varias `on X catch` es prolijo y propenso a olvidar casos.
- **Descartado por**: falta de exhaustividad verificada y mezcla de flujos.

### B. `fpdart` `Either<L, R>`

Librería que aporta tipos funcionales tipo Haskell a Dart.

- **Pros**: ecosistema funcional completo, comunidad activa.
- **Contras**: arrastra decenas de tipos que el proyecto no usa; `.match(left, right)` es menos legible que `switch` exhaustivo Dart-nativo; sintaxis de combinadores (`flatMap`, `fold`) añade una capa de abstracción que el equipo no necesita.
- **Descartado por**: sobre-dimensionado para el caso.

### C. Tuplas `(T?, Failure?)` o records `(value: T?, error: Failure?)`

Records Dart 3 permiten devolver pares.

- **Pros**: nativo Dart sin clase auxiliar.
- **Contras**: no es exhaustivo — el consumidor podría leer `value` aunque `error` esté presente, o viceversa. El compilador no impide el bug "asumí que era éxito sin comprobar".
- **Descartado por**: el `sealed class` da garantías que la tupla no.

### D. `Result<T, E>` con dos parámetros genéricos

```dart
sealed class Result<T, E> {}
final class Success<T, E> extends Result<T, E> { final T value; ... }
final class Fail<T, E> extends Result<T, E> { final E error; ... }
```

- **Pros**: el tipo del error queda explícito en la firma.
- **Contras**: la firma de cada repository es más larga (`Future<Result<List<Voluntario>, Failure>>`), y como **el tipo del error es siempre `Failure`** en todo el proyecto, el segundo parámetro genérico no aporta. El código del consumidor también se vuelve más ruidoso (`Result<List<Voluntario>, Failure>` vs `Result<List<Voluntario>>`).
- **Descartado por**: sobre-genérico para un proyecto con un único tipo de error.

## Implicaciones operativas

- **Jerarquía `Failure`** documentada en `lib/infrastructure/error/`:

    ```dart
    sealed class Failure {
      const Failure();
    }
    final class AuthFailure extends Failure {
      const AuthFailure.sessionExpired();
      const AuthFailure.invalidCredentials();
      ...
    }
    final class NetworkFailure extends Failure {
      const NetworkFailure.noConnection();
      const NetworkFailure.serverError(this.statusCode);
      ...
    }
    final class ValidationFailure extends Failure {
      const ValidationFailure(this.errors);
      ...
    }
    ```

- **Mapeo del `Failure` a UI**: el ViewModel propaga el `Failure` al estado `AsyncError`; la página consumidora muestra un mensaje en español derivado del tipo de `Failure` (helper `failureToUserMessage(failure)`).

- **Tests de repository**: cada test verifica el `Failure` específico devuelto en cada camino de error. La firma exhaustiva de `switch (failure)` también aplica a `Failure` (sealed), por lo que olvidar un caso al añadir un subtipo nuevo causa error de compilación en cualquier consumer que haga el switch.

- **Logging del `Fail`**: el `ApiClient` ([ADR-004](adr-004-http-cliente.md)) loguea cada `Fail` con `dev.log(name: 'API')` antes de devolverlo, así DevTools muestra qué falló sin que el ViewModel tenga que volver a loguear.

## Referencias

- **[Dart 3 — sealed classes](https://dart.dev/language/class-modifiers#sealed)** — base del modelo.
- **[Dart 3 — pattern matching](https://dart.dev/language/patterns)** — sintaxis `switch` exhaustivo.
- **[ADR-004 Cliente HTTP](adr-004-http-cliente.md)** — el wrapper convierte excepciones a `Result<T>` en la capa data.
- **[ADR-012 Riverpod](adr-012-riverpod.md)** — los ViewModels traducen `Result<T>` a `AsyncValue` para la UI.
