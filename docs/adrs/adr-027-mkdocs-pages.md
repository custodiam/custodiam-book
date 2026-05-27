---
title: ADR-027 — Material for MkDocs + GitHub Pages para el book
description: >-
  La documentación pública de Custodiam vive en un repo separado custodiam-book
  con Material for MkDocs, hosted en GitHub Pages directo, dominio docs.custodiam.es
  vía Cloudflare DNS modo DNS only. Solo español en F1.
---

# ADR-027 — Material for MkDocs + GitHub Pages para el book

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 26 de mayo de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

Custodiam es un proyecto **abierto al mundo** bajo licencia AGPL-3.0. El código vive en tres repositorios públicos (`custodiam-app`, `custodiam-api`, `custodiam-infra`) y un repositorio **privado** de documentación interna que alberga el material conceptual, las guías técnicas detalladas, el backlog operativo y el material académico del TFG. Al cierre del Sprint 4 el privado había acumulado:

- 27 ADRs arquitectónicos.
- ~28 guías técnicas numeradas.
- 10 documentos conceptuales versionados.
- Backlog estructurado (epics, user stories, enablers, spikes, seguimiento).
- Diagramas Mermaid.
- Material académico del TFG (memoria, lecciones operativas).

El problema operativo es triple:

1. **Visibilidad**: como proyecto open-source AGPL-3.0, Custodiam debe ofrecer documentación pública accesible a contributors, otras agrupaciones de Protección Civil, evaluadores académicos y comunidad técnica. Los `README.md` de los tres repos de código son insuficientes (~40–100 líneas cada uno; no cubren arquitectura, decisiones, ni guías de instalación detalladas).
2. **Frontera público/privado**: el material privado mezcla "explicación técnica reutilizable" (apta para público) con "narrativa interna" (TFG, backlog operativo, lecciones con info sensible). Una publicación automática del privado al público filtraría material no apto.
3. **Navegabilidad**: leer 28 guías + 27 ADRs + 10 conceptuales en bruto en GitHub es UX pobre — sin búsqueda full-text, sin sidebar, sin vinculación cruzada visual.

## Decisión

Sistema de documentación pública implementado como **book con Material for MkDocs en repo separado público, hosted en GitHub Pages directo, dominio propio gestionado vía Cloudflare DNS en modo `DNS only`, contenido únicamente en español durante F1**.

Materialización:

