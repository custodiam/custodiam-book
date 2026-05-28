---
title: ADR-019 — Gestión de secretos con sops + age
description: >-
  Los secretos de despliegue (credenciales SMTP, tokens Cloudflare Tunnel,
  passwords de BD) viven cifrados con sops + age en `docker/.env.sops`,
  versionado en el repo. Cifrado simétrico con multidestinatario; cada
  miembro del equipo descifra con su clave age personal.
---

# ADR-019 — Gestión de secretos con sops + age

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 8 de abril de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El stack del proyecto necesita varias categorías de secretos en runtime:

- **Credenciales de bases de datos** (`CUSTODIAM_DB_PASSWORD`, `KC_DB_PASSWORD`, [ADR-009](adr-009-2-bds-separadas.md)).
- **Token de Cloudflare Tunnel** (`CLOUDFLARE_TUNNEL_TOKEN`) — autentica el conector con la zona del proyecto.
- **Credenciales SMTP de Keycloak** (`KEYCLOAK_SMTP_USERNAME`, `KEYCLOAK_SMTP_PASSWORD`, [ADR-021](adr-021-smtp-resend.md)).
- **Admin password de Keycloak** (`KC_BOOTSTRAP_ADMIN_PASSWORD`) — solo el primer arranque del realm.
- **Credenciales Firebase** (JSON del service account para enviar push notifications desde el backend).

Estas variables se inyectan al stack `docker compose` vía un `.env` que el wrapper del modo (`dev-up.sh`, `tunnel-up.sh`, `prod-up.sh`, [ADR-020](adr-020-tres-modos-despliegue.md)) carga antes del `docker compose up -d`.

La práctica clásica es **`.env` en `.gitignore` y compartirlo por canal seguro** (KeePassXC, Bitwarden, mensajería cifrada). Esa práctica tiene tres problemas operativos:

1. **Sin trazabilidad de cambios**: nadie sabe quién cambió un secreto ni cuándo.
2. **Riesgo de divergencia**: cada miembro mantiene su copia del `.env` y se desincronizan con el tiempo.
3. **Onboarding incómodo**: un nuevo contributor necesita pedir el `.env` por canal seguro, esperar a que alguien lo envíe, y guardarlo manualmente fuera del repo.

Hay que decidir un mecanismo de gestión de secretos que mantenga los tres problemas resueltos sin abrir un agujero de seguridad nuevo.

## Decisión

**[sops](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age)** para cifrar el archivo `docker/.env.sops` que se versiona en el repo `custodiam-infra`.

- **`age`** es la herramienta de cifrado moderna que reemplaza GPG en flujos sencillos. Cada miembro del equipo genera una **clave age personal** (`age-keygen -o ~/.config/sops/age/keys.txt`), publica la clave **pública** (`age1...`) y guarda la privada localmente.
- **`sops`** (de Mozilla, ahora getsops) toma el archivo claro `.env`, lo cifra de forma **multidestinatario** (cifrado simétrico envuelto con N cifrados asimétricos, uno por cada clave pública en la lista) y produce `.env.sops` con el contenido cifrado. Cualquier miembro con su clave privada age puede descifrarlo.
- El archivo cifrado `.env.sops` **se commitea** al repo en `custodiam-infra/docker/.env.sops`. Las claves públicas autorizadas viven en `.sops.yaml` del repo, también versionado.

Los scripts wrapper (`dev-up.sh`, `tunnel-up.sh`, `prod-up.sh`) descifran el archivo en memoria al arrancar con `sops -d docker/.env.sops > /tmp/custodiam-env.tmp` y lo pasan a `docker compose --env-file ...`.

## Justificación

1. **Trazabilidad nativa.** Cualquier cambio en un secreto es un commit Git como cualquier otro: `git log docker/.env.sops` muestra quién cambió qué y cuándo. La diff es opaca a humanos (texto cifrado) pero el metadato de "alguien cambió esto" es transparente.

2. **Sin divergencia entre máquinas.** Todos los miembros tiran del repo y obtienen automáticamente la versión actual de los secretos. Si alguien rota el token de Cloudflare Tunnel, el resto se entera en el siguiente `git pull` (y necesita aplicar el cambio al stack, no antes).

3. **Onboarding bajo demanda.** Un nuevo contributor no necesita pedir el `.env` por mensajería: añade su clave pública age al `.sops.yaml`, otro miembro reencripta el archivo (`sops updatekeys docker/.env.sops`) y commitea el resultado. A partir de ahí, el nuevo contributor descifra como cualquier otro.

4. **Revocación granular.** Si un miembro abandona el proyecto, basta con quitar su clave del `.sops.yaml` y reencriptar. El miembro saliente sigue teniendo el archivo `.env.sops` antiguo pero el cifrado nuevo no le incluye, así que las versiones futuras le son ilegibles.

