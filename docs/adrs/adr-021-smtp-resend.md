---
title: ADR-021 — Proveedor SMTP para emails transaccionales de Keycloak
description: >-
  Resend (sobre AWS SES eu-west-1) como proveedor SMTP para los emails
  transaccionales del realm Keycloak. Tracking opt-in por dominio (OFF por
  defecto) que mantiene los enlaces intactos para App Links / Universal Links.
---

# ADR-021 — Proveedor SMTP para emails transaccionales de Keycloak

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 12 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

Keycloak es un Identity Provider, no un Mail Transfer Agent. Por diseño no incluye servidor SMTP propio: para enviar emails transaccionales (`forgot password`, `verify email`, `invite user`) requiere conectarse a un MTA externo vía SMTP estándar. El soporte se reduce a cinco campos en `Realm Settings → Email`: `host`, `port`, `username`, `password`, `from` — sin SDK, sin integración propietaria.

Custodiam ya tiene tres canales de mensajería decididos previamente:

- **Firebase Cloud Messaging** — push notifications críticas (emergencias). Latencia ~1 s.
- **ntfy** self-hosted — push notifications normales (servicios preventivos, ciudadanía) y red de seguridad si FCM falla.
- **Cloudflare Email Routing** — inbox de `contacto@custodiam.es` y `soporte@custodiam.es`, redirige a buzones reales del equipo. **Solo entrada, no envío.**

Ninguno cubre el caso "Keycloak envía un email transaccional al usuario que ha pulsado 'olvidé mi contraseña'". La verificación end-to-end del flujo de "recuperar contraseña" reveló que el realm tenía la sección de SMTP vacía (`"smtpServer": {}`): los flujos de email simplemente no se habían ejercitado nunca. Esta ADR cierra la laguna registrando el proveedor SMTP y delimitando con claridad qué entra en el alcance del MVP y qué se difiere a fases posteriores.

## Decisión

