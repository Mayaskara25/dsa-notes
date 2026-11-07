#!/usr/bin/env python3
"""Build the DSA notes website into ./public and validate it.

Standard library only (Render's build image just needs python3).
Exit code 1 = validation failed -> Render aborts the deploy and keeps the last good version live.

Usage (from the repo root):  python3 site/build.py
"""
import html, json, os, re, shutil, subprocess, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "public")
errors = []


def err(msg):
    errors.append(msg)


def version():
    v = os.environ.get("RENDER_GIT_COMMIT", "")
    if v:
        return v[:7]
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "local"


def human(d):
    y, m, dd = map(int, d.split("-"))
    return f"{dd} {date(y, m, dd):%b} {y}"


def moved_banner(cfg, path=""):
    """Deprecation bar shown on every page once site.json has "moved_to" set."""
    url = cfg.get("moved_to", "").rstrip("/")
    if not url:
        return ""
    href = html.escape(url + "/dsa/" + path, quote=True)
    return ('<div role="note" style="position:sticky;top:0;z-index:100;background:#A66A0D;color:#fff;'
            'font:600 14px/1.45 Inter,system-ui,sans-serif;padding:10px 16px;text-align:center">'
            'These notes have moved, and this copy is no longer updated. '
            f'<a href="{href}" style="color:#fff;text-decoration:underline">Open the new site →</a></div>\n')


def inject_body(page, banner):
    if not banner:
        return page
    m = re.search(r"<body[^>]*>", page)
    return page[:m.end()] + "\n" + banner + page[m.end():] if m else page


# ---------- validation (same checks as the notes-maker Tier-1 script) ----------
TAGS = ["section", "div", "svg", "g", "table", "ul", "ol", "tr", "td", "th", "h1", "h2", "h3"]


def validate_unit(name, c):
    for t in TAGS:
        o = len(re.findall(r"<" + t + r"(\s|>)", c))
        cl = len(re.findall(r"</" + t + r">", c))
        if o != cl:
            err(f"{name}: <{t}> opened {o} times but closed {cl} times")
    ids = re.findall(r'id="([\w-]+)"', c)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        err(f"{name}: duplicate ids {dup[:8]}")
    broken = set(re.findall(r'href="#([\w-]+)"', c)) - set(ids)
    if broken:
        err(f"{name}: links to missing sections {sorted(broken)[:8]}")
    figs = re.findall(r'class="cap"[^>]*>\s*(?:<[^>]+>\s*)*Fig (\d+)([a-z]?)\.', c)
    keys = [(int(n), s) for n, s in figs]
    if keys != sorted(keys):
        err(f"{name}: figure captions out of order: {['%d%s' % k for k in keys]}")
    curved = re.findall(r'<path d="M[^"]*[QC][^"]*"[^>]*>', c)
    bad = [p for p in curved if "fill=" not in p]
    if bad:
        err(f"{name}: {len(bad)} curved <path> without fill=\"none\"")
    if re.search(r"</?(antml|thinking)\b|<cite\b", c):
        err(f"{name}: contains chat-formatting artifacts")
    if "</head>" not in c or "</body>" not in c:
        err(f"{name}: missing </head> or </body>")


# ---------- content extraction ----------
def plain(s):
    s = re.sub(r"<(svg|script|style)\b.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def sections(c):
    out = []
    for m in re.finditer(r'<section\b([^>]*)>(.*?)</section>', c, flags=re.S):
        attrs, body = m.group(1), m.group(2)
        idm = re.search(r'\bid="([\w-]+)"', attrs)
        if not idm or "section" not in attrs:
            continue
        tag = re.search(r'class="tag"[^>]*>(.*?)</span>', body, flags=re.S)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.S)
        out.append({"id": idm.group(1), "tag": plain(tag.group(1)) if tag else "",
                    "title": plain(h1.group(1)) if h1 else idm.group(1), "text": plain(body)})
    return out


