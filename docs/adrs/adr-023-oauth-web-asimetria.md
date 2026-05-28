---
title: ADR-023 — Asimetría OAuth + PKCE en SPA web vs cliente móvil
description: >-
  Dos implementaciones de AuthService seleccionadas por kIsWeb + persistencia
  del code_verifier en sessionStorage para la implementación web. La interfaz
  AuthService permanece invariante y el resto del cliente no ve la división.
---

# ADR-023 — Asimetría OAuth + PKCE en SPA web vs cliente móvil

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 20 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Tras estabilizar el despliegue de la PWA pública `https://app.custodiam.es` con la imagen `custodiam-web` (nginx + cache busting correcto), las verificaciones *end-to-end* del flujo de autenticación revelaron un fallo distinto: el botón "Iniciar sesión" redirige correctamente a Keycloak (`https://auth.custodiam.es/realms/custodiam/...`), el usuario se autentica, Keycloak devuelve el control a `https://app.custodiam.es/callback?code=...`, pero la app **no completa el intercambio del código por tokens** y rebota al usuario a `/login`.

La causa raíz es estructural y específica del flujo OAuth 2.0 + PKCE en aplicaciones de página única:

- **En móvil (Android/iOS)**, `KeycloakAuthService.login()` lanza el navegador externo con `launchUrl(authUrl, mode: LaunchMode.externalApplication)`. La app Flutter **sigue viva en memoria**, esperando el `callback` por *deep link* a través de `app_links`. Al volver del navegador, el método `_pendingGrant.handleAuthorizationResponse()` se ejecuta dentro de la misma instancia que conserva el `code_verifier` PKCE generado al inicio del flujo.
- **En web**, `launchUrl(authUrl, webOnlyWindowName: '_self')` **sustituye la pestaña actual** por la URL de Keycloak. Cuando Keycloak redirige de vuelta a `/callback`, el navegador carga la aplicación Flutter **completamente desde cero**: una nueva instancia de `KeycloakAuthService` se crea con `_pendingGrant == null`, y `handleWebCallback` falla silenciosamente devolviendo `Fail(AuthFailure.refreshFailed())`.

Es un problema clásico del flujo PKCE en SPAs, conocido en la industria, y para el que existen patrones canónicos de solución. La asimetría móvil/web estaba documentada a alto nivel desde el inicio, pero **no se descendió al detalle de la persistencia del `code_verifier` entre cargas**, lo que dejó el bug latente hasta la primera prueba end-to-end real contra el dominio público.

## Decisión

Combinación de dos resoluciones complementarias:

1. **Separación de implementaciones por plataforma vía Clean Architecture.** La interfaz `AuthService` permanece invariante. Se crean dos implementaciones concretas:
    - **`KeycloakMobileAuthService`** — especializada en el flujo OAuth + PKCE con redirect a navegador externo y captura del callback por *deep link*. Equivale a la implementación previa sin las ramas condicionales `kIsWeb`.
    - **`KeycloakWebAuthService`** — especializada en el flujo OAuth + PKCE con redirect `_self` y reconstrucción del grant tras la nueva carga de la app.

    El `authServiceProvider` (Riverpod, en `lib/infrastructure/di/providers.dart`) selecciona una u otra implementación en tiempo de ejecución vía `kIsWeb`.

2. **Persistencia del `code_verifier` en `window.sessionStorage` para la implementación web.** Antes de lanzar el redirect a Keycloak, `KeycloakWebAuthService.login()` guarda el `code_verifier` en `sessionStorage` bajo una clave identificada (`custodiam.oauth.code_verifier`). En `handleWebCallback` recupera el `code_verifier` persistido, reconstruye el `oauth2.AuthorizationCodeGrant` con el parámetro `codeVerifier:` apuntando a ese valor, procesa el callback, limpia la clave de `sessionStorage` y completa el flujo.

`sessionStorage` se elige sobre `localStorage` por su semántica precisa: vida útil ligada a la pestaña del navegador (se limpia al cerrarla), no se sincroniza entre pestañas (lo cual evita interferencias entre ventanas simultáneas), y desaparece automáticamente sin que la app tenga que recordar limpiarlo en caminos de error.

## Justificación

1. **Coherencia con Clean Architecture.** El cliente Flutter adopta Clean estricto + Feature-first. Una asimetría real entre dos plataformas se modela con **dos implementaciones concretas de una misma interfaz**, no con ramificación condicional dentro de una sola clase. Mantener `kIsWeb` dentro de `KeycloakAuthService` introduce dos flujos divergentes que comparten estado por accidente; separarlos elimina el origen del bug operativo.

