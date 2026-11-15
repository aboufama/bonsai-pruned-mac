"""Overlay states drawn on top of a finished screen: an open menu-bar menu, a context menu, an
open dropdown, a tooltip, an overflow or account popover, or a modal dialog. Elements hidden
under an overlay stop being targets automatically (the page scan checks what is on top)."""
from .splits import free_owner, is_generic, pool
from .ui import esc, CHEV_D
from .vocab import C, P

# ---- vocabulary used only by overlays ---------------------------------------------------------
C("dlg.dontsave", "Don't save|Discard changes|Close without saving", "", "throw away my edits and carry on|abandon what I changed and move on|let my unsaved work go")
C("dlg.create", "Create|Add it|Make it", "", "finish making the new entry with these details|confirm these details and make the new entry|go ahead and make the entry I just filled in")
C("dlg.signout", "Sign out|Log out|End session", "log-out|door-open|power", "leave my account on this device|stop being logged in here|disconnect my user from this app")
C("dlg.replace", "Replace|Overwrite|Use new version", "", "let the new one take the place of the old one|write over the existing one|swap the old one out for the new one")
C("dlg.keep", "Keep both|Keep separate copies|Keep the two", "", "hold on to the old and the new side by side|retain the existing one and the incoming one together|end up with the pair rather than choosing")
C("dlg.learn", "Learn more|Read details|Find out more", "", "read an explanation of what this means|get more background before deciding|see the documentation about this prompt")
C("dlg.dontask", "Don't ask again|Remember my choice|Always do this", "", "stop this prompt from appearing in future|skip this question from now on|make this decision stick for next time")
C("dlg.copylink", "Copy invite link|Copy sharing link|Copy access link", "link|link-2|clipboard-copy", "grab a URL I can paste to give someone access|put the access URL on my clipboard|get an address others can use to join")
C("dlg.browse", "Browse|Choose file|Pick a file", "", "choose something from my disk instead of typing a path|look through my folders to select one|select the location using the file chooser")

HELP_ITEMS = P("hm", [
    ("Keyboard shortcuts", "see the list of key combinations"), ("Release notes", "read what changed in the latest version"),
    ("Report a problem", "tell the developers that something is broken"), ("Check for updates", "see whether a newer version is available"),
    ("About this app", "see the version number and credits"), ("Contact support", "reach a human who can assist me"),
    ("Video tutorials", "watch a walkthrough of the features"), ("Send feedback", "tell the team what I think of the product"),
    ("Privacy policy", "read how my information is handled"), ("What's new", "see the recently added features"),
    ("Community forum", "ask other users a question"), ("Getting started guide", "go through the beginner walkthrough"),
    ("License information", "see the legal terms the software ships under"), ("System status", "check whether the service is having an outage"),
    ("Tip of the day", "see a quick hint about a feature I may not know"),
])
WINDOW_ITEMS = P("wm", [
    ("New window", "get a second window of this app"), ("Bring all to front", "raise every window of this app above the others"),
    ("Next tab", "switch to the tab to the right"), ("Previous tab", "switch to the tab to the left"),
    ("Move to other display", "send the window over to my second monitor"), ("Tile left", "snap the window to the left half of the screen"),
    ("Tile right", "snap the window to the right half of the screen"), ("Merge all windows", "combine every open window into one with tabs"),
    ("Show tab bar", "make the strip of tabs visible"), ("Enter picture in picture", "float this in a small always-visible box"),
    ("Reset layout", "put all the panes back where they were originally"), ("Detach panel", "pull this pane out into its own floating window"),
    ("Always on top", "keep this window above all the others"), ("Center window", "put the window in the middle of the screen"),
    ("Split view", "show two things next to each other in one window"),
])
ACCOUNT_ITEMS = P("am", [
    ("Manage subscription", "change or cancel the plan I pay for"), ("Switch workspace", "change over to a different organization"),
    ("Billing history", "look at my past invoices and payments"), ("Appearance", "choose between the light and dark look"),
    ("Language", "change which language the interface uses"), ("Invite teammates", "bring more colleagues into this workspace"),
    ("Security checkup", "review my passwords and two-step verification"), ("Connected apps", "see which third-party services are linked"),
    ("Usage and limits", "see how much of my quota I have consumed"), ("Add another account", "sign in with a second identity as well"),
    ("Download desktop app", "get the installable version for my computer"), ("Referral rewards", "see what I earn for recommending this to friends"),
    ("API tokens", "create credentials for scripts to access my data"), ("Status: Away", "change whether others see me as available"),
    ("Notification schedule", "set quiet hours when I won't be disturbed"),
])
FORM_FIELDS = """Full name|Email address|Phone number|Company|Job title|Street address|City|Postal code|Country|Website
Notes|Department|Start date|Budget|Owner|Description|Username|Display name|Time zone|Tax ID|Reference code|Nickname
Project name|Due date|Location|Category|Priority|Assignee|Summary|Team|Invoice number|Coupon code|Card holder
Middle initial|Suite or unit|Region|Fax number|Mobile number|Cost center|Manager|Alias|Building|Employee ID|Subject line
Reply-to address|Short bio|Pronouns|Billing contact|Delivery window|Purchase order""".replace("\n", "|").split("|")
EXPORT_OPTS = """Include headers|Selected rows only|Compress output|Include hidden columns|Embed fonts|Flatten layers
Include comments|Password protect|Use high quality|Strip metadata|Include attachments|Open when done|Append date to name
Include archived items|Preserve formatting|Split into multiple files|Include change history|Use relative paths
Add page numbers|Include speaker notes|Transparent background|Convert text to outlines|Include summary sheet
Skip empty rows|Anonymize names""".replace("\n", "|").split("|")
FORMATS = ["PDF document", "CSV (comma separated)", "Excel workbook", "PNG image", "JSON", "Plain text", "Markdown", "ZIP archive", "HTML page", "XML"]
ROLES = ["Viewer", "Commenter", "Editor", "Owner", "Admin", "Guest", "Can view", "Can edit", "Full access"]
DIALOG_TITLES = {
    "form": ["New project", "Add contact", "Create event", "New record", "Add team member", "Create workspace", "New customer", "Add shipping address"],
    "confirm": [("Delete {n} items?", "These items will be removed from all devices. This action cannot be undone.", "delete"),
                ("Replace existing file?", "A file with this name already exists in the destination folder.", "dlg.replace"),
                ("Sign out of this device?", "You will need your password to sign back in. Unsynced drafts stay on this computer.", "dlg.signout"),
                ("Remove from shared folder?", "Collaborators will lose access immediately.", "delete")],
}

