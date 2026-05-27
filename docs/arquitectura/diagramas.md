---
title: Diagramas del sistema
description: >-
  Diagramas de componentes y flujos clave de Custodiam.
---

# Diagramas del sistema

Diagramas Mermaid de los flujos principales del sistema. Renderizados nativamente por el plugin `mkdocs-mermaid2-plugin`.

## Topología de despliegue (modo producción)

```d2
direction: down

internet: Internet {
  shape: cloud
}

cf: Cloudflare Edge {
  style.fill: "#fef7ed"
  style.stroke: "#f97316"

  dns: DNS\ncustodiam.es {
    shape: circle
  }
  tunnel: Tunnel\ncloudflared
  book_pages: GitHub Pages\ndocs.custodiam.es {
    shape: page
  }
}

host: PC anfitrión (modo prod) {
  style.fill: "#f8fafc"
  style.stroke: "#475569"

  compose: Docker Compose --profile tunnel {
    style.italic: true
  }

  stack: Stack de servicios {
    style.fill: "#ffffff"

    web: custodiam-web\n(Nginx + PWA Flutter)\n:80
    api: custodiam-api\n:8000
    keycloak: Keycloak 26\n:8080
    db: PostgreSQL 15 {
      shape: cylinder
    }
    ntfy: ntfy\n:80
  }
}

internet -> cf.dns: HTTPS
cf.dns -> cf.tunnel: app/api/auth/ntfy.custodiam.es
cf.dns -> cf.book_pages: docs.custodiam.es

cf.tunnel -> host.stack.web: cloudflared connect {style.stroke-dash: 3}
cf.tunnel -> host.stack.api: cloudflared connect {style.stroke-dash: 3}
cf.tunnel -> host.stack.keycloak: cloudflared connect {style.stroke-dash: 3}
cf.tunnel -> host.stack.ntfy: cloudflared connect {style.stroke-dash: 3}

host.stack.api -> host.stack.db
host.stack.keycloak -> host.stack.db
host.stack.api -> host.stack.keycloak: admin API {style.stroke-dash: 3}
```

## Flujo OAuth2 + PKCE (móvil)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant App as Flutter App<br/>(Android/iOS)
    participant KC as Keycloak
    participant API as custodiam-api

    U->>App: Toca "Iniciar sesión"
    App->>App: Genera code_verifier + code_challenge<br/>(_pendingGrant en memoria)
    App->>KC: Abre Custom Tab con<br/>authorize?code_challenge=...
    KC-->>U: Pantalla de login
    U->>KC: Credenciales (usuario + password)
    KC-->>App: Redirige a<br/>es.custodiam://callback?code=...
    Note over App: Deep link captura el code
    App->>KC: POST /token<br/>code + code_verifier
    KC-->>App: access_token + refresh_token
    App->>App: Guarda en flutter_secure_storage
    App->>API: GET /me<br/>Authorization: Bearer <access_token>
    API->>API: Valida JWT localmente con PyJWT<br/>(usa JWKS cacheado)
    API-->>App: 200 OK + datos del voluntario
```

## Flujo OAuth2 + PKCE (web)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant Web as PWA Web<br/>(Flutter Web)
    participant SS as sessionStorage
    participant KC as Keycloak
    participant API as custodiam-api

    U->>Web: Click "Iniciar sesión"
    Web->>Web: Genera code_verifier + code_challenge
    Web->>SS: Persiste code_verifier<br/>(clave: custodiam.oauth.code_verifier)
    Web->>KC: window.location = authorize?code_challenge=...<br/>(webOnlyWindowName: '_self')
    Note over Web: ⚠️ Recarga completa del navegador
    KC-->>U: Pantalla de login
    U->>KC: Credenciales
    KC-->>Web: Redirige a<br/>https://app.custodiam.es/callback?code=...
    Note over Web: GoRouter (PathUrlStrategy) matcha /callback
    Web->>SS: Lee code_verifier
    Web->>KC: POST /token<br/>code + code_verifier
    KC-->>Web: access_token + refresh_token
    Web->>SS: Limpia code_verifier<br/>Guarda tokens en sessionStorage
    Web->>API: GET /me<br/>Authorization: Bearer <access_token>
    API-->>Web: 200 OK + datos del voluntario
```

!!! info "Asimetría móvil/web — ADR-023"
    La diferencia clave entre móvil y web: en móvil la app sobrevive la redirección al IdP (deep link vuelve a la misma instancia con el `_pendingGrant` intacto en memoria); en web, la navegación a Keycloak recarga la PWA completa, perdiendo el estado en memoria. Por eso web necesita persistir el `code_verifier` en `sessionStorage` antes de redirigir. Se implementa con dos `AuthService` distintos seleccionados vía `kIsWeb`. Detalle completo en [ADR-023 del repo privado].

## Flujo de notificación de emergencia

```mermaid
sequenceDiagram
    participant Coord as Coordinador<br/>(usuario)
    participant App as App Coord
    participant API as custodiam-api
    participant FCM as Firebase FCM
    participant NTFY as ntfy
    participant Volunt as App Voluntario<br/>(N dispositivos)

    Coord->>App: Crea convocatoria de emergencia
    App->>API: POST /servicios<br/>tipo=emergencia, voluntarios_filtrados
    API->>API: Filtra voluntarios disponibles + permisos
    API->>FCM: Envía push a tokens FCM<br/>(canal principal)

    alt FCM responde 200
        FCM-->>Volunt: Push notification<br/>(notificación + datos del servicio)
        Note over Volunt: Voluntario toca → abre app en pantalla del servicio
    else FCM falla o timeout > 5s
        API->>NTFY: Publica al canal /custodiam-emergencia<br/>(fallback ADR-005)
        NTFY-->>Volunt: Push via ntfy<br/>(canal secundario)
        Note over API: Log de fallo de FCM<br/>+ telemetría para análisis
    end

    Volunt->>API: PATCH /servicios/{id}/voluntarios/{me}<br/>{respuesta: "acepto" | "rechazo"}
    API-->>App: Notifica al coordinador<br/>(via FCM tambien)
```

## Despliegue del book de documentación

```d2
direction: down

dev: Dev\n(commit + push)
gh: GitHub Actions\nworkflow deploy.yml {
  shape: hexagon
}
pages: GitHub Pages\nbranch gh-pages {
  shape: page
}
dns: Cloudflare DNS\nCNAME docs → custodiam.github.io\n(DNS only, sin proxy) {
  shape: cloud
}
user: Usuario {
  shape: person
}

dev -> gh: push a main
gh -> gh: uv sync + mkdocs build
gh -> pages: peaceiris/actions-gh-pages@v4
user -> dns: https\://docs.custodiam.es
dns -> pages: resuelve a IP de GitHub Pages
user -> pages: fallback custodiam.github.io/custodiam-book/ {
  style.stroke-dash: 3
}
```

!!! tip "Resiliencia vendor-lock-free"
    El sitio sigue siendo accesible en `https://custodiam.github.io/custodiam-book/` aunque Cloudflare desaparezca: solo se perdería el dominio "bonito" `docs.custodiam.es`. Cloudflare se reserva como CDN opcional futuro (toggle `Proxied` reversible). Decisión en [ADR-027].

## Referencias

- **[Stack técnico](stack.md)** — tecnologías concretas con versiones.
- **[ADRs](../adrs/index.md)** — decisiones arquitectónicas que sostienen estos diagramas.
