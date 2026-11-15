"""System Settings: panes, seeded values and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

The panes are data (SCHEMA); web/apps/settings.js draws them. Most tasks pick their control from
the schema by seed, so the same task id covers many different controls.
"""
from ..oracle import Click, Drag, Reveal, Type
from . import pools
from .base import Spec, cond, only, say, task, unchanged, verdict

SIZE = (860, 600)
WIN = '.win[data-app="settings"] '
SLIDER_W = 200                       # px, .st-slide .slider in settings.css


def T(k, label, sub=None):
    return {"t": "toggle", "k": k, "label": label, **({"sub": sub} if sub else {})}


def S_(k, label, lo=None, hi=None):
    return {"t": "slider", "k": k, "label": label, "lo": lo, "hi": hi}


def P(k, label, opts):
    return {"t": "select", "k": k, "label": label, "opts": opts}


def I(label, value):
    return {"t": "info", "label": label, "value": value}


def G(*rows, title=None):
    return {"title": title, "rows": list(rows)}


ACCENTS = [["Multicolour", "conic-gradient(#ff5f57, #febc2e, #28c840, #0a7aff, #bf5af2, #ff5f57)"], ["Blue", "#0a7aff"], ["Purple", "#a550a7"],
           ["Pink", "#f74f9e"], ["Red", "#ff5257"], ["Orange", "#f7821b"], ["Yellow", "#ffc600"], ["Green", "#62ba46"], ["Graphite", "#8c8c8c"]]

