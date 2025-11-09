# app/render.py
"""
Template rendering: thin Jinja2 wrapper for MD/TXT/YAML outputs.

Design:
- StrictUndefined -> fail fast on missing variables.
- No autoescape (outputs are not HTML).
- Whitespace control for clean Markdown/YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

# Project templates directory (…/templates)
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

# Jinja environment, tuned for prose (MD/TXT/YAML)
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,            # not rendering HTML
    trim_blocks=True,            # nicer whitespace
    lstrip_blocks=True,          # strip leading spaces before blocks
    undefined=StrictUndefined,   # fail fast on missing keys
)

__all__ = ["render_template", "render_to_file", "TEMPLATES_DIR"]


def render_template(name: str, **ctx: Any) -> str:
    """
    Render a template by name with context.

    Raises:
        FileNotFoundError: if the template does not exist.
        Exception: jinja will raise with a helpful message on missing vars.
    """
    try:
        tpl = env.get_template(name)
    except TemplateNotFound as ex:
        raise FileNotFoundError(f"Template not found: {name} in {TEMPLATES_DIR}") from ex
    return tpl.render(**ctx)


def render_to_file(name: str, out_path: str | Path, **ctx: Any) -> Path:
    """
    Render a template and write to a file (UTF-8, newline LF).

    Returns:
        Path to the written file.
    """
    output = render_template(name, **ctx)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8", newline="\n")
    return out
