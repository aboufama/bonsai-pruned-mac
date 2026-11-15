"""macsim.cases: from the elements of one screen to pointing challenges.

Seven kinds, each with a target that the instruction picks out without doubt:
    name        by the visible title, or by the accessibility description of an icon ("the Next button")
    function    by what the element does ("go to the next month")
    position    by its place among neighbours ("the arrow to the right of Today", "the second tab in Safari")
    state       by its state ("the unchecked checkbox in Calendar", "the selected tab")
    same_name   a name that is on screen more than once, told apart by the window or surface
    tiny        a target under 14 px on its short side in the saved image (phrased as one of the above)
    partial     a target partly hidden behind another window or cut by an edge (phrased as one of the above)
Every case carries what the scorer needs: the target's box, its neighbours on four sides, the other
elements with the same name, and the surfaces (windows, menus, Dock, menu bar) back to front.
"""
TINY = 14
TITLE = {"calendar": "Calendar", "finder": "Finder", "mail": "Mail", "notes": "Notes", "reminders": "Reminders", "safari": "Safari", "settings": "System Settings", "messages": "Messages", "music": "Music"}
OPP = {"left": "right", "right": "left", "up": "down", "down": "up"}
ORD = ["first", "second", "third", "fourth", "fifth"]
NOUN = {"button": "button", "tab": "tab", "checkbox": "checkbox", "switch": "switch", "menu": "menu", "menu item": "menu item", "status item": "menu bar icon", "Dock icon": "Dock icon", "sidebar item": "sidebar item",
        "mailbox": "mailbox", "folder": "folder", "list": "list", "playlist": "playlist", "cell": "day", "event": "event", "file": "file", "message": "email", "note": "note", "conversation": "conversation", "song": "song",
        "album": "album", "link": "link", "bookmark": "bookmark", "tag": "tag", "text field": "text field", "search field": "search field", "address field": "address field", "pop-up button": "pop-up menu", "slider": "slider",
        "path item": "path bar item", "column header": "column header", "search result": "result"}
STATE_ROLES = {"checkbox", "switch", "tab", "sidebar item", "mailbox", "folder", "list", "playlist", "message", "conversation", "song", "file", "note", "menu item"}
STATE_WORDS = {"checked": ["the checked {w}", "the {w} that is checked", "the only {w} with a tick"], "unchecked": ["the unchecked {w}", "the {w} that is not checked", "the only {w} without a tick"],
               "on": ["the {w} that is on", "the {w} that is switched on", "the only {w} that is turned on"], "off": ["the {w} that is off", "the {w} that is switched off", "the only {w} that is turned off"],
               "selected": ["the selected {w}", "the {w} that is selected", "the currently selected {w}", "the highlighted {w}"], "unread": ["the unread {w}", "the {w} that has not been read", "the only unread {w}"],
               "completed": ["the completed reminder", "the reminder that is already done", "the ticked reminder"], "not completed": ["the reminder that is not done yet", "the only reminder still open"],
               "playing": ["the song that is playing", "the song playing now"]}


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def inside(b, x, y):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def gap(e, c, d):
    """Distance from e to c when c lies on side d of e and the two overlap on the other axis by half of the smaller; else None."""
    a, b = e["full"], c["full"]
    if d in ("left", "right"):
        over, need = min(a[3], b[3]) - max(a[1], b[1]), 0.5 * min(a[3] - a[1], b[3] - b[1])
        g = a[0] - b[2] if d == "left" else b[0] - a[2]
    else:
        over, need = min(a[2], b[2]) - max(a[0], b[0]), 0.5 * min(a[2] - a[0], b[2] - b[0])
        g = a[1] - b[3] if d == "up" else b[1] - a[3]
    return g if over >= need and g >= -2 else None


