---
title: Glosario
description: >-
  Términos técnicos, herramientas y conceptos del proyecto Custodiam, con
  enlace al recurso oficial cuando existe.
---

# Glosario

Página de consulta rápida. Los términos también aparecen subrayados (con
tooltip al pasar el ratón) en el resto del book; haz clic para volver
aquí.

Organizado en cuatro secciones:

- **Acrónimos** — siglas técnicas con enlace a su especificación o estándar.
- **Herramientas** — librerías, frameworks y servicios del stack actual.
- **Conceptos del proyecto** — clases, patrones y archivos canónicos
  específicos de Custodiam.
- **Alternativas evaluadas y descartadas** — herramientas mencionadas en
  los ADRs como opciones que se consideraron y no se eligieron. **No
  forman parte del stack actual.**

---

## Acrónimos

### ABAC { #abac }

*Attribute-Based Access Control*. Modelo de autorización donde el acceso a
un recurso depende de atributos (del usuario, del recurso, del entorno)
evaluados por un motor de políticas. Más expresivo que RBAC pero más
costoso de mantener. Custodiam optó por RBAC; ver
[ADR-013](adrs/adr-013-rbac-lockstep.md).

- :material-text-box-check: NIST: <https://csrc.nist.gov/projects/attribute-based-access-control>

### ADR { #adr }

*Architecture Decision Record*. Documento breve que registra una decisión
técnica importante con su contexto, alternativas evaluadas y
justificación. La colección de Custodiam vive en
[la sección de ADRs](adrs/index.md).

- :material-web: Plantillas y ejemplos: <https://adr.github.io/>
- :material-github: Repo de referencia:
  <https://github.com/joelparkerhenderson/architecture-decision-record>

### AGPL { #agpl }

*GNU Affero General Public License*. Licencia copyleft fuerte que obliga
a publicar el código fuente incluso cuando el software se ofrece como
servicio en red. Custodiam se distribuye bajo AGPL-3.0.

- :material-text-box-check: Texto oficial:
  <https://www.gnu.org/licenses/agpl-3.0.html>

### BFF { #bff }

*Backend for Frontend*. Patrón donde cada frontend (web, móvil, tercero)
tiene un backend propio adaptado a sus necesidades en lugar de
consumir un único API genérico. Se menciona en
[ADR-023](adrs/adr-023-oauth-web-asimetria.md) como contraste a la
asimetría que sí adopta Custodiam.

- :material-web: Sam Newman:
  <https://samnewman.io/patterns/architectural/bff/>

### CI/CD { #ci-cd }

*Continuous Integration / Continuous Delivery*. Prácticas que automatizan
build, test y despliegue tras cada cambio en el repositorio. Custodiam
usa GitHub Actions para la parte de CI y publica imágenes a GHCR.

- :material-web: Explicación: <https://about.gitlab.com/topics/ci-cd/>

### CNAME { #cname }

*Canonical Name record*. Tipo de registro DNS que apunta un nombre de
dominio a otro nombre. Custodiam lo usa para que `docs.custodiam.es`
resuelva al hosting de GitHub Pages; ver
[ADR-027](adrs/adr-027-mkdocs-pages.md).

- :material-text-box-check: RFC 1035:
  <https://datatracker.ietf.org/doc/html/rfc1035>

### CORS { #cors }

*Cross-Origin Resource Sharing*. Mecanismo HTTP que permite a un servidor
indicar qué orígenes (dominios) tienen permiso para hacer peticiones a
sus recursos desde JavaScript de navegador.

- :material-text-box-check: MDN:
  <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>

### DI { #di }

*Dependency Injection*. Patrón donde un objeto recibe sus dependencias
de fuera en lugar de crearlas internamente, facilitando los tests y la
sustitución por implementaciones alternativas. En el frontend de
Custodiam el contenedor de DI es Riverpod; ver
[ADR-012](adrs/adr-012-riverpod.md).

- :material-web: Martin Fowler:
  <https://martinfowler.com/articles/injection.html>

### DKIM { #dkim }

*DomainKeys Identified Mail*. Mecanismo que firma criptográficamente las
cabeceras de un correo saliente para que el receptor pueda verificar
que el mensaje no se ha modificado y procede del dominio declarado.
Custodiam lo configura sobre Resend; ver
[ADR-021](adrs/adr-021-smtp-resend.md).

- :material-text-box-check: RFC 6376:
  <https://datatracker.ietf.org/doc/html/rfc6376>

### DoD { #dod }

*Definition of Done*. Criterios objetivos que una historia o tarea debe
cumplir para considerarse completada. Custodiam la aplica especialmente
a las pruebas E2E con Patrol; ver
[ADR-024](adrs/adr-024-patrol-e2e.md).

- :material-web: Scrum.org:
  <https://www.scrum.org/resources/blog/scrum-glossary>

### E2E { #e2e }

*End-to-End test*. Prueba que ejecuta la aplicación completa contra una
infraestructura real (frontend, backend, base de datos, IdP) y valida
flujos de usuario, no unidades aisladas. En Custodiam corre con Patrol;
ver [ADR-024](adrs/adr-024-patrol-e2e.md).

### FCM { #fcm }

*Firebase Cloud Messaging*. Servicio de Google para enviar notificaciones
push a Android, iOS y web. Custodiam lo combina con ntfy como segundo
canal de respaldo; ver [arquitectura de
notificaciones](arquitectura/notificaciones.md).

- :material-web: Docs:
  <https://firebase.google.com/docs/cloud-messaging>

### GHCR { #ghcr }

*GitHub Container Registry*. Registro de imágenes Docker integrado en
GitHub, ligado a la organización o usuario del repositorio. Custodiam
publica todas sus imágenes a `ghcr.io/custodiam/*`; ver
[ADR-007](adrs/adr-007-ghcr.md).

