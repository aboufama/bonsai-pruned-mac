"""File managers: desktop explorers and a web drive."""
from ..ui import CHEV_D, CHEV_R, esc
from ..vocab import C

NAME = "files"
KIND = "either"
VARIANTS = {"list_details": "train", "icon_grid": "train", "column_view": "train", "tree_dual": "dev", "web_drive": "test"}

C("fs.newfolder", "New folder|Create folder|Add directory", "folder-plus|folder-open-dot|folder-dot", "make an empty directory right here|set up an empty directory in this location|start a blank container for documents in this spot")
C("fs.preview", "Preview|Quick look|Peek", "eye|scan-eye|view", "glance at what is inside {o} without launching an app|see the contents of {o} at a glance|take a fast look inside {o} without fully opening it", o="the selected file")
C("fs.compress", "Compress|Zip|Create archive", "file-archive|folder-archive|package", "pack {o} into one smaller bundle|squeeze {o} into a single bundled download|bundle {o} up so it takes less space", o="the selected items")
C("fs.openwith", "Open with|Open in app|Choose application", "app-window|square-arrow-out-up-right|app-window-mac", "pick which program should load {o}|launch {o} in a program other than the default|decide what software handles {o}", o="the selected file")
C("fs.terminal", "Open in terminal|Shell here|Command line here", "terminal|square-terminal|file-terminal", "get a command prompt already pointed at this directory|start typing commands in this location|bring up a prompt whose working directory is this one")
C("fs.eject", "Eject|Unmount|Safely remove", "eject|circle-arrow-up|hard-drive-upload", "disconnect {o} so it can be unplugged|release {o} before pulling the cable|detach {o} from this computer", o="this drive")
C("fs.emptytrash", "Empty trash|Empty bin|Purge deleted files", "", "permanently wipe everything that was thrown away|erase all discarded items for good|clear out the discarded items forever")
C("fs.view.columns", "Column view|Columns|Side-by-side panes", "columns-3|columns-2|columns-4", "browse with one sliding pane per level of nesting|show each level of nesting in its own vertical strip|lay the hierarchy out as adjacent vertical strips")
C("fs.recent", "Recent|Recents|Recently opened", "clock-3|clock-9|clock-fading", "see the items I worked on lately|find what I touched in the last few days|list the things I used most lately")
C("fs.trash", "Trash can|Wastebasket|Discarded files", "archive-x|folder-x|octagon-x", "look through the things I threw away|recover something I got rid of by mistake|see what is waiting to be erased for good")
C("fs.network", "Network|Shared drives|Servers", "network|server|ethernet-port|router", "browse other computers on the office LAN|reach storage hosted on other machines|connect to remote volumes")
C("fs.cloud", "Cloud drive|Online storage|My drive", "cloud|cloud-check|cloudy", "browse the documents kept on the internet service|see what I have stored remotely|go to my remotely hosted documents")
C("fs.shared", "Shared with me|Shared|From others", "users|users-round|user-round-check", "see items other people gave me access to|find what colleagues have passed to me|list the things that belong to somebody else but I can open")
C("fs.pinned", "Pinned items|Quick access|Bookmarked", "pin|bookmark|star|square-star|circle-star", "jump to the places I marked to keep handy|get to my shortcut locations|reach the spots I saved for fast access")
C("fs.pathedit", "Edit path|Type a location|Go to folder", "", "enter the address of a directory by hand|jump somewhere by typing its full address|key in where I want to go")
C("fs.iconsize", "Icon size|Thumbnail size|Tile zoom", "", "make the item pictures larger or smaller|scale the previews of the entries up or down|change how big each entry is drawn")
C("fs.showinfo", "Show details pane|Info panel|Inspector", "panel-right|info|panel-right-open", "{show} the strip with metadata about the selection|{show} the column of facts about what is selected|{show} the area describing the selection")
VOLUMES = ["Macintosh HD", "Backup Disk", "USB Drive", "SD Card", "Time Capsule", "Data (D:)", "Local Disk (C:)", "NAS Media", "Photos SSD",
           "Archive HDD", "Work Laptop", "Team Share", "Scratch Disk", "Recovery", "Install Media", "Camera Card", "Render Farm", "Vault", "Lab Server", "Old iMac"]