SCHEMA = [
    {"id": "wifi", "label": "Wi-Fi", "icon": "wifi", "color": "#0a7aff", "blurb": "Set up Wi-Fi to connect your Mac to the internet.", "groups": [
        G(T("wifi.on", "Wi-Fi")),
        G({"t": "pick", "k": "wifi.network", "from": "networks"}, title="Known Networks"),
        G(T("wifi.ask", "Ask to join networks", "Known networks will be joined automatically."), T("wifi.hotspot", "Ask to join hotspots"))]},
    {"id": "bluetooth", "label": "Bluetooth", "icon": "bluetooth", "color": "#0a7aff", "blurb": "Connect to accessories you can use for typing, listening and more.", "groups": [
        G(T("bt.on", "Bluetooth")), G(I("Magic Keyboard", "Connected"), I("AirPods Pro", "Not Connected"), I("MX Anywhere 3", "Not Connected"), title="My Devices"),
        G(T("bt.menu", "Show Bluetooth in menu bar"))]},
    {"id": "network", "label": "Network", "icon": "globe", "color": "#0a7aff", "blurb": "Wi-Fi is connected and has an IP address.", "groups": [
        G(I("Wi-Fi", "Connected"), I("Thunderbolt Bridge", "Not Connected")), G(T("net.firewall", "Firewall"), T("net.vpn", "VPN"), T("net.limit", "Limit IP address tracking"))]},
    None,
    {"id": "notifications", "label": "Notifications", "icon": "bell", "color": "#ff3b30", "blurb": "Choose how notifications appear.", "groups": [
        G(P("notif.previews", "Show previews", ["Always", "When Unlocked", "Never"])),
        G(T("notif.sleep", "Allow notifications when the display is sleeping"), T("notif.locked", "Allow notifications when the screen is locked"),
          T("notif.sharing", "Allow notifications when mirroring or sharing the display"))]},
    {"id": "sound", "label": "Sound", "icon": "speaker", "color": "#ff2d55", "blurb": "Sound effects, output and input.", "groups": [
        G(P("sound.alert_sound", "Alert sound", ["Boop", "Breeze", "Bubble", "Crystal", "Funky", "Heroine", "Jump", "Mezzo", "Pebble", "Pluck"]),
          S_("sound.alert", "Alert volume", "speakerlow", "speaker"), T("sound.startup", "Play sound on startup"),
          T("sound.ui", "Play user interface sound effects"), T("sound.feedback", "Play feedback when volume is changed"), title="Sound Effects"),
        G(P("sound.output", "Output device", ["MacBook Speakers", "AirPods Pro", "Studio Display"]),
          S_("sound.volume", "Output volume", "speakerlow", "speaker"), T("sound.mute", "Mute"), title="Output")]},
    {"id": "focus", "label": "Focus", "icon": "moon", "color": "#5856d6", "blurb": "Stay in the moment by silencing notifications.", "groups": [
        G(T("focus.dnd", "Do Not Disturb"), T("focus.sleep", "Sleep Focus")), G(T("focus.share", "Share across devices"), T("focus.status", "Share Focus status"))]},
    {"id": "screentime", "label": "Screen Time", "icon": "clock", "color": "#5856d6", "blurb": "See how much time you spend on your devices.", "groups": [
        G(T("st.activity", "App & Website Activity"), T("st.share", "Share across devices"), T("st.lock", "Lock Screen Time settings"))]},
    None,
    {"id": "general", "label": "General", "icon": "gear", "color": "#8e8e93", "blurb": "Software updates, language, sharing and more.", "groups": [
        G(I("macOS", "Sequoia 15.6"), I("Model", "MacBook, 13-inch, M4")),
        G(T("general.updates", "Automatic updates"), P("general.browser", "Default web browser", ["Safari", "Chrome", "Firefox", "Arc"]),
          P("general.language", "Preferred language", ["English (UK)", "English (US)", "Français", "Deutsch", "Español"]), T("general.airdrop", "AirDrop & Handoff"))]},
    {"id": "appearance", "label": "Appearance", "icon": "eye", "color": "#1c1c1e", "blurb": "Choose the look of buttons, menus and windows.", "groups": [
        G({"t": "thumbs", "k": "appear.mode", "label": "Appearance", "opts": ["Light", "Dark", "Auto"]},
          {"t": "colors", "k": "appear.accent", "label": "Accent colour", "opts": ACCENTS},
          P("appear.sidebar", "Sidebar icon size", ["Small", "Medium", "Large"]), T("appear.tint", "Allow wallpaper tinting in windows")),
        G(P("appear.scrollbars", "Show scroll bars", ["Automatically", "When scrolling", "Always"]))]},
    {"id": "accessibility", "label": "Accessibility", "icon": "person", "color": "#0a7aff", "blurb": "Customise your Mac for vision, hearing and motor needs.", "groups": [
        G(T("acc.motion", "Reduce motion"), T("acc.contrast", "Increase contrast"), T("acc.transparency", "Reduce transparency"),
          T("acc.zoom", "Use keyboard shortcuts to zoom"), S_("acc.pointer", "Pointer size"))]},
    {"id": "control", "label": "Control Centre", "icon": "control", "color": "#8e8e93", "blurb": "Choose what appears in the menu bar and in Control Centre.", "groups": [
        G(P("cc.wifi", "Wi-Fi", ["Show in Menu Bar", "Don't Show in Menu Bar"]), P("cc.bluetooth", "Bluetooth", ["Show in Menu Bar", "Don't Show in Menu Bar"]),
          P("cc.sound", "Sound", ["Always Show in Menu Bar", "Show When Active", "Don't Show in Menu Bar"])),
        G(T("cc.battery", "Show battery percentage"), T("cc.seconds", "Display the time with seconds"))]},
    {"id": "siri", "label": "Siri & Spotlight", "icon": "mic", "color": "#bf5af2", "blurb": "Ask Siri and search with Spotlight.", "groups": [
        G(T("siri.on", "Ask Siri"), P("siri.voice", "Siri voice", ["Voice 1", "Voice 2", "Voice 3", "Voice 4"]), T("siri.suggest", "Siri Suggestions"))]},
    {"id": "privacy", "label": "Privacy & Security", "icon": "hand", "color": "#0a7aff", "blurb": "Control which apps can use your data.", "groups": [
        G(T("priv.location", "Location Services"), T("priv.analytics", "Share Mac Analytics"), T("priv.ads", "Personalised Ads")),
        G(P("priv.apps", "Allow applications from", ["App Store", "App Store & Known Developers"]))]},
    None,
    {"id": "dock", "label": "Desktop & Dock", "icon": "display", "color": "#1c1c1e", "blurb": "Dock size and position, windows and Mission Control.", "groups": [
        G(S_("dock.size", "Size"), T("dock.magnify", "Magnification"), P("dock.position", "Position on screen", ["Left", "Bottom", "Right"]),
          P("dock.minimise", "Minimise windows using", ["Genie Effect", "Scale Effect"]), T("dock.autohide", "Automatically hide and show the Dock"),
          T("dock.recents", "Show suggested and recent apps in Dock"), title="Dock"),
        G(T("dock.stage", "Stage Manager"), T("dock.widgets", "Show widgets on desktop"), title="Desktop & Stage Manager")]},
    {"id": "displays", "label": "Displays", "icon": "sun", "color": "#0a7aff", "blurb": "Resolution, brightness and Night Shift.", "groups": [
        G({"t": "seg", "k": "disp.res", "label": "Resolution", "opts": ["Larger Text", "Default", "More Space"]},
          S_("disp.brightness", "Brightness", "sun", "sun"), T("disp.auto", "Automatically adjust brightness"), T("disp.truetone", "True Tone"),
          P("disp.nightshift", "Night Shift", ["Off", "Sunset to Sunrise", "Custom"]))]},
    {"id": "wallpaper", "label": "Wallpaper", "icon": "photo", "color": "#32ade6", "blurb": "Choose a picture for your desktop.", "groups": [
        G(T("wall.rotate", "Change picture automatically"), P("wall.every", "Change picture", ["Every 30 Minutes", "Every Hour", "Every Day", "When Waking from Sleep"]),
          T("wall.all", "Show on all Spaces"))]},
    {"id": "battery", "label": "Battery", "icon": "battery", "color": "#34c759", "blurb": "Battery health and energy use.", "groups": [
        G(I("Battery Health", "Normal"), P("batt.lowpower", "Low Power Mode", ["Never", "Always", "Only on Battery", "Only on Power Adapter"])),
        G(T("batt.dim", "Slightly dim the display on battery"), T("batt.optimise", "Optimised Battery Charging"), T("batt.wake", "Wake for network access"))]},
    None,
    {"id": "lock", "label": "Lock Screen", "icon": "lock", "color": "#1c1c1e", "blurb": "What happens when your Mac is locked or idle.", "groups": [
        G(P("lock.saver", "Start Screen Saver when inactive", ["For 5 minutes", "For 10 minutes", "For 20 minutes", "Never"]),
          P("lock.display", "Turn display off when inactive", ["For 2 minutes", "For 5 minutes", "For 10 minutes", "Never"]),
          P("lock.password", "Require password after screen saver begins", ["Immediately", "After 5 seconds", "After 1 minute", "After 5 minutes"])),
        G(T("lock.clock", "Show large clock"), T("lock.hints", "Show password hints"))]},
    {"id": "users", "label": "Users & Groups", "icon": "person", "color": "#0a7aff", "blurb": "Accounts on this Mac.", "groups": [
        G(I("Administrator", "This Mac"), T("users.guest", "Guest User"), T("users.switch", "Show fast user switching menu"))]},
    {"id": "passwords", "label": "Passwords", "icon": "lock", "color": "#8e8e93", "blurb": "Saved passwords and passkeys.", "groups": [
        G(T("pw.autofill", "AutoFill Passwords and Passkeys"), T("pw.detect", "Detect compromised passwords"), T("pw.codes", "Clean up verification codes automatically"))]},
    None,
    {"id": "keyboard", "label": "Keyboard", "icon": "keyboard", "color": "#8e8e93", "blurb": "Key repeat, shortcuts and text input.", "groups": [
        G(S_("kb.repeat", "Key repeat rate"), S_("kb.delay", "Delay until repeat"), T("kb.autobright", "Adjust keyboard brightness in low light"),
          S_("kb.brightness", "Keyboard brightness", "sun", "sun"),
          P("kb.globe", "Press fn key to", ["Change Input Source", "Show Emoji & Symbols", "Start Dictation", "Do Nothing"]), T("kb.nav", "Keyboard navigation"))]},
    {"id": "mouse", "label": "Mouse", "icon": "cursor", "color": "#8e8e93", "blurb": "Tracking speed and clicking.", "groups": [
        G(S_("mouse.speed", "Tracking speed"), T("mouse.natural", "Natural scrolling"), P("mouse.secondary", "Secondary click", ["Click Right Side", "Click Left Side"]),
          S_("mouse.dbl", "Double-click speed"))]},
    {"id": "trackpad", "label": "Trackpad", "icon": "hand", "color": "#8e8e93", "blurb": "Pointing, clicking and gestures.", "groups": [
        G(S_("tp.speed", "Tracking speed"), P("tp.click", "Click", ["Light", "Medium", "Firm"]), T("tp.tap", "Tap to click"), T("tp.natural", "Natural scrolling"),
          T("tp.force", "Force Click and haptic feedback"), T("tp.lookup", "Look up & data detectors"))]},
    {"id": "printers", "label": "Printers & Scanners", "icon": "doc", "color": "#8e8e93", "blurb": "Printers, scanners and paper sizes.", "groups": [
        G(P("print.default", "Default printer", ["Last Printer Used", "Office LaserJet", "Home Inkjet"]), P("print.paper", "Default paper size", ["A4", "US Letter", "A5"]),
          T("print.share", "Share printers on this network"))]},
]
PANES = [p for p in SCHEMA if p]
LOW = {"displays", "wallpaper", "battery", "lock", "users", "passwords", "keyboard", "mouse", "trackpad", "printers"}   # below the fold of the sidebar at the start
NETWORKS = ["Alder Row 14", "Harbor Guest", "juniper-5G", "Quarry_Fitness", "TidewaterPress", "Lindqvist Home", "NETGEAR-88", "Saffron Kitchen WiFi",
            "Bluebird-Office", "eduroam", "Kestrel Lounge", "Flat 2B", "orchard-staff", "Copperline", "Meridian 5", "the-annex"]


