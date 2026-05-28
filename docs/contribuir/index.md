---
title: Contribuir
description: >-
  Cómo aportar al proyecto Custodiam — issues, pull requests, código de
  conducta y licencia.
---

# Contribuir

Custodiam es un proyecto open-source bajo licencia [AGPL-3.0](https://github.com/custodiam/custodiam-book/blob/main/LICENSE) que acepta contribuciones de la comunidad. Esta página describe cómo participar.

!!! info "Estado del proyecto"
    Custodiam está en desarrollo activo durante el curso académico 2025-2026 como Trabajo de Fin de Grado del ciclo DAM (Salesianos Zaragoza). Durante esta fase, las contribuciones externas se aceptan pero se priorizan las que alinean con el roadmap planificado. Tras el cierre del TFG (verano 2026), el proyecto pasará a mantenimiento abierto estándar.

## Tipos de contribución

<div class="grid cards" markdown>

- :material-bug: **Reportar bugs**

    Abre un issue en el repo correspondiente (`custodiam-app`, `custodiam-api`, `custodiam-infra`) describiendo el problema, los pasos para reproducirlo, lo esperado y lo observado. Incluye versión del software, sistema operativo y logs relevantes.

- :material-lightbulb-on: **Proponer features**

    Abre un issue de tipo *feature request*. Explica el caso de uso, el valor que aporta, y si tienes una propuesta de implementación. El equipo lo revisa antes de aprobar trabajo.

- :material-source-pull: **Pull Requests de código**

    Para cambios pequeños (typos, fixes obvios), abre directamente el PR. Para cambios mayores, abre primero un issue para alinearse en alcance antes de invertir tiempo en código.

- :material-book-edit: **Mejorar documentación**

    PR directos contra el repo `custodiam-book` (esta documentación) o contra los `README.md` de los repos de código. Cada página del book tiene un icono ✏️ en la esquina superior derecha que enlaza al archivo fuente en GitHub.

</div>

## Proceso de Pull Request

1. **Fork del repo** correspondiente.
2. **Rama** desde `develop` con nombre descriptivo (`feature/voluntario-baja`, `fix/auth-redirect`, etc.).
3. **Commits atómicos** con mensaje claro. Convencional (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
4. **Tests** que cubran el cambio. PR sin tests para código nuevo se devuelve.
5. **Lint y format** pasando localmente antes de pushear:
    - `custodiam-api`: `uv run ruff check && uv run ruff format`.
    - `custodiam-app`: `flutter analyze && dart format --set-exit-if-changed .`.
    - `custodiam-infra`: `docker compose ... config` valida YAML.
6. **PR contra `develop`** del repo afectado. Describe el cambio, el porqué, y vincula con issues si aplica.
7. **Review**: al menos 1 aprobación. Comentarios se atienden o se discuten.
8. **Merge a `develop`**. Las promociones a `main` las realiza el equipo en ciclos de release.

## Estilo de mensaje de commit

Convención **Conventional Commits**:

```text
<tipo>(<scope>): <descripción corta>

[opcional: cuerpo explicando el porqué]

[opcional: footer con BREAKING CHANGE o issues cerrados]
```

Tipos válidos:

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Solo cambios en documentación |
| `refactor` | Refactor sin cambio funcional |
| `test` | Añadir o corregir tests |
| `chore` | Tareas de mantenimiento (deps, CI, tooling) |
| `style` | Formato sin cambio de código (espacios, comas) |
| `perf` | Mejora de rendimiento |

Ejemplos:

```text
feat(auth): persist code_verifier in sessionStorage for web OAuth flow

fix(api): handle missing telefono in voluntario create payload

docs(book): add ADR-001 explaining polyrepo structure

chore(tooling): migrate to uv as package manager
```

## Licencia y propiedad intelectual

Todo el proyecto está bajo **GNU Affero General Public License v3.0** (AGPL-3.0). Esto significa:

- Puedes usar, modificar y distribuir el código.
- Si despliegas una versión modificada como servicio en red, debes publicar el código fuente modificado bajo la misma licencia.
- Cualquier contribución que aceptes hacer al proyecto se entiende bajo AGPL-3.0.

Al abrir un PR, confirmas que tienes derecho a contribuir ese código y que aceptas la licencia AGPL-3.0 para tu aportación.

## Código de conducta

Trato respetuoso, técnico y orientado al proyecto. Se aceptan discusiones técnicas vigorosas; no se aceptan ataques personales, lenguaje discriminatorio ni comportamientos disruptivos. El equipo se reserva el derecho de moderar comentarios y bloquear contribuidores que no respeten estas normas básicas.

## Contacto

- **Issues en cada repo** son la vía principal para reportar bugs y discutir cambios.
- **Discussions** (cuando se habiliten en cada repo) para preguntas abiertas y propuestas.
- Para temas que no encajen en ninguno de los anteriores, abre un issue genérico en este repo (`custodiam-book`).

Gracias por considerar contribuir al proyecto.
