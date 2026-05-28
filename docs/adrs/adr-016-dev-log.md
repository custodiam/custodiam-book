---
title: ADR-016 — Logging estructurado con `dev.log`
description: >-
  Todo logging del cliente Flutter usa `dev.log()` de `dart:developer` con
  parámetro `name:` para filtrar por sistema en Flutter DevTools. Sin print,
  sin debugPrint, sin paquete logger.
---

# ADR-016 — Logging estructurado con `dev.log`

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 27 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

La app Flutter genera mensajes de log relevantes en runtime — peticiones HTTP, refresh de tokens, errores de auth, fichajes encolados, notificaciones push entrantes, decisiones del `AppStartupUseCase`, etc. Hay que decidir **cómo se emiten esos logs** y **cómo se filtran** durante el desarrollo y la depuración.

Las opciones en Flutter son:

- `print(...)` — escribe a stdout. Sin estructura, sin filtrado, ruidoso.
- `debugPrint(...)` — variante con throttling automático para evitar overflow del buffer de logcat.
- `dev.log(...)` de `dart:developer` — escribe a la consola de DevTools con metadata (name, level, error, stackTrace).
- Paquetes externos (`logger`, `simple_logger`, `loggy`) — capas sobre lo anterior con formato bonito.

## Decisión

**`dev.log()` de `dart:developer`** con el parámetro `name:` para filtrar en DevTools:

```dart
import 'dart:developer' as dev;

dev.log('✅ [RESPONSE] 200 /voluntarios', name: 'API');
dev.log('Token refrescado', name: 'Auth');
dev.log('Encolada acción: fichaje', name: 'Sync');
dev.log('Notificación recibida: emergencia', name: 'Push');
```

Convención de `name:` por sistema:

| Sistema | `name` |
| --- | --- |
| API HTTP | `'API'` |
| Auth (login, refresh, logout) | `'Auth'` |
| Sincronización offline | `'Sync'` |
| Notificaciones push | `'Push'` |
| Routing y guards | `'Router'` |
| Almacenamiento local | `'Storage'` |
| Splash y arranque | `'Startup'` |

## Justificación

1. **Filtrado nativo en DevTools.** El panel de logging de Flutter DevTools permite filtrar por `name`. Durante una sesión de depuración, escribir `name:Auth` en el filtro muestra solo los logs del subsistema de autenticación, dejando fuera el ruido del resto.

2. **Cero dependencias externas.** `dart:developer` viene en el SDK. No hay paquete que mantener actualizado ni versión transitiva que monitorizar.

3. **Errores y stack traces tipados.** `dev.log` acepta `error:` y `stackTrace:` opcionales que DevTools muestra como bloques expandibles separados del mensaje. `print` los hace texto plano.

4. **Sin overhead significativo en release.** `dev.log` se compila pero los listeners de DevTools no están conectados en una app en producción, por lo que la llamada pasa rápidamente sin emitir nada perceptible. Si en el futuro hace falta filtrar logs en release (para no exponer información sensible), se envuelve en helpers que respeten `kDebugMode`.

5. **Consistencia con la jerga del proyecto.** Cada subsistema tiene un nombre canónico documentado y usado uniformemente. Buscar `dev.log(... name: 'Auth')` da todos los puntos del proyecto donde el subsistema Auth emite mensajes — útil cuando se diagnostica un bug en la cadena de refresh.

## Alternativas evaluadas y descartadas

### A. `print(...)`

- **Pros**: trivial.
- **Contras**: sin metadata, sin filtrado, sin estructura. En Android puede saturar el buffer de logcat (Flutter usa `debugPrint` por debajo precisamente para evitar esto en mensajes largos). Difícil distinguir el mensaje de Auth del de API cuando se inundan al arrancar.
- **Descartado por**: ruido y falta de estructura.

### B. `debugPrint(...)`

- **Pros**: tiene throttling automático.
- **Contras**: sin `name:` ni metadata. Solo soluciona la saturación del buffer, no la filtrabilidad.
- **Descartado por**: insuficiente para el caso de uso.

### C. Paquete `logger`

Librería popular con formato colorido en consola, niveles tipo `trace`/`debug`/`info`/`warn`/`error`/`fatal`.

- **Pros**: salida visualmente atractiva, niveles ricos.
- **Contras**: dependencia externa para una capacidad que el SDK ya cubre adecuadamente; el formato bonito en consola no aporta sobre el panel estructurado de DevTools; introduce un concepto de niveles que el proyecto no necesita en MVP.
- **Descartado por**: dependencia opcional sin valor diferencial.

### D. Centralización en una clase `Logger` propia

Wrapper interno con métodos `Logger.api.info(...)`, `Logger.auth.warn(...)`, etc.

- **Pros**: forzaría disciplina mediante el sistema de tipos.
- **Contras**: añade infraestructura para hacer lo que la convención de `name:` ya logra; código de presentación de los logs (cómo se serializan, en qué archivo) no se necesita.
- **Descartado por**: sobre-ingeniería; la convención de `name:` cubre el caso.

## Implicaciones operativas

- **Convención obligatoria en revisiones de PR**: un PR que introduzca `print(...)` en código de producción debe ser rechazado por el reviewer y sustituido por `dev.log` con `name:` adecuado.
- **DevTools como herramienta de depuración estándar**: el filtrado de logs por `name` se documenta en la guía técnica de desarrollo Flutter del proyecto. Cada miembro del equipo conoce los nombres canónicos.
- **Sanitización de PII**: ningún `dev.log` debe contener datos personales identificables (nombre completo, DNI, email, token JWT). Los repositories logean IDs y operaciones, no contenido. El reviewer marca cualquier log que filtre PII.
- **Logs en tests**: los tests pueden capturar logs con `Zone.fork(specification: ...)` si necesitan verificar que se emitió un log específico. En la práctica esto se hace solo en tests del subsistema Auth para verificar mensajes de refresh.
- **Sin logs en release**: si el proyecto decide en una fase futura emitir logs estructurados a un backend remoto (Crashlytics, Sentry, custom endpoint), se introduce un servicio `LogService` que envuelve `dev.log` y duplica al canal remoto. La superficie de cambio queda contenida.

## Referencias

- **[`dart:developer` — `log` function](https://api.dart.dev/stable/dart-developer/log.html)** — documentación oficial.
- **[Flutter DevTools — Logging view](https://docs.flutter.dev/tools/devtools/logging)** — panel donde se filtra por `name`.
- **[ADR-012 Riverpod](adr-012-riverpod.md)** — los ViewModels y use cases consumen logs vía esta convención.
- **[ADR-004 Cliente HTTP](adr-004-http-cliente.md)** — el wrapper API es el mayor productor de logs (`name: 'API'`).
