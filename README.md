# Custodiam — Book de documentación pública

Documentación pública del proyecto **Custodiam**, sistema multiplataforma de gestión para agrupaciones de Protección Civil. Generada con **Material for MkDocs** y desplegada en GitHub Pages con dominio propio.

🌐 **Sitio publicado**: <https://docs.custodiam.es>

📚 **Fallback**: <https://custodiam.github.io/custodiam-book/>

## Stack

- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — engine + theme.
- [uv](https://docs.astral.sh/uv/) — package manager Python (mismo stack que `custodiam-api`).
- Plugins: `mkdocs-mermaid2-plugin` (sequences, state, flowcharts), `mkdocs-d2-plugin` (topologías y diagramas ER), `pymdown-extensions`, `mike` (versionado opcional).
- Hosting: GitHub Pages directo (branch `gh-pages`), dominio `docs.custodiam.es` vía CNAME en Cloudflare DNS modo *DNS only*.

## Requisitos para desarrollo local

- **uv** ≥ 0.9 — package manager Python. Instalación: <https://docs.astral.sh/uv/#installation>.
- **d2** 0.7.1+ — binario nativo invocado por `mkdocs-d2-plugin` durante el build. **Sin él, los diagramas D2 no se renderizan**. Instalación:
  - Windows: `winget install Terrastruct.D2` o `scoop install d2`.
  - macOS: `brew install d2`.
  - Linux: `curl -fsSL https://d2lang.com/install.sh | sh -s -- --version v0.7.1`.

El paquete Python `mkdocs-d2-plugin` se instala automáticamente con `uv sync`; el binario `d2` se gestiona aparte porque es nativo del sistema, no Python.

## Desarrollo local

```bash
# Sincronizar dependencias en .venv/
uv sync

# Servidor de desarrollo con hot reload (puerto 8000)
uv run mkdocs serve

# Build estático (output en site/)
uv run mkdocs build

# Build con modo estricto (falla si hay warnings — lo que usa el CI Linux)
uv run mkdocs build --strict
```

> **Gotcha 1**: si tu terminal hereda `VIRTUAL_ENV` de otro venv padre, `uv` lo respeta y no usa el `.venv/` local del repo. Solución: `unset VIRTUAL_ENV` antes de `uv sync`.
>
> **Gotcha 2 (Windows)**: `mkdocs build --strict` aborta localmente por un warning de `mkdocs-d2-plugin` que usa `\` en lugar de `/` en la ruta del CSS. El warning solo aparece en Windows; en el runner Linux del CI no ocurre. Usa `mkdocs build` (sin `--strict`) para desarrollo local en Windows.

## Estructura del repo

```text
custodiam-book/
├── docs/                       # Source markdown del book
│   ├── index.md                # Página de inicio
│   ├── empezar/                # Recorridos de instalación por repo
│   ├── arquitectura/           # Stack, diagramas, decisiones
│   ├── adrs/                   # Architecture Decision Records (curados)
│   ├── guias/                  # Guías técnicas (en proceso de publicación)
│   ├── contribuir/             # Cómo contribuir, código de conducta
│   ├── assets/                 # Logo, favicon, imágenes
│   ├── stylesheets/extra.css   # Overrides del theme (naranja PC)
│   └── CNAME                   # docs.custodiam.es
├── .github/workflows/
│   └── deploy.yml              # CI: build mkdocs + deploy a gh-pages
├── mkdocs.yml                  # Config del site (nav, theme, plugins)
├── pyproject.toml              # [project] PEP 621 + deps mkdocs
├── uv.lock                     # Lockfile reproducible
└── LICENSE                     # AGPL-3.0
```

## Despliegue

Cada push a `main` dispara el workflow `Deploy book` que:

1. Instala uv con cache habilitada.
2. Instala Python 3.13.
3. Ejecuta `uv sync --frozen`.
4. Construye con `uv run mkdocs build --strict`.
5. Empuja el `site/` resultante a la rama `gh-pages` con `peaceiris/actions-gh-pages@v4`.

GitHub Pages sirve directamente desde `gh-pages`. El `docs/CNAME` se preserva en cada build (mkdocs lo copia al output, peaceiris no lo elimina al hacer `force_orphan`).

## Contribuir

Ver [contribuir/index.md](docs/contribuir/index.md) en el book publicado.

## Licencia

Custodiam se distribuye bajo licencia [GNU Affero General Public License v3.0](./LICENSE). Los cuatro repositorios del proyecto usan la misma licencia.

## Repos relacionados

- [custodiam-app](https://github.com/custodiam/custodiam-app) — App Flutter (Android + iOS + Web)
- [custodiam-api](https://github.com/custodiam/custodiam-api) — Backend FastAPI + SQLModel
- [custodiam-infra](https://github.com/custodiam/custodiam-infra) — Docker Compose + Keycloak + scripts