def rows(pane_ids=None, kind=None):
    out = []
    for p in PANES:
        if pane_ids is not None and p["id"] not in pane_ids:
            continue
        for g in p["groups"]:
            for r in g["rows"]:
                if kind is None or r["t"] == kind:
                    out.append((p, r))
    return out


def default(rng):
    v = {}
    for _, r in rows():
        if r["t"] == "toggle":
            v[r["k"]] = rng.random() < 0.5
        elif r["t"] == "slider":
            v[r["k"]] = round(rng.uniform(0.15, 0.85), 2)
        elif r["t"] in ("select", "seg", "thumbs"):
            v[r["k"]] = rng.choice(r["opts"])
        elif r["t"] == "colors":
            v[r["k"]] = rng.choice(r["opts"])[0]
    v["wifi.on"] = True
    nets = rng.sample(NETWORKS, 6)
    v["wifi.network"] = nets[rng.randrange(6)]
    return {"schema": SCHEMA, "v": v, "networks": nets, "owner": pools.person(rng),
            "ui": {"pane": rng.choice(["general", "wifi", "appearance", "sound", "dock"]), "search": ""}}


def side(p):
    return WIN + f'.st-item[data-arg="{p["id"]}"]'


def val(st, k):
    return st["apps"]["settings"]["v"][k]


