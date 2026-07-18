"""Robust Chat — parser + renderer core (Python reference implementation).

Mirrors common/parser.js exactly. Pure: no mkdocs/markdown dependency here; the mkdocs
extension passes in a render_markdown callable. The test suite checks this and the JS
core emit identical HTML scaffolding.  See ../../SPEC.md.
"""
import re

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "avif", "bmp", "ico"}
ENTRY_KEYS = {"type", "link_to", "align", "avatar"}
STYLE_ALIAS = {
    "background_color": "background-color",
    "border_color": "border-color",
    "font_color": "color",
}

_LTRIM = re.compile(r"^[ \t]+")
_TRAIL_SEMI = re.compile(r";+\s*$")
_LEAD_NL = re.compile(r"^\n+")
_TAIL_NL = re.compile(r"\n+$")
_HAS_WS = re.compile(r"\s")


# ---------- helpers ----------
def split_lines(src):
    return str(src).replace("\r\n", "\n").replace("\r", "\n").split("\n")


def ltrim(s):
    return _LTRIM.sub("", s)


def starts_key(line, key):
    return line[: len(key) + 1] == key + ":"


def after_colon(line):
    i = line.find(":")
    return "" if i < 0 else line[i + 1:].strip()


def esc_html(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def esc_attr(s):
    return (str(s).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def basename(p):
    parts = re.split(r"[\\/]", str(p))
    return parts[-1] or str(p)


def ext_of(p):
    b = basename(p)
    i = b.rfind(".")
    return b[i + 1:].lower() if i > 0 else ""


def clean_style_value(v):
    v = _TRAIL_SEMI.sub("", str(v).strip())
    if re.search(r"[<>{}]", v) or re.search(r"url\s*\(", v, re.I) \
            or re.search(r"expression", v, re.I) or ";" in v:
        return None
    return v


def style_prop(key):
    return STYLE_ALIAS.get(key, key.replace("_", "-"))


def strip_one(line):
    if line[:2] == "> ":
        return line[2:]
    if line == ">":
        return ""
    if line[:1] == ">":
        return line[1:]
    return line


# ---------- config ----------
def parse_config(lines):
    displays, order, current, in_style = {}, [], None, False
    for raw in lines:
        line = ltrim(raw)
        if line == "" or line == "displays:":
            continue
        ci = line.find(":")
        if ci < 0:
            continue
        key = line[:ci].strip()
        val = line[ci + 1:].strip()
        has_val = len(val) > 0

        if key == "style" and not has_val:
            if current:
                in_style = True
            continue
        if key in ENTRY_KEYS:
            in_style = False
            if current:
                displays[current][key] = val
            continue
        if in_style and has_val:
            cv = clean_style_value(val)
            if cv is not None and current:
                displays[current]["style"].append((style_prop(key), cv))
            continue
        if not has_val:
            current = key
            in_style = False
            if current not in displays:
                displays[current] = {"style": []}
                order.append(current)
            continue
        # has_val, not entry key, not in style -> ignore
    return {"displays": displays, "order": order}


def merge_displays(global_cfg, local_cfg):
    out = {}

    def put(src):
        for name, s in src.items():
            d = out.setdefault(name, {"style": []})
            for k in ("type", "link_to", "align", "avatar"):
                if s.get(k):
                    d[k] = s[k]
            if s.get("style"):
                merged = d["style"] + s["style"]
                seen, result = set(), []
                for prop, v in reversed(merged):
                    if prop in seen:
                        continue
                    seen.add(prop)
                    result.insert(0, (prop, v))
                d["style"] = result

    if global_cfg:
        put(global_cfg)
    if local_cfg:
        put(local_cfg)
    return out


# ---------- body segmentation ----------
def segment_body(stripped):
    segs, buf = [], []

    def flush():
        text = _TAIL_NL.sub("", _LEAD_NL.sub("", "\n".join(buf)))
        if text.strip() != "":
            segs.append({"kind": "md", "text": text})
        buf.clear()

    i = 0
    n = len(stripped)
    while i < n:
        if stripped[i].strip() == "tool_called:":
            flush()
            tool = []
            i += 1
            while i < n and stripped[i][:1] == ">":
                tool.append(strip_one(stripped[i]))
                i += 1
            summary = tool[0].strip() if tool else ""
            output = _TAIL_NL.sub("", _LEAD_NL.sub("", "\n".join(tool[1:])))
            segs.append({"kind": "tool", "summary": summary, "output": output})
            continue
        buf.append(stripped[i])
        i += 1
    flush()
    return segs


def parse_commentary(stripped):
    comments, cur = [], None

    def is_header(l):
        t = l.strip()
        if l[:1] == ">" or t == "":
            return False
        return t[-1:] == ":" or not _HAS_WS.search(t)

    for l in stripped:
        if is_header(l):
            if cur:
                comments.append(cur)
            cur = {"name": l.strip().rstrip(":"), "lines": []}
        elif cur:
            cur["lines"].append(strip_one(l) if l[:1] == ">" else l)
    if cur:
        comments.append(cur)

    out = []
    for c in comments:
        text = _TAIL_NL.sub("", _LEAD_NL.sub("", "\n".join(c["lines"])))
        if c["name"] != "":
            out.append({"name": c["name"], "text": text})
    return out


# ---------- message record ----------
def collect_quoted(lines, start):
    body, i = [], start
    while i < len(lines):
        if lines[i][:1] == ">":
            body.append(lines[i])
            i += 1
        else:
            break
    return body, i


def parse_message(chunk):
    msg = {"user": "", "date": None, "thoughts": None,
           "attachments": None, "message": None, "commentary": None}
    i = 0
    while i < len(chunk):
        line = chunk[i]
        if starts_key(line, "user"):
            msg["user"] = after_colon(line); i += 1; continue
        if starts_key(line, "date"):
            msg["date"] = after_colon(line); i += 1; continue
        if starts_key(line, "thoughts"):
            body, i = collect_quoted(chunk, i + 1)
            msg["thoughts"] = segment_body([strip_one(x) for x in body]); continue
        if starts_key(line, "attachments"):
            body, i = collect_quoted(chunk, i + 1)
            paths = [strip_one(x).strip() for x in body]
            msg["attachments"] = [p for p in paths if p != ""]; continue
        if starts_key(line, "message"):
            body, i = collect_quoted(chunk, i + 1)
            msg["message"] = segment_body([strip_one(x) for x in body]); continue
        if starts_key(line, "commentary"):
            body, i = collect_quoted(chunk, i + 1)
            msg["commentary"] = parse_commentary([strip_one(x) for x in body]); continue
        i += 1
    return msg


def parse_chat(source):
    lines = split_lines(source)
    first_user = -1
    for idx, l in enumerate(lines):
        if starts_key(l, "user"):
            first_user = idx
            break
    config_lines = lines if first_user < 0 else lines[:first_user]
    msg_lines = [] if first_user < 0 else lines[first_user:]
    cfg = parse_config(config_lines)

    messages, chunk = [], None
    for l in msg_lines:
        if starts_key(l, "user"):
            if chunk is not None:
                messages.append(parse_message(chunk))
            chunk = [l]
        elif chunk is not None:
            chunk.append(l)
    if chunk is not None:
        messages.append(parse_message(chunk))
    return {"displays": cfg["displays"], "messages": messages}


# ---------- render ----------
def render_style(style_list):
    if not style_list:
        return ""
    parts = ["%s: %s;" % (k, v) for k, v in style_list]
    return ' style="' + esc_attr(" ".join(parts)) + '"'


def side_for(disp):
    a = disp.get("align")
    if a in ("left", "right"):
        return a
    if disp.get("type") == "model":
        return "right"
    return "left"


def render_segments(segs, md):
    if not segs:
        return ""
    html = []
    for s in segs:
        if s["kind"] == "md":
            html.append(md(s["text"]))
        else:
            html.append('<details class="rc-tool"><summary>' + esc_html(s["summary"]) +
                        '</summary><div class="rc-body">' + md(s["output"]) + "</div></details>")
    return "".join(html)


def render_attachments(paths):
    if not paths:
        return ""
    tiles = []
    for p in paths:
        ext = ext_of(p)
        name = basename(p)
        href = esc_attr(p)
        if ext in IMAGE_EXTS:
            tiles.append('<a class="rc-attach rc-attach--image" href="' + href + '" data-ext="' +
                         esc_attr(ext) + '" title="' + esc_attr(name) + '"><img src="' + href +
                         '" alt="' + esc_attr(name) + '" loading="lazy"></a>')
        else:
            tiles.append('<a class="rc-attach" href="' + href + '" data-ext="' + esc_attr(ext) +
                         '" title="' + esc_attr(name) + '"><span class="rc-attach-icon">' +
                         esc_html(ext or "file") + '</span><span class="rc-attach-name">' +
                         esc_html(name) + "</span></a>")
    return '<div class="rc-attachments">' + "".join(tiles) + "</div>"


def render_commentary(comments, md):
    if not comments:
        return '<div class="rc-commentary"></div>'
    items = []
    for c in comments:
        items.append('<div class="rc-comment"><div class="rc-commenter">' + esc_html(c["name"]) +
                     '</div><div class="rc-body">' + md(c["text"]) + "</div></div>")
    return '<div class="rc-commentary">' + "".join(items) + "</div>"


def render_message(msg, displays, md):
    name = msg["user"]
    disp = displays.get(name, {"style": []})
    is_system = name == "system"

    if is_system:
        sys_body = render_segments(msg["message"], md)
        return ('<div class="rc-row rc-row--system">'
                '<div class="rc-msg rc-msg--system" data-user="' + esc_attr(name) + '">'
                '<div class="rc-bubble"' + render_style(disp.get("style")) +
                '><div class="rc-body">' + sys_body + "</div></div></div>" +
                render_commentary(msg["commentary"], md) + "</div>")

    side = side_for(disp)
    link = esc_attr(disp["link_to"]) if disp.get("link_to") else None

    if disp.get("avatar"):
        avatar_inner = ('<img src="' + esc_attr(disp["avatar"]) + '" alt="' +
                        esc_attr(name) + '" loading="lazy">')
    else:
        avatar_inner = esc_html((name[:1] or "?").upper())
    if link:
        avatar = '<a class="rc-avatar" href="' + link + '">' + avatar_inner + "</a>"
    else:
        avatar = '<span class="rc-avatar">' + avatar_inner + "</span>"

    if link:
        name_el = '<a class="rc-name" href="' + link + '">' + esc_html(name) + "</a>"
    else:
        name_el = '<span class="rc-name">' + esc_html(name) + "</span>"
    date_el = ('<time class="rc-date" datetime="' + esc_attr(msg["date"]) + '">' +
               esc_html(msg["date"]) + "</time>") if msg["date"] else ""
    meta = '<div class="rc-meta">' + name_el + date_el + "</div>"

    thoughts = ""
    if msg["thoughts"]:
        thoughts = ('<details class="rc-thoughts"><summary>Thoughts</summary>'
                    '<div class="rc-body">' + render_segments(msg["thoughts"], md) + "</div></details>")

    attachments = render_attachments(msg["attachments"])
    bubble = ('<div class="rc-bubble"' + render_style(disp.get("style")) +
              '><div class="rc-body">' + render_segments(msg["message"], md) + "</div></div>")

    col = '<div class="rc-col">' + meta + thoughts + attachments + bubble + "</div>"
    type_attr = ' data-type="' + esc_attr(disp["type"]) + '"' if disp.get("type") else ""

    return ('<div class="rc-row rc-row--' + side + '">'
            '<div class="rc-msg rc-msg--' + side + '" data-user="' + esc_attr(name) + '"' + type_attr + '>' +
            avatar + col + "</div>" +
            render_commentary(msg["commentary"], md) + "</div>")


def render_chat(parsed, render_markdown=None, global_displays=None):
    md = render_markdown or (lambda t: "<p>" + esc_html(t) + "</p>")
    displays = merge_displays(global_displays, parsed["displays"])
    rows = "".join(render_message(m, displays, md) for m in parsed["messages"])
    return ('<div class="rc-chat" data-commentary="collapsed">'
            '<div class="rc-toolbar"><button class="rc-commentary-toggle" type="button" '
            'aria-pressed="false">Commentary</button></div>'
            '<div class="rc-thread">' + rows + "</div></div>")


def chat_to_html(source, render_markdown=None, global_displays=None):
    return render_chat(parse_chat(source), render_markdown, global_displays)