TAGS = ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Gray", "Important", "Home", "In progress", "To review", "Archive later",
        "Client A", "Tax 2025", "Print queue", "Waiting", "Reference", "Keepers", "Confidential", "Draft"]
FILTERS = ["Type", "People", "Modified", "Location", "Owner", "File size", "Shared by", "Created", "Extension", "Status", "Label", "Source",
           "Last opened", "Has comments", "Starred"]
FOPTS = ["Documents", "Spreadsheets", "Images", "Videos", "Audio", "Archives", "Anyone", "Only me", "Today", "Last 7 days", "This year", "Larger than 10 MB"]
ICON = {"doc": ("file-text", "file-type", "file-pen", "notepad-text", "file-pen-line", "scroll-text", "file-type-2"),
        "sheet": ("file-spreadsheet", "file-chart-column", "sheet", "table-2", "file-digit", "file-chart-pie", "file-chart-line"),
        "image": ("file-image", "images", "image-play", "camera", "file-scan", "book-image"),
        "code": ("file-code", "file-json", "file-braces", "braces", "file-code-2", "code-xml", "square-code"),
        "media": ("file-video", "file-audio", "film", "clapperboard", "file-play", "file-music", "file-volume"),
        "folder": ("folder", "folder-closed", "folders", "folder-open", "folder-dot")}
# plain page / folder outlines for splits whose icon subset has no glyph for a kind (not from the icon set)
_PAGE = '<path d="M6 2.5h8l4.5 4.5v14.5H6z"/><path d="M14 2.5V7h4.5"/><path d="M9 12.5h6M9 16h6"/>'
_DIR = '<path d="M3 6.5h6l2 2.5h10v10.5H3z"/>'
KINDNAME = {"doc": "Document", "sheet": "Spreadsheet", "image": "Image", "code": "Source code", "media": "Media", "folder": "Folder"}
FCOL = {"doc": "#3b82f6", "sheet": "#16a34a", "image": "#d946ef", "code": "#f59e0b", "media": "#ef4444", "folder": "var(--ac)"}
CTX = ["open", "fs.openwith", "fs.preview", "-", "cut", "copy", "paste", "-", "rename", "duplicate", "fs.compress", "move", "-", "share", "link",
       "tagit", "info", "-", "delete"]

CSS = """
.fs-tile{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 6px;border-radius:var(--r2);flex:none;text-align:center}
.fs-tile.sel{background:var(--acs2)}
.fs-tile .nm{max-width:100%;font-size:.92em;line-height:1.25;word-break:break-word}
.fs-ico{display:flex;align-items:center;justify-content:center;border-radius:8px}
.fs-crumb{display:flex;align-items:center;height:var(--ch);padding:0 6px;border-radius:var(--r);white-space:nowrap}
.fs-col{flex:none;display:flex;flex-direction:column;border-right:1px solid var(--bd);overflow:hidden;padding:4px 0}
.fs-kv{display:grid;grid-template-columns:auto 1fr;gap:5px 12px;font-size:.92em}
"""


def _ico(ctx, kind, size=None, tint=True):
    svg = ctx.deco(*ICON[kind], size=size)
    if not svg:
        dim = f"width:{size}px;height:{size}px" if size else "width:var(--is);height:var(--is)"
        svg = (f'<svg viewBox="0 0 24 24" style="{dim};flex:none;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linejoin:round;stroke-linecap:round">'
               f'{_DIR if kind == "folder" else _PAGE}</svg>')
    return f'<span style="color:{FCOL[kind]};display:flex">{svg}</span>' if tint else svg


def _items(ctx, n_files, n_folders):
    """Folders (for places and listing) and files, all with distinct names."""
    d = ctx.d
    folders = d.files("folder", 60)
    files = d.mixed_files(n_files)
    return folders, files


