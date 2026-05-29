<!--
  Definiciones de tooltip (Markdown abbr extension).
  Incluido automáticamente en cada página vía pymdownx.snippets:auto_append.
  Cada *[Término]: ... añade un <abbr title="..."> con tooltip al hacer hover.
  Las definiciones se mantienen alineadas con docs/glosario.md.
-->

*[ABAC]: Attribute-Based Access Control. Modelo de autorización por atributos.
*[ADR]: Architecture Decision Record. Documento breve que registra una decisión técnica con su contexto y alternativas.
*[AGPL]: GNU Affero General Public License. Licencia copyleft fuerte; obliga a publicar el fuente incluso en servicios en red.
*[BFF]: Backend for Frontend. Patrón con un backend dedicado a cada cliente.
*[CI/CD]: Continuous Integration / Continuous Delivery. Build, test y despliegue automatizados.
*[CNAME]: Canonical Name. Tipo de registro DNS que apunta un dominio a otro nombre.
*[CORS]: Cross-Origin Resource Sharing. Mecanismo HTTP que controla peticiones cross-origin desde JavaScript.
*[DI]: Dependency Injection. Patrón en el que un objeto recibe sus dependencias de fuera.
*[DKIM]: DomainKeys Identified Mail. Firma criptográfica de las cabeceras de un correo saliente.
*[DoD]: Definition of Done. Criterios objetivos que una tarea debe cumplir para considerarse completada.
*[E2E]: End-to-End test. Prueba que ejecuta toda la app contra infraestructura real.
*[FCM]: Firebase Cloud Messaging. Servicio de Google para notificaciones push.
*[GHCR]: GitHub Container Registry. Registro de imágenes Docker integrado en GitHub.
*[IdP]: Identity Provider. Sistema que autentica usuarios y emite tokens de identidad.
*[JSONB]: Tipo de PostgreSQL para almacenar JSON en formato binario indexable.
*[JWKS]: JSON Web Key Set. Documento con las claves públicas que verifican un JWT.
*[JWT]: JSON Web Token. Token JSON firmado y compacto.
*[MFA]: Multi-Factor Authentication. Login que combina dos o más factores distintos.
*[MTA]: Mail Transfer Agent. Servidor que envía y reenvía correo por SMTP.
*[OAuth 2.0]: Marco IETF de autorización delegada por token (RFC 6749).
*[OIDC]: OpenID Connect. Capa de identidad sobre OAuth 2.0 que añade id_token.
*[PII]: Personally Identifiable Information. Datos que permiten identificar a una persona física.
*[PKCE]: Proof Key for Code Exchange. Extensión de OAuth 2.0 que protege el Authorization Code en clientes públicos.
*[PWA]: Progressive Web App. App web con capacidades nativas (instalación, offline, push).
*[RBAC]: Role-Based Access Control. Modelo de autorización por roles.
*[RFC]: Request for Comments. Documento de estándar publicado por el IETF.
*[RGPD]: Reglamento General de Protección de Datos (UE 2016/679). GDPR en inglés.
*[SMTP]: Simple Mail Transfer Protocol. Protocolo estándar de envío de correo (RFC 5321).
*[SPA]: Single Page Application. App web que se carga una sola vez y navega por JavaScript.
*[SPF]: Sender Policy Framework. Publica en DNS qué servidores pueden enviar correo en nombre de un dominio.
*[SSO]: Single Sign-On. Un solo login da acceso a varias apps que comparten IdP.
*[WSL2]: Windows Subsystem for Linux v2. Capa de Microsoft que corre un kernel Linux dentro de Windows.