# which modal layouts each split may show
MODALS = {
    "train": ["confirm", "form", "export", "rename", "picker", "palette"],
    "dev": ["unsaved", "share"],
    "test": ["sheet", "prefs"],
}

DEFAULT_MENUS = {
    "mb.file": ["new", "open", "-", "save", "saveas", "-", "import", "export", "-", "print", "share"],
    "mb.edit": ["undo", "redo", "-", "cut", "copy", "paste", "-", "duplicate", "delete", "-", "selectall", "search"],
    "mb.view": ["zoomin", "zoomout", "fullscreen", "-", "sidebar.toggle", "panel.toggle", "-", "refresh", "view.grid", "view.list"],
    "mb.help": HELP_ITEMS,
    "mb.window": ["win.min", "win.max", "-"] + WINDOW_ITEMS,
}
DEFAULT_CONTEXT = ["open", "-", "cut", "copy", "paste", "-", "rename", "duplicate", "move", "-", "share", "link", "info", "-", "delete"]


def _footer(ctx, region, primary, extra="", danger=False):
    return (f'<div class="df">{extra}<div class="sp"></div>{ctx.tbtn("cancel", region)}'
            f'{ctx.tbtn(primary, region, cls="pri" + (" dng" if False else ""))}</div>')


def _close_x(ctx, region):
    return ctx.ibtn("dlg.close", region, cls="s", anchor=None)


