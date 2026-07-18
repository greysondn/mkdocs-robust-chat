# Robust Chat — format & output specification

This one spec is implemented **twice** — once in JavaScript (Obsidian) and once in
Python (mkdocs-material). Both parsers MUST produce the same HTML scaffolding so the
one shared stylesheet (`chat.css`) and the one shared runtime (`chat.js`) render and
behave identically in both ecosystems. The only thing that legitimately differs between
the two is how the *inner message markdown* is turned into HTML, because each platform
uses its own markdown renderer (Obsidian's, so vault links/embeds work; Python-Markdown,
so mkdocs plugins work). The chat chrome around that markdown is identical.

---

## 1. The block

Everything lives in a fenced code block tagged `chat`:

    ```chat
    ...config header (optional)...

    user: ...
    ...message...

    user: ...
    ...message...
    ```

The block has two parts:

1. **Config header** — every line *before the first line that starts with `user:` at
   column 0*. Optional; may be empty when a global config supplies the display settings.
2. **Messages** — one or more message records, each introduced by a `user:` line at
   column 0.

Message records are delimited purely by the `user:` line at column 0 — blank lines are
*not* required between them and are not significant as separators.

---

## 2. Config header

Describes the participants ("displays"). Parsed by a lenient state machine that ignores
leading indentation, so both the indented canonical form and a flat form parse the same.

```
displays:                      # optional container marker, ignored
  system:                      # reserved participant for system messages
    style:
      background_color: #1b1b1b;
      border_color: #333333;
      font_color: #dddddd;
  alice:                       # a participant key == the value used in `user:`
    type: human                # human | model  (affects a data-attr + default side)
    link_to: /people/alice.md  # username/avatar link target (optional)
    align: left                # left | right   (overrides the type default)
    avatar: /img/alice.png     # avatar image path (optional)
    style:
      background_color: #0d1b2a;
      border_color: #1b3a5b;
      font_color: #e0e6ed;
```

Rules:

- A **bare key** (`name:` with nothing after the colon) that is **not** `style` starts a
  new participant entry named `name`. `system` is just a reserved participant name.
- The bare key `style` starts a style sub-block on the current participant.
- Entry keys `type`, `link_to`, `align`, `avatar` set a field on the current participant
  and end any open style sub-block.
- Any other `key: value` line while a style sub-block is open is a **CSS declaration**.
  The key is converted to a CSS property: known aliases `background_color`→`background-color`,
  `border_color`→`border-color`, `font_color`→`color`; otherwise `_`→`-` passthrough.
  A trailing `;` is optional. Values are sanitized (see §6).
- `type` defaults the side: `human`→left, `model`→right. `align` overrides it.
- Global config (Obsidian settings / mkdocs.yml) provides a default participant map with
  the same schema; a per-block entry is **merged over** the global one (per-block wins,
  field by field; style declarations merge key by key).

---

## 3. Message record

```
user: alice
date: 2025-06-01T14:30:00-04:00
thoughts:
> ordinary markdown
>
> tool_called:
> > summary shown when folded
> > full output, any markdown
>
> more thoughts
attachments:
> /files/diagram.png
> /files/notes.pdf
message:
> the visible message, ordinary markdown
>
> tool_called:
> > ran search
> > ...results...
commentary:
> reviewer:
> > a note about the whole message
> editor:
> > another note
```

Column-0 keys inside a record: `user`, `date`, `thoughts`, `attachments`, `message`,
`commentary`. Only `user` is required; every other section is optional and independent.

Declaring a `user:` is by itself enough to draw a message box: when there is no
`message:` body, the bubble is still rendered (empty, with a min-height) so the box
always appears. Empty `thoughts`, `attachments`, and `commentary` sections, by contrast,
render nothing at all (no empty disclosure, no empty commentary entry) — only the
per-row commentary *column* is always present, so bubbles stay aligned.

- **user**: participant key. `user: system` → system message styling.
- **date**: passed through into a `<time datetime="…">`; the runtime localizes it to the
  viewer's timezone. ISO-8601 with offset (`2025-06-01T14:30:00-04:00`) is recommended;
  anything the browser's `Date` can parse works, and unparseable values display verbatim.