def prepare(els):
    """Holes (child elements inside an element), the free part of the box, neighbours on four sides, name counts."""
    by_i = {e["i"]: e for e in els}
    for e in els:
        e["holes"], e["nb"], e["ok"] = [], {}, e["vis"] >= 0.35 and e["mid"]
    for e in els:
        p = by_i.get(e["parent"])
        if p is not None:
            p["holes"].append(e["full"])
    for e in els:
        if not e["holes"]:
            continue
        b, hs = e["box"], e["holes"]
        x0, y0, x1, y1 = min(h[0] for h in hs), min(h[1] for h in hs), max(h[2] for h in hs), max(h[3] for h in hs)
        free = max(([b[0], b[1], x0, b[3]], [x1, b[1], b[2], b[3]], [b[0], b[1], b[2], y0], [b[0], y1, b[2], b[3]]), key=area)
        if min(free[2] - free[0], free[3] - free[1]) >= 8 and area(free) >= 0.12 * area(b):
            e["box"] = free
        elif any(inside(h, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for h in hs):
            e["ok"] = False                                  # its middle belongs to a child: never a target
    groups = {}
    for e in els:
        groups.setdefault(e["surface"], []).append(e)
    for group in groups.values():
        for e in group:
            for d in OPP:
                best = None
                for c in group:
                    if c is e or c["i"] == e["parent"] or c["parent"] == e["i"]:
                        continue
                    g = gap(e, c, d)
                    if g is not None and (best is None or g < best[0]):
                        best = (g, c)
                if best:
                    e["nb"][d] = (best[1]["i"], best[0])
    names = {}
    for e in els:
        names.setdefault(e["name"].lower(), []).append(e)
    for e in els:
        e["same"] = [c for c in names[e["name"].lower()] if c is not e]
    return by_i


def loc(e, r):
    w, app = e["where"], TITLE.get(e["app"], "")
    return {"window": r.choice([f"in the {app} window", f"in {app}"]), "alert": r.choice([f"in the {app} dialog", "in the dialog", "in the alert"]), "popover": "in the event popover", "menu": "in the open menu",
            "menubar": "in the menu bar", "dock": "in the Dock", "spotlight": "in Spotlight"}.get(w, "")


def ref(e, r, bare=True):
    """A phrase for the element. The second value says whether the phrase already tells where it is."""
    n, ro, noun = e["name"], e["role"], e["noun"]
    q = f"“{n}”"
    if ro == "message":
        frm, subj = n.split(": ", 1)
        solo = not any(c["role"] == "message" and c["name"].startswith(frm + ": ") for c in e["all"] if c is not e)
        forms = [f"the “{subj}” email", f"the email “{subj}” from {frm}"] + ([f"the email from {frm}", f"the message from {frm}"] if solo else [])
    elif ro == "cell":
        forms = [f"the month of {n}", f"{n} in the year view"] if noun == "month" else [f"{n} in the calendar", f"the day {n}", f"the {n} cell"]
    elif ro == "file":
        forms = [f"the {n} folder", f"the folder {q}", f"the {q} folder"] if noun == "folder" else [f"the file {q}", f"{q}", f"the {n} file"]
    elif ro == "Dock icon":
        return r.choice([f"{n} in the Dock", f"the {n} icon in the Dock", f"the {n} Dock icon"]), True
    elif ro == "status item":
        return r.choice(["the clock in the menu bar", "the date and time in the menu bar"] if n == "Clock" else [f"the {n} icon in the menu bar", f"the {n} menu bar icon", f"{n} in the menu bar"]), True
    elif ro == "menu":
        return r.choice(["the Apple menu", "the Apple logo in the menu bar"] if n == "Apple menu" else [f"the {n} menu", f"the {n} menu in the menu bar", f"{n} in the menu bar"]), True
    elif ro == "menu item":
        return r.choice([f"the {q} menu item", f"{q} in the menu", f"the {n} item in the open menu"]), True
    elif ro == "search result":
        return r.choice([f"the {q} result", f"{n} in the Spotlight results"]), True
    elif ro == "checkbox":
        forms = [f"the {n} calendar checkbox", f"the checkbox for the {n} calendar", f"the {n} checkbox"] if noun == "calendar" else [f"the circle next to {q}", f"the checkbox for {q}", f"the round checkbox of {q}"] if noun == "circle" else [f"the {q} checkbox", f"the checkbox {q}"]
    elif ro == "switch":
        forms = [f"the {n} switch", f"the switch for {n}", f"the {n} toggle"]
    elif ro == "pop-up button":
        forms = [f"the {n} pop-up menu", f"the pop-up button for {n}", f"the {n} drop-down"]
    elif ro == "slider":
        forms = [f"the {n} slider", f"the slider for {n}"]
    elif ro == "text field":
        forms = [f"the {n} field", f"the {q} text field"]
    elif ro == "search field":
        forms = ["the search field", "the search box"] if n == "Search" else [f"the {n} field", f"the {q} field"]
    elif ro == "address field":
        return r.choice(["the address bar", "the address and search field", "Safari's address field"]), True
    elif ro == "button" and n in ("Close", "Minimise", "Zoom") and e["icon"] and not e["fn"].startswith("discard"):
        forms = [f"the {n} button", {"Close": "the red close button", "Minimise": "the yellow minimise button", "Zoom": "the green zoom button"}[n], f"the {n.lower()} traffic light"]
    else:
        forms = {"tab": [f"the {n} tab", f"the {q} tab"], "link": [f"the {q} link", f"the link {q}"], "event": [f"the {q} event", f"the event {q}"], "sidebar item": [f"{n} in the sidebar", f"the {n} sidebar item"],
                 "mailbox": [f"the {n} mailbox", f"{n} in the mailbox list"], "folder": [f"the {n} folder", f"the folder {q}"], "list": [f"the {n} list", f"the list {q}"], "playlist": [f"the {n} playlist", f"the playlist {q}"],
                 "bookmark": [f"the {n} bookmark", f"the bookmark {q}"], "tag": [f"the {n} tag"], "note": [f"the note {q}", f"the {q} note"], "conversation": [f"the conversation with {n}", f"{n} in the conversation list"],
                 "song": [f"the song {q}", f"{q} in the song list"], "album": [f"the album {q}", f"the {q} album"], "path item": [f"{n} in the path bar", f"the {n} path bar item"], "column header": [f"the {n} column header"],
                 "button": [f"the {n} button", f"the {q} button"] + ([f"the {n} toolbar button"] if e["icon"] and e["where"] == "window" else [])}.get(ro, [f"the {n} {NOUN.get(ro, ro)}"])
        if bare and ro in ("button", "tab", "link", "event", "album"):
            forms.append(n if ro in ("button", "tab") else q)
    return r.choice(forms), False


def command(e, x, r):
    ro = e["role"]
    verbs = {"text field": ["Click {x}", "Click in {x}", "Put the cursor in {x}"], "search field": ["Click {x}", "Click in {x}"], "address field": ["Click {x}", "Click in {x}"],
             "Dock icon": ["Click {x}", "Open {x}"], "menu": ["Click {x}", "Open {x}"], "mailbox": ["Click {x}", "Open {x}", "Go to {x}"], "tab": ["Click {x}", "Switch to {x}", "Go to {x}"], "conversation": ["Click {x}", "Open {x}"],
             "playlist": ["Click {x}", "Open {x}"], "note": ["Click {x}", "Open {x}", "Select {x}"], "link": ["Click {x}", "Follow {x}"], "checkbox": ["Click {x}", "Toggle {x}"], "switch": ["Click {x}", "Toggle {x}", "Flip {x}"],
             "menu item": ["Choose {x}", "Click {x}", "Pick {x}"], "file": ["Select {x}", "Click {x}"], "message": ["Select {x}", "Click {x}", "Open {x}"], "song": ["Select {x}", "Click {x}"], "event": ["Click {x}", "Select {x}"]}.get(ro, ["Click {x}", "Click on {x}", "Press {x}"])
    forms = verbs + ["Click {x}", "{X}", "Point at {x}", "Where is {x}?"]
    return r.choice(forms).format(x=x, X=x[0].upper() + x[1:] if x.startswith(("the ", "in ")) else x)


def name_phrase(e, r, force_loc=False):
    x, has_loc = ref(e, r, bare=not e["same"] and not force_loc)
    if not has_loc and (force_loc or (e["where"] in ("window", "alert", "popover") and r.random() < 0.3)):
        x += " " + loc(e, r)
    return command(e, x, r)


def unique_fn(e, els, r):
    alts = [a for a in e["fn"].split("|") if a]
    r.shuffle(alts)
    for a in alts:
        others = [c for c in els if c is not e and a in c["fn"].split("|")]
        if e["role"] == "search field" and e["where"] == "window":
            if any(c["surface"] == e["surface"] for c in others):
                continue
            text = f"{a} in {TITLE[e['app']]}"                # "search" alone could be any search field, the address bar or Spotlight
        elif not others:
            text = a
        elif e["where"] == "window" and not any(c["surface"] == e["surface"] for c in others):
            text = f"{a} in {TITLE[e['app']]}"
        else:
            continue
        return r.choice(["{F}", "{F}", "I want to {f}", "Where do I click to {f}?", "How do I {f}?", "Help me {f}", "{F}, please"]).format(f=text, F=text[0].upper() + text[1:])
    return None


def lines(els):
    """Rows and columns of like elements on one surface (for "the second tab", "the last icon in the Dock")."""
    out, groups = [], {}
    for e in els:
        if e["vis"] >= 0.99:
            groups.setdefault((e["surface"], e["role"], e["noun"]), []).append(e)
    for (surface, role, noun), g in groups.items():
        if len(g) < 3 or role in ("cell", "event") or any(c["vis"] < 0.99 for c in els if c["surface"] == surface and c["role"] == role and c["noun"] == noun):
            continue
        ys, xs = sorted((e["full"][1] + e["full"][3]) / 2 for e in g), sorted(e["full"][0] for e in g)
        if ys[-1] - ys[0] <= 4:
            out.append(("row", sorted(g, key=lambda e: e["full"][0])))
        elif xs[-1] - xs[0] <= 4:
            out.append(("column", sorted(g, key=lambda e: e["full"][1])))
    return out


def make(els, surf, r, want=None):
    """The challenges of one screen: a list of {"e": element, "kind", "phrase", "instruction", ...}."""
    by_i = prepare(els)
    for e in els:
        e["all"] = els
    targets = [e for e in els if e["ok"] and not e["dim"] and e["role"] != "column header"]
    want = want or {"name": 3, "function": 2, "position": 2, "state": 1, "same_name": 2, "tiny": 1, "partial": 1}
    used, out = set(), []
    tiny = lambda e: min(e["box"][2] - e["box"][0], e["box"][3] - e["box"][1]) <= TINY
    partial = lambda e: e["vis"] < 0.75                  # a round control loses its corners to the probe grid; that is not "hidden"
    light = lambda e: e["role"] == "button" and e["icon"] and e["fn"].split("|")[0] in ("close this window", "minimise this window", "make this window fill the screen")
    lights_ok, dock_cap = r.random() < 0.6, 1 + (r.random() < 0.3)
    role_word = lambda e: e["noun"] if e["noun"] in ("arrow", "circle", "folder", "file", "calendar") else "icon" if e["icon"] and e["role"] in ("button", "status item", "Dock icon") and r.random() < 0.5 else NOUN.get(e["role"], e["role"])

    def by_name(e):
        if not e["same"]:
            return name_phrase(e, r), "none"
        if all(NOUN.get(c["role"]) != NOUN.get(e["role"]) or c["where"] != e["where"] for c in e["same"]) and e["role"] in ("Dock icon", "status item", "menu", "menu item", "search result"):
            return name_phrase(e, r), "role"                 # the phrase names its surface (Dock, menu bar, menu)
        return None, None

    def by_same(e):
        if not e["same"]:
            return None, None
        x, has_loc = ref(e, r, bare=False)
        if has_loc:                                          # the phrase names its surface: Dock, menu bar, menu, Spotlight
            if any(c["where"] == e["where"] and NOUN.get(c["role"]) == NOUN.get(e["role"]) for c in e["same"]):
                return None, None
        else:
            here = [c for c in e["same"] if c["surface"] == e["surface"]]
            if e["where"] not in ("window", "alert", "popover") or any(c["where"] == e["where"] for c in here) or (here and e["where"] == "window"):
                return None, None                            # twice in one window: the window does not tell them apart
            x += " " + loc(e, r)
        windows = ("window", "alert", "popover")
        return command(e, x, r), "window" if e["where"] in windows and all(c["where"] in windows for c in e["same"]) else "surface"

    def by_function(e):
        t = unique_fn(e, els, r) if e["fn"] else None
        return t, "none"

    def positions():
        cands = []
        for e in targets:
            for d, (j, g) in e["nb"].items():
                n = by_i[j]
                if g > 30 or n["nb"].get(OPP[d], (None,))[0] != e["i"] or n["same"] or n["vis"] < 0.9 or n["role"] in ("cell", "event", "column header") or n["dim"]:
                    continue
                (we, he), (wn, hn) = [(x["full"][2] - x["full"][0], x["full"][3] - x["full"][1]) for x in (e, n)]
                if (d in ("left", "right") and (max(we, wn) > 320 or max(he, hn) > 2.5 * min(he, hn))) or (d in ("up", "down") and (max(he, hn) > 90 or max(we, wn) > 3 * min(we, wn))):
                    continue                                 # a row beside a sidebar item is "left of" it only on paper
                side = {"left": ["to the right of", "just right of", "right after"], "right": ["to the left of", "just left of", "right before"], "up": ["below", "just below", "under"], "down": ["above", "just above", "right above"]}[d]
                anchor = ref(n, r, bare=False)[0]
                text = f"the {role_word(e)} {r.choice(side)} {anchor}" + (f" {loc(e, r)}" if e["where"] == "window" and r.random() < 0.3 else "")
                cands.append((e, command(e, text, r), "neighbour", 3 if e["icon"] else 1))
        for way, g in lines(els):
            e0 = g[0]
            for k, e in enumerate(g):
                if e not in targets or not (k < 5 or k == len(g) - 1):
                    continue
                last_ok = k == len(g) - 1 and (way == "row" or e0["where"] != "window")     # a column in a window may go on below its edge
                if k >= 5 and not last_ok:
                    continue
                o = "last" if last_ok and (k >= 5 or r.random() < 0.5) else ORD[k]
                w = NOUN.get(e["role"], e["role"]) if not e["noun"] or e["noun"] == "arrow" else e["noun"]
                if e0["where"] == "dock":
                    text = f"the {o} icon in the Dock" + (", counting from the left" if o != "last" else "")
                elif e0["where"] == "menubar":                       # not the menus: does the Apple logo count as the first?
                    text = f"the {o} status icon in the menu bar, counting from the left" if e["role"] == "status item" else None
                elif e0["where"] == "menu":
                    text = f"the {o} item in the open menu" if len([u for u in surf if u["name"].startswith("menu:")]) == 1 else None
                elif e0["where"] == "spotlight":
                    text = f"the {o} Spotlight result"
                else:
                    text = f"the {o} {w} {loc(e, r)}" + ("" if way == "column" else ", counting from the left")
                if text:
                    cands.append((e, command(e, text, r), "ordinal", 1))
        return cands

    def states():
        cands, groups = [], {}
        for e in els:
            if e["role"] in STATE_ROLES and e["vis"] >= 0.5:
                groups.setdefault((e["surface"], e["role"], e["noun"]), []).append(e)
        for g in groups.values():
            for e in g:
                if e in targets and e["state"] in STATE_WORDS and len(g) >= 2 and sum(c["state"] == e["state"] for c in g) == 1:
                    w = {"calendar": "calendar checkbox", "circle": "reminder", "folder": "folder", "file": "file"}.get(e["noun"], NOUN.get(e["role"], e["role"]))
                    if e["noun"] == "circle" and e["state"] not in ("completed", "not completed"):
                        w = "checklist item"
                    text = r.choice(STATE_WORDS[e["state"]]).format(w=w) + " " + loc(e, r)
                    cands.append((e, command(e, text.strip(), r), e["state"]))
        return cands

    def add(e, kind, phrase, text, **more):
        if e["i"] in used or not text:
            return False
        if light(e) and (not lights_ok or any(light(c["e"]) for c in out)):
            return False                                     # the traffic lights are on every window: at most one of them per screen
        if e["where"] in ("dock", "menubar") and sum(c["e"]["where"] == e["where"] for c in out) >= (dock_cap if e["where"] == "dock" else 2):
            return False
        used.add(e["i"])
        out.append(dict(e=e, kind=kind, phrase=phrase, instruction=text, tiny=tiny(e), partial=partial(e), **more))
        return True

    def take(kind, cands, n):
        """cands: (element, text, detail, weight)."""
        cands = [c for c in cands if c[0]["i"] not in used and c[1]]
        while n > 0 and cands:
            c = r.choices(cands, weights=[c[3] for c in cands])[0]
            cands = [x for x in cands if x[0] is not c[0]]
            n -= add(c[0], kind, kind, c[1], detail=c[2])

    pos = positions()
    # Calendar's Previous / Today / Next: the mistake that started this folder. One of the three on every Calendar screen.
    trio = [e for e in targets if e["app"] == "calendar" and e["where"] == "window" and e["name"] in ("Previous", "Today", "Next") and e["role"] == "button"]
    if trio:
        e = r.choice(trio)
        how = r.choice(["name", "function", "position"])
        p = [c for c in pos if c[0] is e]
        text, detail = (by_function(e) if how == "function" else (p[0][1], p[0][2]) if how == "position" and p else (None, None))
        if not text:
            how, (text, detail) = ("name", by_name(e)) if not e["same"] else ("same_name", by_same(e))
        add(e, how, how, text, detail=detail, must="calendar_nav")
    shuffled = lambda: r.sample(targets, len(targets))
    for where, n in (("menu", 2), ("alert", 1), ("popover", 1), ("spotlight", 1)):          # what is open on top is asked for
        for e in shuffled():
            if n <= 0:
                break
            if e["where"] != where:
                continue
            ways = [("name", by_name), ("name", by_name), ("same_name", by_same), ("function", by_function)]
            r.shuffle(ways)
            p = [c for c in pos if c[0] is e]
            for how, f in ways + ([("position", lambda e: (p[0][1], p[0][2]))] if p else []):
                text, detail = f(e)
                if text and add(e, how, how, text, detail=detail, must=where):
                    n -= 1
                    break
    for kind, pick in (("partial", partial), ("tiny", tiny)):               # hard targets first, phrased in whichever way fits
        n = want.get(kind, 0)
        for e in shuffled():
            if n <= 0:
                break
            if not pick(e) or e["i"] in used:
                continue
            ways = [("name", by_name), ("function", by_function), ("same_name", by_same)]
            r.shuffle(ways)
            p = [c for c in pos if c[0] is e]
            for how, f in ways + ([("position", lambda e: (p[0][1], p[0][2]))] if p else []):
                text, detail = f(e)
                if text and add(e, kind, how, text, detail=detail):
                    n -= 1
                    break
    same = [(e, *by_same(e)) for e in shuffled()]
    take("same_name", [(e, t, d, 3 if d == "window" else 1) for e, t, d in same], want.get("same_name", 0))
    take("position", [c for c in pos if c[2] == "neighbour"], (want.get("position", 0) + 1) // 2)
    take("position", pos, want.get("position", 0) - sum(c["kind"] == "position" for c in out))
    take("state", [(e, t, d, 1) for e, t, d in states()], want.get("state", 0))
    take("function", [(e, *by_function(e), 2 if e["icon"] else 1) for e in shuffled() if e["fn"]], want.get("function", 0))
    take("name", [(e, *by_name(e), 2 if e["icon"] else 1) for e in shuffled()], want.get("name", 0))
    return out, by_i


def record(c, by_i, surf, screen, k):
    """One challenge as a case in the loader's format (cases.jsonl of bench/pointing/generate.py), plus what the scorer needs."""
    e = c["e"]
    small = lambda x: {"name": x["name"], "role": x["role"], "box": x["full"]}
    w, h = e["box"][2] - e["box"][0], e["box"][3] - e["box"][1]
    label_visible = bool(e["text"]) and e["name"].split(": ")[-1].lower() in e["text"].lower()
    ui = "icon" if e["icon"] or not label_visible else "text"
    meta = {"archetype": "macsim_" + c["kind"], "kind": c["kind"], "phrase": c["phrase"], "detail": c.get("detail"), "split": screen["split"], "seed": screen["seed"], "screen": screen["id"], "points": screen["points"],
            "scale": screen["scale"], "theme": screen["theme"], "app": e["app"], "where": e["where"], "surface": e["surface"], "role": e["role"], "name": e["name"], "function": e["fn"], "state": e["state"],
            "visible": round(e["vis"], 2), "full_box": e["full"], "holes": e["holes"], "tiny": c["tiny"], "partial": c["partial"],
            "neighbours": {d: dict(small(by_i[j]), gap=g) for d, (j, g) in e["nb"].items()}, "same_name": [dict(small(x), surface=x["surface"]) for x in e["same"]],
            "surfaces": [{"name": u["name"], "box": u["box"]} for u in surf]}
    if c.get("must"):
        meta["must"] = c["must"]
    return {"id": f"{screen['id']}-{k:02d}", "image": screen["image"], "width": screen["width"], "height": screen["height"], "bbox": e["box"], "instruction": c["instruction"],
            "element": {"label": e["name"], "label_visible": label_visible, "region": e["surface"], "role": e["role"], "ui_type": ui},
            "tags": {"archetype": "macsim", "instruction_kind": c["phrase"], "challenge": c["kind"], "surface": e["where"], "app": e["app"] or "", "theme": screen["theme"], "ui_type": ui, "state": e["state"] or "normal",
                     "w1280": w, "h1280": h, "size": "xs" if min(w, h) <= TINY else "s" if min(w, h) <= 28 else "m" if max(w, h) <= 160 else "l", "tiny": c["tiny"], "partial": c["partial"], "window_size": "x".join(map(str, screen["points"]))},
            "meta": meta}


def public(e):
    """An element as screens.jsonl stores it."""
    return {"i": e["i"], "role": e["role"], "label": e["name"], "function": e["fn"], "state": e["state"], "bbox": e["box"], "full_box": e["full"], "visible": round(e["vis"], 2), "region": e["surface"], "where": e["where"],
            "app": e["app"], "icon": e["icon"], "dim": e["dim"], "parent": e["parent"], "neighbours": {d: j for d, (j, g) in e["nb"].items()}}