*[age]: Herramienta moderna de cifrado de archivos con sintaxis simple y clave pública X25519.
*[Alembic]: Herramienta de migraciones de esquema para SQLAlchemy/SQLModel.
*[app_links]: Paquete Flutter que captura App Links de Android y Universal Links de iOS.
*[Cloudflare Tunnel]: Túnel saliente desde tu infra hasta Cloudflare; expone servicios sin abrir puertos.
*[cloudflared]: Daemon que mantiene abierto el Cloudflare Tunnel desde el servidor.
*[D2]: Lenguaje declarativo moderno para diagramas, alternativo a Mermaid.
*[FastAPI]: Framework Python para APIs HTTP con tipado, validación Pydantic y soporte OpenAPI.
*[Firebase]: Plataforma de Google con servicios para apps móviles y web.
*[firebase_core]: Paquete Flutter que inicializa Firebase antes de usar otros paquetes Firebase.
*[Flutter]: Framework de Google para construir apps Android, iOS, Web y desktop desde un código Dart.
*[flutter_riverpod]: Paquete Flutter que adapta Riverpod al árbol de widgets.
*[flutter_secure_storage]: Paquete Flutter que cifra pares clave-valor usando Keystore / Keychain.
*[GoRouter]: Paquete Flutter oficial para enrutado declarativo con soporte de deep links.
*[just]: Command runner en Rust orientado a tareas, alternativa moderna a make.
*[KeePassXC]: Gestor de contraseñas de escritorio con base de datos cifrada local (.kdbx).
*[Keycloak]: Servidor OIDC y OAuth 2.0 de código abierto; Identity Provider de Custodiam.
*[Material Design 3]: Tercera generación del sistema de diseño de Google.
*[Material for MkDocs]: Theme y plugins para MkDocs muy mantenido; renderiza este book.
*[Mermaid]: Lenguaje basado en texto para describir diagramas que se renderizan en el navegador.
*[MkDocs]: Generador Python de sitios estáticos a partir de Markdown.
*[n8n]: Plataforma de automatización tipo workflow (Zapier autoalojado).
*[ntfy]: Servicio de notificaciones push HTTP autoalojable.
*[oauth2]: Paquete Dart oficial que implementa OAuth 2.0 con PKCE (no confundir con el estándar).
*[Patrol]: Framework de testing E2E para Flutter, con gestos nativos y orquestación en Android, iOS y Web.
*[psycopg3]: Driver PostgreSQL para Python v3, con soporte async y type hints.
*[Pydantic]: Librería Python de validación y serialización basada en type hints.
*[PyJWT]: Librería Python de referencia para emitir y verificar JWT.
*[pytest]: Framework de testing más usado en Python; runner de tests de custodiam-api.
*[Resend]: Servicio SaaS de envío transaccional de correo con SMTP y API HTTP.
*[Riverpod]: Framework de gestión de estado e inyección de dependencias para Flutter, sucesor de Provider.
*[Ruff]: Linter y formatter de Python escrito en Rust, mucho más rápido que Flake8/Pylint.
*[sops]: Secrets OPerationS. Cifra archivos estructurados campo a campo con age, GPG o KMS.
*[sqflite]: Paquete Flutter de SQLite para Android e iOS; almacenamiento local offline-first.
*[SQLAlchemy]: ORM y toolkit SQL de referencia en Python.
*[SQLModel]: Capa que combina SQLAlchemy y Pydantic en una sola declaración de modelo.
*[url_launcher]: Paquete Flutter para abrir URLs externas desde la app.
*[uv]: Toolchain Python de Astral escrita en Rust. Sustituye pip + venv + pip-tools.

