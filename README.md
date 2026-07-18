# AI DISCLOSURE

This repo is almost entirely coded via a spec --> iterate process using modern AI models. (The models are credited per-commit for the curious.)

Outside this disclosure, changes made by humans are properly credited.

Do as you wish with that information.

## Contributing

Please don't. You're welcome to fork it, though - it's MIT for a reason. Just don't forget a lot of people want to know if it's AI-generated code.

# mkdocs-robust-chat

Render ` ```chat ` code blocks as modern chat threads in **mkdocs-material** — system
messages, foldable thoughts and tool calls, rich attachment tiles, timezone-aware dates,
and a collapsible per-message commentary column.

The full input format and HTML output contract are in [`SPEC.md`](SPEC.md).

This plugin **does not silently rewire your config**: you register the fence and load the
assets yourself (section 2), and the optional plugin only applies global display defaults
and copies the CSS/JS into the built site.

---

## 1. Install (no PyPI)

The package just needs to be importable by mkdocs at build time so that
`!!python/name:robust_chat.superfence.format_chat` resolves.

### pipenv (git)

Add to your `Pipfile` — pin a tag so `Pipfile.lock` stays reproducible:

```toml
[packages]
mkdocs-robust-chat = {git = "https://github.com/USER/mkdocs-robust-chat.git", ref = "v1.0.0"}
```

Then:

```bash
pipenv install
```

Or in one command (also writes the Pipfile entry):

```bash
pipenv install "git+https://github.com/USER/mkdocs-robust-chat.git@v1.0.0#egg=mkdocs-robust-chat"
```

- **Private repo (SSH):** `{git = "ssh://git@github.com/USER/mkdocs-robust-chat.git", ref = "v1.0.0"}`
- **Editable / hacking:** add `editable = true` to the dict.

Because the packaging lives at the repo **root**, no `#subdirectory=` fragment is needed.

### plain pip

```bash
pip install "git+https://github.com/USER/mkdocs-robust-chat.git@v1.0.0"
```

Verify:

```bash
python -c "import robust_chat; print(robust_chat.__version__)"
```

---

## 2. Config you add to `mkdocs.yml`

Three pieces: register the fence, load the assets, (optionally) add the plugin.

```yaml
markdown_extensions:
  - pymdownx.superfences:
      custom_fences:
        - name: chat
          class: chat
          format: !!python/name:robust_chat.superfence.format_chat
          validator: !!python/name:robust_chat.superfence.validator

extra_css:
  - assets/robust-chat/chat.css
extra_javascript:
  - assets/robust-chat/chat.js

plugins:
  - search
  - robust-chat            # optional — global_config + asset copy only
```

> **Already using `pymdownx.superfences`?** mkdocs-material enables it by default. Don't add
> a second `pymdownx.superfences:` entry — add the `custom_fences:` list **under your
> existing one** (merge, don't duplicate).

The `class: chat` value is required by superfences' schema but isn't used by the formatter
(the returned HTML already carries its own classes).

---

## 3. Where the CSS/JS come from

Your `extra_css` / `extra_javascript` point at `assets/robust-chat/chat.css` and `chat.js`.
Two ways to make those paths exist in the built site:

- **Let the plugin copy them (default).** With `robust-chat` in `plugins:`, the files are
  copied into `site/assets/robust-chat/` on every build.
- **Do it yourself.** Copy the two files out of the installed package into your docs folder:
  ```bash
  python - <<'PY'
  import os, shutil, robust_chat
  src = os.path.join(os.path.dirname(robust_chat.__file__), "assets")
  os.makedirs("docs/assets/robust-chat", exist_ok=True)
  for f in ("chat.css", "chat.js"):
      shutil.copyfile(os.path.join(src, f), f"docs/assets/robust-chat/{f}")
  PY
  ```

---

## 4. Plugin options (all optional)

```yaml
plugins:
  - robust-chat:
      # Global participant defaults — same header syntax as a chat block.
      global_config: |
        displays:
          alice:
            type: human
            avatar: /img/alice.png
      # Extensions for the *inner* message markdown (default shown).
      inner_markdown_extensions:
        - extra
        - sane_lists
      # Set false to manage the CSS/JS yourself (section 3).
      copy_assets: true
```

If you skip the plugin entirely, chat blocks still render — you just won't have
`global_config`, and you'll copy the assets yourself.

---

## License

MIT — see [`LICENSE.md`](LICENSE.md).