def modal(ctx, kind):
    rng, d, region = ctx.rng, ctx.d, "the dialog"
    back_cls = "back"
    if kind == "confirm":
        title, text, cid = rng.choice(DIALOG_TITLES["confirm"])
        title = title.format(n=rng.randint(2, 48))
        ico = ctx.deco("triangle-alert", "circle-alert", "octagon-alert", "shield-alert", "badge-alert", size=22)
        body = (f'<div class="dlg" style="width:{rng.choice([400, 440, 480])}px"><div class="db" style="padding-top:18px">'
                f'<div class="row g12 top"><div class="wrn">{ico}</div><div class="col g6"><div class="b lg">{esc(title)}</div>'
                f'<div class="mut">{esc(text)}</div></div></div></div>{_footer(ctx, region, cid)}</div>')
    elif kind == "form":
        title = rng.choice(DIALOG_TITLES["form"])
        names = d.take("form.fields", FORM_FIELDS, rng.randint(3, 6))
        people = d.people(3)
        rows = []
        for i, n in enumerate(names):
            val = rng.choice(["", "", people[0], "Q3 rollout", "42", d.date(True)])
            if i == 2 and len(names) > 3:
                rows.append(ctx.select(n, rng.choice(["Select…", "Standard", "None", "Default"]), region=region))
            else:
                rows.append(ctx.field(n, val, ph="", region=region))
        grid = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px 14px">{"".join(rows)}</div>' if len(rows) > 3 else "".join(rows)
        body = (f'<div class="dlg" style="width:{rng.choice([460, 520, 560])}px"><div class="dh"><span class="sp">{esc(title)}</span>{_close_x(ctx, region)}</div>'
                f'<div class="db">{grid}</div>{_footer(ctx, region, "dlg.create")}</div>')
    elif kind == "export":
        opts = d.take("export.opts", EXPORT_OPTS, rng.randint(3, 5))
        checks = "".join(ctx.check(o, rng.random() < 0.4, region=region) for o in opts)
        fmt = ctx.select("Format", rng.choice(FORMATS), region=region, w=220)
        dest = ctx.field("Destination", "~/Documents/exports", region=region, cls="mono")
        body = (f'<div class="dlg" style="width:{rng.choice([440, 480, 520])}px"><div class="dh"><span class="sp">Output settings</span>{_close_x(ctx, region)}</div>'
                f'<div class="db">{fmt}<div class="row g8" style="align-items:flex-end"><div class="f1">{dest}</div>{ctx.tbtn("dlg.browse", region)}</div>'
                f'<div class="col g8">{checks}</div></div>{_footer(ctx, region, "export")}</div>')
    elif kind == "rename":
        name = d.files("doc", 1)[0]
        body = (f'<div class="dlg" style="width:{rng.choice([360, 400, 440])}px"><div class="dh">Name this item</div>'
                f'<div class="db">{ctx.field("New name", name, region=region, focus=True)}</div>{_footer(ctx, region, "rename")}</div>')
    elif kind == "picker":
        places = "".join(ctx.nav(p, region, deco=("folder", "folder-closed", "folder-open", "hard-drive", "folders"), noun="folder", on=i == 1)
                         for i, p in enumerate(d.files("folder", 6)))
        rows = []
        for name, k in d.mixed_files(rng.randint(7, 10)):
            attr = ctx.reg("row", "file", name, region=region)
            rows.append(f'<div class="tr"{attr}><div class="td f">{ctx.deco("file", "file-text", "file-image", "file-code", blank=True)}<span class="el">{esc(name)}</span></div>'
                        f'<div class="td mut" style="width:110px">{d.date(True)}</div><div class="td mut r" style="width:80px">{d.size()}</div></div>')
        body = (f'<div class="dlg" style="width:{rng.choice([680, 740, 800])}px"><div class="dh"><span class="sp">Choose a file</span>{ctx.search(region, w=180)}</div>'
                f'<div class="row str bt" style="height:{rng.choice([280, 320, 360])}px"><div class="side br py8" style="width:170px">{places}</div>'
                f'<div class="col f1 clip">{"".join(rows)}</div></div>'
                f'<div class="df">{ctx.field("File name", "", ph="", region=region, w=240, above=False)}<div class="sp"></div>{ctx.tbtn("cancel", region)}{ctx.tbtn("open", region, cls="pri")}</div></div>')
    elif kind == "palette":
        entries = ctx.pick(["new", "open", "save", "export", "print", "share", "settings", "refresh", "fullscreen", "duplicate", "rename",
                            "history", "sidebar.toggle", "zoomin", "zoomout", "import", "help"], rng.randint(6, 9))
        cmd = ctx.field("Command", "", ph="Type a command…", region=region, above=False, cls="soft")
        listing = ctx.menu(entries, region, icons_=True, hi=0, noun="command").replace('class="menu"', 'class="pal"', 1)
        body = (f'<div class="dlg" style="width:{rng.choice([520, 580, 640])}px"><div class="p8 bb">{cmd}</div>'
                f'<div style="padding:4px">{listing}</div></div>')
        back_cls = "back topa"
        body = f'<div style="margin-top:{rng.choice([70, 90, 120])}px">{body}</div>'
    elif kind == "unsaved":
        doc = d.files("doc", 1)[0]
        ico = f'<div class="thumb" style="width:52px;height:52px;border-radius:12px;--c1:var(--ac);--c2:var(--acs2)"></div>'
        btns = "".join(f'<div style="display:flex;flex-direction:column">{b}</div>' for b in (
            ctx.tbtn("save", region, cls="pri lgb"), ctx.tbtn("dlg.dontsave", region, cls="lgb"), ctx.tbtn("cancel", region, cls="lgb")))
        body = (f'<div class="dlg" style="width:{rng.choice([280, 300, 320])}px;border-radius:14px"><div class="col g10 p20" style="align-items:center;text-align:center">{ico}'
                f'<div class="b lg">Do you want to keep the changes made to “{esc(doc)}”?</div><div class="mut sm">Your changes will be lost if you choose not to keep them.</div>'
                f'<div class="col g6 w100" style="margin-top:6px">{btns}</div></div></div>')
    elif kind == "share":
        people = d.people(rng.randint(3, 5))
        rows = []
        for p in people:
            sel = ctx.select(f"Role for {p}", rng.choice(ROLES), region=region, w=120, above=False, cls="soft",
                             refs=[f"the role dropdown for {p}", f"the permission dropdown next to {p}", f"{p}'s access level dropdown"])
            rows.append(f'<div class="row g10">{ctx.av(p, 30)}<div class="col f1"><span class="m">{esc(p)}</span><span class="mut sm">{esc(d.email_of(p))}</span></div>{sel}</div>')
        body = (f'<div class="dlg" style="width:{rng.choice([480, 520, 560])}px"><div class="dh"><span class="sp">Share “{esc(d.files("doc", 1)[0])}”</span>{_close_x(ctx, region)}</div>'
                f'<div class="db"><div class="row g8"><div class="f1">{ctx.field("Add people", "", ph="Add people by name or email", region=region, above=False)}</div>{ctx.tbtn("share", region, cls="pri", func=False)}</div>'
                f'<div class="col g10">{"".join(rows)}</div></div>'
                f'<div class="df">{ctx.tbtn("dlg.copylink", region, icon=True, cls="ghost")}<div class="sp"></div>{ctx.tbtn("done", region, cls="pri")}</div></div>')
    elif kind == "sheet":
        title, text, cid = rng.choice(DIALOG_TITLES["confirm"])
        body = (f'<div class="dlg" style="width:{rng.choice([460, 520])}px;border-radius:0 0 10px 10px;border-top:none"><div class="db" style="padding-top:16px">'
                f'<div class="b lg">{esc(title.format(n=rng.randint(2, 30)))}</div><div class="mut">{esc(text)}</div>{ctx.check(ctx.lab("dlg.dontask"), False, region=region, cid="dlg.dontask") if ctx.has("dlg.dontask") else ""}</div>'
                f'<div class="row g8 p12" style="padding-top:0">{ctx.tbtn("dlg.learn", region, cls="ghost")}<div class="sp"></div>{ctx.tbtn("cancel", region)}{ctx.tbtn(cid, region, cls="pri")}</div></div>')
        back_cls = "back topa"
    else:  # prefs
        secs = d.take("prefs.sections", ["General", "Editor", "Sync", "Shortcuts", "Privacy", "Network", "Advanced", "Backups", "Plugins", "Accounts",
                                         "Updates", "Fonts", "Colors", "Proxy", "Sharing"], 5)
        left = "".join(ctx.nav(s, region, noun="section", on=i == 0) for i, s in enumerate(secs))
        from .archetypes.settings import TOGGLES  # shared pool of settings switches
        togs = ctx.pick(TOGGLES, 5)
        right = "".join(ctx.toggle_row(ctx.lab(c), rng.random() < 0.5, region=region, cid=c, cls="py8 bb") for c in togs)
        body = (f'<div class="dlg" style="width:{rng.choice([620, 680])}px"><div class="row str" style="height:{rng.choice([340, 380])}px">'
                f'<div class="side br py8" style="width:170px">{left}</div><div class="col f1 p16">{right}</div></div>'
                f'<div class="df">{ctx.tbtn("clear", region, cls="ghost")}<div class="sp"></div>{ctx.tbtn("cancel", region)}{ctx.tbtn("save", region, cls="pri")}</div></div>')
    return {"id": "modal", "place": "modal", "html": f'<div class="{back_cls}">{body}</div>'}