def _slider(ctx, cid, frac, region, w):
    """A slider with no visible caption: only functional instructions make sense for it."""
    if not ctx.has(cid):
        return ""
    attr = ctx.reg("slider", "slider", ctx.lab(cid), cid=cid, region=region, direct=False)
    pct = round(frac * 100)
    return (f'<div class="sld"{attr} style="width:{w}px;flex:none"><div class="fill" style="width:{pct}%"></div>'
            f'<div class="th" style="left:{pct}%"></div></div>')


def _avatar(ctx, me, region, size=26):
    if not ctx.has("account"):
        return ctx.av(me, size)
    attr = ctx.reg("button", "avatar", ctx.lab("account"), ui="icon", cid="account", region=region, anchor="account")
    return f'<div class="row"{attr}>{ctx.av(me, size)}</div>'


def _sidebar(ctx, places, w, region="the sidebar", tags=True):
    rng, d = ctx.rng, ctx.d
    fav = "".join(ctx.navc(c, region, noun="location") for c in ctx.pick(["fs.recent", "fs.pinned", "fs.cloud", "fs.shared"], 3))
    fav += "".join(ctx.nav(p, region, noun="folder", deco=ICON["folder"], on=i == 1) for i, p in enumerate(places))
    vols = []
    for v in d.take("fs.volumes", VOLUMES, rng.randint(2, 4)):
        ej = ctx.ibtn("fs.eject", region, row=v, obj=f"the {v} drive", cls="s", anchor=None)
        vols.append(ctx.nav(v, region, noun="drive", deco=("hard-drive", "server", "usb", "database", "disc"), tail=f'<span style="margin-left:auto">{ej}</span>'))
    extra = "".join(ctx.navc(c, region, noun="location") for c in ctx.avail(["fs.network", "fs.trash"]))
    tg = ""
    if tags:
        tg = '<div class="hd">Tags</div>' + "".join(
            ctx.nav(t, region, noun="tag", icon_html=f'<span class="dot" style="background:{d.color()};margin:0 4px"></span>')
            for t in d.take("fs.tags", TAGS, rng.randint(2, 4)))
    return (f'<div class="side br" style="width:{w}px"><div class="hd">Favorites</div><div class="col g2">{fav}</div>'
            f'<div class="hd">Locations</div><div class="col g2">{"".join(vols)}{extra}</div>{tg}</div>')


def _crumbs(ctx, parts, region="the path bar", fixed=2):
    """Path segments; the first `fixed` (root and user name) are plain text, the rest are targets."""
    out = []
    for i, p in enumerate(parts):
        attr = "" if i < fixed else ctx.reg("nav", "breadcrumb", p, region=region, refs=[f"{p} in the path bar", f"the {p} breadcrumb", f"the path segment {p}"])
        out.append(f'<div class="fs-crumb{" b" if i == len(parts) - 1 else " mut"}"{attr}>{esc(p)}</div>')
    return f'<span class="mut" style="display:flex">{CHEV_R}</span>'.join(out)


def _toolbar(ctx, parts, region="the file manager toolbar"):
    rng = ctx.rng
    nav = ctx.ibtn("back", region) + ctx.ibtn("forward", region) + ctx.ibtn("up", region)
    views = ctx.iseg(["view.list", "view.grid", "fs.view.columns"], rng.randrange(3), region=region)
    acts = ctx.ibtns(["fs.newfolder", "upload", "|", "share", "tagit", "fs.preview", "delete", "|", "sort"], region, obj="the selected file")
    acts += ctx.ibtn("more", region, obj="the selected file", anchor="more")
    path = f'<div class="row g2 f1 clip" style="min-width:0">{_crumbs(ctx, parts)}</div>'
    return (f'<div class="tb">{nav}<div class="vsep"></div>{path}{views}<div class="vsep"></div>{acts}'
            f'{ctx.search(region, w=rng.choice([180, 220, 260]), cls="soft")}</div>')


