---
title: ADR-028 — Catálogo central de ValueKeys para tests
description: >-
  Toda ValueKey estable usada por los tests del cliente Flutter vive en una
  única clase `K` en `lib/app/test_keys.dart`, importable tanto desde los
  widgets de producción como desde los tests de widget y los E2E. Una sola
  fuente del string evita el drift silencioso entre la pantalla y el test.
---

# ADR-028 — Catálogo central de ValueKeys para tests

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 28 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Los tests del cliente Flutter —tanto los de widget como los de extremo a extremo— necesitan **localizar widgets concretos de forma estable** en el árbol. Las dos estrategias que ofrece el framework por defecto son frágiles para una app que crece:

- `find.byType(...)` falla en cuanto hay más de un widget del mismo tipo en pantalla (dos botones primarios, varias tarjetas).
- `find.text(...)` se rompe cuando cambia el copy de la interfaz, y queda inservible el día que se introduzca internacionalización.

La práctica robusta es asignar una `ValueKey` estable a cada widget que un test necesite localizar y buscarlo con `find.byKey(...)`. Pero eso abre una pregunta de organización: **¿dónde se define el string de cada key?**

Si el literal del `ValueKey('login_submit_button')` se escribe directamente en la pantalla y, por separado, el mismo literal se vuelve a escribir en el test, existen **dos fuentes del mismo string**. El día que una cambie y la otra no, el test deja de encontrar el widget sin que nada lo advierta en tiempo de compilación: un *drift* silencioso que solo se manifiesta como un fallo de test difícil de diagnosticar.

A esto se añade un segundo consumidor. Cuando aparecen tests de widget (que se ejecutan sobre el árbol de Flutter, no como E2E externos), esos tests también necesitan las keys, y viven en una carpeta distinta de los E2E. Cualquier ubicación del catálogo de keys que no sea importable desde el código de producción obliga a duplicar los strings.

## Decisión

**Todas las `ValueKey` estables usadas por tests se definen en una única clase `K`, ubicada en `lib/app/test_keys.dart`.**

```dart
// lib/app/test_keys.dart
abstract final class K {
  static const loginSubmitButton = ValueKey('login_submit_button');
  static const shellBranchServicios = ValueKey('shell_branch_servicios');
  // factory para listas parametrizadas:
  static ValueKey servicioCard(int index) => ValueKey('servicio_card_$index');
}
```

La clave de la decisión es la **ubicación**: `lib/app/`, dentro del código de producción. Eso la hace importable desde los tres consumidores:

- **Las pantallas de producción** (`lib/features/**`) aplican la key: `AppPrimaryButton(key: K.loginSubmitButton, ...)`.
- **Los tests de widget** (`test/**`) la localizan: `find.byKey(K.loginSubmitButton)`.
- **Los tests E2E** (`patrol_test/**`) la localizan con la misma referencia.

El símbolo `K.loginSubmitButton` es la **única fuente** del string `'login_submit_button'`. La pantalla lo aplica y el test lo busca usando exactamente la misma constante.

## Justificación

1. **Una sola fuente del string elimina el drift.** Como la pantalla y el test referencian la misma constante de Dart, es imposible que diverjan: no hay dos literales que mantener sincronizados a mano.

2. **Refactor seguro con el IDE.** Renombrar `K.loginSubmitButton` con la herramienta de refactor del IDE actualiza simultáneamente la pantalla y todos los tests que la usan. Con literales hardcodeados, el renombrado es una búsqueda-y-reemplazo manual propensa a olvidos.

3. **La compilación bloquea las ausencias.** Si se elimina una key que un test todavía usa, el proyecto no compila. El error sale en tiempo de build, no como un fallo de test en CI.

4. **Importable desde producción y desde ambos tipos de test.** Situar el catálogo en `lib/app/` —y no en una carpeta exclusiva de tests— es lo que permite que el código de producción aplique las mismas keys que los tests buscan. Una ubicación solo accesible para los tests obligaría a duplicar los literales en la pantalla.

5. **Catálogo localizable.** Un único archivo concentra todas las keys estables del proyecto. Buscar `K.` da el inventario completo de puntos del árbol que los tests pueden anclar, y la convención de nombres (`K.<scope><Elemento>`) las agrupa por pantalla.

## Alternativas evaluadas y descartadas

### A. Strings literales hardcodeados en pantalla y test

Escribir `ValueKey('login_submit_button')` directamente en ambos sitios.

- **Pros**: cero infraestructura.
- **Contras**: dos fuentes del mismo string; drift silencioso en cuanto una cambia; el renombrado es manual; nada lo verifica en compilación.
- **Descartado por**: es exactamente el problema que la decisión resuelve.

### B. Catálogo de keys en la carpeta de tests de integración

Definir las keys en una clase dentro de la carpeta de los tests de extremo a extremo.

- **Pros**: mantiene las keys cerca de los tests que las usan.
- **Contras**: esa carpeta **no es importable desde `lib/`**, así que el código de producción no puede aplicar las mismas constantes; obliga a duplicar el literal en la pantalla, reintroduciendo el drift.
- **Descartado por**: rompe el requisito de fuente única importable desde producción.

### C. Catálogo de keys en la carpeta de tests E2E

Variante de la anterior, ubicando las keys junto a los flujos E2E.

- **Pros**: las keys viven con los flujos que más las explotan.
- **Contras**: mismo defecto que (B) —no importable desde `lib/`—, agravado porque un segundo consumidor (los tests de widget) tampoco comparte esa carpeta.
- **Descartado por**: idéntico motivo que (B).

### D. Una clase de keys por cada módulo de funcionalidad

Fragmentar las keys en clases separadas, una por feature.

- **Pros**: cada módulo encapsula sus propias keys.
- **Contras**: no hay catálogo único; verificar colisiones de strings entre módulos se vuelve manual; el inventario global de keys se dispersa en muchos archivos.
- **Descartado por**: sin catálogo central se pierde la principal ventaja de localización y verificación.

## Implicaciones operativas

- **Toda key estable vive en `K`**, nunca hardcodeada en el widget. La pantalla importa la constante y la aplica.
- **Convención de nombres**: `K.<scope><Elemento>` en camelCase (`K.loginEmailField`). Para listas parametrizadas, función factory (`K.servicioCard(int index)`).
- **Revisión de PR**: un PR que añada una pantalla o un botón crítico debe añadir su `ValueKey` en `K` antes del merge.
- **Tres consumidores**: la clase se importa desde producción (`lib/features/**`), tests de widget (`test/**`) y tests E2E (`patrol_test/**`), con la misma referencia en todos.

## Referencias

- **[Flutter — `ValueKey` y la API de Keys](https://api.flutter.dev/flutter/foundation/ValueKey-class.html)** — fundamento del mecanismo.
- **[Flutter — Finders en tests de widget](https://api.flutter.dev/flutter/flutter_test/CommonFinders/byKey.html)** — `find.byKey` que localiza los widgets.
- **[ADR-018 Design System](adr-018-design-system.md)** — los componentes `App*` aceptan y propagan la `key` hasta el widget Material subyacente.
- **[ADR-024 Patrol E2E](adr-024-patrol-e2e.md)** — los flujos E2E consumen este catálogo para anclar sus interacciones.
