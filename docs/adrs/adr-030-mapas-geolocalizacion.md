---
title: ADR-030 — Mapas y geolocalización con stack diferenciado por plataforma
description: >-
  El picker de ubicación y la apertura de ruta usan un stack distinto en móvil
  y en web para no pagar el paywall de Google Maps en web; la consistencia de
  la ubicación la garantiza el modelo de datos (coordenadas exactas), no el
  proveedor de teselas.
---

# ADR-030 — Mapas y geolocalización con stack diferenciado por plataforma

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 27 de mayo de 2026 |
| **Decisores** | Equipo Custodiam (Marcos Val Sanz, Rodrigo Mulero García) |

## Contexto

El módulo de Servicios necesita situar cada servicio en el espacio: elegir su ubicación sobre un mapa, verla y, en operativo, abrir la ruta hacia ella. Sobre ese mapa se apoyan tanto el coordinador que crea el servicio desde el ordenador como el voluntario que consume la ruta desde el móvil.

El obstáculo es de costes y de calidad a la vez. El *free tier* de Google Maps cubre únicamente los SDK nativos de Android e iOS; la **Maps JavaScript API**, necesaria para un mapa de Google en web, **se factura desde la primera carga**, fuera de cualquier capa gratuita. A la vez, un mapa de calidad insuficiente no sirve para uso operativo, donde la precisión de la ubicación es crítica. El reto es ofrecer un mapa de calidad en las tres plataformas sin incurrir en coste recurrente y garantizando que la ubicación elegida es **la misma** se vea donde se vea.

## Decisión

Adoptar un **stack diferenciado por plataforma**, unificado por el modelo de datos:

- **Mapa interactivo móvil** (Android, iOS): `google_maps_flutter` sobre el Maps SDK nativo, dentro del *free tier*.
- **Mapa interactivo web**: `flutter_map` con teselas de **CARTO** (estilo *Voyager*), sin clave ni facturación.
- **Posición del usuario**: `geolocator` (móvil y web), leída solo bajo demanda.
- **Geocodificación inversa** (coordenada → dirección legible): geocodificador nativo del sistema operativo en móvil; **Nominatim** (servicio público de OpenStreetMap) en web.
- **Apertura de ruta**: enlace universal de mapas abierto con `url_launcher`, que delega en la app de mapas del dispositivo (solo móvil; en escritorio la acción se limita a "ver en el mapa").

La pieza que hace coherente todo el conjunto es el **modelo de datos**: la ubicación se persiste siempre como **coordenadas exactas** (latitud y longitud) más una etiqueta de texto legible. La coordenada es la fuente de verdad; la etiqueta es una conveniencia humana. Así, un servicio ubicado desde la web y consultado desde el móvil aparece exactamente en el mismo punto, aunque las teselas las sirva un proveedor distinto en cada plataforma.

En el cliente, las dos implementaciones de mapa se seleccionan por **importación condicional** y nunca conviven en tiempo de ejecución; el resto de la aplicación dialoga con un tipo de coordenada neutro y no importa ningún paquete de mapas directamente. La clave de API de los SDK móviles, que por naturaleza viaja dentro del binario, se protege mediante **restricción en la consola de Google Cloud** (por nombre de paquete y huella del certificado en Android, por identificador de *bundle* en iOS) y se gestiona cifrada con la misma cadena `sops` + `age` que el resto de secretos del proyecto (ver [ADR-019](adr-019-sops-age.md)).

## Justificación

1. **Elimina el coste recurrente sin sacrificar calidad.** El único punto de pago —la Maps JavaScript API en web— se evita por completo sustituyéndolo por teselas CARTO gratuitas, mientras el móvil conserva la cartografía de Google dentro del *free tier*. El gasto cloud previsible es nulo para el volumen del proyecto.

2. **La consistencia vive en el dato, no en el proveedor.** Al guardar siempre la coordenada exacta, la diferencia de teselas entre plataformas es puramente estética: el punto representado es idéntico. Esto desacopla la corrección funcional de la elección de proveedor y permite cambiar de proveedor de teselas en el futuro sin migrar dato alguno.

3. **La importación condicional desacopla las dependencias.** Cada plataforma carga solo su implementación de mapa; los paquetes de móvil y de web no se cruzan en el árbol de compilación ni en runtime, y el código de dominio permanece agnóstico al hablar un tipo de coordenada propio. Esto evita además que un paquete pensado para web rompa la compilación de las pruebas en la máquina virtual de Dart.

4. **Lock-in acotado y reversible.** CARTO y Nominatim se asientan sobre datos de OpenStreetMap y son sustituibles por otros proveedores equivalentes; la dependencia de Google se limita al móvil y se mantiene dentro de su capa gratuita. No hay un proveedor único cuyo cambio obligue a rehacer la integración entera.

