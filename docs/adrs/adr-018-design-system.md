---
title: ADR-018 — Design System propio con prefijo `App*` y ThemeExtensions
description: >-
  El cliente Flutter mantiene un catálogo de componentes propios en
  `lib/core/ui/` con prefijo `App*` que envuelven Material 3 y exponen una API
  estable. Tokens, ThemeData y ThemeExtensions separados por responsabilidad.
---

# ADR-018 — Design System propio con prefijo `App*` y ThemeExtensions

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 2 de marzo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

La app Flutter tiene una identidad visual concreta (color de marca naranja Protección Civil, tipografía Roboto, jerarquía tipográfica propia) y necesita componentes consistentes entre features (botones, inputs, cards, dialogs). Material Design 3 cubre lo básico pero:

- Material directo en cada feature acaba en inconsistencias — un `FilledButton` con `style: ButtonStyle(backgroundColor: ...)` aquí, un `ElevatedButton` con padding propio allá.
- Material no cubre todo lo que la app necesita: colores semánticos (`success`, `warning`, `danger`, `info`), tokens de espaciado consistentes, breakpoints, duraciones de animación, elevaciones.
- Si la identidad visual evoluciona (rebranding, cambio de marca), tener `ElevatedButton` directo en 50 sitios obliga a tocar 50 archivos.

## Decisión

**Catálogo de componentes propios con prefijo `App*`** en `lib/core/ui/`, que envuelven Material y exponen una API estable al resto de la app. Tres reglas:

1. **Composición sobre extensión** — `AppPrimaryButton` envuelve `FilledButton` por dentro; no hereda de él. La API pública del Design System es independiente de Material.
2. **Si dos features usan el mismo widget, vive en el Design System.** Si solo una, vive en `features/<feature>/presentation/widgets/`.
3. **Nada de Material directo en `features/`.** Si un PR introduce `ElevatedButton(...)` en una pantalla de voluntarios, el reviewer lo señala y sustituye por `AppPrimaryButton`.

Estructura del catálogo:

```text
lib/core/ui/
├── tokens/          # AppSpacing, AppRadius, AppBreakpoints, AppDurations, AppElevations
├── theme/           # AppTheme.light/dark + ColorScheme + ThemeExtensions (semantic colors)
├── buttons/         # AppPrimaryButton, AppSecondaryButton, AppTextButton, AppDestructiveButton, AppIconButton
├── inputs/          # AppTextField, AppPasswordField, AppEmailField, AppSearchField, AppDatePicker
├── toggles/         # AppSwitch, AppCheckbox, AppRadioGroup
├── feedback/        # AppDialog, AppConfirmDialog, AppBottomSheet, AppSnackbar, AppBanner, AppLoadingIndicator
├── containers/      # AppCard, AppPageScaffold (SafeArea + maxWidth), AppListTile, AppSection
├── states/          # AppEmptyState, AppErrorState, AppLoadingState
└── misc/            # AppAvatar, AppChip, AppDivider
```

**Tokens vs `ThemeData` vs `ThemeExtension`** — tres conceptos distintos, vives en sitios distintos:

| Concepto | Vive en | Para qué |
| --- | --- | --- |
| **Token** | `tokens/app_*.dart` (constantes Dart) | Valores absolutos del sistema: `AppSpacing.md = 16.0` |
| **`ThemeData`** | `theme/app_theme.dart` (Material) | `ColorScheme`, `TextTheme`, defaults Material |
| **`ThemeExtension`** | `theme/extensions/` (`ThemeExtension<T>`) | Lo que Material no cubre: colores semánticos (`success` / `warning` / `danger` / `info`), spacing accesible vía `context.spacing.md` |

## Justificación

1. **API estable independiente de Material.** Si Material 4 (hipotético) cambia componentes o si una feature futura necesita un look distinto del Material por defecto, el cambio queda contenido en `lib/core/ui/`. Las features consumen `AppPrimaryButton` sin saber qué hay por debajo.

2. **Consistencia obligatoria.** El reviewer aplica la regla "nada de Material directo en features". Esto convierte el Design System en el único camino para construir UI, lo que garantiza que dos features con la misma acción (`primaryAction`) renderizan idénticas en pixel y comportamiento.

