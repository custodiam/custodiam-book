"""Hook MkDocs: auto-linkea términos del glosario en cada página.

Lee los términos de docs/glosario.md al arranque (headings H3 con
anchor explícito `### Término { #slug }`) y, en cada página, sustituye
TODAS las ocurrencias de cada término por un enlace al glosario con
clase CSS `glossary-term`.

Todo el reemplazo se hace en un único pase con un patrón regex con
alternancia (ordenada por longitud descendente para que los términos
largos ganen frente a los cortos que serían subcadena). Esto evita el
problema de sustituciones en cascada donde un reemplazo previo
introduce texto que mataría con un término posterior.

Bloques protegidos (no se tocan): code fenced, inline code, links
existentes, imágenes, attribute lists, frontmatter, headings, snippet
includes y definiciones de abreviatura.
"""

from __future__ import annotations

import re
from pathlib import Path

_HEADING_RE = re.compile(
    r"^###\s+(.+?)\s*\{\s*#([\w.-]+)\s*\}\s*$",
    re.MULTILINE,
)

_PROTECT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"```.*?```", re.DOTALL),
    re.compile(r"~~~.*?~~~", re.DOTALL),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"\[[^\]]*\]\([^)]*\)"),
    re.compile(r"\[[^\]]*\]\[[^\]]*\]"),
    re.compile(r"\{[^}\n]*\}"),
    re.compile(r"^---\n.*?\n---", re.DOTALL),
    re.compile(r"^#{1,6}\s.*$", re.MULTILINE),
    re.compile(r"^--8<--.*$", re.MULTILINE),
    re.compile(r"^\*\[[^\]]+\]:[^\n]*$", re.MULTILINE),
]

_SKIP_PAGES: frozenset[str] = frozenset({"glosario.md"})

_terms_cache: list[tuple[str, str]] | None = None
_pattern_cache: re.Pattern[str] | None = None
_anchor_map_cache: dict[str, str] | None = None


def _load_terms(docs_dir: Path) -> list[tuple[str, str]]:
    glossary = docs_dir / "glosario.md"
    if not glossary.exists():
        return []
    content = glossary.read_text(encoding="utf-8")
    pairs = [
        (m.group(1).strip(), m.group(2).strip())
        for m in _HEADING_RE.finditer(content)
    ]
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def _build_pattern(terms: list[tuple[str, str]]) -> re.Pattern[str]:
    alternation = "|".join(re.escape(t) for t, _ in terms)
    return re.compile(
        rf"(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])"
    )


_PLACEHOLDER_FMT = "zzGLOSARIOPROTECTzz{idx}zz"
_PLACEHOLDER_RE = re.compile(r"zzGLOSARIOPROTECTzz(\d+)zz")


def _protect(text: str) -> tuple[str, list[str]]:
    placeholders: list[str] = []

    def repl(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return _PLACEHOLDER_FMT.format(idx=len(placeholders) - 1)

    out = text
    for pat in _PROTECT_PATTERNS:
        out = pat.sub(repl, out)
    return out, placeholders


def _restore(text: str, placeholders: list[str]) -> str:
    out = text
    for _ in range(10):
        if not _PLACEHOLDER_RE.search(out):
            return out
        out = _PLACEHOLDER_RE.sub(
            lambda m: placeholders[int(m.group(1))], out
        )
    return out


def _relative_glossary_url(src_path: str) -> str:
    depth = len(Path(src_path).parent.parts)
    return ("../" * depth) + "glosario.md" if depth else "glosario.md"


def on_page_markdown(markdown: str, *, page, config, files) -> str:
    global _terms_cache, _pattern_cache, _anchor_map_cache

    src = page.file.src_path.replace("\\", "/")
    if src in _SKIP_PAGES:
        return markdown

    if _terms_cache is None:
        _terms_cache = _load_terms(Path(config["docs_dir"]))
        _pattern_cache = (
            _build_pattern(_terms_cache) if _terms_cache else None
        )
        _anchor_map_cache = (
            dict(_terms_cache) if _terms_cache else {}
        )

    if not _terms_cache or _pattern_cache is None:
        return markdown

    protected, placeholders = _protect(markdown)
    glossary_url = _relative_glossary_url(src)
    anchor_map = _anchor_map_cache or {}

    def replace_fn(match: re.Match[str]) -> str:
        term = match.group(0)
        anchor = anchor_map.get(term)
        if anchor is None:
            return term
        return (
            f"[{term}]({glossary_url}#{anchor})"
            "{.glossary-term}"
        )

    replaced = _pattern_cache.sub(replace_fn, protected)
    return _restore(replaced, placeholders)