2. **Decisiones arquitectónicas previas se conservan.** La elección del stack (`oauth2` + `url_launcher` + `app_links`, [ADR-010](adr-010-oauth-pkce-keycloak.md)) no requiere modificación. Esta decisión opera estrictamente dentro de la capa `infrastructure/auth/` sin propagarse al resto de la arquitectura (ViewModels, router, ni el resto de features ven el cambio).

3. **Riesgo y coste de implementación bajos.** Refactor localizado (renombrar la clase actual, crear la nueva, ajustar el provider). Estimación realista: 1-2 días de trabajo. Los mocks de tests existentes (`_MockAuthService`, `_ToggleAuthService`, `_InMemoryAuthService`) siguen siendo válidos porque la interfaz no cambia.

4. **Aplicación canónica del principio "separar el qué del cómo".** Una misma capacidad funcional (autenticación) implementada con dos mecanismos distintos según el contexto de ejecución, sin que el resto del sistema deba saber cuál está en uso. Encaja con el patrón general aplicable cuando una plataforma real impone restricciones distintas a las de otra.

5. **Reversibilidad alta.** Si en el futuro se decide migrar al patrón BFF (ver alternativas descartadas), las dos implementaciones aquí decididas se sustituyen por una sola (`KeycloakBffAuthService` o equivalente) sin que el resto del cliente vea el cambio. El compromiso aquí es mínimo.

## Alternativas evaluadas y descartadas

### A. Single-service con `kIsWeb` interno (lo que había, fallido)

- **Pros**: una sola clase, menos código.
- **Contras**: el estado en memoria (`_pendingGrant`) no sobrevive a la redirección `_self` en web y el código se enreda al intentar gestionar dos modelos de ciclo de vida en una misma instancia.
- **Descartado por**: es el origen del bug operativo detectado.

### B. `localStorage` en lugar de `sessionStorage` para persistir el `code_verifier`

- **Pros**: persiste entre pestañas y entre sesiones del navegador.
- **Contras**: el `code_verifier` es un secreto efímero del flujo; no debe sobrevivir al cierre de la pestaña. `localStorage` introduce riesgo de fuga y obliga a la aplicación a limpiarlo explícitamente en caminos de error que podrían no ejecutarse.
- **Descartado por**: vida útil incorrecta para un secreto efímero.

### C. `flutter_secure_storage` para el `code_verifier`

- **Pros**: almacenamiento cifrado por dispositivo (Keychain en iOS, EncryptedSharedPreferences en Android, IndexedDB cifrado en web).
- **Contras**: sobredimensionado — es la respuesta correcta para *refresh tokens* persistentes pero excesiva para un secreto que solo necesita sobrevivir una redirección de unos segundos.
- **Descartado por**: complejidad innecesaria para el caso.

### D. `shared_preferences`

- **Pros**: paquete ya declarado en `pubspec.yaml`.
- **Contras**: en web `shared_preferences` utiliza `localStorage` por debajo, heredando los mismos problemas que la alternativa B.
- **Descartado por**: implementación equivalente a `localStorage` con misma semántica errónea.

### E. Popup OAuth en lugar de redirect `_self` (`webOnlyWindowName: '_blank'`)

- **Pros**: la app principal queda viva, el popup se cierra al terminar.
- **Contras**: la mayoría de navegadores bloquean *popups* no iniciados por interacción directa del usuario; la UX en móvil web es deficiente; complica el manejo del cierre prematuro del popup.
- **Descartado por**: experiencia de usuario degradada y bloqueo del navegador.

### F. Iframe oculto con `prompt=none` (silent SSO)

- **Pros**: refrescos invisibles cuando hay sesión activa.
- **Contras**: solo funciona cuando existe una sesión activa en Keycloak; no resuelve el flujo de *login* inicial. Es complemento posible para refrescos silenciosos en navegadores donde la cookie de Keycloak siga viva, pero no es la primera línea de defensa.
- **Descartado** como única solución; queda apuntado como complemento futuro.

### G. Cambio de paquete a `openid_client` o `keycloak_flutter`

- **Pros**: librerías especializadas pueden gestionar internamente la persistencia.
- **Contras**: ambos cambian la decisión de stack de auth, obligan a refactorizar también el flujo móvil que hoy funciona, y representan ecosistemas menos maduros en Flutter que `oauth2 + url_launcher + app_links`.
- **Descartado por**: refactor de alcance mayor sin beneficio sobre la solución propuesta.

### H. Patrón BFF (*Backend for Frontend*) en FastAPI

En el patrón BFF, la PWA nunca recibe tokens: toda la danza OAuth (incluido el `code_verifier`) ocurre en `custodiam-api`, que gestiona una sesión web vía cookie `httpOnly` y hace de proxy para las llamadas autenticadas. Es el patrón **recomendado por OWASP para SPAs nuevas desde aproximadamente 2023** por su reducción de la superficie de ataque XSS sobre tokens.

