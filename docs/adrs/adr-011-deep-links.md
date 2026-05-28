---
title: ADR-011 — Estrategia de deep links
description: >-
  Custodiam combina custom scheme para el callback OAuth (es.custodiam://callback)
  con App Links Android y Universal Links iOS verificados sobre HTTPS para
  emails transaccionales, notificaciones push y enlaces compartidos.
---

# ADR-011 — Estrategia de deep links

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 18 de febrero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Custodiam necesita que ciertos enlaces, recibidos desde fuera de la aplicación, abran la app móvil instalada (o la PWA cuando la app nativa no lo está) en lugar de un navegador web genérico. Tres familias de enlaces concentran esta necesidad:

1. **Callback del flujo OAuth/OIDC con Keycloak.** Tras autenticarse en `auth.custodiam.es`, el servidor de identidad redirige al cliente con un `authorization code` que la app debe canjear por tokens. La redirección ocurre dentro del contenedor de autenticación que la propia app inicia (Chrome Custom Tab en Android o `ASWebAuthenticationSession` en iOS).
2. **Enlaces dentro de emails transaccionales generados por Keycloak.** Recuperación de contraseña y verificación de email contienen un token de un solo uso que la app debe procesar para completar la operación.
3. **Enlaces dentro de notificaciones push y enlaces compartidos entre usuarios.** Deep links a entidades específicas del modelo (`/servicio/{id}`, `/emergencia/{id}`) cuyo destino es la pantalla concreta de esa entidad.

Android (desde 6.0) e iOS (desde 9.0) ofrecen dos mecanismos para resolver el problema, con perfiles muy distintos:

| Mecanismo | Declaración en la app | Verificación de propiedad del dominio | Manifiesto del dominio |
| --- | --- | --- | --- |
| **Custom URL scheme** | `CFBundleURLSchemes` en `Info.plist` (iOS) o `intent-filter` con `android:scheme` (Android) | Ninguna — cualquier app instalada puede declarar cualquier scheme | No requiere |
| **App Links / Universal Links HTTPS** | `applinks:` entitlement (iOS) o `intent-filter` con `android:autoVerify="true"` (Android) | Criptográfica — el sistema operativo descarga un manifiesto en el dominio y comprueba que su contenido autoriza al binario firmado de la app | `apple-app-site-association` (iOS) y `assetlinks.json` (Android) servidos en `/.well-known/` con `Content-Type: application/json` |

La decisión a tomar: ¿qué mecanismo se usa en cada familia?

## Decisión

| Familia de enlaces | Plataforma | Mecanismo | URL canónica |
| --- | --- | --- | --- |
| Callback OAuth (Keycloak) | Android e iOS | Custom URL scheme | `es.custodiam://callback` |
| Callback OAuth (Keycloak) | Flutter Web | Ruta interna de la PWA (no aplica AASA / `assetlinks`) | `https://app.custodiam.es/callback`, interceptada por `go_router` |
| Email "recuperar contraseña" y "verificar email" (Keycloak) | Android, iOS y Web | App Link / Universal Link HTTPS verificado | `https://app.custodiam.es/reset-password`, `/verify-email` |
| Deep links de notificaciones push y enlaces compartidos | Android, iOS y Web | App Link / Universal Link HTTPS verificado | `https://app.custodiam.es/servicio/*`, `/emergencia/*` |

## Justificación

1. **Los clientes de email strippean los custom schemes; los contenedores OAuth no.** Es el argumento operativo principal. Gmail, Outlook, Apple Mail y otros clientes de correo de cuota relevante eliminan o desactivan los enlaces con esquemas no estándar (`whatever://`) por razones de seguridad anti-phishing — un enlace `bank://login?token=...` podría secuestrar una aplicación maliciosa instalada por el usuario sin que este lo perciba. La consecuencia práctica es que, si Keycloak enviase emails con `es.custodiam://reset-password?token=...`, los usuarios verían un enlace inerte o ausente y el flujo se rompería. El callback de OAuth, en cambio, **nunca atraviesa un cliente de email**: vive dentro de un Chrome Custom Tab o `ASWebAuthenticationSession` que el propio sistema operativo proporciona como contenedor del flujo de autenticación, contenedores diseñados específicamente para capturar custom schemes y devolver el control a la app que los inició.

2. **PKCE neutraliza la vulnerabilidad clásica del custom scheme en OAuth.** La objeción histórica al uso de custom schemes en OAuth es el riesgo de *scheme hijacking*: una app maliciosa instalada antes que la nuestra podría declarar el mismo scheme y, en sistemas operativos que muestren un selector de aplicaciones, recibir el `authorization code` legítimo. Si después intercambiase ese code por tokens, conseguiría suplantar la sesión. Este vector está neutralizado en Custodiam porque el cliente OAuth tiene **PKCE S256 obligatorio** ([ADR-010](adr-010-oauth-pkce-keycloak.md)). El intercambio `code → tokens` exige presentar el `code_verifier` original, un secreto generado dinámicamente y mantenido en memoria por el cliente que originó el flujo. Una app maliciosa que capturara el code no tendría manera de adivinarlo, y Keycloak rechazaría la petición con `invalid_grant`. [RFC 8252 §8.1](https://datatracker.ietf.org/doc/html/rfc8252#section-8.1) reconoce explícitamente esta combinación (custom scheme con dominio propio del fabricante + PKCE obligatorio) como aceptable para *native apps*.

3. **App Links y Universal Links sobre HTTPS introducen fricción operacional grave en desarrollo móvil local.** Las verificaciones criptográficas exigen tres elementos no triviales:
    - **Certificado HTTPS público** firmado por una autoridad certificadora reconocida por el sistema operativo. Certificados autofirmados, `mkcert` local o autoridades certificadoras propias no son válidos para Universal Links en iOS.
    - **Archivo de manifiesto** (`assetlinks.json` o `apple-app-site-association`) servido sobre ese HTTPS público en la ruta canónica `/.well-known/`, con MIME type correcto.
    - **Cache de verificación propio del sistema operativo**. Cada cambio en el manifiesto requiere desinstalar y reinstalar la app en el dispositivo o emulador para forzar la re-validación.

    Esta fricción es asumible para enlaces *outbound* (emails y notificaciones, que en local se simulan con dominio público de pruebas o se aceptan como flujo no validado localmente). Pero sería un coste recurrente fijo para todo desarrollo iOS/Android de OAuth, que es uno de los flujos más ejercitados durante el ciclo de desarrollo del frontend. El custom scheme funciona sin red pública, sin DNS, sin certificados y sin reinstalaciones — declararlo en el manifiesto nativo de cada plataforma es suficiente.

4. **La asimetría plataforma móvil ↔ plataforma web es natural, no es divergencia.** En Flutter Web, el `redirect_uri` del cliente OAuth ya es HTTPS (`https://app.custodiam.es/callback` en producción) porque el callback es una ruta interna del propio PWA: el navegador la sirve mediante navegación habitual y `go_router` la intercepta. Aquí no interviene el sistema operativo móvil; AASA y `assetlinks.json` son **irrelevantes** para una SPA que se navega a sí misma. La elección del custom scheme en móvil **no genera divergencia conceptual** con la rama web: cada plataforma usa el mecanismo nativo más simple para su entorno, y el cliente OAuth de Keycloak acepta los tres `redirect_uri` declarados (móvil custom scheme + web localhost de desarrollo + web HTTPS de producción).

5. **Los enlaces *outbound* a la app no incluyen nunca el callback OAuth.** El callback se produce siempre como continuación inmediata del flujo de autenticación iniciado *desde dentro* de la app. Nunca llega al usuario por canal asíncrono: ningún email, push, enlace compartido ni mensaje en otra app va a contener un `/callback?code=...`. En consecuencia, ningún flujo realista justifica que `/callback` esté declarado en los manifiestos `apple-app-site-association` o `assetlinks.json`. Si se incluyera, sería un path que el sistema operativo verificaría sin que ningún emisor lo use jamás — declaración muerta que invita a confusión sobre qué partes del flujo de auth están migradas y cuáles no.

## Alternativas evaluadas y descartadas

### A. Custom scheme también para emails y notificaciones

Era el estado original del proyecto en la fase de fundación.

- **Pros**: simplicidad operativa, sin manifiestos `/.well-known/` ni certificados.
- **Contras**: argumento 1 (strippeo en clientes de correo) lo invalida para email. Notificaciones push y enlaces compartidos también pueden pasar por canales externos (Telegram, WhatsApp) que aplican el mismo strippeo.
- **Descartado por**: no escala al canal email ni a enlaces compartidos.

### B. App Link HTTPS también para el callback OAuth

- **Pros**: paridad de mecanismo en todos los enlaces.
- **Contras**: argumentos 3 (fricción en desarrollo local) y 5 (canal de entrega del callback es OAuth-contained, no outbound). El intercambio en seguridad no compensa: PKCE ya elimina el vector que App Link aportaría como mejora.
- **Descartado por**: coste operativo desproporcionado para una protección que PKCE ya garantiza.

### C. División parcial: custom scheme para algunos emails y HTTPS para otros

Por ejemplo, custom scheme para `reset-password` (porque "el usuario ya sabe lo que ha pedido") y HTTPS para `verify-email`.

- **Pros**: optimizaría el flujo de reset.
- **Contras**: inconsistencia operacional — la división correcta es por **canal** de entrega (Chrome Custom Tab contained vs cualquier canal outbound), no por el tipo concreto de email.
- **Descartado por**: invertiría la lógica del argumento 1.

## Implicaciones operativas

- **OAuth móvil funciona en cualquier entorno de desarrollo** sin red pública ni certificados — solo manifiestos nativos (`Info.plist` y `AndroidManifest.xml`). Coste cero por iteración.
- **Emails y notificaciones requieren `app.custodiam.es` accesible públicamente con HTTPS válido.** En desarrollo local se simulan apuntando a un dominio público de pruebas, o se acepta que ese flujo concreto no se valide localmente. En producción lo cubre la PWA servida con los manifiestos en `/.well-known/`.
- **El cliente OAuth en Keycloak** declara tres `redirect_uri` separados y disjuntos: `es.custodiam://callback` para móvil, `http://localhost:3000/callback` para web de desarrollo y `https://app.custodiam.es/callback` para web de producción. Cualquier nuevo dominio que sirva la PWA requiere registro adicional como `redirect_uri` válido.
- **Los manifiestos `apple-app-site-association` y `assetlinks.json`** declaran exclusivamente los paths de canal outbound: `/reset-password`, `/verify-email`, `/servicio/*`, `/emergencia/*`. **No** declaran `/callback`, coherente con esta decisión.
- **Las plantillas de email en Keycloak** usan `https://app.custodiam.es/...` como URL base de los enlaces. El `redirect_uri` del custom scheme se mantiene en la configuración del cliente Keycloak indefinidamente: cumple solo el flujo OAuth, no los flujos de email.

## Referencias

- **[RFC 8252 — OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252)** — establece PKCE obligatorio (§7.2) y reconoce el uso de custom schemes con dominio propio del fabricante (§7.1) como aceptable para aplicaciones nativas.
- **[Apple Developer — Supporting Associated Domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains)** — requisitos de servido del `apple-app-site-association`, cache de verificación e integración con Xcode.
- **[Google Developers — Verify Android App Links](https://developer.android.com/training/app-links/verify-android-applinks)** — especificación del `assetlinks.json`, verificación con `pm verify-app-links`, casos de fallback.
- **[ADR-010 OAuth + PKCE + Keycloak](adr-010-oauth-pkce-keycloak.md)** — establece PKCE S256 obligatorio en el cliente, base del argumento 2.