5. **La clave de cliente se protege por restricción, no por secreto.** Una clave de Maps SDK es extraíble del binario distribuido por diseño; su seguridad real es la restricción por aplicación en la consola cloud. Cifrarla con `sops` + `age` no la "oculta", sino que mantiene el repositorio público sin credenciales en claro y resuelve el reparto de secretos en el equipo con el mismo mecanismo ya adoptado para el resto.

## Alternativas evaluadas y descartadas

### A. Google Maps en todas las plataformas, incluida la web

Usar el ecosistema de Google de extremo a extremo, con la Maps JavaScript API para el mapa web.

- **Pros**: un único proveedor, una sola curva de aprendizaje, estilo cartográfico homogéneo.
- **Contras**: la Maps JavaScript API se factura desde la primera carga; introduce un coste recurrente y la necesidad de vigilar cuotas y facturación para una funcionalidad que en web es de baja intensidad.
- **Descartado por**: coste recurrente inaceptable para el proyecto frente a una alternativa web gratuita de calidad equivalente.

### B. OpenStreetMap "puro" en todas las plataformas

Renunciar a Google también en móvil y usar teselas OSM directas en las tres plataformas.

- **Pros**: un solo stack, sin clave, sin facturación en ningún sitio.
- **Contras**: la calidad cartográfica y de búsqueda de las teselas OSM directas resultó insuficiente para uso operativo, donde la precisión y la legibilidad del mapa son críticas.
- **Descartado por**: calidad cartográfica insuficiente para el caso de uso de intervención.

### C. Proveedor único multiplataforma con capa gratuita (Mapbox, MapTiler, HERE)

Unificar con un proveedor que ofrezca *free tier* en móvil y web a la vez.

- **Pros**: un solo proveedor para las tres plataformas, sin la asimetría del stack diferenciado.
- **Contras**: añade una dependencia y una clave más que gestionar y vigilar, cuando el stack diferenciado ya cubre todas las plataformas sin coste; el *free tier* de estos proveedores también tiene límites que habría que monitorizar.
- **Descartado por**: no aporta sobre el stack diferenciado y suma superficie de gestión. Queda anotado como plan B si la asimetría diera fricción.

## Implicaciones operativas

- **Configuración nativa.** Android exige nivel de API mínimo 24 (requisito del Maps SDK) y el permiso de ubicación "en uso"; iOS declara el propósito de uso de la ubicación. El acceso a la ubicación se solicita únicamente al abrir el mapa o la ruta, **nunca en segundo plano**, en línea con la minimización de datos personales.
- **Gestión de la clave.** La clave de Maps se cifra con `sops` + `age` y se descifra a archivos locales ignorados por el control de versiones en un único paso de preparación del entorno; las compilaciones de desarrollo no cambian. La clave debe quedar **restringida** en la consola cloud por aplicación. Con firma gestionada por la tienda, la huella a registrar es la del certificado de la tienda, no la de desarrollo, o el mapa no cargará en la versión publicada.
- **Geocodificación inversa de mejor esfuerzo.** Si la sugerencia de dirección falla (sin red, tiempo de espera agotado, sin punto de interés, límite de peticiones), la coordenada se conserva y el flujo no se bloquea: el usuario siempre puede escribir la dirección a mano.
- **Accesibilidad.** El campo de texto de la ubicación es una alternativa no cartográfica siempre válida: se puede crear un servicio sin abrir el mapa. La sugerencia de dirección se anuncia a los lectores de pantalla. El lienzo del mapa, opaco a la inspección de accesibilidad, no se somete a las comprobaciones automáticas de contraste; se cubre con una alternativa textual.
- **Pruebas.** El render del mapa y la lectura de posición son dependientes de plataforma y no se prueban directamente; se sustituyen por dobles en la capa de lógica, donde sí se prueban la construcción de las URL de geocodificación y de ruta y el flujo de sugerencias.

## Referencias

- **[ADR-019 — Gestión de secretos con sops + age](adr-019-sops-age.md)** — cadena de cifrado con la que se gestiona la clave de Maps.
- **[google_maps_flutter](https://pub.dev/packages/google_maps_flutter)** — mapa interactivo en móvil.
- **[flutter_map](https://pub.dev/packages/flutter_map)** — mapa interactivo en web.
- **[CARTO basemaps](https://carto.com/basemaps)** — teselas usadas en web.
- **[Nominatim](https://nominatim.org/)** — geocodificación inversa en web sobre OpenStreetMap.
- **[geolocator](https://pub.dev/packages/geolocator)** — lectura de la posición del usuario.