- **Pros**: técnicamente superior. Elimina el almacenamiento de tokens en el cliente web. Reduce el riesgo XSS sobre credenciales. Postura de seguridad alineada con las recomendaciones actuales.
- **Contras**:
    - Cambia la decisión de stack de auth ([ADR-010](adr-010-oauth-pkce-keycloak.md)) fundamentalmente: en web los tokens dejan de ser artefacto del cliente.
    - Requiere implementar middleware de sesión en FastAPI (cookies `httpOnly`, protección CSRF, refresh server-side), no presupuestado.
    - Estimación realista: 2-3 semanas de trabajo en una fase del proyecto orientada al cierre del piloto.
    - El piloto utilizará principalmente la app móvil, donde el flujo OAuth + PKCE directo (cliente nativo confiable) es perfectamente apropiado. La PWA web es canal secundario.
- **Descartado para el MVP**, **apuntado como evolución natural** en fases posteriores. Una migración futura a BFF puede realizarse sin invalidar esta decisión: las dos implementaciones de `AuthService` se sustituyen por una sola (`KeycloakBffAuthService`) o se mantiene el modelo cliente-nativo en móvil y se añade el `KeycloakBffAuthService` solo para web.

### I. Cambio de Identity Provider a Auth0, AWS Cognito u Okta

- **Pros**: gestionado, sin necesidad de operar Keycloak.
- **Contras**: cambia decisiones arquitectónicas fundamentales — el proyecto ha sostenido la elección de Keycloak con argumentos sólidos (soberanía sobre los datos, AGPL-3.0, autohospedaje, sin coste por usuario activo).
- **Descartado por**: cambio de IdP fuera del alcance.

## Implicaciones operativas

- **Refactor incremental, no *big bang*.** La interfaz `AuthService` se mantiene exactamente igual. El cambio es invisible para el resto del cliente Flutter (ViewModels, router, redirects de GoRouter). Únicamente `lib/infrastructure/di/providers.dart` selecciona una u otra implementación.
- **Tests existentes válidos.** Los mocks (`_MockAuthService`, `_ToggleAuthService`, `_InMemoryAuthService`) implementan `AuthService` y siguen siendo válidos. Se añaden tests específicos para `KeycloakWebAuthService` que cubren el ciclo *login → persistir `code_verifier` → callback con grant reconstruido*.
- **Tres pruebas E2E nuevas requeridas:**
    1. **Login web feliz** hasta `/home`.
    2. **Login web con `sessionStorage` deshabilitado** por el navegador — la app debe degradar a un mensaje de error claro en lugar de fallar en silencio.
    3. **Recarga manual de la pestaña** en medio del flujo (entre el redirect y el callback) — escenario poco frecuente pero conviene cubrirlo.
- **Sin impacto en seguridad respecto al modelo PKCE estándar.** El `code_verifier` permanece en `sessionStorage` durante segundos (los que tarda Keycloak en responder y el callback en ejecutarse), bajo el modelo de aislamiento de orígenes del navegador. No es un secreto persistente: si la pestaña se cierra antes de completar el flujo, el `code_verifier` se descarta automáticamente y el `code` recibido en el callback resulta inutilizable por sí solo.
- **Documentación a actualizar.** La sección sobre la asimetría móvil/web del flujo OIDC se reescribe con la nueva estructura de dos implementaciones. La capa `infrastructure/auth/` queda como ejemplo canónico del patrón "interfaz cross-cutting + implementaciones por plataforma" aplicable a futuras asimetrías reales.

## Referencias

- **[RFC 7636 — Proof Key for Code Exchange](https://datatracker.ietf.org/doc/html/rfc7636)** — fundamento del flujo PKCE.
- **[RFC 9700 — Best Current Practice for OAuth 2.0 Security](https://datatracker.ietf.org/doc/html/rfc9700)** §2.1.1 — trata explícitamente el problema de la persistencia del `code_verifier` en clientes SPA.
- **[Paquete `oauth2` en pub.dev](https://pub.dev/packages/oauth2)** — referencia del parámetro `codeVerifier:` opcional del constructor de `AuthorizationCodeGrant`, que permite la reconstrucción del grant desde un `code_verifier` persistido.
- **[Web Storage API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)** — semántica de `sessionStorage` (por pestaña, no se sincroniza entre tabs, se limpia al cerrar).
- **[OAuth 2.0 for Browser-Based Apps (IETF draft)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-browser-based-apps)** — discusión del patrón BFF como alternativa a OAuth + PKCE directo en SPA (relevante para la evolución futura mencionada en la alternativa H).
- **[ADR-010 OAuth + PKCE + Keycloak](adr-010-oauth-pkce-keycloak.md)** — stack de auth sobre el que se asienta esta decisión.
