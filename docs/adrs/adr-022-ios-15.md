---
title: ADR-022 — Versión mínima de iOS soportada
description: >-
  custodiam-app declara iOS 15.0 como versión mínima soportada, forzada por
  Firebase iOS SDK 12.x que custodiam consume vía firebase_core para FCM.
  Materializada en Podfile y project.pbxproj.
---

# ADR-022 — Versión mínima de iOS soportada

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 15 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El template `flutter create` deja `ios/Podfile` con la línea `platform :ios, '13.0'` comentada y `IPHONEOS_DEPLOYMENT_TARGET = 13.0` por defecto. Mientras la app solo usaba dependencias compatibles con iOS 13, esa configuración compilaba sin fricción.

Al integrar Firebase Cloud Messaging para el sistema de notificaciones del proyecto, se añadió `firebase_core ^4.9.0` al `pubspec.yaml`. El primer `flutter run` real sobre iOS tras esa incorporación falló con:

```
[!] CocoaPods could not find compatible versions for pod "firebase_core":
    Specs satisfying the `firebase_core` dependency were found,
    but they required a higher minimum deployment target.

Error: The plugin "firebase_core" requires a higher minimum iOS deployment
version than your application is targeting. To build, increase your
application's deployment target to at least 15.0.
```

El detonante es **Firebase iOS SDK 12.x**, que el paquete Flutter `firebase_core 4.x` consume directamente. Firebase elevó el mínimo a iOS 15.0 en la línea 12 del SDK (release notes oficiales de octubre de 2024) alineándose con el ciclo de soporte de Apple. La decisión a tomar: subir el mínimo o renunciar a Firebase.

## Decisión

**iOS 15.0 como mínimo soportado**, materializado en tres puntos del proyecto Flutter:

| Punto | Cambio |
| --- | --- |
| `ios/Podfile` (línea 2) | `# platform :ios, '13.0'` → `platform :ios, '15.0'` (descomentada y bumpeada) |
| `ios/Runner.xcodeproj/project.pbxproj` (config Debug) | `IPHONEOS_DEPLOYMENT_TARGET = 13.0;` → `15.0;` |
| `ios/Runner.xcodeproj/project.pbxproj` (config Release) | Idem |
| `ios/Runner.xcodeproj/project.pbxproj` (config Profile) | Idem |

Tras los cambios, `cd ios && pod install --repo-update` regenera el `Podfile.lock` con `Firebase 12.13.0` + `FirebaseCore 12.13.0` + `FirebaseCoreInternal 12.13.0` + `GoogleUtilities 8.1.0` instalados sin conflicto. `flutter run --release` arranca limpio.

Existe un warning residual sobre `Profile.xcconfig` (CocoaPods no puede enganchar su `.profile.xcconfig` porque la config `Profile` del target reutiliza `Release.xcconfig`) que **no bloquea `--release` ni `--debug`** — solo afectaría a `flutter run --profile`. Si llega el caso, crear `Flutter/Profile.xcconfig` espejo del `Release` y reapuntar `baseConfigurationReference`.

## Justificación

1. **Forzado por dependencia ya decidida.** Firebase Cloud Messaging es el canal primario de notificaciones del proyecto (FCM principal, ntfy de respaldo). Renunciar a Firebase para mantener iOS 13/14 contradice esa decisión y deja a ntfy sin redundancia en iOS, donde además ntfy depende de polling porque Apple no permite *long-lived background sockets*. **No es una decisión libre — es la consecuencia coherente de decisiones arquitectónicas previas.**

2. **Cobertura suficiente para el piloto.** iOS 15 salió en septiembre de 2021 y soporta iPhone 6s en adelante (lanzado 2015). Los dispositivos descartados son iPhone 5s/6/6 Plus, iPod touch 7G y dispositivos no actualizables más allá de iOS 14. Para el piloto de Protección Civil Bajo Gállego (~50 voluntarios), la asunción razonable es que el parque de iPhones está mayoritariamente en iOS 16-18; los que estén en iOS 14 ya tienen ventana de upgrade gratuita a iOS 15 disponible desde hace años. Riesgo de exclusión real estimado: <5 % de los voluntarios con iPhone.

3. **Alineado con el ciclo de Apple.** Apple deja de firmar versiones antiguas de iOS poco después de cada release mayor. iOS 13 dejó de recibir actualizaciones de seguridad en marzo de 2023, iOS 14 en septiembre de 2023. Soportar versiones sin parches de seguridad en una app que gestiona datos personales de voluntarios (RGPD aplicable por dominio de Protección Civil) es difícilmente defendible en una auditoría de seguridad o de cumplimiento.

