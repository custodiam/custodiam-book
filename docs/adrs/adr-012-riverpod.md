---
title: ADR-012 — Riverpod como state management
description: >-
  El cliente Flutter usa `flutter_riverpod` ≥2.6 para inyección de dependencias
  y estado reactivo. Reglas de uso explícitas (Provider/StateProvider/Notifier/
  AsyncNotifier) y testabilidad por overrides como principio.
---

# ADR-012 — Riverpod como state management

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 20 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

La app Flutter necesita resolver dos problemas relacionados:

1. **Inyección de dependencias** — los repositories, use cases y servicios deben construirse en algún sitio y ser accesibles desde las pages/widgets sin que cada feature reinstancie sus dependencias.
2. **Estado reactivo** — los ViewModels exponen estado que la UI consume (`loading`, `data`, `error`); cuando ese estado cambia, la UI se reconstruye automáticamente.

El ecosistema Flutter ofrece varias opciones (BLoC, Provider clásico, GetIt, Riverpod, setState + InheritedWidget). Hay que elegir una y aplicarla con reglas consistentes en todo el proyecto.

## Decisión

**[`flutter_riverpod`](https://pub.dev/packages/flutter_riverpod) ≥2.6** como sistema unificado de DI + estado reactivo. La elección viene acompañada de reglas duras de uso:

| Tipo de provider | Caso de uso |
| --- | --- |
| `Provider<T>` | Valores inmutables o computados (config, instancia de servicio) |
| `StateProvider<T>` | Valor mutable simple (tab index, toggle UI) |
| `NotifierProvider<N, T>` | Lógica con métodos (controllers de UI) |
| `AsyncNotifierProvider<N, T>` | Carga async con estados loading/error/data (ViewModels de feature) |

Reglas duras:

- **`ref.watch`** en `build()` (suscribe y reconstruye).
- **`ref.read`** en callbacks / handlers (one-shot).
- **Providers de ViewModel** viven en el archivo del ViewModel; providers de la cadena de datos viven en `[feature]_di.dart`.
- **Inyección de use cases en ViewModels vía getters** (no `late final`): `GetVoluntarios get _getVoluntarios => ref.read(getVoluntariosProvider);`. Esto permite que los overrides de tests intercepten todas las invocaciones, no solo la primera.

## Justificación

1. **DI + estado reactivo en una sola pieza.** Resuelve los dos problemas a la vez sin necesitar `GetIt` (para DI) + otra librería para estado.

2. **Testabilidad por overrides como first-class concern.** Cualquier provider puede ser sobreescrito en tests con `ProviderScope(overrides: [...])`. Esto permite tests que ejercitan ViewModels reales sustituyendo solo el repository o el use case por un fake. No hay que diseñar la testabilidad como afterthought; viene gratis con el modelo.

3. **Auto-dispose y ciclo de vida explícitos.** Riverpod gestiona automáticamente la destrucción de providers cuando dejan de ser observados. Los recursos (subscripciones, controllers, BLoCs internos) se limpian sin código manual de `dispose`.

4. **API tipada y sin global state implícito.** A diferencia de Provider clásico (que depende del árbol de widgets), Riverpod expone los providers como constantes globales pero el acceso siempre va vía `ref`, lo que mantiene la traza explícita y permite que el análisis estático detecte accesos incorrectos.

5. **Sin code generation obligatorio.** Riverpod tiene un modo con anotaciones (`@riverpod`) y `build_runner`, pero la API "classic" sin generación está plenamente soportada y es la que el proyecto utiliza para evitar la fricción de `flutter pub run build_runner watch` permanente.

## Alternativas evaluadas y descartadas

### A. BLoC + bloc_test

- **Pros**: comunidad amplia, libros y cursos abundantes, separación estricta event ↔ state.
- **Contras**: más boilerplate por feature (events, states, transitions) que el modelo Notifier/AsyncNotifier; el patrón cuesta a desarrolladores nuevos en Flutter; menos ergonómico para casos simples ("un botón que cambia un toggle" pide cinco archivos).
- **Descartado por**: relación coste/beneficio peor para el tamaño del equipo y del proyecto.

### B. Provider (clásico, de `package:provider`)

- **Pros**: oficial Flutter, simple.
- **Contras**: dependencia del árbol de widgets para resolver providers (testabilidad más frágil); no resuelve directamente el patrón async-with-states; sucesor "espiritual" en términos de comunidad ha sido Riverpod del mismo autor.
- **Descartado por**: Riverpod del mismo autor es la versión evolucionada con sus correcciones de diseño.

### C. GetIt + StreamBuilder / ValueListenableBuilder

- **Pros**: DI explícita y minimalista con GetIt; estado nativo Flutter sin librerías adicionales.
- **Contras**: dos sistemas distintos (DI + estado) con APIs diferentes; testabilidad de los `ValueListenableBuilder` directos es prolija; el patrón se acaba pareciendo a un Riverpod hecho a mano peor estructurado.
- **Descartado por**: peor cohesión interna que la opción elegida.

### D. `setState` + `InheritedWidget` (puro Flutter)

- **Pros**: cero dependencias.
- **Contras**: no escala — propagar estado complejo o async pide reinventar Riverpod manualmente; testabilidad complicada.
- **Descartado por**: inadecuado para el tamaño de la app.

## Implicaciones operativas

- **`ProviderScope` en `main.dart`** envuelve `CustodiamApp`. Es el contenedor raíz.
- **Estructura de DI por feature**: `lib/features/<feature>/<feature>_di.dart` declara los providers de repositorios, use cases y dependencias específicas de la feature. Los providers de ViewModel viven junto a la clase ViewModel en su mismo archivo.
- **Providers globales** (api client, secure storage, env config) viven en `lib/infrastructure/di/providers.dart`.
- **Tests con `ProviderContainer`** para tests unitarios; `pumpRiverpod` (helper interno) para widget tests que necesitan árbol de widgets.
- **Versión mínima 2.6**: la API de `AsyncNotifier` necesaria para los ViewModels async se estabilizó en esa versión.
- **Convención de naming**: providers terminan en `Provider`. `voluntariosRepositoryProvider`, `getVoluntariosProvider`, `voluntariosViewModelProvider`. Esto facilita la búsqueda en el IDE.

## Referencias

- **[flutter_riverpod en pub.dev](https://pub.dev/packages/flutter_riverpod)** — documentación oficial.
- **[Riverpod docs](https://riverpod.dev/)** — sitio del autor con guías completas.
- **[ADR-013 Clean Architecture](adr-013-rbac-lockstep.md)** — Riverpod es el motor de la capa Presentation y de DI cross-cutting.
- **[ADR-014 `Result<T>`](adr-014-result-failure.md)** — los ViewModels async consumen `Result<T>` y lo proyectan a `AsyncValue`.
