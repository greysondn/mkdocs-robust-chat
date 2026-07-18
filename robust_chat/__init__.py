"""Robust Chat for mkdocs-material."""
from .parser import parse_chat, render_chat, chat_to_html  # noqa: F401
from .plugin import RobustChatPlugin  # noqa: F401
from .superfence import format_chat  # noqa: F401

__version__ = "1.0.0"