- :material-web: Docs:
  <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>

### IdP { #idp }

*Identity Provider*. Sistema que autentica usuarios y emite tokens o
aserciones de identidad para que aplicaciones externas confíen en él.
El IdP de Custodiam es Keycloak; ver
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-web: Wikipedia:
  <https://en.wikipedia.org/wiki/Identity_provider>

### JSONB { #jsonb }

Tipo de datos de PostgreSQL que almacena JSON en formato binario
descompuesto, permitiendo indexar y consultar campos internos con
buen rendimiento. Custodiam lo usa para los campos variables de los
catálogos extensibles; ver [ADR-025](adrs/adr-025-modelo-extensible.md).

- :material-web: PostgreSQL docs:
  <https://www.postgresql.org/docs/current/datatype-json.html>

### JWKS { #jwks }

*JSON Web Key Set*. Documento JSON con las claves públicas que un
emisor de tokens (p. ej. Keycloak) publica para que los receptores
puedan verificar la firma de los JWT. Custodiam lo consume desde el
backend; ver [ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-text-box-check: RFC 7517:
  <https://datatracker.ietf.org/doc/html/rfc7517>

### JWT { #jwt }

*JSON Web Token*. Formato de token compacto y firmado que codifica
información sobre un sujeto (usuario, sesión) en un objeto JSON. En
Custodiam el access token es JWT firmado por Keycloak y verificado por
el backend; ver [ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-text-box-check: RFC 7519:
  <https://datatracker.ietf.org/doc/html/rfc7519>

### MFA { #mfa }

*Multi-Factor Authentication*. Autenticación que combina dos o más
factores distintos (conocimiento, posesión, inherencia). Custodiam no
exige MFA en el MVP, pero Keycloak la soporta nativamente para
activarla en fases posteriores.

- :material-web: NIST:
  <https://www.nist.gov/itl/applied-cybersecurity/tig/back-basics-multi-factor-authentication>

### MTA { #mta }

*Mail Transfer Agent*. Servidor responsable de enviar y reenviar correos
electrónicos siguiendo el protocolo SMTP. Custodiam no operara su
propio MTA, sino que delega en Resend; ver
[ADR-021](adrs/adr-021-smtp-resend.md).

- :material-text-box-check: RFC 5321:
  <https://datatracker.ietf.org/doc/html/rfc5321>

### OAuth 2.0 { #oauth-2-0 }

Marco de autorización delegada estandarizado por el IETF. Permite a
una aplicación obtener un token de acceso a recursos en nombre de un
usuario sin manejar sus credenciales. Custodiam lo combina con OIDC y
PKCE; ver [ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-text-box-check: RFC 6749:
  <https://datatracker.ietf.org/doc/html/rfc6749>
- :material-web: oauth.net: <https://oauth.net/2/>

### OIDC { #oidc }

*OpenID Connect*. Capa de identidad construida sobre OAuth 2.0 que
añade un `id_token` con información del usuario autenticado. Es lo que
permite que la app Flutter sepa "quién es" el usuario, no solo "qué
puede hacer".

- :material-text-box-check: Spec:
  <https://openid.net/specs/openid-connect-core-1_0.html>

### PII { #pii }

*Personally Identifiable Information*. Cualquier dato que, solo o
combinado con otros, permita identificar a una persona física. En
Custodiam las operaciones sobre PII (alta, edición, anonimización) se
registran en `audit_log` por requisito RGPD.

- :material-web: NIST glossary:
  <https://csrc.nist.gov/glossary/term/PII>

### PKCE { #pkce }

*Proof Key for Code Exchange*. Extensión de OAuth 2.0 que protege el
flujo Authorization Code contra interceptación del código de
autorización en clientes públicos (móvil y SPA). Custodiam lo usa en
los tres clientes (Android, iOS, Web); ver
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-text-box-check: RFC 7636:
  <https://datatracker.ietf.org/doc/html/rfc7636>

### PWA { #pwa }

*Progressive Web App*. Aplicación web que ofrece capacidades
tradicionalmente nativas (instalación, offline, notificaciones). La
versión web de Custodiam se distribuye como PWA servida por Nginx
Alpine; ver [ADR-006](adrs/adr-006-nginx-alpine.md).

- :material-web: web.dev:
  <https://web.dev/explore/progressive-web-apps>

### RBAC { #rbac }

*Role-Based Access Control*. Modelo de autorización donde los
permisos se asignan a roles y los roles a usuarios. Custodiam lo
implementa con un catálogo canónico de permisos espejado entre
backend y frontend; ver [ADR-013](adrs/adr-013-rbac-lockstep.md).

- :material-web: NIST:
  <https://csrc.nist.gov/projects/role-based-access-control>

### RFC { #rfc }

*Request for Comments*. Documentos publicados por el IETF que
establecen estándares y prácticas de Internet (HTTP, OAuth, JWT,
SMTP, DKIM, etc.). Custodiam cita los RFCs relevantes cuando justifica
decisiones de seguridad o protocolo.

- :material-web: IETF: <https://www.ietf.org/standards/rfcs/>

### RGPD { #rgpd }

*Reglamento General de Protección de Datos* (en inglés GDPR).
Reglamento UE 2016/679 que regula el tratamiento de datos personales
de residentes en la Unión Europea. Custodiam aplica el Art. 17 sobre
derecho de supresión vía anonimización irreversible.

- :material-text-box-check: Texto consolidado:
  <https://gdpr-info.eu/>

### SMTP { #smtp }

*Simple Mail Transfer Protocol*. Protocolo estándar para enviar correo
electrónico entre servidores. Keycloak lo usa para enviar emails de
verificación y reset de contraseña a través de Resend; ver
[ADR-021](adrs/adr-021-smtp-resend.md).

- :material-text-box-check: RFC 5321:
  <https://datatracker.ietf.org/doc/html/rfc5321>

### SPA { #spa }

*Single Page Application*. Aplicación web cuyo HTML inicial se carga
una sola vez y donde el cambio de "página" se hace por JavaScript sin
recargar. Las versiones web de Flutter son técnicamente SPAs y eso
condiciona cómo se sirven; ver [ADR-006](adrs/adr-006-nginx-alpine.md).

- :material-web: MDN:
  <https://developer.mozilla.org/en-US/docs/Glossary/SPA>

### SPF { #spf }

*Sender Policy Framework*. Mecanismo que publica en DNS qué servidores
están autorizados a enviar correo en nombre de un dominio, ayudando a
detectar spoofing. Custodiam lo configura junto con DKIM para el
dominio del proyecto; ver [ADR-021](adrs/adr-021-smtp-resend.md).

- :material-text-box-check: RFC 7208:
  <https://datatracker.ietf.org/doc/html/rfc7208>

### SSO { #sso }

*Single Sign-On*. Esquema en el que un único login da acceso a
múltiples aplicaciones que confían en el mismo IdP. Custodiam queda
preparada para SSO porque centraliza la autenticación en Keycloak.

- :material-web: Wikipedia:
  <https://en.wikipedia.org/wiki/Single_sign-on>

### WSL2 { #wsl2 }

*Windows Subsystem for Linux versión 2*. Capa de Microsoft que ejecuta
un kernel Linux real dentro de Windows. Docker Desktop la usa por
debajo para correr contenedores Linux en máquinas Windows del equipo.

- :material-web: Microsoft Learn:
  <https://learn.microsoft.com/en-us/windows/wsl/>

---

## Herramientas

### age { #age }

Herramienta moderna de cifrado de archivos con sintaxis simple y
soporte de clave pública (X25519). Custodiam la usa con sops para
cifrar los archivos `.env` versionados; ver
[ADR-019](adrs/adr-019-sops-age.md).

- :material-web: Sitio oficial: <https://age-encryption.org/>
- :material-github: Repo:
  <https://github.com/FiloSottile/age>

### Alembic { #alembic }

Herramienta de migraciones de esquema para SQLAlchemy. Compatible con
SQLModel. Custodiam la usa para versionar el esquema de PostgreSQL
con `autogenerate` semiautomático; ver
[ADR-003](adrs/adr-003-alembic.md).

- :material-web: Docs: <https://alembic.sqlalchemy.org/>
- :material-github: Repo: <https://github.com/sqlalchemy/alembic>

### app_links { #app-links-package }

Paquete Dart que captura deep links (App Links de Android y Universal
Links de iOS) y los entrega a la app Flutter. Custodiam lo usa en el
flujo de OAuth para recibir el callback del IdP; ver
[ADR-011](adrs/adr-011-deep-links.md).

- :material-package: pub.dev:
  <https://pub.dev/packages/app_links>
- :material-github: Repo:
  <https://github.com/llfbandit/app_links>

### Cloudflare Tunnel { #cloudflare-tunnel }

Servicio de Cloudflare que crea un túnel saliente desde tu
infraestructura hasta su red, exponiendo servicios internos sin abrir
puertos. Custodiam lo usa para acceder al stack local desde
internet sin VPN; ver
[ADR-020](adrs/adr-020-tres-modos-despliegue.md).

- :material-web: Docs:
  <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>

### cloudflared { #cloudflared }

Daemon ligero que mantiene abierto el Cloudflare Tunnel desde el
servidor o el contenedor. Se distribuye como binario único y
contenedor Docker oficial.

- :material-github: Repo:
  <https://github.com/cloudflare/cloudflared>

### D2 { #d2 }

Lenguaje declarativo moderno para diagramas, alternativo a Mermaid,
con sintaxis más compacta y mejor manejo de tablas SQL y topologías
estáticas. Custodiam lo usa junto con Mermaid en el book; ver
[ADR-027](adrs/adr-027-mkdocs-pages.md).

- :material-web: Sitio oficial: <https://d2lang.com/>
- :material-github: Repo:
  <https://github.com/terrastruct/d2>

### FastAPI { #fastapi }

Framework Python para construir APIs HTTP basado en `pydantic` para
validación y tipado, con soporte nativo de OpenAPI y ASGI. Es el
framework backend de Custodiam (`custodiam-api`).

- :material-web: Docs: <https://fastapi.tiangolo.com/>
- :material-github: Repo:
  <https://github.com/fastapi/fastapi>

### Firebase { #firebase }

Plataforma de Google que agrupa servicios para apps móviles y web
(Cloud Messaging, Analytics, Crashlytics, etc.). Custodiam la usa
para FCM como canal primario de notificaciones push.

- :material-web: Sitio oficial: <https://firebase.google.com/>

### firebase_core { #firebase-core }

Paquete Flutter que inicializa Firebase en la app antes de poder usar
ningún otro paquete de la familia (Messaging, Analytics, etc.).
Requiere configuración nativa por plataforma (Android, iOS, Web).

- :material-package: pub.dev:
  <https://pub.dev/packages/firebase_core>

### Flutter { #flutter }

Framework de Google para construir aplicaciones nativas para
Android, iOS, Web y desktop desde un único código base en Dart. Es la
plataforma del cliente de Custodiam (`custodiam-app`).

- :material-web: Sitio oficial: <https://flutter.dev>
- :material-github: Repo: <https://github.com/flutter/flutter>

### flutter_riverpod { #flutter-riverpod }

Paquete Flutter que adapta Riverpod al árbol de widgets, exponiendo
`ConsumerWidget`, `ref.watch()` y `ref.read()`. Custodiam lo usa como
contenedor de DI y gestión de estado en toda la app.

- :material-package: pub.dev:
  <https://pub.dev/packages/flutter_riverpod>

### flutter_secure_storage { #flutter-secure-storage }

Paquete Flutter que guarda pares clave-valor cifrados usando Keystore
(Android) y Keychain (iOS). Custodiam lo usa para persistir tokens
OAuth en móvil; en web los tokens viven en memoria (no hay sustituto
seguro equivalente).

- :material-package: pub.dev:
  <https://pub.dev/packages/flutter_secure_storage>

### GoRouter { #gorouter }

Paquete oficial de Flutter para enrutado declarativo, soporte de deep
links y manejo del back button. Custodiam lo usa como router único de
la app; ver [ADR-011](adrs/adr-011-deep-links.md).

- :material-package: pub.dev:
  <https://pub.dev/packages/go_router>

### just { #just }

Command runner escrito en Rust, alternativa moderna a `make` orientada
a tareas (no a builds). Sirve como envoltura uniforme de comandos en
`custodiam-infra` y `custodiam-app`; "envuelve, no sustituye".

- :material-web: Sitio oficial: <https://just.systems/>
- :material-github: Repo: <https://github.com/casey/just>

### KeePassXC { #keepassxc }

Gestor de contraseñas de escritorio que almacena credenciales en una
base de datos local cifrada (`.kdbx`). Custodiam lo recomienda al
equipo como sitio donde guardar la clave age personal y secretos no
versionados; ver [ADR-019](adrs/adr-019-sops-age.md).

- :material-web: Sitio oficial: <https://keepassxc.org/>
- :material-github: Repo:
  <https://github.com/keepassxreboot/keepassxc>

### Keycloak { #keycloak }

Servidor OIDC y OAuth 2.0 de código abierto. Hace de Identity
Provider de Custodiam: maneja login, registro, reset de contraseña,
emisión de tokens y gestión de realms; ver
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

- :material-web: Sitio oficial: <https://www.keycloak.org/>
- :material-github: Repo: <https://github.com/keycloak/keycloak>

### Material Design 3 { #material-design-3 }

Tercera generación del sistema de diseño de Google, con tokens
dinámicos de color y mayor flexibilidad de personalización. Custodiam
lo adopta como base del Design System de la app; ver
[ADR-018](adrs/adr-018-design-system.md).

- :material-web: Sitio oficial: <https://m3.material.io/>

### Material for MkDocs { #material-for-mkdocs }

Theme y plugins para MkDocs muy mantenido, con búsqueda integrada,
modo oscuro, soporte de instant navigation y muchas extensiones.
Es el theme que renderiza este book; ver
[ADR-027](adrs/adr-027-mkdocs-pages.md).

- :material-web: Sitio oficial:
  <https://squidfunk.github.io/mkdocs-material/>
- :material-github: Repo:
  <https://github.com/squidfunk/mkdocs-material>

### Mermaid { #mermaid }

Lenguaje basado en texto para describir diagramas (sequence, state,
flowchart). Renderiza en el navegador. Custodiam lo usa junto con D2;
ver [ADR-027](adrs/adr-027-mkdocs-pages.md).

- :material-web: Sitio oficial: <https://mermaid.js.org/>
- :material-github: Repo: <https://github.com/mermaid-js/mermaid>

### MkDocs { #mkdocs }

Generador de sitios estáticos a partir de archivos Markdown, escrito
en Python. Base sobre la que corre el book; ver
[ADR-027](adrs/adr-027-mkdocs-pages.md).

- :material-web: Sitio oficial: <https://www.mkdocs.org/>
- :material-github: Repo: <https://github.com/mkdocs/mkdocs>

### n8n { #n8n }

Plataforma de automatización tipo workflow ("Zapier autoalojado").
Custodiam la levanta en el stack local para integrar flujos
auxiliares.

- :material-web: Sitio oficial: <https://n8n.io/>
- :material-github: Repo: <https://github.com/n8n-io/n8n>

### ntfy { #ntfy }

Servicio de notificaciones push HTTP-based, autoalojable, sin requerir
cuentas. Custodiam lo usa como segundo canal de notificaciones, en
paralelo con FCM, para reducir dependencia de Google.

- :material-web: Sitio oficial: <https://ntfy.sh/>
- :material-github: Repo:
  <https://github.com/binwiederhier/ntfy>

### oauth2 { #oauth2-dart }

Paquete Dart oficial (no confundir con el estándar [OAuth 2.0](#oauth-2-0))
mantenido por el equipo de Dart, que implementa el flujo OAuth 2.0 con
soporte de PKCE. Custodiam lo usa en móvil; en web el flujo se
gestiona manualmente; ver
[ADR-023](adrs/adr-023-oauth-web-asimetria.md).

- :material-package: pub.dev: <https://pub.dev/packages/oauth2>
- :material-github: Repo: <https://github.com/dart-lang/oauth2>

### Patrol { #patrol }

Framework de testing E2E para Flutter, con soporte de gestos nativos,
permisos del sistema y orquestación en Android, iOS y Web. Custodiam
lo adopta como herramienta E2E oficial; ver
[ADR-024](adrs/adr-024-patrol-e2e.md).

- :material-web: Sitio oficial: <https://patrol.leancode.co/>
- :material-github: Repo:
  <https://github.com/leancodepl/patrol>

### psycopg3 { #psycopg3 }

Versión 3 del driver de PostgreSQL para Python. Soporta async, type
hints nativos y mejor performance que `psycopg2`. Custodiam lo usa con
URL `postgresql+psycopg://...`; ver [ADR-008](adrs/adr-008-psycopg3.md).

- :material-web: Docs: <https://www.psycopg.org/psycopg3/>
- :material-github: Repo: <https://github.com/psycopg/psycopg>

### Pydantic { #pydantic }

Librería Python de validación y serialización basada en type hints.
Es el motor de validación de FastAPI y la base sobre la que SQLModel
construye sus modelos.

- :material-web: Docs: <https://docs.pydantic.dev/>
- :material-github: Repo: <https://github.com/pydantic/pydantic>

### PyJWT { #pyjwt }

Librería Python de referencia para emitir y verificar JWTs. Custodiam
la usa en el backend para verificar los tokens emitidos por Keycloak
contra el JWKS publicado.

- :material-web: Docs: <https://pyjwt.readthedocs.io/>
- :material-github: Repo: <https://github.com/jpadilla/pyjwt>

### pytest { #pytest }

Framework de testing más usado en el ecosistema Python. Sintaxis
declarativa, fixtures y plugins ricos. Es el runner de tests de
`custodiam-api`.

- :material-web: Docs: <https://docs.pytest.org/>
- :material-github: Repo:
  <https://github.com/pytest-dev/pytest>

### Resend { #resend }

Servicio SaaS de envío transaccional de correo, con SMTP relay y API
HTTP. Custodiam lo elige sobre AWS SES y otros por simplicidad de
onboarding y precio; ver [ADR-021](adrs/adr-021-smtp-resend.md).

- :material-web: Sitio oficial: <https://resend.com/>
- :material-github: Org: <https://github.com/resend>

### Riverpod { #riverpod }

Framework de gestión de estado e inyección de dependencias para
Flutter, sucesor moderno de Provider. Custodiam lo adopta como base
para ViewModels y servicios; ver [ADR-012](adrs/adr-012-riverpod.md).

- :material-web: Sitio oficial: <https://riverpod.dev/>
- :material-github: Repo:
  <https://github.com/rrousselGit/riverpod>

### Ruff { #ruff }

Linter y formatter de Python escrito en Rust, varias órdenes de
magnitud más rápido que Flake8/Pylint. Custodiam lo usa como única
herramienta de lint y formato en `custodiam-api`.

- :material-web: Docs: <https://docs.astral.sh/ruff/>
- :material-github: Repo: <https://github.com/astral-sh/ruff>

### sops { #sops }

*Secrets OPerationS*. Herramienta de Mozilla (hoy CNCF) para cifrar
archivos estructurados (YAML, JSON, ENV) campo a campo con backends
intercambiables (age, GPG, KMS). Custodiam la usa con age para
versionar `.env.sops`; ver [ADR-019](adrs/adr-019-sops-age.md).

- :material-github: Repo: <https://github.com/getsops/sops>

### sqflite { #sqflite }

Paquete Flutter de SQLite para Android y iOS. Custodiam lo usa como
almacenamiento local offline-first; ver
[ADR-005](adrs/adr-005-sqflite.md).

- :material-package: pub.dev: <https://pub.dev/packages/sqflite>
- :material-github: Repo:
  <https://github.com/tekartik/sqflite>

### SQLAlchemy { #sqlalchemy }

ORM y toolkit SQL de referencia en Python, con dos APIs (Core y ORM).
SQLModel se construye encima. Custodiam lo usa indirectamente vía
SQLModel.

- :material-web: Sitio oficial: <https://www.sqlalchemy.org/>
- :material-github: Repo:
  <https://github.com/sqlalchemy/sqlalchemy>

### SQLModel { #sqlmodel }

Capa de modelos que combina SQLAlchemy y Pydantic en una sola
declaración. Custodiam la adopta como ORM de `custodiam-api` para
evitar duplicar modelo ORM y modelo de validación; ver
[ADR-002](adrs/adr-002-sqlmodel.md).

- :material-web: Docs: <https://sqlmodel.tiangolo.com/>
- :material-github: Repo: <https://github.com/fastapi/sqlmodel>

### url_launcher { #url-launcher }

Paquete Flutter para abrir URLs externas (navegador, app de correo,
teléfono) desde la app. Custodiam lo usa en el flujo web de OAuth para
abrir la pantalla de login del IdP en pestaña nueva o `_self`.

- :material-package: pub.dev:
  <https://pub.dev/packages/url_launcher>

### uv { #uv }

Toolchain de empaquetado y entornos virtuales para Python escrita en
Rust por Astral. Sustituye `pip` + `venv` + `pip-tools` + `pipx` con
un único binario muy rápido. Adoptada como toolchain canónica de
`custodiam-api` por [ADR-026](adrs/adr-026-uv.md).

- :material-web: Docs: <https://docs.astral.sh/uv/>
- :material-github: Repo: <https://github.com/astral-sh/uv>

---

## Conceptos del proyecto

### anonimización Art. 17 { #anonimizacion-art-17 }

Operación que pisa los campos PII de una fila de voluntario con valores
neutros y conserva su `keycloak_id` y `audit_log`, cumpliendo el
derecho de supresión del Art. 17 RGPD sin perder integridad
referencial. Se distingue del *soft delete* (que solo marca como
borrado).

### App Links { #app-links }

Mecanismo de Android para vincular un dominio HTTPS a una app de
forma que abrir la URL desde un navegador o cliente de correo
arranque directamente la app (verificación de propiedad por
`assetlinks.json`). Equivalente Android de los Universal Links de
iOS; ver [ADR-011](adrs/adr-011-deep-links.md).

### AppPermissionGate { #app-permission-gate }

Widget Flutter que envuelve cualquier afordancia del UI condicionada
a un permiso. Si el `CurrentUser` no tiene el `Permission` requerido,
devuelve `SizedBox.shrink()` (oculta) o un `AppEmptyState` con copy
"Sin acceso". Patrón espejado en backend (`require_permission()`).
Documentado en [ADR-013](adrs/adr-013-rbac-lockstep.md).

### AppStartup { #app-startup }

Caso de uso que ejecuta toda la lógica de arranque de la app (carga
de configuración, restauración de sesión, comprobación de versión)
antes de decidir a qué ruta navegar. Convive con `SplashPage` para
ofrecer feedback visual durante el proceso; ver
[ADR-017](adrs/adr-017-splash-app-startup.md).

### Authorization Code { #authorization-code }

Tipo de concesión (grant) de OAuth 2.0 en el que el cliente
intercambia un código de autorización corto por un access token. Es
el grant recomendado para clientes con UI (móvil, web) y el único
que Custodiam acepta; ver
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

### AuthService { #auth-service }

Servicio Dart de la app que coordina el flujo OAuth 2.0 contra
Keycloak (login, refresh, logout) y expone el estado de sesión al
resto de la app vía Riverpod. Tiene implementaciones distintas para
móvil y web; ver [ADR-023](adrs/adr-023-oauth-web-asimetria.md).

### audit_log { #audit-log }

Tabla del backend que registra eventos de auditoría
(crear/editar/borrar voluntario, cambio de rol, anonimización, login
fallido). Cumple obligación RGPD y de trazabilidad operativa.
Documentado en [arquitectura](arquitectura/audit-log.md).

### Clean Architecture { #clean-architecture }

Aproximación arquitectónica con capas concéntricas (entidades, casos
de uso, adaptadores, frameworks) donde las dependencias siempre
apuntan hacia el centro. Custodiam la aplica de forma estricta en
`custodiam-app`; ver [arquitectura](arquitectura/index.md).

### client scope { #client-scope }

Concepto de Keycloak: conjunto de roles, claims y protocolos mappers
que se pueden asignar a un cliente OIDC. Custodiam usa scopes
distintos para el cliente web y el móvil; ver
[guía de configuración de Keycloak](guias/configuracion-keycloak.md).

### code_verifier { #code-verifier }

Cadena aleatoria secreta que el cliente OAuth genera al iniciar un
flujo PKCE y envía al servidor en el intercambio del código. Junto
con `code_challenge` (su hash SHA-256), demuestra que quien canjea el
código es quien inició el flujo; ver
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md).

### custom scheme { #custom-scheme }

Esquema de URL no estándar (p. ej. `com.custodiam.app://callback`)
que una app registra en el sistema operativo para recibir deep links.
Alternativa a App Links / Universal Links cuando no se quiere
configurar verificación por dominio; ver
[ADR-011](adrs/adr-011-deep-links.md).

### deep links { #deep-links }

Genéricamente, cualquier URL que abre una vista concreta dentro de
una app móvil. Bajo este paraguas caben App Links, Universal Links y
custom schemes; ver [ADR-011](adrs/adr-011-deep-links.md).

### EnvConfig { #env-config }

Clase Dart que centraliza la lectura de variables de entorno
inyectadas en build time con `--dart-define`. Evita strings
hardcoded dispersos y permite cambiar el endpoint del backend/IdP
sin recompilar. Documentado en [ADR-015](adrs/adr-015-env-config.md).

### mapper { #mapper }

Concepto de Keycloak: regla que transforma datos de un usuario en
claims del token. Custodiam configura mappers para incluir los roles
del realm en el `access_token` que verifica el backend; ver
[guía de configuración de Keycloak](guias/configuracion-keycloak.md).

### Permission enum { #permission-enum }

Catálogo cerrado de permisos canónicos del dominio
(`voluntarios.crear`, `servicios.editar`, etc.). Reside en el backend
y se espeja literal en el frontend para garantizar el lockstep; ver
[ADR-013](adrs/adr-013-rbac-lockstep.md).

### polyrepo { #polyrepo }

Estructura de proyecto donde cada componente vive en su propio
repositorio Git, en contraste con monorepo. Custodiam adopta
polyrepo con cuatro repos (`custodiam-app`, `custodiam-api`,
`custodiam-infra`, `custodiam-book`); ver
[ADR-001](adrs/adr-001-polyrepo.md).

### RBAC lockstep { #rbac-lockstep }

Disciplina por la que cualquier cambio en el catálogo de permisos
debe aplicarse de forma síncrona en backend y frontend en el mismo
PR, manteniendo ambos espejos de la misma matriz. Documentado en
[ADR-013](adrs/adr-013-rbac-lockstep.md).

### realm { #realm }

Concepto de Keycloak: contenedor lógico aislado con sus propios
usuarios, roles, clientes y políticas. Custodiam usa dos realms
distintos (`master` para administración de Keycloak, `custodiam` para
los usuarios de la app); ver
[la página de usuarios de prueba](empezar/usuarios-prueba.md).

### Result<T> { #result-t }

Tipo sellado del frontend que representa o bien un valor de éxito
(`Success<T>`) o bien una `Failure` tipada. Sustituye al manejo de
excepciones para flujos previsibles (red, validación, autenticación);
ver [ADR-014](adrs/adr-014-result-failure.md).

### sessionStorage { #session-storage }

Almacenamiento por pestaña del navegador (se borra al cerrarla).
Custodiam lo usa en web para guardar el `code_verifier` mientras dura
el redirect del flujo OAuth, evitando exponerlo en `localStorage`;
ver [ADR-023](adrs/adr-023-oauth-web-asimetria.md).

### soft delete { #soft-delete }

Borrado lógico: la fila no se elimina físicamente sino que se marca
con un campo `deleted_at`. Custodiam lo usa para "dar de baja" un
voluntario manteniendo histórico. **Distinto** de la anonimización
Art. 17, que pisa los datos personales.

### SplashPage { #splash-page }

Pantalla inicial de la app Flutter que se muestra durante el arranque
mientras se ejecuta el caso de uso `AppStartup`. Documentada en
[ADR-017](adrs/adr-017-splash-app-startup.md).

### Universal Links { #universal-links }

Mecanismo de iOS análogo a los App Links de Android: vincula un
dominio HTTPS a una app verificando la propiedad mediante un archivo
`apple-app-site-association`. Si la app está instalada, abre
directamente; si no, abre el navegador como fallback. Ver
[ADR-011](adrs/adr-011-deep-links.md).

---

## Alternativas evaluadas y descartadas

!!! info "Estas herramientas no son parte del stack actual"

    Esta sección lista herramientas que aparecen mencionadas en los
    ADRs como alternativas evaluadas y finalmente **no elegidas**.
    Se incluyen para que el lector entienda por qué se descartaron,
    pero **no se usan en Custodiam**.

### Auth0 { #auth0 }

Plataforma SaaS de Identity-as-a-Service. Descartada en
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md) en favor de Keycloak
autoalojado, por compatibilidad con AGPL y para evitar lock-in y
costes por usuario activo.

- :material-web: Sitio oficial: <https://auth0.com/>

### BLoC { #bloc }

Patrón de gestión de estado basado en streams para Flutter.
Descartado en [ADR-012](adrs/adr-012-riverpod.md) frente a Riverpod
por boilerplate más alto y curva de aprendizaje menos cómoda para el
equipo.

- :material-web: Sitio oficial: <https://bloclibrary.dev/>
- :material-github: Repo: <https://github.com/felangel/bloc>

### Caddy { #caddy }

Servidor web moderno con HTTPS automático integrado. Descartado en
[ADR-006](adrs/adr-006-nginx-alpine.md) en favor de Nginx Alpine por
ecosistema mucho más maduro para servir bundles SPA/PWA.

- :material-web: Sitio oficial: <https://caddyserver.com/>
- :material-github: Repo:
  <https://github.com/caddyserver/caddy>

### Casbin { #casbin }

Librería multi-lenguaje de autorización con soporte de RBAC, ABAC y
políticas custom. Descartada en
[ADR-013](adrs/adr-013-rbac-lockstep.md) frente a un enum estático
por sobreingeniería para un catálogo pequeño y estable.

- :material-web: Sitio oficial: <https://casbin.org/>
- :material-github: Repo: <https://github.com/casbin/casbin>

### Cedar { #cedar }

Lenguaje de políticas de AWS para autorización fine-grained.
Descartado en [ADR-013](adrs/adr-013-rbac-lockstep.md) por el mismo
motivo que Casbin: demasiada maquinaria para un RBAC clásico.

- :material-web: Sitio oficial: <https://www.cedarpolicy.com/>
- :material-github: Repo:
  <https://github.com/cedar-policy/cedar>

### Chopper { #chopper }

Cliente HTTP con generación de código para Flutter. Descartado en
[ADR-004](adrs/adr-004-http-cliente.md) en favor del paquete oficial
`http` por no necesitar `build_runner` en el cliente y minimizar
generación de código.

- :material-package: pub.dev: <https://pub.dev/packages/chopper>

### Cypress { #cypress }

Framework de E2E para web. Descartado en
[ADR-024](adrs/adr-024-patrol-e2e.md) por no soportar móvil nativo
(Android/iOS) y por requerir mantener dos frameworks distintos.

- :material-web: Sitio oficial: <https://www.cypress.io/>
- :material-github: Repo:
  <https://github.com/cypress-io/cypress>

### Dio { #dio }

Cliente HTTP popular para Flutter con interceptors, cancelación y
adapters. Descartado en [ADR-004](adrs/adr-004-http-cliente.md) en
favor del paquete oficial `http` por mantener el stack
deliberadamente minimalista.

- :material-package: pub.dev: <https://pub.dev/packages/dio>
- :material-github: Repo: <https://github.com/cfug/dio>

### drift { #drift }

ORM moderno y tipado para SQLite en Flutter con generación de código.
Descartado en [ADR-005](adrs/adr-005-sqflite.md) en favor de sqflite
puro por evitar `build_runner` y mantener queries SQL explícitas.

- :material-web: Docs: <https://drift.simonbinder.eu/>
- :material-github: Repo: <https://github.com/simolus3/drift>

### Flyway { #flyway }

Herramienta de migraciones de BD basada en JVM (Java). Descartada en
[ADR-003](adrs/adr-003-alembic.md) frente a Alembic por evitar el
runtime Java en el contenedor de migraciones y mantener el stack en
Python.

- :material-web: Sitio oficial: <https://flywaydb.org/>
- :material-github: Repo: <https://github.com/flyway/flyway>

### GetIt { #get-it }

Service locator simple para Flutter. Descartado en
[ADR-012](adrs/adr-012-riverpod.md) frente a Riverpod por no ofrecer
gestión reactiva de estado además de DI.

- :material-package: pub.dev:
  <https://pub.dev/packages/get_it>

### GitBook { #gitbook }

Plataforma SaaS de documentación con editor WYSIWYG. Descartada en
[ADR-027](adrs/adr-027-mkdocs-pages.md) por lock-in al editor
propietario y dificultad para versionar el contenido en Git plano.

- :material-web: Sitio oficial: <https://www.gitbook.com/>

### Hatch { #hatch }

Toolchain Python moderno de PyPA (gestor de proyectos, entornos y
builds). Descartado en [ADR-026](adrs/adr-026-uv.md) frente a uv por
no integrar resolución de dependencias tan rápida ni envoltura del
intérprete.

- :material-web: Docs: <https://hatch.pypa.io/>
- :material-github: Repo: <https://github.com/pypa/hatch>

### hive { #hive }

Base de datos NoSQL ligera para Flutter, escrita en Dart puro.
Descartada en [ADR-005](adrs/adr-005-sqflite.md) frente a SQLite por
no soportar queries relacionales ni migraciones de esquema robustas.

- :material-package: pub.dev: <https://pub.dev/packages/hive>

### isar { #isar }

Base de datos NoSQL embebida para Flutter, sucesora moderna de hive.
Descartada en [ADR-005](adrs/adr-005-sqflite.md) por el mismo motivo:
modelo NoSQL no encaja con queries relacionales del dominio.

- :material-web: Sitio oficial: <https://isar.dev/>
- :material-github: Repo: <https://github.com/isar/isar>

### Liquibase { #liquibase }

Herramienta de migraciones de BD multi-formato (XML, YAML, SQL).
Descartada en [ADR-003](adrs/adr-003-alembic.md) frente a Alembic por
preferir migraciones declaradas en Python (mismo lenguaje que el
backend).

- :material-web: Sitio oficial: <https://www.liquibase.org/>
- :material-github: Repo:
  <https://github.com/liquibase/liquibase>

### Maestro { #maestro }

Framework de E2E para móvil con sintaxis declarativa en YAML.
Descartado en [ADR-024](adrs/adr-024-patrol-e2e.md) por menos
expresivo que un test programado en Dart y por no integrarse
nativamente con la app Flutter.

- :material-web: Sitio oficial: <https://maestro.mobile.dev/>
- :material-github: Repo:
  <https://github.com/mobile-dev-inc/maestro>

### mdBook { #mdbook }

Generador de sitios estáticos para libros técnicos escrito en Rust.
Descartado en [ADR-027](adrs/adr-027-mkdocs-pages.md) frente a
MkDocs+Material por ecosistema de plugins más limitado.

- :material-web: Sitio oficial:
  <https://rust-lang.github.io/mdBook/>
- :material-github: Repo: <https://github.com/rust-lang/mdBook>

### OPA { #opa }

*Open Policy Agent*. Motor de políticas de propósito general (CNCF).
Descartado en [ADR-013](adrs/adr-013-rbac-lockstep.md) por la misma
razón que Casbin: complejidad excesiva para un RBAC clásico.

- :material-web: Sitio oficial: <https://www.openpolicyagent.org/>
- :material-github: Repo:
  <https://github.com/open-policy-agent/opa>

### Ory { #ory }

Suite de productos (Kratos, Hydra, Keto, Oathkeeper) para identidad y
autorización. Descartada en
[ADR-010](adrs/adr-010-oauth-pkce-keycloak.md) frente a Keycloak por
preferir una solución más integrada y mejor documentada para el
caso de uso de Custodiam.

- :material-web: Sitio oficial: <https://www.ory.sh/>

### PDM { #pdm }

Toolchain Python alternativo a Poetry, basado en estándares PEP.
Descartado en [ADR-026](adrs/adr-026-uv.md) frente a uv por
velocidad de resolución y por no incluir gestión del intérprete.

- :material-web: Docs: <https://pdm-project.org/>
- :material-github: Repo: <https://github.com/pdm-project/pdm>

### Pipenv { #pipenv }

Toolchain Python que combina `pip` y `virtualenv` en un solo CLI.
Descartado en [ADR-026](adrs/adr-026-uv.md) por velocidad muy
inferior a uv y por ritmo de mantenimiento irregular.

- :material-web: Docs: <https://pipenv.pypa.io/>
- :material-github: Repo: <https://github.com/pypa/pipenv>

### Poetry { #poetry }

Toolchain Python con manejo de dependencias, builds y publicación.
Descartado en [ADR-026](adrs/adr-026-uv.md) frente a uv por
velocidad y por sintaxis propia de `pyproject.toml` no perfectamente
alineada con PEPs recientes.

- :material-web: Sitio oficial: <https://python-poetry.org/>
- :material-github: Repo:
  <https://github.com/python-poetry/poetry>

### Provider { #provider }

Librería de gestión de estado anterior y base sobre la que se
construyó Riverpod. Descartada en [ADR-012](adrs/adr-012-riverpod.md)
porque Riverpod la sustituye con menos dependencia del árbol de
widgets y mejor ergonomía.

- :material-package: pub.dev:
  <https://pub.dev/packages/provider>

### Rye { #rye }

Toolchain Python anterior de Astral, predecesor parcial de uv.
Descartada en [ADR-026](adrs/adr-026-uv.md) porque la propia Astral
recomienda migrar a uv.

- :material-web: Sitio oficial: <https://rye.astral.sh/>
- :material-github: Repo: <https://github.com/astral-sh/rye>

### Sphinx { #sphinx }

Generador de documentación clásico del ecosistema Python, basado en
reStructuredText. Descartado en
[ADR-027](adrs/adr-027-mkdocs-pages.md) frente a MkDocs por sintaxis
RST menos cómoda que Markdown para el flujo del equipo.

- :material-web: Sitio oficial: <https://www.sphinx-doc.org/>
- :material-github: Repo: <https://github.com/sphinx-doc/sphinx>

### Vercel { #vercel }

Plataforma de despliegue serverless con foco en frontend. Descartada
en [ADR-006](adrs/adr-006-nginx-alpine.md) frente a Nginx Alpine
autoalojado para evitar dependencia de plataforma propietaria al
servir el bundle de Flutter Web.

- :material-web: Sitio oficial: <https://vercel.com/>