def top_panes():
    return [p["id"] for p in PANES if p["id"] not in LOW]


def toggle_task(S, here, pane_ids):
    s = S.apps["settings"]
    p, r = S.rng.choice(rows(pane_ids, "toggle"))
    want = not s["v"][r["k"]]
    if here:
        s["ui"]["pane"] = p["id"]
    elif s["ui"]["pane"] == p["id"]:
        s["ui"]["pane"] = "general" if p["id"] != "general" else "wifi"
    S.open("settings")
    word = "on" if want else "off"
    request = say(S.rng, f"Turn {word} “{r['label']}” in {p['label']} settings.", f"In System Settings, under {p['label']}, switch {word} “{r['label']}”.")
    click = Click(WIN + f'.toggle[data-arg="{r["k"]}"]', f"Click the switch next to “{r['label']}”")
    check = lambda st, init: verdict(cond(val(st, r["k"]) is want, f"“{r['label']}” is not {word}"), only(st, init, f"settings.v.{r['k']}"))
    return p, request, click, check


@task("settings.toggle_here", "single")
def toggle_here(S):
    p, request, click, check = toggle_task(S, True, set(top_panes()) - {"wifi"})
    return Spec(request=request, steps=[click], check=check)


@task("settings.toggle", "chain")
def toggle(S):
    p, request, click, check = toggle_task(S, False, set(top_panes()) - {"wifi"})
    return Spec(request=request, steps=[Reveal(side(p)), Click(side(p), f"Click “{p['label']}” in the sidebar of System Settings"), click], check=check)


@task("settings.toggle_low", "scroll")
def toggle_low(S):
    p, request, click, check = toggle_task(S, False, LOW)
    return Spec(request=request, steps=[Reveal(side(p)), Click(side(p), f"Click “{p['label']}” in the sidebar of System Settings"), click], check=check)


