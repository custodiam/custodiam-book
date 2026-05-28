---
title: ADR-020 — Tres modos de despliegue
description: >-
  El stack se levanta en exactamente uno de tres modos mutuamente excluyentes
  (dev, tunnel, prod) materializados por tres scripts simétricos en
  custodiam-infra. La conmutación pasa obligatoriamente por down.sh, enforced
  por un guard.
---

# ADR-020 — Tres modos de despliegue

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 5 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El stack de Custodiam tiene seis servicios productivos (`postgres`, `keycloak`, `api`, `web`, `ntfy`, `cloudflared`) más dos opt-in (`n8n`, `mock-oidc`). En distintos momentos del ciclo de desarrollo se necesitan **composiciones diferentes** del mismo conjunto:

1. **Iterar código de la app o la API en local.** Hot reload de `uvicorn` y de Flutter, puertos del host expuestos para `adb reverse` y para entrar con el navegador. No hace falta — y sería contraproducente — atravesar Cloudflare Tunnel.
2. **Probar contra dispositivos móviles reales el flujo de App Links, Universal Links y emails de Keycloak.** Los SO móviles exigen verificar manifiestos `.well-known/` accesibles por HTTPS desde el dominio real (`https://app.custodiam.es`), los clientes de email recortan custom schemes, y Keycloak debe emitir URLs públicas. El túnel sí es imprescindible. No hace falta el endurecimiento de producción.
3. **Despliegue real en el PC anfitrión del piloto.** Endurecer Keycloak con `KC_HOSTNAME_STRICT=true` para rechazar *Host header spoofing*, apagar `DEBUG` en la API, y arrancar `cloudflared` como parte del stack sin que el operador tenga que pasar manualmente `--profile tunnel`.

Un **modo único parametrizable por `.env`** parece atractivo (un solo wrapper, una sola composición) pero choca con una restricción real de Keycloak. La variable `KC_HOSTNAME` es **escalar y debe coincidir con el host real desde el que entra el cliente**:

- Si vale `http://localhost:8080`, Keycloak emite todas sus URLs absolutas (form actions de login, redirects OIDC, cookies `Domain=...`, manifiesto `.well-known/openid-configuration`) contra `localhost`. Un cliente que entre por `https://auth.custodiam.es` recibe redirects a `localhost`, su navegador no llega ahí y la sesión muere.
- Si vale `auth.custodiam.es`, ocurre lo simétrico: el cliente local que apunta a `localhost:8080` recibe redirects al dominio público, su loopback no resuelve eso, sesión muere.

Esto **no es una limitación de Compose ni de los scripts**: es una propiedad estructural del flujo OIDC. Cualquier "modo unificado" exige resolver primero qué hace Keycloak con `KC_HOSTNAME`.

## Decisión

Tres composiciones distintas, materializadas con el patrón Docker Compose **base + override**:

| Modo | Composición | Profile extra | `KC_HOSTNAME` | `STRICT` | `DEBUG` | Imágenes `api`/`web` | `cloudflared` | Puertos al host |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **dev** | `base + docker-compose.dev.yml` | — | `http://localhost:8080` | `false` | `true` | build local (`custodiam-{api,app}:dev`) | no | `5432`, `8080`, `8000`, `3000`, `8090` |
| **tunnel** | `base` | `--profile tunnel` | `auth.${DOMAIN}` | `false` | (sin definir) | GHCR `:latest` | sí | ninguno |
| **prod** | `base + docker-compose.prod.yml` | `--profile tunnel` (interno) | `auth.${DOMAIN}` | **`true`** | **`false`** | GHCR `:latest` | sí | ninguno |

Tres scripts simétricos en `custodiam-infra/scripts/` exponen un único entry point por modo:

```bash
./scripts/dev-up.sh        # modo dev (local, hot reload)
./scripts/tunnel-up.sh     # modo tunnel (staging vía Cloudflare Tunnel)
./scripts/prod-up.sh       # modo prod (endurecido, cloudflared incluido)
./scripts/down.sh          # baja el stack (volúmenes sobreviven)
```