**[Resend](https://resend.com)** (basado en AWS SES `eu-west-1`) como proveedor SMTP para los emails transaccionales del realm `custodiam`, con la siguiente configuración:

| Campo | Valor | Origen |
| --- | --- | --- |
| Servidor SMTP | `smtp.resend.com` | Resend dashboard |
| Puerto | `587` | STARTTLS |
| Cifrado | STARTTLS | `Enable StartTLS` ON en Keycloak |
| Usuario SMTP | literal `resend` | Convención de Resend |
| Contraseña SMTP | API key generada en Resend (`re_...`) | Revocable individualmente |
| From | `noreply@custodiam.es` | Remitente |
| Reply-To | `soporte@custodiam.es` (opcional) | Las respuestas caen en Cloudflare Email Routing |
| Tracking | **OFF** por dominio | Opt-in en Resend; deliberadamente desactivado |

**Validación de dominio:** `custodiam.es` queda verificado en Resend con tres registros DNS gestionados en Cloudflare:

- **DKIM** (`TXT resend._domainkey`) — firma criptográfica de cada email, evita spoofing.
- **MX `send.custodiam.es`** — Resend usa subdominio `send.custodiam.es` para el *envelope sender* (`bounces@send.custodiam.es`), lo que evita tocar el SPF del root.
- **SPF subdomain** (`TXT send.custodiam.es`) — autoriza los servidores de AWS SES `eu-west-1` que Resend usa.

**Almacenamiento de credenciales:** el usuario literal `resend` y la API key viven en `docker/.env.sops` cifradas con `sops` + `age`. Nunca en `realm-custodiam.json` plano. Se inyectan al contenedor Keycloak vía variables de entorno (`KEYCLOAK_SMTP_USERNAME` y `KEYCLOAK_SMTP_PASSWORD`) que el contenedor mapea a la configuración SMTP del realm en arranque.

**Alcance estricto** — solo los emails transaccionales que Keycloak emite nativamente:

- `forgot-password` (recuperar contraseña).
- `verify-email` (verificar email tras registro).
- `executeActions` (acción requerida — futuro: confirmar cambio de email).

**Quedan fuera** y se replantean cuando aparezcan, con análisis de volumen real:

- Emails iniciados por la API (`custodiam-api`), no por Keycloak.
- Email como canal de notificación de servicio/emergencia para usuario final.
- Newsletters, recordatorios, *digests*.

## Justificación

1. **Tracking opt-in por dominio (OFF por defecto)** — es el criterio diferenciador. Los enlaces del cuerpo del email salen **sin reescritura**, llegan al móvil intactos, y los App Links / Universal Links ([ADR-011](adr-011-deep-links.md)) funcionan como espera el manifiesto `.well-known/`. Proveedores que reescriben obligatoriamente los enlaces a un dominio propio de tracking rompen este flujo y obligarían a soluciones forzadas.

2. **AWS SES `eu-west-1` (Irlanda) underneath** — Resend delega la entrega real en SES, con servidores en la región europea. Postura GDPR sólida ("dónde viven los datos") sin necesidad de gestionar la consola AWS directamente.

3. **Free tier 3000/mes (~100/día) sin tarjeta de crédito** — suficiente para los ~150 emails/año transaccionales del MVP con dos órdenes de magnitud de margen. Sin compromiso financiero, sin trial limitado en el tiempo.

4. **SMTP estándar con convención limpia** — `smtp.resend.com:587` con username literal `resend` y password = API key. La separación entre login web de la cuenta y credenciales SMTP elimina la confusión de proveedores que usan un *SMTP login* derivado distinto del email de la cuenta.

5. **Arquitectura provider-agnostic preservada** — el bloque `smtpServer` en `realm-custodiam.json` usa placeholders `${env.KEYCLOAK_SMTP_USERNAME}` y `${env.KEYCLOAK_SMTP_PASSWORD}`. Cambiar de proveedor en el futuro toca el `host` del realm, dos secretos en `.env.sops` y los registros DNS — pero no la lógica del backend ni del cliente. No hay vendor lock-in.

## Alternativas evaluadas y descartadas

### A. Brevo (ex-Sendinblue)

Free tier indefinido 300 emails/día, origen europeo, SMTP estándar.

- **Pros**: free tier superior (300/día vs 100/día de Resend), origen europeo, sin tarjeta.
- **Contras**: **reescribe obligatoriamente todos los enlaces a través de `sendibt3.com`** (click tracking) y añade un pixel de open tracking, sin posibilidad de desactivarlo. Limitación confirmada en el [hilo oficial de la comunidad de Brevo](https://community.brevo.com/t/no-way-to-disable-by-option-tracking-in-transactional-e-mail/201), abierto hace años, con respuesta institucional "no lo permitimos por motivos de seguridad anti-fraude". Esto invalida los App Links / Universal Links: el sistema operativo móvil no reconoce el dominio `sendibt3.com` como autorizado por el manifiesto `.well-known/` y abre el navegador en lugar de la app.
- **Descartado por**: el tracking obligatorio rompe el contrato con [ADR-011](adr-011-deep-links.md). Fue la elección inicial; tras verificar el comportamiento real durante la implementación se migró a Resend en la misma sesión de trabajo.

### B. Gmail con App Password

`smtp.gmail.com:587` con un App Password generado en una cuenta Google del proyecto. Free hasta ~500 emails/día.

- **Pros**: cero coste, sin verificación de dominio.
- **Contras**: los emails salen "via gmail.com" en muchos clientes — imagen de marca débil para un servicio operativo de Protección Civil; obliga a mantener 2FA + App Password en cuenta personal cruzando dominios (auth de Google ↔ servicio operativo de la app); si la cuenta se compromete o se desactiva el App Password, los emails se rompen.
- **Descartado** como opción principal. Se mantiene mentalmente como *fallback de emergencia*: las cuatro líneas SMTP del realm son intercambiables en 30 segundos.

### C. SendGrid (Twilio)

100 emails/día gratis tras la primera semana.

- **Pros**: deliverability muy alta, integración madura.
- **Contras**: requiere tarjeta de crédito desde el principio. Burocracia añadida sin beneficio sobre Resend para el volumen del piloto.
- **Descartado por**: barrera de entrada injustificada.

### D. Mailgun

5 000 emails los primeros 3 meses, luego pay-as-you-go (~$0.001/email).

- **Pros**: alto volumen gratis al inicio.
- **Contras**: el free tier es trial, no indefinido. Para un piloto que puede prolongarse 6-12 meses, no sirve a largo plazo.
- **Descartado por**: free tier limitado en el tiempo.

### E. Amazon SES (directo)

$0.10 por mil emails.

- **Pros**: el más barato a escala.
- **Contras**: requiere cuenta AWS con tarjeta, verificación del dominio en SES, salir del sandbox inicial (limitado a destinatarios verificados) solicitando explícitamente el levantamiento del límite, comprensión de la consola y las cuotas. Sobre-ingeniería para los ~150 emails/año del MVP.
- **Descartado para el MVP**, **reservado como camino preferente** si en el futuro se añade email como canal de notificación masiva y el volumen pasa de centenas/año a miles/día. Resend, al usar SES por debajo, deja una vía natural de migración.

### F. Postmark

Especializado en transaccional con muy alta deliverability.

- **Pros**: foco transaccional, soporte excelente.
- **Contras**: sin free tier real — solo 100 emails de trial. Plan pago razonable pero innecesario para un piloto cero-coste.
- **Descartado por**: ausencia de free tier indefinido.

### G. Postfix self-hosted

Levantar un MTA propio en un contenedor en `custodiam-infra`.

- **Pros**: cero dependencia de proveedor externo.
- **Contras**: arrastra reputación IP (los proveedores rechazan o marcan como spam los emails de IPs nuevas sin historial), DKIM/SPF/DMARC/ARC, spam scoring entrante y saliente, listas negras (RBL/DNSBL — una IP residencial está casi garantizado en alguna), anti-relay, rate limiting, queue management, monitoring de bounces, complaints y FBL.
- **Descartado de plano por**: es trabajo full-time para un equipo de operaciones. Inaceptable para un equipo de dos personas con un piloto.

## Implicaciones operativas

- **Una cuenta Resend única, propiedad del equipo.** El acceso (email, contraseña, MFA) se documenta en el gestor de secretos del equipo (KeePassXC o equivalente). Nunca en repo Git.
- **El dominio `custodiam.es` se verifica una vez.** Los tres registros DNS (DKIM, MX `send`, SPF `send`) viven en Cloudflare DNS. La verificación es persistente; cambiar de proveedor SMTP en el futuro requiere reemplazar registros, no añadir más.
- **La API key es revocable.** Si se sospecha compromiso, regenerar la key en Resend, actualizar `docker/.env.sops`, redesplegar el stack. La cuenta Resend sigue intacta.
- **`docker/.env.sops` lleva dos variables nuevas**: `KEYCLOAK_SMTP_USERNAME` (= `resend`) y `KEYCLOAK_SMTP_PASSWORD` (= API key). La inyección al contenedor Keycloak se hace vía variables de entorno mapeadas en `docker-compose.yml`.
- **El `realm-custodiam.json` lleva la configuración no-secreta de SMTP** (host, port, starttls, from, replyTo). El contenedor sustituye username/password en arranque desde las variables de entorno.
- **Tracking deliberadamente OFF** en el dashboard de Resend para el dominio `custodiam.es`. Esto se documenta como parte de la configuración inicial del proveedor; el ratio de open/click no se monitoriza programáticamente en el MVP.
- **Bounce y complaint management**: Resend lleva el panel con bounces y complaints en su dashboard. Para MVP no se integra programáticamente — revisión manual periódica. Fases posteriores pueden integrar webhooks.

## Evolución a fases posteriores

Si en una fase futura se decide añadir **email como canal de notificación de la app** (preferencias por usuario, fallback automático cuando FCM/ntfy no entreguen, recordatorios programados), el volumen pasa de ~150 emails/año a potencialmente miles/día en escenarios multi-agrupación. Tres caminos:

1. **Resend plan pago** (~$20/mes por 50 000 emails) — camino más limpio si el volumen es predecible.
2. **Amazon SES directo** ($0.10/1000 emails) — camino preferente si el volumen es alto o variable. Requiere setup AWS + salir del sandbox. Coste marginal por email mínimo. Resend ya usa SES por debajo, así que la migración es lateral, no destructiva.
3. **Dividir transaccional vs notificación masiva** — Resend se queda con transaccional crítico (auth), SES asume notificación bulk. Patrón habitual en aplicaciones serias: separa "no puedes equivocarte" (auth) de "alto volumen" (notificación).

El cambio es trivial a nivel de Keycloak (sigue apuntando a Resend para transaccional). Lo que cambia es el segundo proveedor que el backend de `custodiam-api` use para notificaciones de la app. La arquitectura sin lock-in lo permite.

## Lección operativa derivada

Las ADRs son hipótesis hasta que se ejercitan operacionalmente. La primera implementación real con SMTP reveló en menos de cuatro horas una limitación del proveedor inicial (Brevo) que la documentación oficial no anunciaba y que la comunidad lleva años pidiendo sin éxito. El ciclo **Plan → Build → Discover → Adapt** se completó en una sola sesión, con esta ADR reescrita en vivo desde Brevo a Resend. La arquitectura provider-agnostic con placeholders en el realm hizo que el coste técnico de la migración fuera trivial (cambio de host + dos secretos + cinco registros DNS). El valor reside en haber dejado abierta la sustitución desde el primer diseño, no en haber acertado en la elección inicial.

## Referencias

- **[Resend — Pricing](https://resend.com/pricing)** y **[Send with SMTP](https://resend.com/docs/send-with-smtp)** — documentación oficial del free tier y del setup SMTP.
- **[Resend — Domains introduction](https://resend.com/docs/dashboard/domains/introduction)** — verificación de dominio con DKIM + SPF + DMARC.
- **[AWS SES — Regions and quotas](https://docs.aws.amazon.com/general/latest/gr/ses.html)** — backend que Resend utiliza por debajo.
- **[Cloudflare — Email Routing](https://developers.cloudflare.com/email-routing/)** — gestión del inbox `contacto@custodiam.es` (complementaria al SMTP de salida).
- **[Comunidad Brevo — hilo sobre tracking obligatorio](https://community.brevo.com/t/no-way-to-disable-by-option-tracking-in-transactional-e-mail/201)** — referencia que sostiene el argumento de descarte de la alternativa A.
- **[ADR-011 Deep links](adr-011-deep-links.md)** — los App Links / Universal Links exigen que los enlaces del cuerpo lleguen sin reescritura al móvil.
