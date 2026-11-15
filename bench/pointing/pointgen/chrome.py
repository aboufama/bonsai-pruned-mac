"""Window chrome and the surrounding desktop: macOS-like, Windows-like and GNOME-like title bars,
menu bars, a browser frame for web apps, and optional OS bars (menu bar, dock, taskbar)."""
from .theme import mix
from .ui import esc

_WIN_GLYPH = {
    "min": '<svg viewBox="0 0 10 10"><path d="M0 5h10"/></svg>',
    "max": '<svg viewBox="0 0 10 10"><rect x=".5" y=".5" width="9" height="9"/></svg>',
    "close": '<svg viewBox="0 0 10 10"><path d="M0 0l10 10M10 0L0 10"/></svg>',
}
_OTHER_TABS = ["New Tab", "Weather — 14°", "Flight status", "Lemon tart recipe", "Transit map", "Dictionary",
               "Unit converter", "Local news", "Photo album", "Package tracking", "Crossword"]
_DOCK = ["folder", "globe", "mail", "calendar", "music", "image", "message-circle", "terminal", "settings", "map",
         "camera", "book-open", "calculator", "notebook", "video", "shopping-bag", "cloud", "pen-tool", "gamepad-2",
         "chart-pie", "compass", "film", "headphones", "newspaper", "palette", "phone", "rocket", "rss", "tv"]


def _controls(ctx, kind):
    """Window buttons, registered as icon targets drawn by CSS."""
    region = "the title bar"

    def one(cid, cls, inner=""):
        attr = ctx.reg("button", "button", ctx.lab(cid), ui="icon", cid=cid, region=region)
        return f'<div class="{cls}"{attr}>{inner}</div>'

    if kind == "mac":
        return '<div class="lights">' + one("win.close", "c") + one("win.min", "n") + one("win.max", "x") + "</div>"
    if kind == "win":
        return ('<div class="wc">' + one("win.min", "", _WIN_GLYPH["min"]) + one("win.max", "", _WIN_GLYPH["max"])
                + one("win.close", "", _WIN_GLYPH["close"]) + "</div>")
    n = ctx.rng.choice([1, 3, 3])
    out = '<div class="gc">'
    if n == 3:
        out += one("win.min", "", _WIN_GLYPH["min"]) + one("win.max", "", _WIN_GLYPH["max"])
    return out + one("win.close", "", _WIN_GLYPH["close"]) + "</div>"


def _menu_items(ctx, menus, region):
    out = []
    for cid in menus:
        if not ctx.has(cid):
            continue
        attr = ctx.reg("menu", "menu", ctx.lab(cid), cid=cid, region=region, anchor="menubar")
        out.append(f'<div class="mb"{attr}>{esc(ctx.lab(cid))}</div>')
    return "".join(out)


def _browser(ctx, kind, app):
    rng = ctx.rng
    others = rng.sample(_OTHER_TABS, rng.randint(1, 3))
    pos = rng.randint(0, len(others))
    tabs = []
    for i, t in enumerate(others[:pos] + [None] + others[pos:]):
        if t is None:
            tabs.append(f'<div class="btab on"><span class="fav" style="background:var(--ac)"></span><span class="el f1">{esc(app["title"])}</span></div>')
        else:
            tabs.append(f'<div class="btab"><span class="fav" style="background:{ctx.d.color()}"></span><span class="el f1">{esc(t)}</span></div>')
    strip = "".join(tabs)
    region = "the browser toolbar"
    plus = '<div class="row mut" style="height:30px;padding:0 8px;font-size:16px">+</div>'
    if kind == "mac":
        top = (f'<div class="btabs" style="align-items:center">{_controls(ctx, "mac")}<div style="width:14px"></div>'
               f'<div class="row" style="align-self:flex-end;gap:2px">{strip}{plus}</div></div>')
    else:
        top = (f'<div class="btabs" style="padding-right:0">{strip}{plus}<div class="sp"></div>'
               f'<div class="tbar win" style="height:38px;border:none;background:none;padding:0">{_controls(ctx, "win")}</div></div>')
    nav = ctx.ibtn("back", region, cls="s") + ctx.ibtn("forward", region, cls="s") + ctx.ibtn("refresh", region, cls="s", obj="this web page")
    lock = ctx.deco("lock", "lock-keyhole", "shield-check", "globe", size=12)
    url = f'<div class="url">{lock}<span class="el">{esc(app.get("url", "app.example.com"))}</span></div>'
    tail = ctx.deco("puzzle", "blocks", "plug", "shapes", size=15) + ctx.av(ctx.d.person(), 22)
    return top + f'<div class="burl">{nav}{url}<div class="row g8 mut">{tail}</div></div>'