Los tres scripts comparten `_lib-env.sh` para descifrar `docker/.env.sops` con sops + age. `tunnel-up.sh` y `prod-up.sh` aplican además dos *pre-checks*:

1. **Guard de cross-mode**: abortan si ya hay contenedores con label `com.docker.compose.project=custodiam` arriba. El mensaje de error nombra los contenedores activos y obliga a correr `./scripts/down.sh` antes. Cierra el escenario en el que un `tunnel-up.sh` sobre un stack que sigue arriba en modo dev **no recrea** Keycloak (porque la mayoría de campos coinciden lo suficiente), heredando el `KC_HOSTNAME=localhost` del dev y rompiendo el OIDC silenciosamente a través del túnel.
2. **Verificación de `CLOUDFLARE_TUNNEL_TOKEN`**: abortan si el env file resuelto no contiene un valor no vacío. Sin el token `cloudflared` arranca pero falla al registrar el túnel silenciosamente.

`tunnel-up.sh` admite `--skip-images` para arrancar solo `postgres + keycloak + cloudflared` cuando se itera sobre la configuración del SSO sin reconstruir api/web.

## Justificación

1. **El modelo mental es explícito y verificable.** Tres scripts nombrados eliminan ambigüedad. El operador sabe en qué modo está mirando el script que ejecuta (no leyendo variables de un `.env` cifrado). Un nuevo miembro del equipo entiende el sistema en cinco minutos.

2. **`KC_HOSTNAME` escalar impone una decisión a tomar.** Como se explicó en el contexto, no existe un valor de `KC_HOSTNAME` que sirva simultáneamente para clientes de `localhost` y clientes de `auth.custodiam.es`. Forzar la decisión al script (en lugar de a una variable de entorno editable) elimina el modo de fallo "olvidé cambiar el `.env` antes de arrancar".

3. **El guard de cross-mode previene fallos silenciosos.** Sin él, el escenario tipo "ya tenía el stack en dev, ahora ejecuto `tunnel-up.sh`" deja Keycloak con `KC_HOSTNAME=localhost` aunque el cliente entre por el túnel, porque Compose no recrea contenedores cuyas variables de entorno coinciden lo suficiente. Estos fallos son los más difíciles de diagnosticar (todo "parece" funcionar pero ningún OIDC completa).

4. **La separación entre `tunnel` y `prod` mantiene el principio "endurecer al final".** El modo `tunnel` deja `STRICT=false` para que los desarrolladores puedan apuntar al túnel desde un dispositivo móvil sin que Keycloak rechace headers `Host:` que no correspondan exactamente al hostname configurado. El modo `prod` activa `STRICT=true` porque ese stack solo lo opera el sistema y los clientes legítimos.

5. **Cada modo es reproducible y portable.** Los tres scripts son CI-friendly: pueden ejecutarse en una máquina virgen tras un `git clone` + descifrado de secretos sin más configuración. La conmutación de modo no exige ediciones de ficheros, solo invocación de un script distinto.

## Alternativas evaluadas y descartadas

### A. Modo único parametrizable por `.env`

Un solo `up.sh` que lea variables `MODE=dev|tunnel|prod` y `KC_HOSTNAME` del `.env` y construya el comando `docker compose` con los overrides correctos.

- **Pros**: un único entry point, lógica centralizada.
- **Contras**: no simplifica el modelo mental (el operador sigue necesitando entender qué combina cada modo); mete la lógica del modo en `.env`, que es donde viven los secretos cifrados — cambiar de modo implicaría editar `.env.sops` en lugar de ejecutar un script distinto. Mala fricción operativa.
- **Descartado por**: ergonomía inferior + acoplamiento entre lógica de modo y secretos.

### B. Dev + tunnel combinado en un solo proceso

Levantar el stack de dev (hot reload + puertos expuestos) y al mismo tiempo activar `cloudflared` para exponer `app.custodiam.es` a Internet. Útil en teoría para probar deep links sin perder hot reload.