5. **Cifrado simétrico envuelto, no asimétrico costoso.** Internamente sops cifra el contenido con AES-256-GCM (rápido, simétrico) y luego envuelve la clave AES con cifrado asimétrico para cada destinatario age. Esto da el coste de cifrado simétrico (irrelevante para archivos `.env` de unas pocas KB) con la propiedad de multidestinatario de la criptografía asimétrica.

## Alternativas evaluadas y descartadas

### A. `.env` en `.gitignore` + KeePassXC para compartir

- **Pros**: cero curva técnica, cero herramientas nuevas.
- **Contras**: los tres problemas del contexto siguen sin resolver: sin trazabilidad, divergencia probable, onboarding manual.
- **Descartado por**: la práctica clásica falla los criterios.

### B. HashiCorp Vault

- **Pros**: gestión profesional de secretos, audit log, rotación automática.
- **Contras**: requiere desplegar y mantener un Vault server, configurar políticas, gestionar tokens de acceso. Sobreingeniería para un equipo de dos personas en MVP.
- **Descartado por**: complejidad operativa desproporcionada.

### C. Doppler / 1Password Secrets / Bitwarden Secrets Manager (SaaS)

- **Pros**: gestionado, UI amigable, SDK para integrar con Docker.
- **Contras**: dependencia de un proveedor externo que vive fuera del repo; coste recurrente; vendor lock-in en herramienta no esencial; requiere autenticación adicional en CI y en local que el equipo no tiene hoy.
- **Descartado por**: añadir un proveedor SaaS por un problema que sops + age resuelve sin terceros.

### D. AWS Secrets Manager / GCP Secret Manager / Azure Key Vault

- **Pros**: integración nativa con el cloud respectivo, auditoría completa.
- **Contras**: vendor lock-in con un cloud que el proyecto no usa para nada más. Coste por secreto. Requiere autenticación de cada máquina contra el cloud para descifrar.
- **Descartado por**: el proyecto es autoalojado, no en cloud.

### E. GPG (GnuPG) en lugar de age

- **Pros**: estándar histórico, multidestinatario igual que age.
- **Contras**: GPG es notablemente más complejo de usar (web of trust, gestión de subkeys, expiración compleja), tiene una UX de línea de comandos hostil, y su valor diferencial sobre age para este caso de uso es nulo. age fue creado precisamente para ofrecer "GPG sin la complejidad".
- **Descartado por**: peor ergonomía con cero ventaja técnica.

## Implicaciones operativas

- **`.sops.yaml`** en la raíz del repo declara la lista de claves age autorizadas y el patrón de archivos cifrados. Cualquier `sops` en el repo lee este archivo automáticamente.
- **Claves age personales en `~/.config/sops/age/keys.txt`** (path canónico que sops busca por defecto). En Windows, la ruta es `%APPDATA%\sops\age\keys.txt` — gotcha conocido del proyecto: si se genera la clave en una ruta no canónica, hay que exportar `SOPS_AGE_KEY_FILE=...` para apuntar a ella.
- **Permisos**: nunca commitear la clave **privada** age. El `.gitignore` excluye `keys.txt`, `*.txt` dentro de `.sops/`, y el patrón `*age*key*`.
- **Rotación de un secreto**: editar con `sops docker/.env.sops` (sops abre `$EDITOR` con el texto descifrado, lo reencripta al guardar), commit, push. El siguiente `dev-up.sh`/`tunnel-up.sh`/`prod-up.sh` de cada miembro recoge el cambio.
- **Añadir un nuevo miembro**: añadir su clave pública age al `.sops.yaml`, ejecutar `sops updatekeys docker/.env.sops` (rencripta el archivo para incluir el nuevo destinatario sin alterar el contenido), commitear. El miembro nuevo solo necesita generar su clave age y compartir la pública por cualquier canal — no es secreta.
- **Revocar un miembro**: quitar su clave del `.sops.yaml` + `sops updatekeys`. Las versiones futuras del `.env.sops` ya no son descifrables por esa clave.

## Referencias

- **[sops — getsops/sops en GitHub](https://github.com/getsops/sops)** — documentación oficial.
- **[age — FiloSottile/age en GitHub](https://github.com/FiloSottile/age)** — herramienta de cifrado.
- **[age — Cifrado pensado para reemplazar GPG](https://age-encryption.org/)** — sitio del autor.
- **[ADR-020 Tres modos de despliegue](adr-020-tres-modos-despliegue.md)** — los scripts wrapper consumen `.env.sops`.
- **[ADR-021 SMTP Resend](adr-021-smtp-resend.md)** — ejemplo concreto de secretos gestionados por sops.