def add(ctx, kinds=None):
    """Pick one overlay that the screen can host. Returns (name, [specs])."""
    rng = ctx.rng
    menus = dict(DEFAULT_MENUS)
    menus.update(ctx.menus)
    bar = [t for t in ctx.anchors["menubar"] if ctx.targets[t].cid in menus]
    options = [("modal", 3)]
    if bar:
        options.append(("menu", 4))
    if ctx.anchors["row"]:
        options.append(("context", 3))
    if ctx.anchors["select"]:
        options.append(("select", 2))
    if ctx.anchors["icon"]:
        options.append(("tooltip", 2))
    if ctx.anchors["more"]:
        options.append(("more", 2))
    if ctx.anchors["account"]:
        options.append(("account", 1))
    if kinds:
        options = [o for o in options if o[0] in kinds] or options
    name = rng.choices([o[0] for o in options], [o[1] for o in options])[0]
    if name == "modal":
        return "modal", [modal(ctx, rng.choice(MODALS[ctx.split]))]
    if name == "menu":
        tid = rng.choice(bar)
        html = ctx.menu(menus[ctx.targets[tid].cid], "the open menu", hi=rng.choice([None, 0, 1, 2, 3]),
                        checks=rng.random() < 0.2)
        return "menu", [{"id": "menu", "place": "below-start", "anchor": tid, "html": html, "mark": "open"}]
    if name == "context":
        tid = rng.choice(ctx.anchors["row"])
        html = ctx.menu(ctx.ctxmenu or DEFAULT_CONTEXT, "the context menu", obj=ctx.ctxobj, icons_=rng.random() < 0.5)
        return "context", [{"id": "context", "place": "point", "anchor": tid, "html": html,
                            "fx": rng.uniform(0.15, 0.6), "fy": rng.uniform(0.4, 0.8)}]
    if name == "select":
        tid = rng.choice(ctx.anchors["select"])
        t = ctx.targets[tid]
        rows = []
        for i, opt in enumerate(ctx.options[tid]):
            mine = is_generic(opt) or free_owner(opt) == ctx.split
            attr = ctx.reg("option", "option", opt, region="the open dropdown") if mine else ""
            rows.append(f'<div class="mi{" on" if i == 1 else ""}"{attr}><span>{esc(opt)}</span></div>')
        return "select", [{"id": "select", "place": "below-start", "anchor": tid, "html": f'<div class="menu" style="min-width:150px">{"".join(rows)}</div>'}]
    if name == "tooltip":
        tid = rng.choice(ctx.anchors["icon"])
        tip = f'<div class="tip{" lt" if rng.random() < 0.2 else ""}" data-o="{tid}">{esc(ctx.targets[tid].label)}</div>'
        return "tooltip", [{"id": "tooltip", "place": rng.choice(["below-center", "below-center", "above-center"]), "anchor": tid, "html": tip}]
    if name == "more":
        tid = rng.choice(ctx.anchors["more"])
        html = ctx.menu(ctx.ctxmenu or DEFAULT_CONTEXT, "the open menu", obj=ctx.ctxobj, icons_=rng.random() < 0.6)
        return "more", [{"id": "more", "place": "below-end", "anchor": tid, "html": html, "mark": "on"}]
    tid = rng.choice(ctx.anchors["account"])
    who = ctx.d.person()
    head = f'<div class="row g8 p8">{ctx.av(who, 32)}<div class="col"><span class="b">{esc(who)}</span><span class="mut sm">{esc(ctx.d.email_of(who))}</span></div></div><div class="msep"></div>'
    items = ctx.pick(ACCOUNT_ITEMS, 5) + ["-", "settings", "help", "-", "dlg.signout"]
    html = ctx.menu(items, "the account menu").replace('<div class="menu">', '<div class="menu" style="width:250px">' + head, 1)
    return "account", [{"id": "account", "place": "below-end", "anchor": tid, "html": html}]
