"""Minimal mkdocs plugin for Robust Chat.

By design this plugin does NOT register the superfences fence or inject
extra_css / extra_javascript — you write those in mkdocs.yml yourself (see README).
It only:

  * applies your global participant defaults (``global_config``) and the inner
    markdown extension list to the chat renderer, and
  * (optionally, on by default) copies the bundled ``chat.css`` / ``chat.js`` into the
    built site so your ``extra_css`` / ``extra_javascript`` references resolve without
    hand-copying files. Set ``copy_assets: false`` to manage the assets yourself.

The plugin is optional: chat blocks render from the superfences fence config alone. Add
the plugin only if you want global display defaults or the asset-copy convenience.
"""
import os
import shutil

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin

from . import parser as rc
from . import superfence

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
ASSET_SUBDIR = ("assets", "robust-chat")
ASSET_FILES = ("chat.css", "chat.js")


class RobustChatPlugin(BasePlugin):
    config_scheme = (
        # Global participant defaults, in the same header syntax as a chat block.
        ("global_config", config_options.Type(str, default="")),
        # Extensions used to render the *inner* message markdown.
        ("inner_markdown_extensions", config_options.Type(list, default=["extra", "sane_lists"])),
        # Copy the bundled chat.css/chat.js into the built site.
        ("copy_assets", config_options.Type(bool, default=True)),
    )

    def on_config(self, config):
        superfence.set_inner_extensions(self.config["inner_markdown_extensions"])
        superfence.set_global_displays(
            rc.parse_chat(self.config["global_config"]).get("displays", {})
        )
        return config

    def on_page_markdown(self, markdown, page, config, files):
        # Lets format_chat resolve avatar/attachment/link_to paths that start with "/"
        # as relative to the docs root, rewritten correctly for this page's depth —
        # raw HTML from the fence otherwise bypasses mkdocs' own link rewriting.
        superfence.set_current_page_url(page.url)
        return markdown

    def on_post_build(self, config):
        if not self.config["copy_assets"]:
            return
        dest = os.path.join(config["site_dir"], *ASSET_SUBDIR)
        os.makedirs(dest, exist_ok=True)
        for f in ASSET_FILES:
            shutil.copyfile(os.path.join(ASSETS_DIR, f), os.path.join(dest, f))
