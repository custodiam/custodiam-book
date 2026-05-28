---
title: ADR-006 — Nginx Alpine como servidor de la PWA
description: >-
  El contenedor `custodiam-web` sirve la PWA Flutter (build estática) con
  Nginx sobre la imagen base `nginx:alpine`. Ligero, estándar, sin sorpresas
  de configuración.
---

# ADR-006 — Nginx Alpine como servidor de la PWA

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 29 de enero de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

La aplicación Flutter genera, mediante `flutter build web`, una salida estática (`build/web/`) compuesta por HTML, JavaScript, CSS, assets y el bundle `flutter.js` / `main.dart.js`. Esa salida necesita servirse desde un proceso HTTP que:

- Responda correctamente a rutas SPA (devolviendo `index.html` para cualquier path no encontrado, para que el `go_router` interno tome el control).
- Aplique cabeceras de cache correctas (cache largo para los assets con hash en el nombre, cache corto o nulo para `index.html` y los bootstrap files que no se hashean).
- Sea liviano en RAM y CPU, porque convive con `keycloak`, `postgres`, `api`, `ntfy` y `cloudflared` en el mismo host del piloto.

## Decisión

**Nginx sobre la imagen base oficial [`nginx:alpine`](https://hub.docker.com/_/nginx)** como contenedor `custodiam-web`. La configuración se mantiene en un único archivo `nginx.conf` montado al contenedor, con dos bloques relevantes:

- `try_files $uri $uri/ /index.html;` para resolver rutas SPA al `index.html`.
- Cabeceras `Cache-Control` diferenciadas: `public, max-age=31536000, immutable` para los assets hasheados, y `no-cache` para los bootstrap files (`index.html`, `flutter.js`, `flutter_bootstrap.js`, `flutter_service_worker.js`, `main.dart.js`).

## Justificación

1. **Rendimiento sin esfuerzo.** Nginx es probadamente el servidor estático de más alto rendimiento por unidad de CPU. Para los volúmenes del piloto (~50 voluntarios concurrentes máximo) el coste de CPU es despreciable y la latencia es indistinguible de servir desde un CDN.

2. **Imagen base ligera.** `nginx:alpine` pesa ~25 MB descomprimida, frente a los ~140 MB de `nginx:debian-slim`. Para una imagen `custodiam-web` que se reconstruye en cada PR mergeada y se publica en GHCR, los megabytes ahorrados cuentan en tiempo de pull, almacenamiento del registry y minutos de CI.

3. **Configuración predecible.** El formato de `nginx.conf` es ampliamente conocido. Cualquier desarrollador con un mínimo de experiencia con HTTP puede leerlo y entenderlo sin documentación adicional. La curva de aprendizaje es nula.

4. **Compatible con Cloudflare Tunnel.** El túnel ([ADR-022](adr-022-ios-15.md) menciona otro contexto pero el patrón aplica) enruta peticiones HTTP directamente al puerto interno del contenedor `custodiam-web:80` sin TLS termination — Nginx escucha en plain HTTP y Cloudflare hace el HTTPS público. Es la configuración más simple que cumple los requisitos.

5. **Estándar de la industria.** La mayoría de aplicaciones SPA en producción se sirven con Nginx. Documentación, recetas, troubleshooting y herramientas de monitorización están normalizadas. Cualquier futura iteración (rate limiting, gzip / brotli compression, security headers, logs estructurados) tiene receta documentada.

## Alternativas evaluadas y descartadas

### A. Caddy

- **Pros**: HTTPS automático con Let's Encrypt, configuración declarativa muy concisa (`Caddyfile`), HTTP/3 nativo.
- **Contras**: el HTTPS automático no aplica porque Cloudflare Tunnel termina TLS antes de llegar al contenedor — la feature estrella de Caddy queda desaprovechada. La configuración no es difícil pero requiere aprenderla por encima de la de Nginx, sin ventaja proporcional.
- **Descartado por**: la feature diferenciadora (HTTPS automático) no aplica al stack del proyecto.

### B. Apache HTTP Server

- **Pros**: estándar histórico, módulos para todo.
- **Contras**: huella mayor (memoria, CPU, tamaño de imagen), configuración más prolija (`.htaccess` o virtual hosts), más viejo y menos ergonómico que Nginx para SPAs estáticas.
- **Descartado por**: peor relación coste/beneficio que Nginx para servir estática.

### C. Servidor HTTP integrado en el bundle Flutter (`flutter run -d web-server`)

- **Pros**: cero dependencias externas, todo en Dart.
- **Contras**: pensado para desarrollo local, no para producción — no soporta gzip, cabeceras de cache configurables, ni el rendimiento de un servidor real.
- **Descartado por**: inadecuado para producción.

### D. CDN puro (Cloudflare Pages, GitHub Pages, Vercel)

- **Pros**: cero infraestructura en el host, edge global, despliegue por push.
- **Contras**: separa el deployment de la PWA del resto del stack, introduce un proveedor más, y el book ya hizo esa decisión por separado para la documentación pública ([ADR-027](adr-027-mkdocs-pages.md)). Mover también la PWA a Pages implicaría dos puntos de despliegue distintos.
- **Descartado por**: complica el modelo de despliegue. La PWA va junto al resto del stack autoalojado.

## Implicaciones operativas

- **Dockerfile multi-stage**: el primer stage construye el bundle Flutter con el SDK; el segundo (final) parte de `nginx:alpine` y copia el `build/web/` resultante a `/usr/share/nginx/html`. La imagen final no contiene el SDK de Flutter ni ningún tooling de desarrollo.
- **`nginx.conf` versionado en el repo**: vive en `custodiam-app/web/nginx.conf` y se copia al contenedor en build. Cualquier cambio en cache busting, security headers o gzip pasa por PR como código normal.
- **Logs en `stdout`/`stderr`**: la imagen oficial ya configura `access.log` y `error.log` apuntando a `/dev/stdout` y `/dev/stderr` respectivamente. `docker compose logs custodiam-web` los muestra sin más configuración.
- **Healthcheck**: `docker-compose.yml` define un healthcheck `curl -fsS http://localhost/` que el contenedor responde con 200 cuando Nginx tiene `index.html` servido. Compose marca el servicio como `healthy` y permite que dependencias (Cloudflare Tunnel) arranquen tras él.

## Referencias

- **[Imagen oficial nginx en Docker Hub](https://hub.docker.com/_/nginx)** — tags `alpine` y políticas de seguridad.
- **[Nginx — Serving SPA](https://nginx.org/en/docs/http/ngx_http_core_module.html#try_files)** — directiva `try_files`.
- **[ADR-027 MkDocs + Pages](adr-027-mkdocs-pages.md)** — patrón aplicado a la documentación pública, no a la PWA.
