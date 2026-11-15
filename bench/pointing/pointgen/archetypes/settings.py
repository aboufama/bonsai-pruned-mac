"""Settings / preferences windows."""
from .. import icons
from ..data import COMPANIES
from ..overlays import FORM_FIELDS
from ..ui import esc
from ..vocab import C, P

NAME = "settings"
KIND = "either"
VARIANTS = {"sidebar": "train", "tabs": "train", "mac_grid": "train", "cards": "dev", "two_level": "test"}

SECTIONS = P("set.sec", [
    ("General", "see the basic everyday preferences", "settings-2|sliders-vertical"),
    ("Appearance", "change the colors and look of the interface", "palette|paintbrush"),
    ("Notifications", "choose which alerts I receive", "bell|bell-ring"),
    ("Privacy & Security", "control who can see my data and how it is protected", "shield|shield-check"),
    ("Accounts", "manage the logins connected to this app", "users|user-round"),
    ("Billing", "see my plan and payment method", "credit-card|wallet"),
    ("Language & Region", "change the tongue and locale the interface uses", "languages|globe"),
    ("Keyboard", "adjust typing behavior and key repeat", "keyboard"),
    ("Accessibility", "make the interface easier to see, hear and operate", "accessibility|person-standing"),
    ("Storage", "see how much disk space is used", "hard-drive|database"),
    ("Network", "configure the internet connection and proxies", "network|ethernet-port"),
    ("Software Update", "check whether a newer version is available", "refresh-cw|download"),
    ("Advanced", "get to the expert-level switches", "wrench|flask-conical"),
    ("Displays", "arrange monitors and set resolution", "monitor|monitor-smartphone"),
    ("Sound", "pick speakers and adjust loudness", "volume-2|speaker"),
    ("Bluetooth", "pair wireless headphones and other nearby devices", "bluetooth"),
    ("Wi-Fi", "join a wireless hotspot", "wifi"),
    ("Battery", "see power usage and energy saving choices", "battery-medium|battery-charging"),
    ("Printers & Scanners", "set up a device for putting documents on paper", "printer"),
    ("Mouse & Trackpad", "change pointer speed and scrolling direction", "mouse|mouse-pointer-2"),
    ("Date & Time", "set the clock and time zone", "clock|calendar-clock"),
    ("Sharing", "let other computers reach my files and screen", "share-2|cast"),
    ("Users & Groups", "add or remove people who can log in to this computer", "users-round|user-cog"),
    ("Backup", "set up automatic safety copies of my data", "archive|cloud-upload"),
    ("Integrations", "connect third-party services to this workspace", "plug|blocks"),
    ("Team members", "invite or remove colleagues from the workspace", "user-plus|users"),
    ("API keys", "create credentials for programmatic access", "key|key-round"),
    ("Focus", "set up do-not-disturb schedules", "moon|circle-minus"),
    ("Wallpaper", "choose the desktop background picture", "image|wallpaper"),
    ("Passwords", "look up my saved logins", "lock-keyhole|key-square"),
    ("Extensions", "manage installed add-ons", "puzzle|blocks"),
    ("Search engine", "choose which service answers queries typed in the address bar", "search|globe"),
    ("Downloads", "choose where fetched files are stored", "download|folder-down"),
    ("Startup", "decide what opens when the app launches", "rocket|power"),
    ("Fonts", "pick typefaces and text size", "type|case-sensitive"),
    ("Labs", "try experimental features early", "flask-conical|test-tube"),
    ("Email preferences", "decide which newsletters and digests reach my inbox", "mail|mailbox"),
    ("Sessions", "see the devices where I am currently logged in", "monitor-smartphone|laptop"),
    ("Data export", "request a download of everything stored about me", "file-down|package"),
    ("Shortcuts", "customize key combinations for commands", "command|keyboard"),
])
TOGGLES = P("set.tog", [
    ("Launch at login", "{enable} starting this app automatically when I sign in to the computer"),
    ("Show in menu bar", "{show} the small status icon at the top of the screen"),
    ("Check spelling while typing", "{enable} the red squiggles under misspelled words"),
    ("Automatic updates", "{enable} installing new versions without asking me"),
    ("Send usage statistics", "{enable} sharing anonymous diagnostics with the developer"),
    ("Dark mode", "switch the interface between its bright and night-time color schemes"),
    ("Reduce motion", "turn {on} the option that tones down animations"),
    ("Play sound on new message", "turn {on} the chime for incoming messages"),
    ("Show line numbers", "{show} the numbering in the editor gutter"),
    ("Sync over cellular", "turn {on} syncing when I am on mobile data instead of wifi"),
    ("Two-factor authentication", "{enable} the extra verification code when signing in"),
    ("Desktop notifications", "turn {on} pop-up banners from this app"),
    ("Open links in new tab", "change whether clicked links replace the current page"),
    ("Remember window position", "{enable} restoring where the window was when I reopen the app"),
    ("Hardware acceleration", "{enable} using the graphics card to draw the interface"),
    ("Auto-save drafts", "{enable} keeping unfinished work automatically"),
    ("Show hidden files", "{show} files whose names start with a dot"),
    ("Compact layout", "turn {on} the tighter, denser spacing"),
    ("Smart quotes", "{enable} converting straight quotation marks into curly ones"),
    ("Weekly summary email", "turn {on} the digest that arrives every seven days"),
    ("Allow mentions from anyone", "{enable} letting people outside my team tag me"),
    ("Show read receipts", "{enable} letting others see when I have viewed their messages"),
    ("Block third-party cookies", "turn {on} protection against trackers from other sites"),
    ("Scroll past end", "{enable} scrolling beyond the last line of a document"),
    ("Word wrap", "turn {on} breaking long lines at the edge of the window"),
    ("Confirm before quitting", "{enable} the are-you-sure prompt when I close the app"),
    ("Use system proxy", "{enable} routing traffic through the operating system's proxy"),
    ("Natural scrolling", "turn {on} content following the direction my fingers move"),
    ("Tap to click", "{enable} clicking by lightly touching the trackpad"),
    ("Night Shift", "turn {on} the warmer screen tint in the evening"),
    ("Location services", "{enable} letting apps know where I am"),
    ("Show battery percentage", "{show} the numeric charge level"),
    ("Keep screen awake", "turn {on} preventing the display from sleeping"),
    ("Backup on Wi-Fi only", "{enable} limiting safety copies to wireless networks"),
    ("Enable beta features", "turn {on} early access to unfinished functionality"),
    ("Minimize to tray", "{enable} hiding to the notification area instead of closing"),
    ("Animate sidebar", "turn {on} the sliding effect for the navigation column"),
    ("Show preview pane", "{show} the area that displays a selected file's contents"),
    ("Group by conversation", "turn {on} threading related messages together"),
    ("Mark as read on scroll", "{enable} clearing unread status as I move past messages"),
    ("Autoplay videos", "turn {on} clips starting by themselves"),
    ("High contrast", "turn {on} stronger borders and bolder colors for visibility"),
    ("Share presence", "{enable} showing teammates whether I am online"),
    ("Require password on wake", "{enable} asking for my login after the computer sleeps"),
    ("Trim trailing whitespace", "{enable} removing spaces at line ends when saving"),
    ("Format on save", "{enable} tidying code automatically each time I store the file"),
    ("Show minimap", "{show} the zoomed-out code overview at the side"),
    ("Inline suggestions", "turn {on} grey completion text appearing as I type"),
    ("Sticky headers", "turn {on} keeping section titles pinned while scrolling"),
    ("Offline access", "{enable} using my documents without an internet connection"),
])
SELECTS = P("set.sel", [
    ("Theme", "choose between the light, dark and system looks"), ("Language", "change which tongue the menus are written in"),
    ("Font size", "make the text larger or smaller"), ("Default view", "pick which screen the app opens on"),
    ("Time format", "choose between 12-hour and 24-hour clocks"), ("Start week on", "pick the first day shown in calendars"),
    ("Auto-lock after", "set how long before the screen secures itself"), ("Default browser", "pick which program opens web links"),
    ("Download location", "choose the folder where fetched files land"), ("Sidebar position", "move the navigation column to the other side"),
    ("Accent color", "pick the highlight hue used for buttons and selections"), ("Refresh rate", "choose how many times per second the screen redraws"),
    ("Resolution", "set how many pixels the display uses"), ("Currency", "pick the money unit amounts are shown in"),
    ("Time zone", "set which region's clock to follow"), ("Measurement units", "switch between metric and imperial"),
    ("Tab size", "set how many spaces an indent uses"), ("Line endings", "choose between LF and CRLF"),
    ("Update channel", "pick between stable and preview releases"), ("Image quality", "choose how much pictures are compressed"),
    ("Notification sound", "pick the chime that plays for alerts"), ("Default calendar", "choose where new events are stored"),
    ("Output device", "pick which speakers or headphones audio plays through"), ("Input device", "choose which microphone is used"),
    ("Keyboard layout", "switch between QWERTY, AZERTY and other key arrangements"), ("Paper size", "choose between A4 and Letter"),
    ("Session timeout", "set how long I can be idle before being logged out"), ("Date format", "choose how day, month and year are ordered"),
    ("Cursor style", "pick between block, bar and underline carets"), ("Startup page", "choose what a new window displays first"),
])
OPTIONS = {
    "Theme": ["System", "Light", "Dark", "High contrast"], "Language": ["English (US)", "Deutsch", "Español", "Français", "日本語"],
    "Font size": ["Small", "Medium", "Large", "Extra large"], "Default view": ["Dashboard", "Inbox", "Last opened", "Calendar"],
    "Time format": ["12-hour", "24-hour"], "Start week on": ["Monday", "Sunday", "Saturday"],
    "Auto-lock after": ["1 minute", "5 minutes", "15 minutes", "1 hour", "Never"], "Default browser": ["Firefox", "Chromium", "Safari"],
    "Download location": ["Downloads", "Desktop", "Ask each time"], "Sidebar position": ["Left", "Right"],
    "Accent color": ["Blue", "Purple", "Pink", "Orange", "Graphite"], "Refresh rate": ["60 Hz", "120 Hz", "144 Hz"],
    "Resolution": ["1920 × 1080", "2560 × 1440", "3840 × 2160"], "Currency": ["USD ($)", "EUR (€)", "GBP (£)", "JPY (¥)"],
    "Time zone": ["UTC−08:00 Pacific", "UTC+00:00 London", "UTC+01:00 Berlin", "UTC+09:00 Tokyo"],
    "Measurement units": ["Metric", "Imperial"], "Tab size": ["2 spaces", "4 spaces", "8 spaces"], "Line endings": ["LF", "CRLF"],
    "Update channel": ["Stable", "Beta", "Nightly"], "Image quality": ["Low", "Balanced", "Original"],
    "Notification sound": ["Chime", "Ping", "Pop", "None"], "Default calendar": ["Personal", "Work", "Family"],
    "Output device": ["Built-in speakers", "Headphones", "HDMI display"], "Input device": ["Built-in microphone", "USB headset"],
    "Keyboard layout": ["US QWERTY", "UK", "German", "French AZERTY"], "Paper size": ["A4", "Letter", "Legal"],
    "Session timeout": ["15 minutes", "1 hour", "8 hours", "30 days"], "Date format": ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
    "Cursor style": ["Block", "Bar", "Underline"], "Startup page": ["Blank", "Home", "Restore previous session"],
}
SLIDERS = P("set.sld", [
    ("Brightness", "make the screen dimmer or brighter"), ("Volume", "make the sound louder or quieter"),
    ("Pointer speed", "change how fast the cursor travels"), ("Key repeat rate", "change how quickly a held key repeats"),
    ("Text size", "scale the lettering up or down with a drag"), ("Transparency", "change how see-through the panels are"),
    ("Zoom level", "scale the whole interface up or down"), ("Double-click speed", "change how quickly two presses must follow each other"),
    ("Alert volume", "change how loud warning sounds are"), ("Scroll speed", "change how far each wheel notch moves the content"),
    ("Dock size", "make the icon strip at the bottom larger or smaller"), ("Line height", "loosen or tighten the spacing between lines of text"),
    ("Balance", "shift the sound between the left and right speaker"), ("Animation speed", "make transitions faster or slower"),
    ("Blur radius", "soften or sharpen the frosted glass effect"),
])
C("set.reset", "Reset to defaults|Restore defaults|Revert to original", "", "put every option back the way it shipped|undo all my customizations at once|return all of these options to their factory values")
C("set.signout", "Sign out everywhere|Log out of all devices|End all sessions", "", "kick my login off every other computer and phone|disconnect all the other places where I am signed in|force every device to ask for my password again")
C("set.delacct", "Delete account|Close my account|Erase account", "", "permanently get rid of my whole membership and its data|shut down my membership for good|wipe my user and everything attached to it")
C("set.change", "Change|Update|Edit value", "", "alter {o}|set a different value for {o}|put in a new value for {o}", o="this setting")
C("set.upgrade", "Upgrade plan|Go premium|See paid plans", "", "move to a paid tier with more features|pay for the higher tier|get the more capable subscription")