- **Pros**: itera la app móvil contra el túnel sin sacrificar el ciclo rápido.
- **Contras**: choca contra la restricción de `KC_HOSTNAME`. Si el túnel atraviesa Keycloak (lo hace porque `cloudflared` enruta `auth.custodiam.es` al servicio interno), `KC_HOSTNAME` debe ser `auth.custodiam.es`; pero entonces el desarrollador local que apunta a `localhost:8080` recibe redirects al dominio público y su sesión se rompe — y viceversa.
- **Variante explorada**: exponer solo `app.custodiam.es` (la PWA) por el túnel, dejando Keycloak en modo `localhost`. Pero los deep links que llevan a flujos OIDC (reset-password con token de Keycloak, p. ej.) dirigen al usuario a `auth.custodiam.es` que no estaría servido, así que el caso de uso real (probar emails de Keycloak desde el móvil) no se cubre.
- **Descartado por**: la restricción estructural de `KC_HOSTNAME` lo invalida.

### C. Multi-hostname experimental de Keycloak 25+

Keycloak 25 introdujo soporte experimental para múltiples hostnames vía configuración avanzada. En teoría permitiría que el mismo Keycloak emita URLs contra `localhost` para clientes que vienen de la red Docker interna y contra `auth.custodiam.es` para los del túnel.

- **Pros**: resolvería el problema sin necesidad de tres modos.
- **Contras**: es **experimental** y la documentación oficial desaconseja explícitamente su uso en producción; requiere configuración adicional no trivial (separar cookies por hostname, sincronizar realm settings); añade una vía de fallo silencioso entre dev y prod (configuración que funciona en dev pero no en prod) que cuesta más depurar que la conmutación explícita de modos.
- **Descartado por**: inmadurez del feature + opacidad operativa.

### D. "Hard down" automático al cambiar de modo

Que `tunnel-up.sh` ejecute `docker compose down` automáticamente si detecta un stack en otro modo, en vez de abortar con mensaje. Más cómodo: una sola invocación cambia de modo.

- **Pros**: ergonomía de una sola invocación.
- **Contras**: bajar el stack mata las sesiones de los desarrolladores que pudieran estar trabajando contra él desde sus máquinas, y silencia el problema (el operador no se entera de que ha cambiado de modo).
- **Descartado por**: seguridad operativa — el comportamiento explícito (abortar y mostrar el comando exacto) es preferible.

## Implicaciones operativas

- **Cualquier conmutación de modo pasa por `./scripts/down.sh` + el script del modo nuevo.** Los volúmenes (`postgres_data`, `ntfy_data`, `n8n_data`) sobreviven, así que no se pierden datos entre cambios.
- **El PC anfitrión del piloto solo necesita `prod-up.sh`** en operación normal. Los otros dos scripts son herramientas de desarrollo.
- **Las imágenes consumidas por `tunnel` y `prod`** son `ghcr.io/custodiam/custodiam-{app,api}:latest`, publicadas por el CI en cada merge a `main`. Son públicas, así que el `docker compose pull` que ejecutan los scripts antes del `up -d` funciona sin `docker login`.
- **Las protecciones de rama de `main`** (en ambos repos) son las que aseguran que solo entran ahí cambios revisados, lo que hace seguro que `prod` consuma `:latest`. Cuando se introduzca pineo por SHA o semver (`:sha-<7>` / `:vX.Y.Z`), `prod-up.sh` podrá fijar una versión exacta cambiando variables en `.env.sops`.

## Referencias

- **[Keycloak — Configuring hostname](https://www.keycloak.org/server/hostname)** — documentación oficial de `KC_HOSTNAME` y su restricción a un único valor.
- **[Docker Compose — Multiple Compose files](https://docs.docker.com/compose/multiple-compose-files/)** — patrón `base + override`.
- **[Docker Compose — Profiles](https://docs.docker.com/compose/profiles/)** — activación selectiva de servicios.
- **[ADR-010 OAuth + PKCE + Keycloak](adr-010-oauth-pkce-keycloak.md)** — base del flujo OIDC sobre el que se asienta esta decisión.