@task("settings.select", "chain")
def select(S):
    s = S.apps["settings"]
    p, r = S.rng.choice(rows(set(top_panes()), "select"))
    want = S.rng.choice([o for o in r["opts"] if o != s["v"][r["k"]]])
    if s["ui"]["pane"] == p["id"]:
        s["ui"]["pane"] = "general" if p["id"] != "general" else "wifi"
    S.open("settings")
    return Spec(request=say(S.rng, f"In {p['label']} settings, set “{r['label']}” to “{want}”.", f"Change “{r['label']}” to {want} in the {p['label']} settings."),
                steps=[Reveal(side(p)), Click(side(p), f"Click “{p['label']}” in the sidebar of System Settings"),
                       Click(WIN + f'.popup[data-arg="{r["k"]}"]', f"Click the pop-up button next to “{r['label']}”"),
                       Click(f'.menu-item:has(.mi-label:text-is("{want}"))', f"Click “{want}” in the menu")],
                check=lambda st, init: verdict(cond(val(st, r["k"]) == want, f"“{r['label']}” is “{val(st, r['k'])}”"), only(st, init, f"settings.v.{r['k']}")))


def slider_to(r, p):
    return Drag(WIN + f'.slider[data-arg="{r["k"]}"] .knob', WIN + f'.slider[data-arg="{r["k"]}"]',
                f"the round knob of the “{r['label']}” slider", "",
                dst_at=((9 + p * (SLIDER_W - 18)) / SLIDER_W, 0.5))


@task("settings.slider", "drag")
def slider(S):
    s = S.apps["settings"]
    p, r = S.rng.choice(rows(set(top_panes()), "slider"))
    cur = s["v"][r["k"]]
    pct = S.rng.choice([x for x in (10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90) if abs(x / 100 - cur) > 0.15])
    s["ui"]["pane"] = p["id"]
    S.open("settings")
    d = slider_to(r, pct / 100)
    d.say_to = f"the point {pct}% of the way along the “{r['label']}” slider, counted from its left end"
    return Spec(request=say(S.rng, f"Set “{r['label']}” to about {pct}% in {p['label']} settings.", f"Move the {r['label']} slider in {p['label']} to roughly {pct} percent."),
                steps=[d],
                check=lambda st, init: verdict(cond(abs(val(st, r["k"]) - pct / 100) <= 0.07, f"“{r['label']}” is at {round(val(st, r['k']) * 100)}%"),
                                               only(st, init, f"settings.v.{r['k']}")))


@task("settings.slider_end", "drag")
def slider_end(S):
    s = S.apps["settings"]
    choices = [("displays", "disp.brightness", "the display brightness"), ("sound", "sound.volume", "the output volume"),
               ("sound", "sound.alert", "the alert volume"), ("keyboard", "kb.brightness", "the keyboard brightness")]
    pid, k, words = S.rng.choice(choices[:3])
    p = next(x for x in PANES if x["id"] == pid)
    r = next(r for _, r in rows({pid}, "slider") if r["k"] == k)
    up = S.rng.random() < 0.5
    s["v"][k] = round(S.rng.uniform(0.3, 0.7), 2)
    if s["ui"]["pane"] == pid:
        s["ui"]["pane"] = "general"
    S.open("settings")
    d = slider_to(r, 1.0 if up else 0.0)
    d.say_to = f"the far {'right' if up else 'left'} end of the “{r['label']}” slider"
    return Spec(request=say(S.rng, f"Turn {words} all the way {'up' if up else 'down'}.", f"Set {words} to its {'maximum' if up else 'minimum'}."),
                steps=[Reveal(side(p)), Click(side(p), f"Click “{p['label']}” in the sidebar of System Settings"), d],
                check=lambda st, init: verdict(cond(val(st, k) >= 0.97 if up else val(st, k) <= 0.03, f"“{r['label']}” is at {round(val(st, k) * 100)}%"),
                                               only(st, init, f"settings.v.{k}")))


