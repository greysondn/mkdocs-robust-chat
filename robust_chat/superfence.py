"""pymdownx.superfences custom fence for ```chat blocks.

`format_chat` is the fence formatter registered with superfences. It parses the fence
source with the shared parser and renders the chat scaffolding, delegating the *inner*
message markdown to a dedicated Python-Markdown instance (kept separate from the page's
own Markdown instance to avoid state/recursion issues).
"""
import markdown

from . import parser as rc

_inner = None
_inner_exts = ["extra", "sane_lists"]
_global_displays = {}


def set_inner_extensions(exts):
    global _inner, _inner_exts
    _inner_exts = list(exts) if exts else []
    _inner = None


def set_global_displays(displays):
    global _global_displays
    _global_displays = displays or {}


def _get_inner():
    global _inner
    if _inner is None:
        _inner = markdown.Markdown(extensions=_inner_exts, output_format="html")
    return _inner


def _render_md(text):
    m = _get_inner()
    m.reset()
    return m.convert(text)


def format_chat(source, language, css_class, options, md, **kwargs):
    """superfences custom-fence formatter -> returns raw HTML for the block."""
    parsed = rc.parse_chat(source)
    return rc.render_chat(parsed, render_markdown=_render_md,
                          global_displays=_global_displays)


def validator(language, inputs, options, attrs, md):
    """Accept the fence with no special options (superfences validator hook)."""
    return True