- **Nuevo repositorio público** [`custodiam-book`](https://github.com/custodiam/custodiam-book) bajo la organización GitHub `custodiam`, licenciado AGPL-3.0 (consistente con el resto). Vida independiente: ciclo de releases propio, versionado `mike` instalado pero no activado en F1.
- **Stack del book**: Material for MkDocs (Squidfunk), instalado vía uv como project Python (`pyproject.toml` PEP 621 + `uv.lock`, [ADR-026](adr-026-uv.md)). Plugins activos: `pymdown-extensions` (admonitions, tabs, footnotes), `mkdocs-mermaid2-plugin` (Mermaid nativo), `mike` (instalado, sin activar).
- **Theme personalizado**: paleta `primary: deep orange` con tinte concreto `#FF6600` (escudo Protección Civil), accent `blue grey`, modo claro/oscuro con toggle, tipografía Roboto + Roboto Mono.
- **Idioma**: **solo español** en F1. Inglés diferido a F3 con plugin `mkdocs-static-i18n` si aplica. Cliente piloto, equipo y contributors esperados son habla hispana.
- **Hosting**: **GitHub Pages directo en la rama `gh-pages` autogenerada por workflow CI**. El contenido HTML estático se sirve desde el mismo proveedor donde vive el código fuente. Sin intermediarios.
- **Dominio público**: `docs.custodiam.es` configurado vía CNAME en Cloudflare DNS apuntando a `custodiam.github.io`. **Modo `DNS only`** (proxy desactivado) en F1: Cloudflare actúa exclusivamente como resolutor DNS, sin interceptar tráfico.
- **CI**: GitHub Actions con `astral-sh/setup-uv@v8` + cache habilitado, `uv sync --all-extras --frozen`, `mkdocs build` y deploy con `peaceiris/actions-gh-pages@v4` al branch `gh-pages`. Disparado en cada push a `main`.
- **HTTPS**: certificado Let's Encrypt automático emitido por GitHub Pages al añadir el custom domain. "Enforce HTTPS" activado.

## Justificación

1. **Resiliencia operativa vendor-lock-free.** Al elegir GitHub Pages como hosting (en lugar de Cloudflare Pages, primera idea), el contenido vive en el mismo proveedor que el código fuente. Si Cloudflare desaparece o se decide migrar el DNS a otro registrar (Namecheap, Route 53, BIND propio), el sitio sigue funcionando en `custodiam.github.io/custodiam-book/` sin downtime — solo se pierde el dominio "bonito". Patrón estándar en open source serio: [Vue](https://vuejs.org), [Vite](https://vitejs.dev), [FastAPI](https://fastapi.tiangolo.com), [Pydantic](https://pydantic.dev), [MkDocs](https://www.mkdocs.org), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), [Rust Book](https://doc.rust-lang.org/book/) — todos hosted en GitHub Pages con custom domain.

2. **Coherencia con stack del proyecto.** Material for MkDocs se instala vía Python + uv ([ADR-026](adr-026-uv.md)). Añadir mdBook (descartado) habría supuesto introducir toolchain Rust (`cargo install mdbook`) sin razón funcional. El stack del book es **extensión natural** del stack del backend.

3. **Mermaid nativo + admonitions ricos.** El repo privado contiene numerosos diagramas Mermaid y las guías técnicas usan intensivamente el patrón `> Nota:`, `> Warning:`, `> Gotcha:`. Material renderiza Mermaid sin configuración (`mkdocs-mermaid2-plugin`) y los admonitions de PyMdown Extensions (`!!! note`, `!!! warning`, `!!! tip`, `!!! danger`) producen UX muy superior a blockquotes planos. mdBook necesita `mdbook-mermaid` separado y los admonitions son HTML manual.

4. **Frontera público/privado preservada.** El repo privado sigue siendo fuente de verdad **interna** para el equipo (TFG, backlog operativo, lecciones con info sensible). El book público es **vista curada**: solo se publica contenido cuando una ADR o guía está madura y revisada. **Sync manual y controlado**, no automático. Ningún script roba material no apto del privado al público accidentalmente.

5. **Vendor-lock-free como principio defendible.** La elección concreta es defendible públicamente: GitHub Pages sobre Cloudflare Pages se defiende con el principio de **"el contenido vive donde vive el código"**. El toggle `Proxied` reversible en Cloudflare DNS permite añadir CDN encima del hosting en F2/F3 si el tráfico real justifica las ventajas (analytics, performance global, WAF). Patrón "arquitectura emergente disciplinada": empezar con setup más simple y resiliente, mejorar con un toggle cuando haya datos que lo justifiquen.

## Alternativas evaluadas y descartadas

### A. mdBook (Rust)

- **Pros**: configuración minimalista (`book.toml` ~10 líneas), performance build excelente (~1–2 s), look "libro académico", lo usan proyectos respetables (Rust Book, just, Lapce, Tauri).
- **Contras**: añade toolchain Rust al stack; Mermaid no es nativo (requiere `mdbook-mermaid`); admonitions tampoco (HTML manual); sin versionado nativo; sin tabs de código.
- **Descartado por**: incoherencia con stack del proyecto (ya usamos Python + uv) y ausencia de features clave que Material trae built-in.

### B. Docusaurus (Meta, React + MDX)

- **Pros**: muy potente, versionado built-in, traducciones, blog integrado, search Algolia.
- **Contras**: overkill para equipo de dos personas; React + MDX no es coherente con stack del proyecto; configuración compleja; curva de aprendizaje alta.
- **Descartado por**: complejidad sin retorno proporcional al tamaño del equipo.

### C. VitePress (Vue)

- **Pros**: moderno, performance excelente, theme limpio.
- **Contras**: curva Vue innecesaria; ecosistema Vue ausente en el resto del proyecto.
- **Descartado por**: alternativa Material cubre las mismas necesidades sin curva nueva.

### D. Sphinx + Read the Docs

- **Pros**: estándar histórico Python (numpy, scipy, scikit-learn, pytest); hosting gratuito en Read the Docs.
- **Contras**: RST como formato por defecto (Markdown vía MyST como afterthought); look anticuado comparado con Material; configuración rígida (`conf.py` Python); Read the Docs limita customización.
- **Descartado por**: experiencia de escritura inferior y look menos defendible.

### E. GitBook hosted

- **Pros**: WYSIWYG, hosting incluido, free tier para open source.
- **Contras**: dependencia de proveedor comercial; menos control sobre theme y estructura; lock-in al editor.
- **Descartado por**: principio open source de auto-hosting.

### F. Antora (Asciidoc, multi-repo)

- **Pros**: orientado a docs distribuidas en múltiples repos.
- **Contras**: Asciidoc no es Markdown estándar; orientado a docs enterprise grandes (Red Hat).
- **Descartado por**: complejidad operativa desproporcionada.

### G. Cloudflare Pages como hosting primario

- **Pros**: CDN global integrado, analytics built-in, edge functions.
- **Contras**: dependencia de proveedor adicional además de GitHub; si Cloudflare cae, el sitio cae completamente; el contenido se separa físicamente del código fuente (vendor split).
- **Descartado como hosting primario, reservado como CDN opcional futuro.** Toggle `Proxied` reversible permite añadir Cloudflare CDN encima del hosting GitHub Pages en F2/F3 si los datos lo justifican.

### H. Bilingüe completo ES + EN desde F1

- **Pros**: profesional, internacional.
- **Contras**: 2× esfuerzo permanente de escritura y mantenimiento; el público realista de Custodiam en F1 es habla hispana.
- **Descartado en F1**, puerta abierta para F3 vía `mkdocs-static-i18n`.

## Implicaciones operativas

- **Coste de mantenimiento**: cada vez que una ADR o guía del privado madura, copia manual al book público con revisión de qué se publica. Ritmo natural ~1–2 documentos por sprint cerrado.
- **Operación local**: `cd custodiam-book && uv sync --all-extras --frozen && mkdocs serve` para preview en `localhost:8000`; push a `main` dispara el workflow CI que regenera `gh-pages` automáticamente.
- **CNAME**: el archivo `docs/CNAME` con contenido `docs.custodiam.es` debe persistir en cada build (el workflow lo preserva al copiar `site/`). Si se pierde, GitHub Pages deja de servir en el dominio custom.
- **DNS Cloudflare**: registro CNAME `docs` → `custodiam.github.io` configurado en modo `DNS only` (proxy gris). Cambio a `Proxied` (naranja) reversible cuando se decida añadir CDN.
- **READMEs minimalistas**: tras publicar el book, los `README.md` de los tres repos de código se reescriben ligeros (~60–80 líneas cada uno) apuntando al book como referencia principal. Patrón clásico: el README cubre instalación rápida + enlace a docs completas.
- **Acceso antes de que DNS propague**: durante el bootstrap inicial, el book está accesible en `https://custodiam.github.io/custodiam-book/`. La URL `docs.custodiam.es` empieza a funcionar tras propagación DNS (~5–30 min) y emisión de cert Let's Encrypt (~10–60 min adicionales).

## Patrones derivados aplicables a futuras decisiones

ADR-027 establece dos principios de proyecto:

1. **Hosting principal en el mismo proveedor que el código fuente**, dominio propio como capa redirigible vía DNS. Aplicable también a futuros sitios complementarios (landing page del producto, dashboard de demo) si los hubiera.
2. **Frontera público/privado documental explícita**: material académico/operativo en repo privado, material reutilizable en repo público con sync manual. Evita filtraciones accidentales.

## Referencias

- **[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)** — sitio oficial.
- **[MkDocs](https://www.mkdocs.org/)** — engine subyacente.
- **[GitHub Pages — Custom Domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)** — guía oficial para CNAME + DNS + HTTPS.
- **[peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)** — action oficial para deploy a `gh-pages`.
- **[mkdocs-mermaid2-plugin](https://github.com/fralau/mkdocs-mermaid2-plugin)** — renderizado Mermaid nativo.
- **[PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/)** — admonitions, tabs, footnotes.
- **[mike](https://github.com/jimporter/mike)** — versionado de docs MkDocs.
- **[Cloudflare DNS — Proxy status](https://developers.cloudflare.com/dns/manage-dns-records/reference/proxied-dns-records/)** — diferencia entre modos DNS only y Proxied.
- **[ADR-026 uv](adr-026-uv.md)** — toolchain Python compartida.