@task("settings.appearance", "chain")
def appearance(S):
    s = S.apps["settings"]
    p = next(x for x in PANES if x["id"] == "appearance")
    if s["ui"]["pane"] == "appearance":
        s["ui"]["pane"] = "general"
    if S.rng.random() < 0.5:
        want = S.rng.choice([o for o in ("Light", "Dark", "Auto") if o != s["v"]["appear.mode"]])
        k, request = "appear.mode", say(S.rng, f"Switch the appearance of this Mac to {want}.", f"Put the Mac in {want} mode." if want != "Auto" else "Make the appearance switch between light and dark automatically.")
        step = Click(WIN + f'.st-thumb[data-arg="appear.mode={want}"]', f"Click the “{want}” appearance thumbnail")
    else:
        want = S.rng.choice([a[0] for a in ACCENTS[1:] if a[0] != s["v"]["appear.accent"]])
        k, request = "appear.accent", say(S.rng, f"Change the accent colour to {want.lower()}.", f"Make {want.lower()} the accent colour of this Mac.")
        step = Click(WIN + f'.st-color[data-arg="appear.accent={want}"]', f"Click the {want.lower()} dot in the “Accent colour” row")
    S.open("settings")
    return Spec(request=request, steps=[Reveal(side(p)), Click(side(p), "Click “Appearance” in the sidebar of System Settings"), step],
                check=lambda st, init: verdict(cond(val(st, k) == want, f"it is set to “{val(st, k)}”"), only(st, init, f"settings.v.{k}")))


@task("settings.join_wifi", "chain")
def join_wifi(S):
    s = S.apps["settings"]
    p = PANES[0]
    want = S.rng.choice([n for n in s["networks"] if n != s["v"]["wifi.network"]])
    if s["ui"]["pane"] == "wifi":
        s["ui"]["pane"] = "general"
    S.open("settings")
    return Spec(request=say(S.rng, f"Connect to the Wi-Fi network “{want}”.", f"Switch the Wi-Fi to {want}."),
                steps=[Reveal(side(p)), Click(side(p), "Click “Wi-Fi” in the sidebar of System Settings"),
                       Click(WIN + f'.st-row.pick:has(.st-label:text-is("{want}"))', f"Click the network “{want}” in the list")],
                check=lambda st, init: verdict(cond(val(st, "wifi.network") == want, f"the network is “{val(st, 'wifi.network')}”"),
                                               only(st, init, "settings.v.wifi.network")))


@task("settings.search", "typing")
def search(S):
    s = S.apps["settings"]
    p = S.rng.choice([x for x in PANES if x["id"] in ("trackpad", "keyboard", "battery", "displays", "printers", "notifications", "wallpaper")])
    word = p["label"].split(" ")[0].lower()
    if s["ui"]["pane"] == p["id"]:
        s["ui"]["pane"] = "general"
    S.open("settings")
    return Spec(request=say(S.rng, f"Type “{word}” into the search field of System Settings and open the {p['label']} settings it finds.",
                            f"Search System Settings for “{word}” and open {p['label']}."),
                steps=[Click(WIN + ".st-search input", "Click the search field at the top of the System Settings sidebar"), Type(word),
                       Reveal(side(p)), Click(side(p), f"Click “{p['label']}” in the sidebar of System Settings")],
                check=lambda st, init: verdict(cond(st["apps"]["settings"]["ui"]["pane"] == p["id"], f"the {p['label']} settings are not open"),
                                               cond(word in st["apps"]["settings"]["ui"]["search"].lower(), "nothing was searched for"),
                                               unchanged(st, init)))


@task("settings.already_set", "already_done")
def already_set(S):
    s = S.apps["settings"]
    p, r = S.rng.choice(rows(set(top_panes()) - {"wifi"}, "toggle"))
    s["ui"]["pane"] = p["id"]
    word = "on" if s["v"][r["k"]] else "off"
    S.open("settings")
    return Spec(request=say(S.rng, f"Make sure “{r['label']}” is turned {word} in {p['label']} settings.", f"“{r['label']}” should be {word}. Please check, and fix it if it isn't."),
                steps=[], kind="already_done", check=unchanged)


@task("settings.no_such_option", "infeasible")
def no_such_option(S):
    s = S.apps["settings"]
    if S.rng.random() < 0.5:
        s["ui"]["pane"] = "wifi"
        ghost = S.rng.choice([n for n in NETWORKS if n not in s["networks"]])
        request = say(S.rng, f"Connect to the Wi-Fi network “{ghost}”.", f"Join the {ghost} Wi-Fi network.")
    else:
        s["ui"]["pane"] = "appearance"
        ghost = S.rng.choice(["turquoise", "brown", "black", "gold"])
        request = say(S.rng, f"Change the accent colour to {ghost}.", f"Make {ghost} the accent colour of this Mac.")
    S.open("settings")
    return Spec(request=request, steps=[], kind="infeasible", check=unchanged)