GROUPS = ["Behavior", "Interface", "Experimental", "Defaults", "Performance", "Content", "Devices", "Permissions", "Editing",
          "Window", "Session", "Text", "Connectivity", "Media", "Workspace", "Conversations", "Safety", "Regional"]
DESC = ["Applies to all windows.", "Takes effect after restart.", "Recommended for most people.", "May affect battery life.",
        "Only on this device.", "Synced across your devices.", "Managed by your organization.", ""]


def _control(ctx, cid, region, kind=None):
    """One setting row: caption on the left, control on the right."""
    rng = ctx.rng
    label = ctx.lab(cid)
    desc = rng.choice(DESC)
    if cid.startswith("set.tog"):
        return ctx.toggle_row(label, rng.random() < 0.5, region=region, cid=cid, desc=desc, cls="py8")
    if cid.startswith("set.sel"):
        opts = OPTIONS[label]
        sel = ctx.select(label, rng.choice(opts), options=opts, region=region, cid=cid, above=False, w=rng.choice([150, 170, 190]))
    else:
        sel = ctx.slider(label, rng.uniform(0.15, 0.9), region=region, cid=cid, w=rng.choice([150, 180, 200]))
    text = f'<div class="col f1" style="min-width:0">{ctx.own(label, "m")}' + (f'<span class="mut sm">{esc(desc)}</span>' if desc else "") + "</div>"
    return f'<div class="row g12 py8">{text}{sel}</div>'