def _row(ctx, name, kind, region, sel=False, owner=None, actions=False, kindcol=True):
    d, rng = ctx.d, ctx.rng
    noun = "folder" if kind == "folder" else "file"
    attr = ctx.reg("row", noun, name, region=region, anchor="row")
    tail = ""
    if actions:
        obj = f"the {noun} {name}"
        tail = (f'<div class="td r" style="width:92px;gap:0">{ctx.ibtn("share", region, row=name, obj=obj, cls="s", anchor=None)}'
                f'{ctx.ibtn("fav", region, row=name, obj=obj, cls="s", anchor=None)}{ctx.ibtn("more", region, row=name, obj=obj, cls="s", anchor="more")}</div>')
    own = ""
    if owner:
        who = owner if rng.random() < 0.6 else "me"
        own = f'<div class="td" style="width:170px">{ctx.av(owner if who != "me" else ctx.me, 20)}<span class="el mut">{esc(who)}</span></div>'
    kc = f'<div class="td mut" style="width:120px">{KINDNAME[kind]}</div>' if kindcol else ""
    size = "—" if kind == "folder" else d.size()
    return (f'<div class="tr{" sel" if sel else ""}"{attr}><div class="td f">{_ico(ctx, kind)}<span class="el">{esc(name)}</span></div>{own}'
            f'<div class="td mut" style="width:130px">{d.date(True)}</div><div class="td mut r" style="width:86px">{size}</div>{kc}{tail}</div>')


def _header(owner=False, actions=False, kindcol=True):
    return ('<div class="tr h"><div class="td f">Name</div>' + ('<div class="td" style="width:170px">Owner</div>' if owner else "")
            + '<div class="td" style="width:130px">Date modified</div><div class="td r" style="width:86px">Size</div>'
            + ('<div class="td" style="width:120px">Kind</div>' if kindcol else "") + ('<div class="td" style="width:92px"></div>' if actions else "") + "</div>")