3. **Identidad visual centralizada.** Si la marca cambia el color primario o la tipografía, basta tocar `AppTheme.light` y los tokens. Cero cambios en features.

4. **Colores semánticos vía `ThemeExtension`.** Material 3 trae paleta tipo `primary` / `secondary` / `tertiary` pero no tiene el concepto de `success` / `warning` / `danger` / `info` que cualquier app de operaciones necesita. Las `ThemeExtension<T>` permiten declararlos como parte del theme con tipado fuerte: `Theme.of(context).extension<AppSemanticColors>()!.warning`.

5. **`AppPageScaffold` con `maxWidth`** evita que en una pantalla web responsive un listado se estire a 1500 px haciendo la lectura incómoda. Encapsular la decisión en el Scaffold del DS asegura que TODAS las páginas la heredan.

## Alternativas evaluadas y descartadas

### A. Material directo en cada feature

- **Pros**: cero infraestructura.
- **Contras**: inconsistencias garantizadas, rebranding costoso, mezcla de estilos según el día del PR. Documentado como anti-patrón en la mayoría de docs serias sobre Flutter.
- **Descartado por**: inviable a medio plazo.

### B. Paquetes de Design System externos (`flutter_widgetkit`, `material_kit`, etc.)

- **Pros**: catálogo listo, sin trabajo inicial.
- **Contras**: identidad visual genérica que no encaja con la marca del proyecto; obliga a customizar/sobreescribir el paquete externo, lo que acaba siendo más trabajo que el catálogo propio; dependencia transitiva pesada.
- **Descartado por**: peor relación calidad/coste.

### C. Componentes con sufijo Custodiam (`PrimaryButtonCustodiam`)

- **Pros**: nombre explícito del proyecto.
- **Contras**: orden alfabético en el IDE muestra los componentes propios mezclados con los Material (`FilledButton`, `OutlinedButton`, `PrimaryButtonCustodiam`...). El prefijo `App*` los agrupa al principio del autocompletar.
- **Descartado por**: peor UX en el IDE.

### D. Componentes que heredan de Material (`class AppPrimaryButton extends FilledButton`)

- **Pros**: reutilización de la API de Material.
- **Contras**: cualquier cambio de Material rompe la jerarquía; impide cambiar la implementación interna sin propagar cambios; los tipos de retorno son `FilledButton`, no `AppPrimaryButton`, lo que confunde el autocompletar.
- **Descartado por**: composición es estrictamente mejor que herencia en este caso.

## Implicaciones operativas

- **Construcción incremental**, no big-bang. El catálogo no se construye entero antes de empezar features. Cada feature que necesite un componente nuevo lo añade al Design System con la regla "si lo necesitas tú, lo van a necesitar otros".
- **Las `ThemeExtension` se registran en `MaterialApp.theme.extensions`**. La app consume con `Theme.of(context).extension<X>()`. Las clases `ThemeExtension` declaran `copyWith`, `lerp`, `==`, `hashCode` siguiendo el contrato del SDK (boilerplate inevitable).
- **Tokens son `const` puros**, no `static getter` — esto permite que el compilador haga inlining y los use como argumentos de `EdgeInsets.all(AppSpacing.md)` sin overhead.
- **Storybook / catalog visual**: el equipo mantiene una página interna `/dev/design-system` (gated por flag `kDebugMode`) que renderiza cada componente con todas sus variantes para revisión visual durante el desarrollo.
- **Convención de no exportar Material**: el archivo `lib/core/ui/ui.dart` (barrel) NO re-exporta nada de `package:flutter/material.dart`. Las features importan Material por separado para los pocos casos donde sí pueden tocarlo (Scaffold, AppBar — pendientes de envolver en `AppScaffold`/`AppAppBar`).

## Referencias

- **[Flutter — ThemeExtension](https://api.flutter.dev/flutter/material/ThemeExtension-class.html)** — API del SDK.
- **[Material 3](https://m3.material.io/)** — base sobre la que el Design System compone.
- **[ADR-013 Clean Architecture](adr-013-rbac-lockstep.md)** — la capa Presentation consume el Design System.