def _rows(ctx, region, n):
    rng = ctx.rng
    cids = ctx.pick(TOGGLES, max(2, n * 3 // 5)) + ctx.pick(SELECTS, max(1, n // 4)) + ctx.pick(SLIDERS, max(1, n // 6))
    rng.shuffle(cids)
    return [_control(ctx, c, region) for c in cids[:n]]


def _group(ctx, title, rows, card=True):
    inner = "".join(f'<div class="{"bb" if i < len(rows) - 1 else ""}">{r}</div>' for i, r in enumerate(rows))
    box = f'<div class="card px16">{inner}</div>' if card else f'<div>{inner}</div>'
    return f'<div class="col g6"><div class="b" style="margin-top:6px">{esc(title)}</div>{box}</div>'


def build(ctx, variant, spec):
    rng, d = ctx.rng, ctx.d
    secs = ctx.pick(SECTIONS, rng.randint(7, 13))
    sel = rng.randrange(len(secs))
    dense = spec["h"] >= 1000
    n_rows = rng.randint(9, 13) + (5 if dense else 0)
    title = rng.choice(["Settings", "Preferences", "System Settings", "Options", "Control Panel"])
    groups = rng.sample(GROUPS, 4)
    me = d.person()

    if variant == "sidebar":
        region = "the sidebar"
        nav = "".join(ctx.navc(c, region, on=i == sel, noun="section") for i, c in enumerate(secs))
        who = f'<div class="row g8 p12 bb">{ctx.av(me, 34)}<div class="col"><span class="b">{esc(me)}</span><span class="mut sm">{esc(d.email_of(me))}</span></div></div>' if rng.random() < 0.5 else ""
        side = f'<div class="side br" style="width:{rng.choice([210, 230, 250])}px">{who}<div class="p8">{ctx.search(region, cls="soft")}</div><div class="col g2">{nav}</div></div>'
        rows = _rows(ctx, "the settings list", n_rows)
        cut = [len(rows) // 3, 2 * len(rows) // 3]
        body = (_group(ctx, groups[0], rows[:cut[0]]) + _group(ctx, groups[1], rows[cut[0]:cut[1]]) + _group(ctx, groups[2], rows[cut[1]:]))
        foot = f'<div class="row g8" style="margin-top:8px">{ctx.tbtn("set.reset", "the settings list")}<div class="sp"></div>{ctx.tbtn("help", "the settings list", cls="ghost", icon=True)}</div>'
        main = (f'<div class="col f1 clip"><div class="col g12 p24" style="max-width:{rng.choice([720, 820, 900])}px;width:100%">'
                f'{body}{foot}</div></div>')
        html = f'<div class="row str f1">{side}{main}</div>'
    elif variant == "tabs":
        region = "the tab bar"
        tabs = ctx.tabs([(ctx.lab(c), c) for c in secs[:rng.randint(5, 8)]], active=min(sel, 4), region=region, cls=rng.choice(["", "box", "pl"]))
        rows = _rows(ctx, "the form", n_rows)
        half = (len(rows) + 1) // 2
        fields = d.take("form.fields", FORM_FIELDS, 4)
        ff = "".join(ctx.field(f, rng.choice([me, "", d.date(True), "Default"]), region="the form") for f in fields)
        left = _group(ctx, groups[0], rows[:half], card=False)
        right = _group(ctx, groups[1], rows[half:], card=False) + f'<div class="col g10" style="margin-top:10px"><div class="b">{esc(groups[2])}</div>{ff}</div>'
        foot = (f'<div class="row g8 p12 bt bg1">{ctx.tbtn("set.reset", "the button bar", cls="ghost")}<div class="sp"></div>'
                f'{ctx.tbtn("cancel", "the button bar")}{ctx.tbtn("save", "the button bar", cls="pri")}</div>')
        html = (f'<div class="col f1">{tabs}<div class="row top g24 f1 clip p20"><div class="col f1">{left}</div><div class="col f1">{right}</div></div>{foot}</div>')
    elif variant == "mac_grid":
        region = "the toolbar"
        panes = []
        for i, c in enumerate(secs[:rng.randint(6, 9)]):
            attr = ctx.reg("tab", "pane", ctx.lab(c), cid=c, region=region)
            ico = icons.svg(ctx.ico(c), size=24) if ctx.ico(c) else '<div style="width:24px;height:24px;border-radius:6px;background:var(--bg4)"></div>'
            panes.append(f'<div class="col g4 rad" style="align-items:center;padding:6px 10px;{"background:var(--bg4);" if i == sel % 6 else ""}"{attr}>'
                         f'<div class="{"acc" if i == sel % 6 else "mut"}">{ico}</div><span class="xs nw">{esc(ctx.lab(c))}</span></div>')
        bar = f'<div class="row cen g4 bg2 bb" style="padding:6px 8px">{"".join(panes)}</div>'
        cids = ctx.pick(TOGGLES, n_rows // 2) + ctx.pick(SELECTS, n_rows // 3) + ctx.pick(SLIDERS, 2)
        rng.shuffle(cids)
        lines = []
        for c in cids:
            label = ctx.lab(c)
            if c.startswith("set.tog"):
                ctl = ctx.check(label, rng.random() < 0.5, region="the form", cid=c)
                lines.append(f'<div></div><div>{ctl}</div>')
            elif c.startswith("set.sel"):
                ctl = ctx.select(label, rng.choice(OPTIONS[label]), options=OPTIONS[label], region="the form", cid=c, above=False, w=200)
                lines.append(f'<div class="rt">{ctx.own(label + ":")}</div><div>{ctl}</div>')
            else:
                ctl = ctx.slider(label, rng.uniform(0.2, 0.9), region="the form", cid=c, w=220)
                lines.append(f'<div class="rt">{ctx.own(label + ":")}</div><div class="row">{ctl}</div>')
        form = f'<div style="display:grid;grid-template-columns:{rng.choice([220, 260, 300])}px auto;gap:10px 12px;align-items:center;justify-content:center">{"".join(lines)}</div>'
        foot = f'<div class="row g8 p12 end">{ctx.ibtn("help", "the form", cls="bdr rnd")}<div class="sp"></div>{ctx.tbtn("set.reset", "the form")}</div>'
        html = f'<div class="col f1">{bar}<div class="col f1 clip" style="padding:24px 0">{form}</div>{foot}</div>'
    elif variant == "cards":
        region = "the top navigation"
        links = "".join(ctx.navc(c, region, noun="link", cls="", icon_html="") for c in secs[:5])
        top = (f'<div class="row g12 bb px16" style="height:52px"><div class="thumb" style="width:26px;height:26px;border-radius:7px;--c1:var(--ac);--c2:var(--acs2)"></div>'
               f'<span class="b lg">{esc(d.one("company", COMPANIES).split()[0])}</span><div class="row g2" style="margin-left:14px">{links}</div><div class="sp"></div>'
               f'{ctx.search(region, w=220, cls="rnd soft")}{ctx.ibtn("notif", region)}{ctx.ibtn("help", region)}{ctx.av(me, 28)}</div>')
        fields = [("Display name", me), ("Email address", d.email_of(me)), ("Phone number", "+1 555 01" + str(rng.randint(10, 99))), ("Time zone", "UTC+01:00 Berlin"),
                  ("Password", "Last changed " + d.date(True)), ("Recovery email", d.email_of(d.people(2)[1])), ("Username", me.split()[0].lower() + str(rng.randint(2, 99)))]
        rng.shuffle(fields)
        prof = []
        for lab, val in fields[:rng.randint(4, 6)]:
            btn = ctx.tbtn("set.change", "the profile card", cls="sm", row=lab, obj=f"my {lab.lower()}")
            prof.append(f'<div class="row g12 py8"><div class="mut" style="width:150px">{esc(lab)}</div><div class="f1 el">{esc(val)}</div>{btn}</div>')
        rows = _rows(ctx, "the preferences card", n_rows - 4)
        danger = (f'<div class="card p16 col g10" style="border-color:var(--err)"><div class="b err">Danger zone</div>'
                  f'<div class="row g12"><div class="f1 mut">Sessions on other devices will need to authenticate again.</div>{ctx.tbtn("set.signout", "the danger zone")}</div>'
                  f'<div class="row g12"><div class="f1 mut">This removes all projects, files and history. It cannot be reversed.</div>{ctx.tbtn("set.delacct", "the danger zone", cls="dng")}</div></div>')
        plan = (f'<div class="card p16 row g12"><div class="col f1"><span class="b">Current plan: {rng.choice(["Free", "Starter", "Team"])}</span>'
                f'<span class="mut sm">{rng.randint(2, 9)} of 10 seats used · renews {d.date(True)}</span></div>{ctx.tbtn("set.upgrade", "the plan card", cls="pri")}</div>')
        prof_html = "".join(f'<div class="bb">{p}</div>' for p in prof)
        col = (f'<div class="col g16" style="width:{rng.choice([680, 760, 820])}px;padding:24px 0"><div class="xxl b">Your account</div>'
               f'<div class="card px16">{prof_html}</div>{plan}{_group(ctx, groups[0], rows)}{danger}</div>')
        html = f'<div class="col f1">{top}<div class="row cen f1 clip bg1 top">{col}</div></div>'
    else:  # two_level
        region = "the icon rail"
        rail = "".join(ctx.ibtn(c, region, on=i == 1) for i, c in enumerate(["home", "search", "notif", "account", "apps"]))
        rail = f'<div class="rail br">{rail}<div class="sp"></div>{ctx.ibtn("help", region)}{ctx.ibtn("settings", region, on=True)}</div>'
        nav = "".join(ctx.navc(c, "the section list", on=i == sel, noun="section") for i, c in enumerate(secs))
        sub = f'<div class="side br" style="width:{rng.choice([200, 220, 240])}px"><div class="hd">{esc(title)}</div><div class="col g2">{nav}</div></div>'
        rows = _rows(ctx, "the settings list", n_rows)
        half = len(rows) // 2
        main = (f'<div class="col f1 clip p20 g12"><div class="row"><span class="xl b">{esc(ctx.lab(secs[sel]))}</span><div class="sp"></div>{ctx.search("the settings list", w=220)}</div>'
                f'{_group(ctx, groups[0], rows[:half])}{_group(ctx, groups[1], rows[half:])}'
                f'<div class="row g8">{ctx.tbtn("set.reset", "the settings list")}</div></div>')
        tips = "".join(f'<div class="col g4 py8 bb"><span class="m">{esc(t)}</span>{ctx.lines(2)}</div>' for t in ["Tips", "Related", "Recently changed"])
        aside = f'<div class="side bl p12" style="width:{rng.choice([220, 250])}px">{tips}{ctx.tbtn("dlg.learn", "the help panel", cls="ghost")}</div>'
        html = f'<div class="row str f1">{rail}{sub}{main}{aside}</div>'
    return {"title": title, "body": html, "menus": ["mb.file", "mb.edit", "mb.view", "mb.window", "mb.help"],
            "url": "account.example.com/settings", "app": title, "compact": variant in ("mac_grid", "tabs") and rng.random() < 0.7}
