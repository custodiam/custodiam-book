---
title: ADR-010 — OAuth 2.0 + PKCE + Keycloak + PyJWT
description: >-
  Custodiam usa Keycloak como Identity Provider con el flujo Authorization Code
  + PKCE, valida el JWT localmente en el backend con PyJWT y mantiene el cliente
  móvil como cliente OAuth público sin secret.
---

# ADR-010 — OAuth 2.0 + PKCE + Keycloak + PyJWT

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 12 de febrero de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

Custodiam requiere autenticación con tres clientes simultáneos: aplicación móvil Android, aplicación móvil iOS y aplicación web servida como SPA (Single Page Application). El sistema debe permitir login y logout, sesión persistente mediante refresh tokens, autorización por roles del servidor (RBAC) y la posibilidad de añadir segundo factor en fases posteriores. Las decisiones a tomar son tres acopladas:

1. **Identity Provider (IdP)**: ¿implementación propia o servicio externo? ¿open-source autoalojable o SaaS?
2. **Flujo OAuth**: con tres clientes públicos (móvil + SPA), no se puede almacenar un *client_secret* de forma segura → flujo Authorization Code con PKCE (Proof Key for Code Exchange, [RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)).
3. **Validación del JWT**: el backend recibe un *bearer token* en cada petición. ¿Lo valida remotamente contra el IdP en cada llamada o lo verifica localmente con la clave pública?

## Decisión

- **IdP**: **[Keycloak](https://www.keycloak.org/)** v26+ autoalojado como contenedor Docker dentro del stack.
- **Flujo de autorización**: **OAuth 2.0 Authorization Code con PKCE** ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) para los tres clientes. Los dos clientes móviles usan deep links (`es.custodiam://callback`); la SPA web usa redirección HTTP estándar (`https://app.custodiam.es/callback`).
- **Cliente Dart**: paquete oficial [`oauth2`](https://pub.dev/packages/oauth2) de `pub.dev` (no `flutter_appauth`, ver ADR-004).
- **Validación JWT en backend**: **local con `PyJWT[crypto]` y verificación de firma RS256** usando la JWKS pública de Keycloak (cacheada cinco minutos en memoria del proceso).
- **Defensa en profundidad**: validación adicional del claim `azp` (*Authorized Party*) según [RFC 9068](https://datatracker.ietf.org/doc/html/rfc9068) contra `settings.keycloak_authorized_party` (configurable, por defecto `custodiam-app`).

## Justificación

1. **Keycloak es el estándar abierto** del espacio IdP autoalojable. Soporta OIDC + SAML, tiene admin UI, gestión de usuarios, segundo factor, federación, plantillas de email, importación de realms desde JSON. Comunidad activa, releases regulares, documentación oficial extensa.

2. **PKCE es obligatorio para clientes públicos**. Sin PKCE, un atacante que interceptase el código de autorización en la redirección podría intercambiarlo por tokens. PKCE genera un `code_verifier` aleatorio por sesión y un `code_challenge = SHA-256(code_verifier)` que solo el cliente original conoce. El servidor de tokens exige el `code_verifier` original al intercambiar el código, cerrando el vector de ataque ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636) §1).

3. **Validación local elimina latencia y acoplamiento**. Cada petición a la API verifica el JWT en microsegundos contra la JWKS cacheada, sin viaje de red al IdP. Si Keycloak cae temporalmente, los tokens emitidos siguen siendo válidos hasta su `exp`; las sesiones activas no se rompen. Esto materializa el principio de resiliencia documentado en la arquitectura.

4. **`azp` check** es defensa en profundidad sobre `verify_aud=False`. Keycloak emite `aud=account` por defecto, lo que obligaría a configurar un *audience-resolve mapper* específico si se activase `verify_aud=True`. La verificación del `azp` (que Keycloak rellena con el `client_id` que solicitó el token) es funcionalmente equivalente y mucho más simple. Sin esta verificación, cualquier futuro cliente OAuth del mismo realm podría obtener tokens válidos para esta API. Cubierto por cinco tests específicos en `test_jwt_azp.py`.

5. **El paquete `oauth2` de Dart** mantiene un `Client` envuelto sobre `http`, gestiona el refresh automático del access token cuando expira, y persiste credenciales con `Credentials.toJson()`. La alternativa `flutter_appauth` era una opción inicial pero ataba a un fork no oficial cuyos breaking changes complicaban el upgrade del cliente.