4. **Coste de mantenimiento al revés.** Soportar iOS 13/14 obligaría a fijar `firebase_core` en una versión antigua de la rama 2.x o 3.x (compatible con Firebase SDK 10.x, que aceptaba iOS 13). Eso arrastra divergencia con el ecosistema actual de FlutterFire, bloquea actualizaciones de seguridad de Firebase y crea deuda técnica que se pagará la primera vez que sea necesario actualizar cualquier otro paquete del ecosistema.

5. **Equivalencia con la decisión Android.** Android tiene `minSdkVersion 21` (Android 5.0, 2014), que cubre ~99 % de dispositivos activos. iOS 15 cubre una proporción equivalente del parque de iPhones reales. La paridad de "mínimos razonables del momento" entre ambas plataformas es coherente.

## Alternativas evaluadas y descartadas

### A. Mantener iOS 13.0 y renunciar a Firebase

- **Pros**: cobertura máxima de dispositivos antiguos.
- **Contras**: obliga a rediseñar la estrategia de notificaciones para iOS, con ntfy en polling como único canal. Viola el principio "FCM primario, ntfy de respaldo" y degrada UX iOS de forma notable (latencia de notificaciones, consumo de batería).
- **Descartado por**: contradice decisiones previas sobre notificaciones y degrada el producto.

### B. Mantener iOS 13.0 fijando `firebase_core` en una versión antigua

`firebase_core ^2.x` (Firebase SDK 10.x) acepta iOS 13.

- **Pros**: cobertura máxima sin renunciar a Firebase.
- **Contras**: divergencia permanente con el ecosistema FlutterFire actual, bloqueo de updates de seguridad, deuda técnica que escala con cada paquete del bundle FlutterFire que más adelante se quiera integrar (`firebase_messaging`, `firebase_analytics`, etc., todos en líneas 10.x si se fija el core en 2.x).
- **Descartado por**: deuda técnica desproporcionada.

### C. iOS 14.0 como compromiso

- **Pros**: aparenta ser intermedio.
- **Contras**: no desbloquea ningún plugin del proyecto — Firebase SDK 12.x requiere 15.0, no 14.0. Es un mínimo "tibio" que descarta los mismos dispositivos que 15.0 (iPhone 5s/6/6 Plus) sin ganar compatibilidad con la dependencia que motiva el bump.
- **Descartado por**: irrelevante; no resuelve el problema.

### D. iOS 16.0+ como mínimo más conservador

- **Pros**: parches de seguridad más recientes.
- **Contras**: recortaría iPhone 6s/7 y otros dispositivos perfectamente válidos sin beneficio técnico observable hoy — ninguna dependencia actual lo exige.
- **Descartado por**: recorte sin contraprestación.

## Implicaciones operativas

- **Builds locales y CI:** cualquier `flutter run` o `flutter build ios` que se ejecute por primera vez tras un `flutter pub get` que toque Firebase invocará `pod install`. Sin el bump, falla en CocoaPods antes incluso de pasar a Xcode. El mensaje de error aparece en troubleshooting con el texto literal para facilitar `grep`.
- **Stores:** Apple App Store acepta deployment targets ≥ iOS 12.0, así que iOS 15 está dentro de rango. El campo `MinimumOSVersion` del `Info.plist` se derivará del `IPHONEOS_DEPLOYMENT_TARGET` del target Runner automáticamente.
- **Aplicación a la app web y Android:** ADR-022 solo afecta a iOS. El `minSdkVersion` de Android sigue en 21 (decisión previa, fuera del alcance). Flutter Web no tiene equivalente.
- **Reversibilidad:** bajar iOS 15 → 14 o 13 requiere bajar `firebase_core` a la rama 2.x (ver alternativa B). La decisión es **reversible solo a coste de deuda técnica acumulada**, lo que en la práctica significa que cualquier revisión futura del mínimo será "subir a 16/17", no "bajar".
- **Próximas revisiones esperadas:** Firebase iOS SDK habitualmente sube su mínimo ~1 año después de cada release mayor de Apple, así que el próximo bump esperado es iOS 16 entre finales de 2026 y principios de 2027.

## Referencias

- **[Firebase Apple platforms — Prerequisites](https://firebase.google.com/docs/ios/setup#prerequisites)** — requisitos oficiales del SDK iOS.
- **[Flutter — Adjusting iOS app version](https://docs.flutter.dev/deployment/ios#review-xcode-project-settings)** — cómo subir el deployment target.
- **[Apple App Store Connect — iOS and iPadOS Usage](https://developer.apple.com/support/app-store/)** — cobertura real de dispositivos por versión.