*[anonimización Art. 17]: Pisar campos PII con valores neutros cumpliendo el derecho de supresión RGPD (Art. 17).
*[App Links]: Mecanismo de Android para vincular un dominio HTTPS a una app vía assetlinks.json.
*[AppPermissionGate]: Widget Flutter que oculta afordancias del UI si el usuario no tiene el permiso requerido.
*[AppStartup]: Caso de uso que ejecuta la lógica de arranque de la app antes de navegar.
*[Authorization Code]: Tipo de grant de OAuth 2.0 donde el cliente canjea un código por un access token.
*[AuthService]: Servicio Dart que coordina el flujo OAuth contra Keycloak en la app Flutter.
*[audit_log]: Tabla backend que registra eventos de auditoría (cambios sobre voluntarios, logins, etc.).
*[Clean Architecture]: Aproximación arquitectónica por capas concéntricas con dependencias hacia el centro.
*[client scope]: Concepto Keycloak: conjunto de roles, claims y mappers asignables a un cliente.
*[code_verifier]: Cadena secreta del flujo PKCE que el cliente envía al canjear el código.
*[custom scheme]: URL no estándar (ej. com.custodiam.app://) que una app registra para recibir deep links.
*[deep links]: URLs que abren una vista concreta dentro de una app móvil.
*[EnvConfig]: Clase Dart que centraliza variables de entorno inyectadas en build time con --dart-define.
*[mapper]: Concepto Keycloak: regla que transforma datos del usuario en claims del token.
*[Permission enum]: Catálogo cerrado de permisos canónicos del dominio, espejado entre backend y frontend.
*[polyrepo]: Estructura de proyecto donde cada componente vive en su propio repositorio Git.
*[RBAC lockstep]: Disciplina por la que cualquier cambio en el catálogo de permisos se aplica síncrono en backend y frontend.
*[realm]: Concepto Keycloak: contenedor lógico aislado con usuarios, roles, clientes y políticas propias.
*[Result<T>]: Tipo sellado del frontend que representa o éxito Success<T> o Failure tipada.
*[sessionStorage]: Almacenamiento por pestaña del navegador (se borra al cerrarla).
*[soft delete]: Borrado lógico (campo deleted_at) que mantiene la fila para histórico.
*[SplashPage]: Pantalla inicial de la app durante el arranque, mientras corre AppStartup.
*[Universal Links]: Mecanismo iOS análogo a App Links de Android, vía apple-app-site-association.
*[ValueKey]: Clave estable de un widget Flutter para que los tests lo localicen con find.byKey.

*[Auth0]: Plataforma SaaS de Identity-as-a-Service. ALTERNATIVA DESCARTADA en Custodiam (ADR-010).
*[BLoC]: Patrón de gestión de estado por streams para Flutter. ALTERNATIVA DESCARTADA (ADR-012).
*[Caddy]: Servidor web moderno con HTTPS automático. ALTERNATIVA DESCARTADA (ADR-006).
*[Casbin]: Librería de autorización multi-lenguaje. ALTERNATIVA DESCARTADA (ADR-013).
*[Cedar]: Lenguaje de políticas de AWS. ALTERNATIVA DESCARTADA (ADR-013).
*[Chopper]: Cliente HTTP con generación de código para Flutter. ALTERNATIVA DESCARTADA (ADR-004).
*[Cypress]: Framework E2E solo para web. ALTERNATIVA DESCARTADA (ADR-024).
*[Dio]: Cliente HTTP popular para Flutter. ALTERNATIVA DESCARTADA (ADR-004).
*[drift]: ORM tipado para SQLite en Flutter. ALTERNATIVA DESCARTADA (ADR-005).
*[Flyway]: Migraciones de BD basadas en JVM. ALTERNATIVA DESCARTADA (ADR-003).
*[GetIt]: Service locator simple para Flutter. ALTERNATIVA DESCARTADA (ADR-012).
*[GitBook]: Plataforma SaaS de documentación con editor WYSIWYG. ALTERNATIVA DESCARTADA (ADR-027).
*[Hatch]: Toolchain Python de PyPA. ALTERNATIVA DESCARTADA (ADR-026).
*[hive]: Base de datos NoSQL ligera para Flutter en Dart puro. ALTERNATIVA DESCARTADA (ADR-005).
*[isar]: Base de datos NoSQL embebida para Flutter. ALTERNATIVA DESCARTADA (ADR-005).
*[Liquibase]: Migraciones de BD multi-formato. ALTERNATIVA DESCARTADA (ADR-003).
*[Maestro]: Framework E2E móvil con sintaxis YAML. ALTERNATIVA DESCARTADA (ADR-024).
*[mdBook]: Generador de sitios para libros técnicos en Rust. ALTERNATIVA DESCARTADA (ADR-027).
*[OPA]: Open Policy Agent. Motor de políticas CNCF. ALTERNATIVA DESCARTADA (ADR-013).
*[Ory]: Suite de productos de identidad (Kratos, Hydra, Keto). ALTERNATIVA DESCARTADA (ADR-010).
*[PDM]: Toolchain Python alternativo a Poetry. ALTERNATIVA DESCARTADA (ADR-026).
*[Pipenv]: Toolchain Python que combina pip y virtualenv. ALTERNATIVA DESCARTADA (ADR-026).
*[Poetry]: Toolchain Python con dependencias y builds. ALTERNATIVA DESCARTADA (ADR-026).
*[Provider]: Librería de estado precursora de Riverpod. ALTERNATIVA DESCARTADA (ADR-012).
*[Rye]: Toolchain Python anterior de Astral. ALTERNATIVA DESCARTADA (ADR-026).
*[Sphinx]: Generador de documentación clásico de Python basado en reStructuredText. ALTERNATIVA DESCARTADA (ADR-027).
*[Vercel]: Plataforma de despliegue serverless con foco en frontend. ALTERNATIVA DESCARTADA (ADR-006).