def main():
    cfg = json.load(open(os.path.join(SITE, "site.json"), encoding="utf-8"))
    ver = version()
    chrome_t = open(os.path.join(SITE, "unit-chrome.html"), encoding="utf-8").read()
    index_t = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    theme_js = open(os.path.join(SITE, "theme-links.js"), encoding="utf-8").read()
    # runs after each guide's own OS-preference script, so an explicit ?theme= wins before first paint
    theme_head = ("<script>(function(){try{var t=new URLSearchParams(location.search).get('theme');"
                  "if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}})();</script>\n")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    search, cards, labs = [], [], []
    for u in cfg["units"]:
        n, src = u["n"], os.path.join(ROOT, u["source"])
        name = f"Unit {n}"
        if not os.path.isfile(src):
            err(f"{name}: source file missing: {u['source']}")
            continue
        c = open(src, encoding="utf-8").read()
        validate_unit(name, c)
        secs = sections(c)
        if not secs:
            err(f"{name}: no sections found")
        ids = set(re.findall(r'id="([\w-]+)"', c))
        if u["lab"] not in ids:
            err(f"{name}: lab anchor #{u['lab']} not found")

        topics = [s for s in secs if re.match(r"\d", s["tag"])]
        nfig = len(set(re.findall(r'class="cap"[^>]*>\s*(?:<[^>]+>\s*)*Fig (\d+[a-z]?)\.', c)))
        nq = len(re.findall(r'class="qbox"', c))

        for s in secs:
            search.append({"n": n, "g": s["tag"], "t": s["title"], "u": f"unit-{n}/#{s['id']}",
                           "x": s["text"][:3000]})

        chrome = (chrome_t.replace("{{UPDATED_HUMAN}}", human(u["updated"]))
                  .replace("{{UPDATED}}", u["updated"]).replace("{{VERSION}}", ver)
                  .replace("{{REPO}}", cfg["repo"]).replace("{{UNIT_N}}", str(n))
                  .replace("{{UNIT_TITLE_JS}}", u["title"].replace("\\", "\\\\").replace('"', '\\"'))
                  .replace("{{DOWNLOAD_NAME}}", html.escape(u["source"], quote=True)))
        page = c.replace("</head>", '<meta name="robots" content="noindex, nofollow">\n' + theme_head + "</head>", 1)
        i = page.rfind("</body>")
        page = page[:i] + chrome + "\n<script>" + theme_js + "</script>\n" + page[i:]
        page = inject_body(page, moved_banner(cfg, f"unit-{n}/"))
        os.makedirs(os.path.join(OUT, f"unit-{n}"))
        open(os.path.join(OUT, f"unit-{n}", "index.html"), "w", encoding="utf-8").write(page)

        e = html.escape
        cards.append(
            f'<div class="unit" style="--accent:{u["accent"]}"><div class="no">UNIT {n}</div>'
            f'<div><h3><a href="unit-{n}/">{e(u["title"])}</a></h3><div class="topics">{e(u["topics"])}</div>'
            f'<div class="stats"><span>{len(topics)} topics</span><span>{nfig} diagrams</span>'
            f'<span>{nq} worked examples</span><span>updated {human(u["updated"])}</span></div></div>'
            f'<div class="acts"><a class="btn primary" href="unit-{n}/">Open</a>'
            f'<a class="btn" href="unit-{n}/index.html" download="{e(u["source"], quote=True)}">Download</a></div></div>')
        labs.append(f'      <li><a href="unit-{n}/#{u["lab"]}">Unit {n} — {e(u["title"])}</a></li>')

    log = []
    for entry in sorted(cfg["changelog"], key=lambda x: x["date"], reverse=True)[:10]:
        tags = "".join(f'<span class="u">U{k}</span>' for k in entry.get("units", []))
        log.append(f'<li><time datetime="{entry["date"]}">{human(entry["date"])}</time>'
                   f'<div>{tags}{html.escape(entry["text"])}</div></li>')

    latest = max([u["updated"] for u in cfg["units"]] + [x["date"] for x in cfg["changelog"]])
    sj = json.dumps(search, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    index = (index_t.replace("{{TITLE}}", html.escape(cfg["title"])).replace("{{COURSE}}", html.escape(cfg["course"]))
             .replace("{{SUBTITLE}}", html.escape(cfg["subtitle"])).replace("{{UPDATED_HUMAN}}", human(latest))
             .replace("{{VERSION}}", ver).replace("{{REPO}}", cfg["repo"])
             .replace("{{UNITS}}", "\n".join(cards)).replace("{{CHANGELOG}}", "\n".join(log))
             .replace("{{LABS}}", "\n".join(labs)).replace("{{THEME_LINKS}}", theme_js)
             .replace("{{SEARCH_JSON}}", sj))
    index = inject_body(index, moved_banner(cfg))
    left = re.findall(r"\{\{[A-Z_]+\}\}", index)
    if left:
        err(f"index: unfilled placeholders {left}")
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(index)
    open(os.path.join(OUT, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(
        '<!DOCTYPE html><meta charset="utf-8"><meta name="robots" content="noindex">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Not found</title>'
        '<body style="font:16px system-ui;padding:48px 20px;max-width:640px;margin:auto">'
        '<h1>Page not found</h1><p><a href="/">Go to all units</a></p></body>')

    # every search link must point at a real section of a built page
    built = {}
    for u in cfg["units"]:
        p = os.path.join(OUT, f"unit-{u['n']}", "index.html")
        if os.path.isfile(p):
            built[f"unit-{u['n']}/"] = set(re.findall(r'id="([\w-]+)"', open(p, encoding="utf-8").read()))
    for s in search:
        page, _, anchor = s["u"].partition("#")
        if anchor not in built.get(page, set()):
            err(f"search link broken: {s['u']}")

    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    if errors:
        print("BUILD FAILED — nothing was deployed:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        sys.exit(1)
    print(f"OK: built {len(cfg['units'])} units, {len(search)} searchable sections, "
          f"{size/1024:.0f} KB total, version {ver}, latest update {latest}")


if __name__ == "__main__":
    main()
