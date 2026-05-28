---
title: ADR-026 — uv como gestor de paquetes Python
description: >-
  custodiam-api adopta uv (Astral) como package y project manager Python,
  reemplazando pip + venv + requirements.txt por pyproject.toml PEP 621 +
  uv.lock + Python 3.13 gestionado automáticamente.
---

# ADR-026 — uv como gestor de paquetes Python

| Campo | Valor |
|---|---|
| **Estado** | Aceptado |
| **Fecha** | 24 de mayo de 2026 |
| **Decisores** | Equipo Custodiam |

## Contexto

Al arrancar la sesión de implementación del módulo de voluntarios, el `venv` local del repo `custodiam-api` apareció roto: `pyvenv.cfg` apuntaba a `Python 3.14.2` cuyo `python.exe` ya no existía en el sistema (la carpeta `Programs/Python314/` se había borrado parcialmente, sin runtime, aunque conservaba `Scripts/`). El equipo había instalado Python 3.13.13 sobre la marcha pero el venv del repo no se había recreado.

La situación expuso dos cuestiones acumuladas:

1. **Versionado de Python**: el proyecto declaraba `>=3.11` en `pyproject.toml` pero la máquina había estado usando 3.14 hasta su desinstalación accidental. La elección concreta nunca se documentó.
2. **Tooling Python**: el repo seguía con el patrón clásico `pip install -r requirements.txt` + `venv` + lockfile manual. Sin reproducibilidad determinista, sin gestión automática de Python, sin paralelismo. Tiempos de `pip install` en CI ~45 s y en local ~30 s.

La propuesta surgió natural: aprovechar el "tengo que recrear el venv de todos modos" para evaluar **uv** (Astral, escrito en Rust), el package manager Python moderno que en 2026 se ha establecido como estándar de facto en proyectos nuevos. La oportunidad encaja con el principio del proyecto de decisiones tomadas al detectar oportunidad durante una sesión de implementación, no por modernización porque sí.

## Decisión