def build_page(ctx, spec, app):
    rng = ctx.rng
    kind, shell, floating = spec["chrome"], spec["shell"], spec["floating"]
    if app.get("compact") and spec["w"] >= 1366 and not spec["web"]:
        # small utility windows (preferences, wizards) float over the desktop instead of filling it
        side, top = int(spec["w"] * rng.uniform(0.13, 0.24)), int(spec["h"] * rng.uniform(0.05, 0.13))
        spec["floating"], spec["inset"] = True, f"{top}px {side}px {top + rng.randint(0, 50)}px {side}px"
        floating = True
    dark = spec["theme"]["mode"] == "dark"
    menus = app.get("menus") or []
    title = app["title"]
    top_os = bottom_os = ""
    clock = f"{rng.choice(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])} {rng.randint(1, 28)} {rng.choice(['Mar', 'Jun', 'Sep', 'Nov'])}  {rng.randint(8, 18)}:{rng.randint(10, 59)}"
    status = "".join(ctx.deco_any(names) for names in (["wifi", "wifi-high", "signal"], ["battery-medium", "battery-full", "battery"],
                                                       ["volume-2", "volume-1", "bluetooth"], ["search", "sliders-horizontal", "toggle-left"]))
    if kind == "mac" and shell:
        items = _menu_items(ctx, menus, "the menu bar") if not spec["web"] else "".join(
            f'<div class="mb">{m}</div>' for m in ["File", "Edit", "View", "History", "Bookmarks", "Window", "Help"])
        appname = esc(app.get("app", title.split(" — ")[-1].split(" - ")[-1])) if not spec["web"] else "Browser"
        top_os = (f'<div class="osbar{"" if dark or rng.random() < 0.4 else " light"}">{ctx.deco("apple", "command", "aperture", "hexagon")}'
                  f'<div class="mb b">{appname}</div>{items}<div class="sp"></div>{status}<span>{clock}</span></div>')
        if floating:
            icons_ = "".join(f'<div class="di" style="background:{ctx.d.color()}">{i}</div>' for i in ctx.deco_some(_DOCK, rng.randint(7, 13)))
            bottom_os = f'<div class="dock">{icons_}</div>'
    elif kind == "win" and shell:
        tis = "".join(f'<div class="ti{" on" if i == 2 else ""}">{ic}</div>' for i, ic in enumerate(ctx.deco_some(_DOCK, rng.randint(5, 9))))
        start = f'<div class="ti">{ctx.deco("layout-grid", "grid-2x2", "app-window", "grip")}</div><div class="ti">{ctx.deco("search", "text-search", "scan-search")}</div>'
        bottom_os = (f'<div class="taskbar{"" if dark else " light"}">{start}<div style="width:8px"></div>{tis}<div class="sp"></div>'
                     f'<div class="row g8" style="font-size:12px">{status}<span>{clock.split("  ")[1]}</span></div></div>')
    elif kind == "gnome" and shell:
        top_os = f'<div class="osbar"><span class="b">Activities</span><div class="sp"></div><span>{clock}</span><div class="sp"></div>{status}</div>'

    if spec["web"]:
        head = _browser(ctx, kind, app)
    else:
        ico = '<div class="appico"></div>'
        if kind == "mac":
            head = f'<div class="tbar mac">{_controls(ctx, "mac")}<div class="ttl">{esc(title)}</div></div>'
        elif kind == "win":
            head = f'<div class="tbar win">{ico}<span class="el">{esc(title)}</span>{_controls(ctx, "win")}</div>'
        else:
            head = f'<div class="tbar gnome"><div class="ttl">{esc(title)}</div><div class="sp"></div>{_controls(ctx, "gnome")}</div>'
        if menus and not (kind == "mac"):
            head += f'<div class="mbar">{_menu_items(ctx, menus, "the menu bar")}</div>'

    v = dict(spec["theme"]["vars"])
    v.update(spec["style"]["vars"])
    hue = rng.randint(0, 359)
    v["--wall"] = (f"linear-gradient({rng.randint(110, 160)}deg,hsl({hue} {rng.randint(35, 60)}% {rng.randint(28, 46)}%),"
                   f"hsl({(hue + rng.randint(30, 80)) % 360} {rng.randint(40, 65)}% {rng.randint(14, 26)}%))") if floating else v["--bg2"]
    v["--font"] = f'"{spec["style"]["font"]}"'
    v["--mono"] = f'"{spec["style"]["mono"]}"'
    v["--wr"] = {"mac": "10px", "win": "8px", "gnome": "12px"}[kind]
    v["--inset"] = spec.get("inset", "0")
    ac = spec["theme"]["accent"]
    v["--sdk"] = mix(ac, "#0c0e1a", 0.70)
    v["--sdkf"] = "#f3f3f6"
    v["--sdkm"] = "#b8bccb"
    root = ";".join(f"{k}:{val}" for k, val in v.items())
    cls = f's-{spec["style"]["btn"]} n-{spec["style"]["navsel"]}'
    return (
        '<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/base.css">'
        f"<style>:root{{{root}}}{app.get('css', '')}</style></head><body class=\"{cls}\"><div id=\"desk\">{top_os}"
        f'<div id="stage" class="{"inset" if floating else ""}"><div id="win" class="{"float" if floating else ""}">'
        f'{head}{app["body"]}</div></div>{bottom_os}</div></body></html>'
    )