def _info(ctx, name, kind, w, region="the info panel"):
    d, rng = ctx.d, ctx.rng
    kv = "".join(f'<span class="mut">{k}</span><span>{esc(v)}</span>' for k, v in [
        ("Kind", KINDNAME[kind]), ("Size", d.size()), ("Created", d.date(True)), ("Modified", d.date(True)), ("Where", "~/" + rng.choice(["Work", "Shared", "Desktop"])),
        ("Dimensions", f"{rng.randint(800, 4000)} × {rng.randint(600, 3000)}")])
    btns = "".join(ctx.tbtn(c, region, cls="w100", icon=True, obj=f"the file {name}") for c in ctx.pick(["fs.openwith", "share", "fs.compress", "link"], 3))
    people = d.people(8)[5:8]
    acc = "".join(f'<div class="row g8">{ctx.av(p, 22)}<span class="f1 el">{esc(p)}</span><span class="mut xs">{rng.choice(["can edit", "can view", "owner"])}</span></div>' for p in people)
    return (f'<div class="side bl p12 g12" style="width:{w}px"><div class="row"><span class="b sp">Details</span>{ctx.ibtn("close.panel", region, cls="s", obj="the info panel")}</div>'
            f'{ctx.thumb(w - 24, int((w - 24) * 0.62), 6)}<div class="b" style="word-break:break-word">{esc(name)}</div><div class="fs-kv">{kv}</div>'
            f'<div class="hsep"></div><div class="col g6"><span class="xs mut up">Who has access</span>{acc}</div><div class="col g6">{btns}</div></div>')


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    W, H = spec["w"], spec["h"]
    me = ctx.me = d.person()
    folders, files = _items(ctx, H // 22 + 6, 0)
    places, sub, more_f = folders[:rng.randint(3, 5)], folders[5:5 + rng.randint(2, 5)], folders[10:]
    here = places[1] if len(places) > 1 else "Home"
    parts = [rng.choice(["Home", "Users", "Computer", "This PC"]), me.split()[0].lower(), here]
    ctx.ctxmenu, ctx.ctxobj = CTX, "the selected file"
    ctx.menus["mb.go"] = ["back", "forward", "up", "-", "fs.recent", "fs.cloud", "fs.network", "home", "-", "fs.pathedit", "fs.terminal"]
    sw = rng.choice([190, 210, 230]) + (30 if W > 1900 else 0)
    listing = [(f, "folder") for f in sub] + files
    seli = rng.randrange(len(sub), min(len(listing), len(sub) + 8))
    selname, selkind = listing[seli]
    free = f"{rng.randint(20, 900)}.{rng.randint(0, 9)} GB available"
    status = (f'<div class="sbar"><span>{len(listing)} items, 1 selected</span><span>{free}</span><div class="sp"></div>'
              f'{_slider(ctx, "fs.iconsize", rng.uniform(0.2, 0.8), "the status bar", 110)}</div>')
    region = "the file list"

    if variant == "list_details":
        rows = "".join(_row(ctx, n, k, region, i == seli) for i, (n, k) in enumerate(listing))
        main = f'<div class="col f1 clip">{_header()}<div class="col f1 clip rel">{rows}{ctx.scroll(3, 34)}</div></div>'
        body = f'<div class="col f1">{_toolbar(ctx, parts)}<div class="row str f1">{_sidebar(ctx, places, sw)}{main}</div>{status}</div>'
    elif variant == "icon_grid":
        big = rng.choice([64, 72, 88])
        tiles = []
        for i, (n, k) in enumerate(listing):
            attr = ctx.reg("row", "folder" if k == "folder" else "file", n, region=region, anchor="row")
            pic = (ctx.thumb(big + 20, big, 6) if k == "image" else
                   f'<div class="fs-ico" style="width:{big}px;height:{big}px">{_ico(ctx, k, size=int(big * 0.72))}</div>')
            tiles.append(f'<div class="fs-tile{" sel" if i == seli else ""}" style="width:{big + 44}px"{attr}>{pic}<span class="nm">{esc(n)}</span></div>')
        grid = f'<div class="row wrap top g8 p16 f1 clip" style="align-content:flex-start">{"".join(tiles)}</div>'
        info = _info(ctx, selname, selkind, rng.choice([260, 290, 320])) if W >= 1360 else ""
        body = f'<div class="col f1">{_toolbar(ctx, parts)}<div class="row str f1">{_sidebar(ctx, places, sw)}{grid}{info}</div>{status}</div>'
    elif variant == "column_view":
        cw = rng.choice([200, 220, 250])

        def col(items, sel, reg, chev=True):
            out = []
            for i, (n, k) in enumerate(items):
                attr = ctx.reg("row", "folder" if k == "folder" else "file", n, region=reg, anchor="row")
                arrow = f'<span class="mut" style="margin-left:auto;display:flex">{CHEV_R}</span>' if k == "folder" and chev else ""
                out.append(f'<div class="li{" sel" if i == sel else ""}"{attr}>{_ico(ctx, k)}<span class="el">{esc(n)}</span>{arrow}</div>')
            return f'<div class="fs-col" style="width:{cw}px">{"".join(out)}</div>'
        c1 = col([(p, "folder") for p in places + more_f[:rng.randint(3, 8)]], 1, "the first column")
        k2 = max(4, len(files) // 3)
        c2 = col([(f, "folder") for f in sub] + files[:k2], len(sub) - 1 if sub else 0, "the second column")
        c3items = files[k2:k2 + max(5, H // 30)]
        s3 = rng.randrange(len(c3items))
        c3 = col(c3items, s3, "the third column", chev=False)
        pn, pk = c3items[s3]
        kv = "".join(f'<span class="mut rt">{k}</span><span>{esc(v)}</span>' for k, v in [("Kind", KINDNAME[pk]), ("Size", d.size()), ("Created", d.date(True)), ("Modified", d.date(True)), ("Last opened", d.date(True))])
        prev = (f'<div class="col f1 clip g12 p20" style="align-items:center">{ctx.thumb(min(360, W // 5), min(240, W // 8), 8)}<div class="b lg">{esc(pn)}</div><div class="fs-kv">{kv}</div>'
                f'<div class="row g8">{ctx.tbtn("fs.openwith", "the preview column", obj=f"the file {pn}")}{ctx.tbtn("share", "the preview column", obj=f"the file {pn}")}{ctx.ibtn("more", "the preview column", cls="bdr", anchor="more")}</div></div>')
        body = (f'<div class="col f1">{_toolbar(ctx, parts + ([sub[-1]] if sub else []))}<div class="row str f1">{_sidebar(ctx, places[:2], sw, tags=False)}'
                f'{c1}{c2}{c3}{prev}</div>{status}</div>')
    elif variant == "tree_dual":
        tabs = ctx.tabs([here] + more_f[:rng.randint(1, 3)], 0, region="the tab bar", cls="box", closable=True, icon_fn=lambda _: _ico(ctx, "folder"))
        rib = "".join('<div class="vsep"></div>' if c == "|" else ctx.tbtn(c, "the command bar", cls="ghost", icon=True, obj="the selected file", caret=c in ("new", "sort"))
                      for c in ["new", "|", "cut", "copy", "paste", "rename", "share", "delete", "|", "sort", "fs.showinfo"])
        rib = f'<div class="tb plain">{rib}<div class="sp"></div>{ctx.ibtn("more", "the command bar", anchor="more")}</div>'
        addr = (f'<div class="tb">{ctx.ibtn("back", "the location bar")}{ctx.ibtn("forward", "the location bar")}{ctx.ibtn("up", "the location bar")}{ctx.ibtn("refresh", "the location bar", obj="this folder")}'
                f'<div class="inp f1" style="gap:2px">{_crumbs(ctx, parts, "the location bar")}</div>{ctx.search("the location bar", w=rng.choice([200, 240]))}</div>')
        tree = []
        nodes = [(p, 0, i == 1) for i, p in enumerate(places)]
        nodes[2:2] = [(s, 1, False) for s in sub]
        for n, depth, opened in nodes + [(m, 0, False) for m in more_f[:max(0, H // 26 - len(nodes) - 6)]]:
            attr = ctx.reg("nav", "folder", n, region="the folder tree")
            tw = ctx.reg("button", "arrow", f"Expand {n}", ui="icon", cid="expand" if not opened else "collapse", region="the folder tree", row=n,
                         obj=f"the {n} folder", func=False, refs=[f"the arrow next to {n} in the folder tree", f"the expand arrow for the {n} folder"])
            tree.append(f'<div class="nav{" on" if opened else ""}" style="padding-left:{8 + depth * 16}px;gap:5px"{attr}><span class="mut" style="display:flex;padding:3px"{tw}>{CHEV_D if opened else CHEV_R}</span>'
                        f'{_ico(ctx, "folder")}<span class="el">{esc(n)}</span></div>')
        left = f'<div class="side br py8 g2" style="width:{sw + 30}px">{"".join(tree)}</div>'
        k = max(6, (H - 330) // 24)
        rows = "".join(_row(ctx, n, kk, region, i == seli) for i, (n, kk) in enumerate(listing[:k + len(sub)]))
        strip = (f'<div class="row g16 p12 bt bg1" style="flex:none">{ctx.thumb(110, 76, 6)}<div class="col g4 f1"><span class="b">{esc(selname)}</span>'
                 f'<span class="mut sm">{KINDNAME[selkind]} · {d.size()} · modified {d.date(True)}</span><div class="row g6">{ctx.tbtn("tagit", "the details strip", cls="sm", obj=f"the file {selname}")}'
                 f'{ctx.tbtn("fs.preview", "the details strip", cls="sm", obj=f"the file {selname}")}{ctx.tbtn("info", "the details strip", cls="sm", obj=f"the file {selname}")}</div></div>'
                 f'<div class="col g4 mut sm rt"><span>Authors: {esc(me)}</span><span>Availability: on this device</span></div></div>')
        main = f'<div class="col f1 clip">{_header()}<div class="col f1 clip">{rows}</div>{strip}</div>'
        body = f'<div class="col f1">{tabs}{rib}{addr}<div class="row str f1">{left}{main}</div>{status}</div>'
    else:  # web_drive
        logo = '<div class="thumb" style="width:26px;height:26px;border-radius:7px;--c1:var(--ac);--c2:var(--acs2)"></div>'
        head = (f'<div class="row g12 bb px16" style="height:calc(var(--ch) + 26px)">{logo}<span class="b lg">{rng.choice(["Stash", "Depot", "Shelf", "Locker"])}</span><div style="width:30px"></div>'
                f'{ctx.search("the header", w=min(620, W // 3), cls="rnd soft")}<div class="sp"></div>{ctx.ibtn("help", "the header")}{ctx.ibtn("settings", "the header")}'
                f'{ctx.ibtn("apps", "the header")}{_avatar(ctx, me, "the header", 28)}</div>')
        nav = "".join(ctx.navc(c, "the sidebar", on=i == 0, noun="section") for i, c in enumerate(ctx.avail(["fs.cloud", "fs.shared", "fs.recent", "fs.pinned", "fs.trash"])))
        used = rng.randint(8, 92)
        side = (f'<div class="side br" style="width:{sw + 20}px"><div class="p12">{ctx.tbtn("new", "the sidebar", cls="pri lgb", icon=True, caret=True, obj="a file or folder")}</div><div class="col g2">{nav}</div>'
                f'<div class="hd">Folders</div><div class="col g2">{"".join(ctx.nav(p, "the sidebar", noun="folder", deco=ICON["folder"]) for p in places)}</div><div class="sp"></div>'
                f'<div class="col g6 p12 bt"><div class="prog"><div style="width:{used}%"></div></div><span class="xs mut">{used} GB of 100 GB used</span>{ctx.tbtn("upload", "the sidebar", cls="sm", icon=True)}</div></div>')
        fl = d.take("fs.filters", FILTERS, 3)
        chips = "".join(ctx.select(f, f, options=rng.sample(FOPTS, 4), region="the filter row", above=False, cls="rnd", w=rng.choice([110, 124])) for f in fl)
        crumb = f'<div class="row g2 lg">{_crumbs(ctx, [parts[0], here], fixed=1)}</div>'
        bar = (f'<div class="row g8 px16" style="padding-top:12px">{crumb}<div class="sp"></div>{ctx.iseg(["view.list", "view.grid"], 0, region="the filter row")}{ctx.ibtn("info", "the filter row", obj="this folder")}</div>'
               f'<div class="row g8 px16 py8">{chips}</div>')
        cards = []
        for n, k in files[:max(3, min(6, W // 330))]:
            attr = ctx.reg("row", "card", n, region="the suggested row", refs=[f"the suggested file {n}", f"the {n} card under Suggested"])
            cards.append(f'<div class="card col f1" style="min-width:0"{attr}>{ctx.thumb(40, 84, 0).replace("width:40px", "width:100%")}<div class="row g8 p8">{_ico(ctx, k)}<span class="el m">{esc(n)}</span></div></div>')
        rest = [(f, "folder") for f in sub] + files[6:]
        owners = d.people(len(rest) + 2)
        rows = "".join(_row(ctx, n, k, region, False, owner=owners[i], actions=True, kindcol=False) for i, (n, k) in enumerate(rest))
        main = (f'<div class="col f1 clip">{bar}<div class="xs mut up px16" style="padding-top:4px">Suggested</div><div class="row g12 px16 py8">{"".join(cards)}</div>'
                f'<div class="col f1 clip px16">{_header(owner=True, actions=True, kindcol=False)}{rows}</div></div>')
        body = f'<div class="col f1">{head}<div class="row str f1">{side}{main}</div></div>'
    return {"title": f"{here} — Files", "body": body, "css": CSS, "app": rng.choice(["Files", "File Manager", "Folders"]),
            "menus": ["mb.file", "mb.edit", "mb.view", "mb.go", "mb.window", "mb.help"], "url": "drive.example.com/folders/" + here.lower().replace(" ", "-")}