Adoptar **[uv](https://docs.astral.sh/uv/) 0.9+** como package manager y project manager de `custodiam-api`:

- **Declaración de dependencias**: migrar de `requirements.txt` a `pyproject.toml` `[project]` ([PEP 621](https://peps.python.org/pep-0621/)), con extras opcionales en `[project.optional-dependencies.dev]` (`pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`).
- **Lockfile reproducible**: `uv.lock` versionado en el repo. Resuelve transitive deps a hashes exactos para reproducibilidad bit-a-bit entre máquinas.
- **Build backend**: `hatchling` declarado en `[build-system]` para permitir `uv pip install -e .` cuando sea útil.
- **Comandos**: `uv sync` (instala/sincroniza el `.venv/` con el lockfile), `uv run <cmd>` (ejecuta comandos sin activación manual), `uv add <paquete>` (añade dep y actualiza lockfile). El `.venv/` vive en el repo (`gitignored`).
- **Versión Python**: **3.13 estable** como versión del equipo. uv descarga e instala Python 3.13 automáticamente si no está disponible (`uv python install 3.13`), evitando incidencias futuras del estilo "el venv apunta a un Python que ya no existe".
- **CI**: GitHub Actions usa `astral-sh/setup-uv@v8` con cache habilitado, ejecuta `uv sync --frozen` (no resuelve versiones nuevas en CI) y luego `uv run pytest` / `uv run ruff check`.
- **Docker**: multi-stage con imagen `ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim` como builder y `python:3.13-slim-bookworm` como runtime (sin uv, solo el `.venv/` copiado). Layer cache más eficiente con `uv sync --no-install-project` antes de copiar `app/`.

`requirements.txt` queda eliminado del repo: las deps viven solo en `pyproject.toml`.

## Justificación

1. **Velocidad operativa medible.** `uv sync --frozen` toma ~3 ms (auditoría de paquetes ya en lockfile) frente a ~30 s de `pip install -r requirements.txt`. Instalación inicial sin cache: ~1 s vs ~30 s. En CI con cache habilitado, el ahorro acumulado por workflow es ~25–40 s, multiplicado por cada PR.

2. **Reproducibilidad exacta.** `uv.lock` versionado garantiza que el conjunto de dependencias instalado en local, CI y Docker es bit-a-bit idéntico. Con `requirements.txt` el equipo dependía de constraints "best-effort" (`>=`) y el resolutor podía elegir versiones diferentes en cada `pip install`. El incidente que motivó esta ADR es un ejemplo.

3. **Gestión automática de Python.** uv descarga e instala intérpretes Python on-demand (`uv python install 3.13`) en una caché global (`~/.local/share/uv/python/`). Esto desacopla el venv del Python del sistema operativo. Si el equipo desinstala Python por error, uv puede reinstalarlo automáticamente al siguiente `uv sync`. El incidente del venv roto **no habría ocurrido con uv ya adoptado**.

4. **Estandarización PEP 621.** `pyproject.toml` con `[project]` es el estándar oficial de Python desde 2022. El proyecto se alinea con la dirección oficial del ecosistema, lo que facilita interoperar con otras herramientas modernas sin configuración paralela.

5. **Coherencia con stack del book.** El sitio público (este book de documentación) también usa Material for MkDocs vía uv + `pyproject.toml` ([ADR-027](adr-027-mkdocs-pages.md)). La misma toolchain Python sirve para backend y documentación pública.

## Alternativas evaluadas y descartadas

### A. Pip + venv tradicional + requirements.txt manual

- **Pros**: cero curva, soporte universal.
- **Contras**: resoluciones lentas, lockfile manual vía `pip-compile` separado, sin gestión de Python, deuda persistente del estilo "venv apuntando a Python desinstalado".
- **Descartado por**: ROI de mantener pip+venv solo por familiaridad no compensa el coste operativo del incidente que motivó esta ADR.

### B. Poetry

- **Pros**: lockfile reproducible (`poetry.lock`), gestión de venv, estándar pre-uv (2018–2023).
- **Contras**: resoluciones lentas en proyectos grandes (SAT solver Python puro; uv usa PubGrub en Rust ~10–100× más rápido); `pyproject.toml` con `[tool.poetry.dependencies]` no es PEP 621 (formato propio); gestión de Python limitada.
- **Descartado por**: velocidad y por no ser PEP 621 nativo.

### C. PDM

- **Pros**: PEP 621 nativo, lockfile, gestión de Python opcional.
- **Contras**: comunidad ~10× menor que uv en 2026; ecosistema CI/Docker menos desarrollado; futuro incierto al consolidarse uv como estándar.
- **Descartado por**: viabilidad a largo plazo.

### D. Pipenv

- **Pros**: histórico, sintaxis simple con `Pipfile`.
- **Contras**: deprecado en la práctica, sin mantenimiento activo, lockfile con problemas conocidos.
- **Descartado por**: estado upstream.

### E. Hatch como project manager

- **Pros**: oficial PyPA, build backend Hatchling es referencia.
- **Contras**: UX menos pulida que uv como project manager, no resuelve deps tan rápido, gestión de entornos prolija.
- **Descartado como project manager**; **aceptado como build backend** (`[build-system].requires = ["hatchling"]`).

### F. Conda / Mamba

- **Pros**: gestiona binarios no-Python.
- **Contras**: overkill para un servicio web FastAPI; ecosistema no alineado con PyPI puro.
- **Descartado por**: no encaja con el dominio.

### G. Rye

- **Pros**: ergonómico, autogestión de Python, lockfile.
- **Contras**: el proyecto se fusionó con uv en 2024 — Rye es alias de uv con UX menos pulida.
- **Descartado por**: convergencia con uv.

## Implicaciones operativas

- **Onboarding del equipo**: única instrucción nueva es instalar uv (`curl -LsSf https://astral.sh/uv/install.sh | sh` en Unix/macOS, instalador `.msi` en Windows). El resto del workflow (`uv sync`, `uv run pytest`) es intuitivo para quien venía de pip + venv.
- **Gotcha conocida**: `VIRTUAL_ENV` heredado de otro venv activo hace que uv use ese venv en lugar del `.venv/` local. Documentado en `CLAUDE.md` del repo. Solución: `unset VIRTUAL_ENV` al cambiar de proyecto.
- **CI más rápido**: con `astral-sh/setup-uv` + `enable-cache: true`, los siguientes runs en la misma rama reutilizan el cache de uv. Reducción típica: 30 → 5 segundos en el step "Install dependencies".
- **Imagen Docker más pequeña**: multi-stage con builder uv + runtime slim. La imagen final NO incluye uv (~30 MB ahorrados respecto a tener uv en runtime), solo el `.venv/` resuelto.
- **Eliminación de `requirements.txt`**: ya no existe. Cualquier referencia externa (Dockerfile, CI workflow, guías de setup) actualizada en el mismo PR de migración.

## Patrón derivado aplicable a otros repos

uv se establece como **herramienta canónica del proyecto para Python** desde esta ADR. Afecta a:

- **`custodiam-api`**: adopción completa (sujeto de esta ADR).
- **`custodiam-book`**: ya nace con uv ([ADR-027](adr-027-mkdocs-pages.md)).
- **`custodiam-infra`**: si en algún momento hay scripts Python operativos, se ejecutan con `uv run` o se declaran como standalone con [PEP 723](https://peps.python.org/pep-0723/).
- **`custodiam-app`**: **no aplica** (proyecto Flutter, no Python).

Patrón derivado para futuros proyectos Python del ecosistema Custodiam: **PEP 621 + uv + lockfile versionado** como baseline. Cualquier decisión contraria requeriría una nueva ADR.

## Referencias

- **[uv documentation](https://docs.astral.sh/uv/)** — guía oficial completa.
- **[PEP 621 — Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)** — estándar oficial del formato `[project]`.
- **[PEP 631 — Dependency specification in pyproject.toml](https://peps.python.org/pep-0631/)** — formato de dependencias.
- **[PEP 723 — Inline script metadata](https://peps.python.org/pep-0723/)** — scripts standalone con metadata inline.
- **[GitHub Actions setup-uv](https://github.com/astral-sh/setup-uv)** — action oficial.
- **[Imágenes Docker uv](https://github.com/astral-sh/uv/pkgs/container/uv)** — imágenes mantenidas con uv + Python pre-instalados.
- **[ADR-002 SQLModel](adr-002-sqlmodel.md)** y **[ADR-010 OAuth + PyJWT](adr-010-oauth-pkce-keycloak.md)** — decisiones que se reflejan ahora como entradas de `pyproject.toml`.