- **thoughts / message**: blockquoted body. Parser strips one `>` level, then splits the
  content into ordinary-markdown runs and `tool_called:` blocks (see §4).
- **attachments**: one path per `>` line; rendered as preview tiles (see §5).
- **commentary**: a sequence of `> commenter:` headers, each followed by that commenter's
  blockquoted markdown (`> >` lines). Lenient: a trailing `:` on the header is optional and
  content may be at `>` or `> >` depth.

### Blockquote stripping

For every section body, remove exactly one leading blockquote marker from each line:
`"> x"` → `"x"`, `">"` → `""`. Then interpret what remains.

---

## 4. tool_called blocks

Inside a stripped thoughts/message body, a line equal to `tool_called:` begins a tool
block. The block consists of the immediately following lines that still start with `>`
(one level, because we already stripped one). Strip that level too:

- the **first** resulting line is the *summary*,
- the **remaining** lines are the *output*.

Rendered as a native `<details class="rc-tool">` (folded by default) with the summary in
`<summary>` and the output as markdown inside. Content before/after the block is rendered
as ordinary markdown runs.

---

## 5. Canonical HTML output

Both parsers emit exactly this structure (whitespace/attribute order aside). `MD(...)`
marks where each platform substitutes its own rendered markdown.

```html
<div class="rc-chat" data-commentary="collapsed">
  <div class="rc-toolbar">
    <button class="rc-commentary-toggle" type="button" aria-pressed="false">Commentary</button>
  </div>
  <div class="rc-thread">

    <!-- system message -->
    <div class="rc-row rc-row--system">
      <div class="rc-msg rc-msg--system" data-user="system">
        <div class="rc-bubble" style="…system style…">
          <div class="rc-body">MD(system text)</div>
        </div>
      </div>
      <div class="rc-commentary"></div>
    </div>

    <!-- participant message -->
    <div class="rc-row rc-row--left">
      <div class="rc-msg rc-msg--left" data-user="alice" data-type="human">
        <a class="rc-avatar" href="/people/alice.md">
          <img src="/img/alice.png" alt="alice" loading="lazy">
        </a>
        <div class="rc-col">
          <div class="rc-meta">
            <a class="rc-name" href="/people/alice.md">alice</a>
            <time class="rc-date" datetime="2025-06-01T14:30:00-04:00">2025-06-01T14:30:00-04:00</time>
          </div>

          <details class="rc-thoughts">
            <summary>Thoughts</summary>
            <div class="rc-body">MD(thoughts, with rc-tool blocks)</div>
          </details>

          <div class="rc-attachments">
            <a class="rc-attach" href="/files/diagram.png" data-ext="png">…tile…</a>
          </div>

          <div class="rc-bubble" style="…alice style…">
            <div class="rc-body">MD(message, with rc-tool blocks)</div>
          </div>
        </div>
      </div>
      <div class="rc-commentary">
        <div class="rc-comment"><div class="rc-commenter">reviewer</div><div class="rc-body">MD(note)</div></div>
      </div>
    </div>

  </div>
</div>
```

Tool block shape (inside an `rc-body`):

```html
<details class="rc-tool"><summary>summary line</summary><div class="rc-body">MD(output)</div></details>
```

Layout contract that the CSS depends on:

- `.rc-thread` is not itself the grid; **each `.rc-row` is a 2-column grid** (message |
  commentary). This makes every message align with its own commentary independently.
- Collapsing commentary is a single attribute flip on `.rc-chat` (`data-commentary`),
  which the CSS uses to drop the commentary column across all rows at once. **The default
  is `collapsed`** (button `aria-pressed="false"`); the runtime restores a per-browser
  saved preference if one exists, and a chat with no commentary at all hides the toolbar.
- `rc-msg--left` / `rc-msg--right` drive bubble side and avatar offset.

## 6. Sanitization

- Style values: strip anything containing `<`, `>`, `{`, `}`, or the sequences `url(`,
  `expression`, or a `;` used to inject extra declarations. Only a single `prop: value`
  survives per declaration. This keeps author-supplied CSS from escaping the inline style.
- All text interpolated into attributes/HTML (usernames, paths, dates, summaries) is HTML-
  escaped. Paths used in `href`/`src` are attribute-escaped and must not contain `"`.
