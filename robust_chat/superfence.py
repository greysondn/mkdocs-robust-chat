"""pymdownx.superfences custom fence for ```chat blocks.

`format_chat` is the fence formatter registered with superfences. It parses the fence
source with the shared parser and renders the chat scaffolding, delegating the *inner*
message markdown to a dedicated Python-Markdown instance (kept separate from the page's
own Markdown instance to avoid state/recursion issues).

Because the rendered chat is raw HTML (bypassing mkdocs' own relative-link rewriting —
mkdocs only rewrites <a>/<img> tags it parsed itself, not raw HTML from custom fences),
any src/href that starts with "/" is treated here as **relative to the docs root** and
rewritten to the correct path for the current page (see set_current_page_url / the
plugin's on_page_markdown hook).
"""
import re

import markdown
from mkdocs.utils import get_relative_url

from . import parser as rc

_inner = None
_inner_exts = ["extra", "sane_lists"]
_global_displays = {}
_page_url = None
_ROOT_REF = re.compile(r'(src|href)="(/[^"]*)"')


def set_inner_extensions(exts):
    global _inner, _inner_exts
    _inner_exts = list(exts) if exts else []
    _inner = None


def set_global_displays(displays):
    global _global_displays
    _global_displays = displays or {}


def set_current_page_url(url):
    """Called from the plugin's on_page_markdown hook before each page renders."""
    global _page_url
    _page_url = url


def _get_inner():
    global _inner
    if _inner is None:
        _inner = markdown.Markdown(extensions=_inner_exts, output_format="html")
    return _inner


def _render_md(text):
    m = _get_inner()
    m.reset()
    return m.convert(text)


def _rewrite_root_refs(html):
    """Rewrite src/href="/..." to be correctly relative to the current page's depth."""
    if _page_url is None:
        return html

    def repl(m):
        attr, path = m.group(1), m.group(2)
        return f'{attr}="{get_relative_url(path.lstrip("/"), _page_url)}"'

    return _ROOT_REF.sub(repl, html)


def format_chat(source, language, css_class, options, md, **kwargs):
    """superfences custom-fence formatter -> returns raw HTML for the block."""
    parsed = rc.parse_chat(source)
    html = rc.render_chat(parsed, render_markdown=_render_md,
                          global_displays=_global_displays)
    return _rewrite_root_refs(html)


def validator(language, inputs, options, attrs, md):
    """Accept the fence with no special options (superfences validator hook)."""
    return True