## Alternativas evaluadas y descartadas

### A. Auth0 / Okta / Cognito (SaaS)

- **Pros**: cero mantenimiento, escalabilidad, integración rápida.
- **Contras**: coste recurrente (Auth0 free tier es muy limitado), dependencia de proveedor externo en flujo crítico, no se puede autoalojar.
- **Descartado por**: el modelo del proyecto exige autoalojable y gratuito ([ADR-001](adr-001-polyrepo.md) y el modelo de sostenibilidad).

### B. Authentik / Ory Hydra

- **Pros**: open-source autoalojable, alternativas modernas a Keycloak.
- **Contras**: comunidades más pequeñas, Authentik con menos años de producción real, Ory Hydra solo OAuth (sin gestión de usuarios incluida, requiere Kratos como complemento).
- **Descartado por**: Keycloak tiene mayor cuota de uso institucional (incluyendo administraciones públicas españolas), facilita encontrar referencias y documentación en castellano.

### C. Validación remota del JWT (introspection)

- **Pros**: revocación inmediata desde Keycloak.
- **Contras**: cada petición a la API añade un viaje de red al IdP; si Keycloak está saturado o caído, toda la API se cae con él; latencia añadida.
- **Descartado por**: rompe el principio de resiliencia operativa; la revocación inmediata se simula con `exp` corto (15 minutos) + refresh token rotation.

### D. Authorization Code sin PKCE + `client_secret`

- **Pros**: flujo más simple, soportado por todos los IdPs.
- **Contras**: imposible almacenar `client_secret` de forma segura en cliente público (móvil o SPA); decompilar el APK extrae el secret en segundos.
- **Descartado por**: vector de ataque inaceptable para un cliente público.

### E. Resource Owner Password Credentials Grant

- **Pros**: simple (el cliente envía usuario+password al IdP y recibe tokens).
- **Contras**: deprecado por OAuth 2.1; el cliente "ve" la contraseña; no permite segundo factor; rompe el modelo de delegación de OAuth.
- **Descartado por**: anti-patrón explícitamente desaconsejado por OAuth 2.0 BCP ([RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700)).

## Implicaciones operativas

- **Dos clientes registrados en Keycloak**: `custodiam-app` (público, sin secret, con PKCE obligatorio, *redirect URIs* para los tres canales) y `custodiam-api` (confidencial, con secret, usado solo por el backend para llamar a la Admin API).
- **Tiempos de sesión configurados**: access token 15 minutos, SSO Idle 24 horas, SSO Max 24 horas, Client login timeout 5 minutos. El refresh token rotation activado.
- **Validación JWT en backend**: implementada en `app/core/security.py` con `PyJWKClient` cacheando claves cinco minutos. Errores tipados: `ExpiredSignatureError`, `InvalidIssuerError`, `PyJWKClientError`, `InvalidTokenError` → HTTP 401.
- **Asimetría móvil/web del flujo OAuth**: el cliente Flutter mantiene dos implementaciones de `AuthService` seleccionadas por `kIsWeb` ([ADR-023](adr-023-oauth-web-asimetria.md)). La razón es que el navegador no soporta deep links del SO; la SPA redirige completamente al IdP y persiste el `code_verifier` en `sessionStorage` para sobrevivir el viaje de ida y vuelta.
- **RBAC en lockstep**: los roles del realm Keycloak se traducen a una matriz rol→permisos definida en `app/core/permissions.py` y espejada en `lib/infrastructure/auth/permissions.dart` ([ADR-013](adr-013-rbac-lockstep.md)).

## Referencias

- **[RFC 7636 — Proof Key for Code Exchange](https://datatracker.ietf.org/doc/html/rfc7636)**
- **[RFC 9068 — JWT Profile for OAuth 2.0 Access Tokens](https://datatracker.ietf.org/doc/html/rfc9068)**
- **[RFC 9700 — Best Current Practice for OAuth 2.0 Security](https://datatracker.ietf.org/doc/html/rfc9700)**
- **[Documentación oficial de Keycloak](https://www.keycloak.org/documentation)**
- **[ADR-013 RBAC lockstep](adr-013-rbac-lockstep.md)** — matriz rol→permisos.
