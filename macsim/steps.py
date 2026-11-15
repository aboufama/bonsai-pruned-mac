"""macsim.steps: short multi-step tasks, each solved by a scripted oracle and judged by a state checker.

A task is a function of (rng, state) that returns None when the screen does not allow it, or
    {"request": what the user asks, "steps": [...], "check": state -> bool, "behind": start with the app's window behind}
A step is a click, double click or right click on an element found by role, name, place and function, or typed text,
or a key. run() plays the steps in the browser; before each step it saves the screenshot, the oracle's action and
(for clicks) the target with its box and neighbours. Only tasks whose checker says "done" are kept.
"""
import copy
import datetime
import random

from . import cases, sim as simlib, world

TASKS = {}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
T = cases.TITLE
MAIL_SUBJECTS = ["Skylight quote", "Invoice 0412 for the awning", "Spare keys for the lock-up", "Second draft of the leaflet", "A question about the allotment", "Minutes of the quiz committee", "Slot on the 19th", "Pictures from the regatta"]
CHAT_TEXTS = ["Leaving the depot now", "Understood, cheers", "Can we speak at ten to five?", "Yes, the pair of us", "The file is in your inbox", "Back within the quarter hour", "Many happy returns!", "Whenever suits you"]


def task(name, app):
    def deco(fn):
        TASKS[name] = (app, fn)
        return fn
    return deco


def C(say, **find):
    return {"do": "click", "say": say, "find": find}


def D(say, **find):
    return {"do": "double", "say": say, "find": find}


def R(say, **find):
    return {"do": "right", "say": say, "find": find}


def TY(text, say=None):
    return {"do": "type", "text": text, "say": say or f"type “{text}”"}


def K(keys, say):
    return {"do": "key", "keys": keys, "say": say}


def menu(app, m, item, say):
    return [C(f"the {m} menu in the menu bar", role="menu", name=m, where="menubar"), C(f"“{item}” in the {m} menu", role="menu item", name=item, where="menu")]


# ------------------------------------------------------------------ Calendar
@task("cal_move", "calendar")
def cal_move(r, st):
    s = st["apps"]["calendar"]
    u = s["ui"]
    u["view"], u["pop"] = r.choice(["Month", "Month", "Week", "Year"]), None
    k, d = r.randint(1, 3), r.choice([-1, 1])
    a = datetime.date.fromisoformat(u["anchor"])
    if u["view"] == "Month":
        m = a.year * 12 + a.month - 1 + k * d
        goal, req = f"{m // 12}-{m % 12 + 1:02d}", f"Show {MONTHS[m % 12]} {m // 12} in Calendar"
        ok = lambda S: S["apps"]["calendar"]["ui"]["anchor"][:7] == goal
    elif u["view"] == "Year":
        goal, req = str(a.year + k * d), f"Show the year {a.year + k * d} in Calendar"
        ok = lambda S: S["apps"]["calendar"]["ui"]["anchor"][:4] == goal
    else:
        goal, req = (a + datetime.timedelta(days=7 * k * d)).isoformat(), f"Go {'forward' if d > 0 else 'back'} {['one week', 'two weeks', 'three weeks'][k - 1]} in Calendar"
        ok = lambda S: S["apps"]["calendar"]["ui"]["anchor"] == goal
    unit = u["view"].lower()
    step = C(f"the {'Next' if d > 0 else 'Previous'} arrow beside Today, to go {'forward' if d > 0 else 'back'} one {unit}", role="button", name="Next" if d > 0 else "Previous", app="calendar", where="window")
    return {"request": req, "steps": [step] * k, "check": ok}


@task("cal_view_move", "calendar")
def cal_view_move(r, st):
    u = st["apps"]["calendar"]["ui"]
    u["pop"] = None
    v = r.choice([x for x in ("Day", "Week", "Month") if x != u["view"]])
    d = r.choice([-1, 1])
    word = {"Day": "day", "Week": "week", "Month": "month"}[v]
    return {"request": f"Switch Calendar to {v} view and go to the {'next' if d > 0 else 'previous'} {word}",
            "steps": [C(f"the {v} tab in Calendar", role="tab", name=v, app="calendar"), C(f"the {'Next' if d > 0 else 'Previous'} arrow beside Today", role="button", name="Next" if d > 0 else "Previous", app="calendar", where="window")],
            "check": lambda S, a=u["anchor"]: S["apps"]["calendar"]["ui"]["view"] == v and S["apps"]["calendar"]["ui"]["anchor"] != a}


@task("cal_today", "calendar")
def cal_today(r, st):
    s = st["apps"]["calendar"]
    u = s["ui"]
    u["pop"], u["view"] = None, r.choice(["Month", "Week", "Year"])
    u["anchor"] = (datetime.date.fromisoformat(s["today"]) + datetime.timedelta(days=r.choice([-70, -40, 45, 80]))).isoformat()
    return {"request": "Go back to today in Calendar and show it by day", "steps": [C("the Today button in Calendar", role="button", name="Today", app="calendar"), C("the Day tab", role="tab", name="Day", app="calendar")],
            "check": lambda S: S["apps"]["calendar"]["ui"]["anchor"] == S["apps"]["calendar"]["today"] and S["apps"]["calendar"]["ui"]["view"] == "Day"}


@task("cal_hide", "calendar")
def cal_hide(r, st):
    s = st["apps"]["calendar"]
    on = [c for c in s["cals"] if c["on"]]
    if len(on) < 2:
        return None
    a, b = r.sample(on, 2)
    side = s["ui"]["side"] = r.random() < 0.5
    s["ui"]["pop"] = None
    steps = ([] if side else [C("the Calendars button, to show the list of calendars", role="button", name="Calendars", app="calendar")]) + [C(f"the checkbox of the {c['name']} calendar", role="checkbox", name=c["name"], app="calendar") for c in (a, b)]
    return {"request": f"Hide the {a['name']} and {b['name']} calendars", "steps": steps, "check": lambda S: all(not c["on"] for c in S["apps"]["calendar"]["cals"] if c["id"] in (a["id"], b["id"]))}


@task("cal_delete", "calendar")
def cal_delete(r, st):
    s = st["apps"]["calendar"]
    on = {c["id"] for c in s["cals"] if c["on"]}
    good = []
    for e in s["events"]:
        day = sorted((x for x in s["events"] if x["date"] == e["date"] and x["cal"] in on), key=lambda x: x["start"])
        if e in day[:3]:
            good.append(e)
    if not good:
        return None
    e = r.choice(good)
    s["ui"].update(view="Month", anchor=e["date"], pop=None)
    return {"request": f"Delete the event “{e['title']}” from the calendar", "steps": [C(f"the event “{e['title']}”", role="event", name=e["title"], app="calendar"), C("the Delete Event button in the popover", role="button", name="Delete Event", where="popover")],
            "check": lambda S: all(x["id"] != e["id"] for x in S["apps"]["calendar"]["events"])}


@task("cal_menu", "calendar")
def cal_menu(r, st):
    u = st["apps"]["calendar"]["ui"]
    u["pop"] = None
    v = r.choice([x for x in ("Day", "Week", "Month", "Year") if x != u["view"]])
    return {"request": f"Use the View menu to show the calendar by {v.lower()}", "steps": menu("calendar", "View", f"By {v}", ""), "check": lambda S: S["apps"]["calendar"]["ui"]["view"] == v}


# ------------------------------------------------------------------ Finder
PLACE = {"docs": "Documents", "down": "Downloads", "desktop": "Desktop"}


@task("fin_open", "finder")
def fin_open(r, st):
    s = st["apps"]["finder"]
    f = r.choice([i for i in s["items"] if i["kind"] == "folder"])
    s["ui"].update(path=r.choice([p for p in PLACE if p != f["parent"]]), sel=None, view=r.choice(["list", "icons"]))
    return {"request": f"Open the {f['name']} folder in {PLACE[f['parent']]}", "steps": [C(f"{PLACE[f['parent']]} in the Finder sidebar", role="sidebar item", name=PLACE[f["parent"]], app="finder"), D(f"the {f['name']} folder", role="file", name=f["name"], app="finder")],
            "check": lambda S: S["apps"]["finder"]["ui"]["path"] == f["id"]}


@task("fin_bin", "finder")
def fin_bin(r, st):
    s = st["apps"]["finder"]
    here = [i for i in s["items"] if i["parent"] == s["ui"]["path"]]
    if not here:
        return None
    f = r.choice(here[:8])
    s["ui"]["sel"] = None
    if r.random() < 0.5:
        steps = [R(f"“{f['name']}”", role="file", name=f["name"], app="finder"), C("“Move to Bin” in the menu", role="menu item", name="Move to Bin", where="menu")]
    else:
        steps = [C(f"“{f['name']}”", role="file", name=f["name"], app="finder")] + menu("finder", "File", "Move to Bin", "")
    return {"request": f"Move “{f['name']}” to the Bin", "steps": steps, "check": lambda S: next(i for i in S["apps"]["finder"]["items"] if i["id"] == f["id"])["parent"] == "bin"}


@task("fin_view", "finder")
def fin_view(r, st):
    u = st["apps"]["finder"]["ui"]
    p = r.choice([x for x in PLACE if x != u["path"]])
    v, n = r.choice([x for x in (("icons", "Icon"), ("list", "List"), ("gallery", "Gallery")) if x[0] != u["view"]])
    return {"request": f"Show {PLACE[p]} in Finder as {'a list' if v == 'list' else 'a gallery' if v == 'gallery' else 'icons'}",
            "steps": [C(f"{PLACE[p]} in the Finder sidebar", role="sidebar item", name=PLACE[p], app="finder"), C(f"the {n} view button in the Finder toolbar", role="button", name=f"{n} view", app="finder")],
            "check": lambda S: S["apps"]["finder"]["ui"]["path"] == p and S["apps"]["finder"]["ui"]["view"] == v}


@task("fin_new", "finder")
def fin_new(r, st):
    u = st["apps"]["finder"]["ui"]
    p = r.choice([x for x in PLACE if x != u["path"]])
    return {"request": f"Create a new folder in {PLACE[p]}", "steps": [C(f"{PLACE[p]} in the Finder sidebar", role="sidebar item", name=PLACE[p], app="finder")] + menu("finder", "File", "New Folder", ""),
            "check": lambda S: sum(i["name"] == "untitled folder" and i["parent"] == p for i in S["apps"]["finder"]["items"]) == 1}


# ------------------------------------------------------------------ Mail
def a_message(r, s, box="inbox", n=6):
    ms = [m for m in s["msgs"] if m["box"] == box][:n]
    return r.choice(ms) if ms else None


@task("mail_act", "mail")
def mail_act(r, st):
    s = st["apps"]["mail"]
    s["ui"].update(box="inbox", sel=None, compose=False)
    m = a_message(r, s)
    if not m:
        return None
    m["flag"] = False
    what = r.choice(["flag", "archive", "delete"])
    name = f"{m['from']}: {m['subject']}"
    btn, ok = {"flag": ("Flag", lambda x: x["flag"]), "archive": ("Archive", lambda x: x["box"] == "archive"), "delete": ("Delete", lambda x: x["box"] == "bin")}[what]
    if what == "flag" and r.random() < 0.4:
        steps = [R(f"the email from {m['from']}", role="message", name=name, app="mail"), C("“Flag” in the menu", role="menu item", name="Flag", where="menu")]
    else:
        steps = [C(f"the email “{m['subject']}” from {m['from']}", role="message", name=name, app="mail"), C(f"the {btn} button in the Mail toolbar", role="button", name=btn, app="mail", where="window")]
    return {"request": f"{what.capitalize()} the email from {m['from']} about “{m['subject']}”", "steps": steps, "check": lambda S: ok(next(x for x in S["apps"]["mail"]["msgs"] if x["id"] == m["id"]))}


@task("mail_box", "mail")
def mail_box(r, st):
    s = st["apps"]["mail"]
    s["ui"].update(box="inbox", sel=None, compose=False)
    box = r.choice(["archive", "sent", "junk"])
    m = a_message(r, s, box)
    if not m:
        return None
    bname = next(b["name"] for b in s["boxes"] if b["id"] == box)
    return {"request": f"Find the email “{m['subject']}” in {bname} and delete it",
            "steps": [C(f"the {bname} mailbox", role="mailbox", name=bname, app="mail"), C(f"the email “{m['subject']}”", role="message", name=f"{m['from']}: {m['subject']}", app="mail"), C("the Delete button in the Mail toolbar", role="button", name="Delete", app="mail", where="window")],
            "check": lambda S: next(x for x in S["apps"]["mail"]["msgs"] if x["id"] == m["id"])["box"] == "bin"}


@task("mail_write", "mail")
def mail_write(r, st):
    s = st["apps"]["mail"]
    s["ui"].update(compose=False, draft={})
    to = f"{r.choice(world.FIRST).lower()}@{r.choice(['example.com', 'mail.example', 'studio.example'])}"
    subj = r.choice(MAIL_SUBJECTS)
    return {"request": f"Write an email to {to} with the subject “{subj}” and send it",
            "steps": [C("the New Message button in the Mail toolbar", role="button", name="New Message", app="mail"), TY(to, f"type the address {to} in the To field"), C("the Subject field of the new message", role="text field", name="Subject", app="mail"), TY(subj, f"type the subject “{subj}”"),
                      C("the Send button of the new message", role="button", name="Send", app="mail")],
            "check": lambda S: bool(S["apps"]["mail"]["sent"]) and S["apps"]["mail"]["sent"][-1].get("To") == to and S["apps"]["mail"]["sent"][-1].get("Subject") == subj}


# ------------------------------------------------------------------ Notes
@task("notes_delete", "notes")
def notes_delete(r, st):
    s = st["apps"]["notes"]
    s["ui"].update(side=True, view="list")
    n = r.choice(s["notes"][:8])
    other = [f for f in s["folders"] if f["id"] != n["folder"]]
    s["ui"]["folder"] = other[0]["id"]
    s["ui"]["sel"] = next((x["id"] for x in s["notes"] if x["folder"] == other[0]["id"]), None)
    fname = next(f["name"] for f in s["folders"] if f["id"] == n["folder"])
    return {"request": f"Delete the note “{n['title']}” from the {fname} folder",
            "steps": [C(f"the {fname} folder in the Notes sidebar", role="folder", name=fname, app="notes"), C(f"the note “{n['title']}” in the list", role="note", name=n["title"], app="notes"), C("the Delete button in the Notes toolbar", role="button", name="Delete", app="notes")],
            "check": lambda S: all(x["id"] != n["id"] for x in S["apps"]["notes"]["notes"])}


@task("notes_gallery", "notes")
def notes_gallery(r, st):
    s = st["apps"]["notes"]
    s["ui"]["view"] = "list"
    here = [n for n in s["notes"] if n["folder"] == s["ui"]["folder"] and n["id"] != s["ui"]["sel"]][:6]
    if not here:
        return None
    n = r.choice(here)
    return {"request": f"Show the notes as a gallery, then open “{n['title']}”", "steps": [C("the Gallery view button in the Notes toolbar", role="button", name="Gallery view", app="notes"), C(f"the note “{n['title']}”", role="note", name=n["title"], app="notes")],
            "check": lambda S: S["apps"]["notes"]["ui"]["sel"] == n["id"]}


@task("notes_new", "notes")
def notes_new(r, st):
    s = st["apps"]["notes"]
    s["ui"]["side"] = True
    f = r.choice([f for f in s["folders"] if f["id"] != s["ui"]["folder"]])
    return {"request": f"Start a fresh note inside the {f['name']} folder", "steps": [C(f"the {f['name']} folder in the Notes sidebar", role="folder", name=f["name"], app="notes"), C("the New Note button in the Notes toolbar", role="button", name="New Note", app="notes")],
            "check": lambda S: S["apps"]["notes"]["notes"][0]["title"] == "New Note" and S["apps"]["notes"]["notes"][0]["folder"] == f["id"]}


# ------------------------------------------------------------------ Reminders
@task("rem_done", "reminders")
def rem_done(r, st):
    s = st["apps"]["reminders"]
    open_ = [i for i in s["items"] if not i["done"]]
    i = r.choice(open_)
    l = next(x for x in s["lists"] if x["id"] == i["list"])
    if sum(x["list"] == l["id"] and not x["done"] for x in s["items"][:s["items"].index(i)]) > 7:
        return None
    s["ui"]["list"] = r.choice([x["id"] for x in s["lists"] if x["id"] != l["id"]])
    return {"request": f"Mark “{i['title']}” as completed in the {l['name']} list", "steps": [C(f"the {l['name']} list in the Reminders sidebar", role="list", name=l["name"], app="reminders"), C(f"the circle next to “{i['title']}”", role="checkbox", name=i["title"], app="reminders")],
            "check": lambda S: next(x for x in S["apps"]["reminders"]["items"] if x["id"] == i["id"])["done"]}


@task("rem_show", "reminders")
def rem_show(r, st):
    s = st["apps"]["reminders"]
    s["ui"]["show"] = False
    l = r.choice(s["lists"])
    s["ui"]["list"] = r.choice([x["id"] for x in s["lists"] if x["id"] != l["id"]])
    return {"request": f"Open the {l['name']} list and show its completed reminders", "steps": [C(f"the {l['name']} list in the Reminders sidebar", role="list", name=l["name"], app="reminders")] + menu("reminders", "View", "Show Completed", ""),
            "check": lambda S: S["apps"]["reminders"]["ui"]["show"] and S["apps"]["reminders"]["ui"]["list"] == l["id"]}


@task("rem_add", "reminders")
def rem_add(r, st):
    s = st["apps"]["reminders"]
    l = r.choice(s["lists"])
    s["ui"]["list"] = r.choice([x["id"] for x in s["lists"] if x["id"] != l["id"]])
    n = len(s["items"])
    return {"request": f"Add a new reminder to the {l['name']} list", "steps": [C(f"the {l['name']} list in the Reminders sidebar", role="list", name=l["name"], app="reminders"), C("the New Reminder button (the plus)", role="button", name="New Reminder", app="reminders")],
            "check": lambda S: len(S["apps"]["reminders"]["items"]) == n + 1 and S["apps"]["reminders"]["items"][-1]["list"] == l["id"]}


# ------------------------------------------------------------------ Safari
@task("saf_tab_back", "safari")
def saf_tab_back(r, st):
    s = st["apps"]["safari"]
    others = [t for t in s["tabs"] if t["id"] != s["active"]]
    if not others:
        return None
    t = r.choice(others)
    t["back"] = [r.choice([k for k in s["pages"] if k != t["page"]])]
    title = s["pages"][t["page"]]["title"]
    return {"request": f"Switch to the {title} tab in Safari and go back one page", "steps": [C(f"the {title} tab in Safari", role="tab", name=title, app="safari"), C("the Back arrow in the Safari toolbar", role="button", name="Back", app="safari")],
            "check": lambda S: S["apps"]["safari"]["active"] == t["id"] and next(x for x in S["apps"]["safari"]["tabs"] if x["id"] == t["id"])["page"] == t["back"][0]}


@task("saf_close", "safari")
def saf_close(r, st):
    s = st["apps"]["safari"]
    if len(s["tabs"]) < 2:
        return None
    t = r.choice(s["tabs"])
    title = s["pages"][t["page"]]["title"]
    return {"request": f"Close the {title} tab in Safari", "steps": [C(f"the small close button on the {title} tab", role="button", name="Close Tab", fn=f"close the {title} tab", app="safari")],
            "check": lambda S: all(x["id"] != t["id"] for x in S["apps"]["safari"]["tabs"])}


@task("saf_fav", "safari")
def saf_fav(r, st):
    s = st["apps"]["safari"]
    s["showFavs"] = True
    cur = next(t for t in s["tabs"] if t["id"] == s["active"])
    f = r.choice([f for f in s["favs"] if f["page"] != cur["page"]])
    return {"request": f"Open {f['title']} from the favourites bar, then come back to the page you were on", "steps": [C(f"{f['title']} in the favourites bar", role="link", name=f["title"], fn=f"open the {f['title']} favourite", app="safari"), C("the Back arrow in the Safari toolbar", role="button", name="Back", app="safari")],
            "check": lambda S, p=cur["page"]: next(x for x in S["apps"]["safari"]["tabs"] if x["id"] == S["apps"]["safari"]["active"])["page"] == p and next(x for x in S["apps"]["safari"]["tabs"] if x["id"] == S["apps"]["safari"]["active"])["fwd"][-1:] == [f["page"]]}


@task("saf_newtab", "safari")
def saf_newtab(r, st):
    s = st["apps"]["safari"]
    k = r.choice([k for k in s["pages"] if k != s["home"]])
    host = s["pages"][k]["host"]
    return {"request": f"Open a new tab in Safari and go to {host}", "steps": [C("the New Tab button (the plus) in the Safari toolbar", role="button", name="New Tab", app="safari"), TY(host, f"type {host} in the address field"), K("Enter", "press Return")],
            "check": lambda S, n=len(s["tabs"]): len(S["apps"]["safari"]["tabs"]) == n + 1 and next(x for x in S["apps"]["safari"]["tabs"] if x["id"] == S["apps"]["safari"]["active"])["page"] == k}


@task("saf_form", "safari")
def saf_form(r, st):
    s = st["apps"]["safari"]
    forms = [k for k, p in s["pages"].items() if p["kind"] == "form"]
    if not forms:
        return None
    k = r.choice(forms)
    next(t for t in s["tabs"] if t["id"] == s["active"])["page"] = k
    pg = s["pages"][k]
    f = r.choice(pg["fields"])
    val = {"Email": "m.rowe@example.com", "Password": "tulip-harbour-19", "Full name": world.person(r), "Phone": "0161 555 0142", "Member number": str(r.randint(100000, 999999)), "Postcode": r.choice(["M4 1HQ", "EH8 9YL", "BS1 5TR"])}[f]
    return {"request": f"On the {pg['site']} page, enter {val} as the {f.lower()} and press {pg['submit']}",
            "steps": [C(f"the {f} field on the page", role="text field", name=f, app="safari"), TY(val), C(f"the {pg['submit']} button on the page", role="button", name=pg["submit"], app="safari")],
            "check": lambda S: (S["apps"]["safari"].get("submitted") or {}).get(f) == val}


# ------------------------------------------------------------------ System Settings
def a_row(r, s, kind, panes=12):
    names = [p["name"] for p in s["panes"][:panes] if p["name"] != s["ui"]["pane"]]
    r.shuffle(names)
    for n in names:
        rows = [x for g in s["rows"][n] for x in g["rows"] if x["t"] == kind]
        if rows:
            return n, r.choice(rows)
    return None, None


@task("set_switch", "settings")
def set_switch(r, st):
    s = st["apps"]["settings"]
    p, row = a_row(r, s, r.choice(["switch", "switch", "check"]))
    if not row:
        return None
    want = not row["v"]
    thing = "switch" if row["t"] == "switch" else "checkbox"
    return {"request": f"Turn {'on' if want else 'off'} “{row['label']}” in {p} settings",
            "steps": [C(f"{p} in the System Settings sidebar", role="sidebar item", name=p, app="settings"), C(f"the {thing} for “{row['label']}”", role=thing, name=row["label"], app="settings")],
            "check": lambda S: S["apps"]["settings"]["ui"]["pane"] == p and next(x for g in S["apps"]["settings"]["rows"][p] for x in g["rows"] if x["k"] == row["k"])["v"] == want}


@task("set_popup", "settings")
def set_popup(r, st):
    s = st["apps"]["settings"]
    p, row = a_row(r, s, "popup")
    if not row:
        return None
    o = r.choice([x for x in row["opts"] if x != row["v"]])
    return {"request": f"In {p} settings, set “{row['label']}” to {o}",
            "steps": [C(f"{p} in the System Settings sidebar", role="sidebar item", name=p, app="settings"), C(f"the pop-up button for “{row['label']}”", role="pop-up button", name=row["label"], app="settings"), C(f"“{o}” in the menu", role="menu item", name=o, where="menu")],
            "check": lambda S: next(x for g in S["apps"]["settings"]["rows"][p] for x in g["rows"] if x["k"] == row["k"])["v"] == o}


@task("set_step", "settings")
def set_step(r, st):
    s = st["apps"]["settings"]
    p, row = a_row(r, s, "stepper")
    if not row:
        return None
    k, d = r.randint(1, 3), r.choice([1, -1])
    row["v"] = max(row["v"], 4)
    name = ("Increase " if d > 0 else "Decrease ") + row["label"]
    return {"request": f"In {p} settings, {'raise' if d > 0 else 'lower'} “{row['label']}” by {k}",
            "steps": [C(f"{p} in the System Settings sidebar", role="sidebar item", name=p, app="settings")] + [C(f"the small {'up' if d > 0 else 'down'} arrow of the “{row['label']}” stepper", role="button", name=name, app="settings")] * k,
            "check": lambda S, v=row["v"]: next(x for g in S["apps"]["settings"]["rows"][p] for x in g["rows"] if x["k"] == row["k"])["v"] == v + k * d}


# ------------------------------------------------------------------ Messages
@task("msg_send", "messages")
def msg_send(r, st):
    s = st["apps"]["messages"]
    names = [c["name"] for c in s["chats"]]
    cands = [c for c in s["chats"][:6] if c["id"] != s["ui"]["chat"] and names.count(c["name"]) == 1]
    if not cands:
        return None
    c = r.choice(cands)
    text = r.choice(CHAT_TEXTS)
    return {"request": f"Send “{text}” to {c['name']} in Messages",
            "steps": [C(f"the conversation with {c['name']}", role="conversation", name=c["name"], app="messages"), C("the iMessage field at the bottom", role="text field", name="iMessage", app="messages"), TY(text), K("Enter", "press Return to send")],
            "check": lambda S: next(x for x in S["apps"]["messages"]["chats"] if x["id"] == c["id"])["msgs"][-1] == {"me": True, "text": text}}


# ------------------------------------------------------------------ Music
@task("mus_song", "music")
def mus_song(r, st):
    s = st["apps"]["music"]
    s["ui"]["view"] = r.choice(["albums", "home", s["playlists"][0]["id"]])
    x = r.choice([x for x in s["songs"][:9] if x["id"] != s["player"]["cur"]])
    return {"request": f"Play the song “{x['title']}” in Music", "steps": [C("Songs in the Music sidebar", role="sidebar item", name="Songs", app="music"), D(f"the song “{x['title']}”", role="song", name=x["title"], app="music")],
            "check": lambda S: S["apps"]["music"]["player"]["cur"] == x["id"] and S["apps"]["music"]["player"]["playing"]}


@task("mus_shuffle", "music")
def mus_shuffle(r, st):
    s = st["apps"]["music"]
    s["player"]["shuffle"] = False
    p = r.choice([p for p in s["playlists"] if p["id"] != s["ui"]["view"]])
    return {"request": f"Open the {p['name']} playlist and turn shuffle on", "steps": [C(f"the {p['name']} playlist in the Music sidebar", role="playlist", name=p["name"], app="music"), C("the Shuffle button at the left of the Music toolbar", role="button", name="Shuffle", fn="play songs in a random order", app="music")],
            "check": lambda S: S["apps"]["music"]["ui"]["view"] == p["id"] and S["apps"]["music"]["player"]["shuffle"]}


@task("mus_skip", "music")
def mus_skip(r, st):
    s = st["apps"]["music"]
    k, d = r.randint(2, 3), r.choice([1, -1])
    ids = [x["id"] for x in s["songs"]]
    goal = ids[(ids.index(s["player"]["cur"]) + k * d) % len(ids)]
    name, fn = ("Next", "skip to the next song") if d > 0 else ("Previous", "skip back")
    return {"request": f"Skip {'ahead' if d > 0 else 'back'} {['', '', 'two', 'three'][k]} songs in Music", "steps": [C(f"the {name} button in the Music toolbar", role="button", name=name, fn=fn, app="music")] * k, "check": lambda S: S["apps"]["music"]["player"]["cur"] == goal}


@task("mus_menu", "music")
def mus_menu(r, st):
    p = st["apps"]["music"]["player"]
    return {"request": f"Use the Controls menu to {'pause' if p['playing'] else 'start'} the music", "steps": menu("music", "Controls", "Pause" if p["playing"] else "Play", ""), "check": lambda S, was=p["playing"]: S["apps"]["music"]["player"]["playing"] != was}


# ------------------------------------------------------------------ Dock, Spotlight (any app)
def follow(r, st, app):
    s = st["apps"][app]
    u = s["ui"]
    if app == "mail":
        b = r.choice([b for b in s["boxes"][:7] if b["id"] != u["box"]])
        return f"open the {b['name']} mailbox", C(f"the {b['name']} mailbox", role="mailbox", name=b["name"], app=app), lambda S: S["apps"][app]["ui"]["box"] == b["id"]
    if app == "notes" and u["side"]:
        f = r.choice([f for f in s["folders"] if f["id"] != u["folder"]])
        return f"open the {f['name']} folder", C(f"the {f['name']} folder in the Notes sidebar", role="folder", name=f["name"], app=app), lambda S: S["apps"][app]["ui"]["folder"] == f["id"]
    if app == "reminders":
        l = r.choice([l for l in s["lists"] if l["id"] != u["list"]])
        return f"open the {l['name']} list", C(f"the {l['name']} list", role="list", name=l["name"], app=app), lambda S: S["apps"][app]["ui"]["list"] == l["id"]
    if app == "music":
        p = r.choice([p for p in s["playlists"] if p["id"] != u["view"]])
        return f"open the {p['name']} playlist", C(f"the {p['name']} playlist", role="playlist", name=p["name"], app=app), lambda S: S["apps"][app]["ui"]["view"] == p["id"]
    if app == "finder":
        p = r.choice([x for x in PLACE if x != u["path"]])
        return f"show {PLACE[p]}", C(f"{PLACE[p]} in the Finder sidebar", role="sidebar item", name=PLACE[p], app=app), lambda S: S["apps"][app]["ui"]["path"] == p
    if app == "settings":
        p = r.choice([p["name"] for p in s["panes"][:10] if p["name"] != u["pane"]])
        return f"open {p} settings", C(f"{p} in the System Settings sidebar", role="sidebar item", name=p, app=app), lambda S: S["apps"][app]["ui"]["pane"] == p
    if app == "calendar":
        v = r.choice([x for x in ("Day", "Week", "Month", "Year") if x != u["view"]])
        return f"switch it to {v} view", C(f"the {v} tab in Calendar", role="tab", name=v, app=app), lambda S: S["apps"][app]["ui"]["view"] == v
    return None


@task("dock_then", None)
def dock_then(r, st):
    if len(st["windows"]) < 2:
        return None
    app = r.choice([w["app"] for w in st["windows"]])
    f = follow(r, st, app)
    if not f:
        return None
    words, step, ok = f
    return {"request": f"Bring {T[app]} to the front and {words}", "app": app, "behind": True, "steps": [C(f"the {T[app]} icon in the Dock", role="Dock icon", name=T[app], where="dock"), step],
            "check": lambda S: S["windows"][-1]["app"] == app and ok(S)}


@task("spot_open", None)
def spot_open(r, st):
    items = st["spot_items"]
    open_apps = [w["app"] for w in st["windows"]]
    cands = [i for i in items if (i.get("app") in open_apps[:-1]) or i["kind"] != "Application"]
    if not cands:
        return None
    it = r.choice(cands)
    low = it["name"].lower()
    q = next((low[:k] for k in range(3, len(low) + 1) if next(i for i in items if low[:k] in i["name"].lower()) is it), None)
    if not q or not any(x["name"] == "Spotlight" for x in st["extras"]):
        return None
    return {"request": f"Use Spotlight to open {it['name']}", "app": it.get("app"), "behind": bool(it.get("app")),
            "steps": [C("the Spotlight icon (the magnifying glass) in the menu bar", role="status item", name="Spotlight", where="menubar"), TY(q, f"type “{q}” in the Spotlight field"), K("Enter", "press Return to open the first result")],
            "check": lambda S: S.get("opened") == it["name"] and (not it.get("app") or S["windows"][-1]["app"] == it["app"])}


# ------------------------------------------------------------------ the oracle
def find(els, spec):
    out = []
    for e in els:
        if e["vis"] < 0.6 or not e["mid"]:
            continue
        if all((v in e["fn"].split("|")) if k == "fn" else e.get(k) == v for k, v in spec.items()):
            out.append(e)
    return out[0] if len(out) == 1 else None


def run(sim, seed):
    """One task. Returns (trajectory or None, why). The trajectory holds PIL images; the caller saves them."""
    r = random.Random(f"macsim/steps/{seed}")
    base, _ = world.build(seed, "steps")
    for s in base["apps"].values():
        s["ui"]["alert"] = None
    base["spot"] = {"open": False, "query": ""}
    apps = list(base["apps"])
    r.shuffle(apps)
    order = ([None] if r.random() < 0.15 else []) + apps + [None]              # an app of this screen first (the Dock and Spotlight tasks now and then)
    t = None
    for app in order:
        names = [n for n, (x, _) in TASKS.items() if x == app]
        r.shuffle(names)
        for name in names:
            st = copy.deepcopy(base)
            t = TASKS[name][1](r, st)
            if t:
                break
        if t:
            break
    if not t:
        return None, "no task fits"
    app = t.get("app") or TASKS[name][0]
    if app:
        k = next(i for i, w in enumerate(st["windows"]) if w["app"] == app)
        w = st["windows"].pop(k)
        st["windows"].insert(0 if t.get("behind") else len(st["windows"]), w)
        if t.get("behind"):                                   # really behind: the front window covers part of it
            f = st["windows"][-1]
            w["x"], w["y"] = max(4, min(w["x"], f["x"] + f["w"] // 3)), max(st["mb"] + 4, min(w["y"], f["y"] + f["h"] // 4))
    sim.boot(st)
    steps, history = [], []
    for k, step in enumerate(t["steps"]):
        image, scale = sim.shot()
        els, surf, _ = sim.elements()
        simlib.to_image(els, surf, scale)
        rec = {"k": k, "image": image, "say": step["say"], "do": step["do"], "els": els, "surf": surf, "scale": scale, "history": list(history)}
        by_i = cases.prepare(els)
        if step["do"] in ("click", "double", "right"):
            e = find(els, step["find"])
            if e is None:
                return None, f"{name}: step {k + 1} target not on screen ({step['find'].get('name')})"
            for x in els:
                x["all"] = els
            b = e["box"]
            x, y = (b[0] + b[2]) / 2 / scale, (b[1] + b[3]) / 2 / scale
            rec.update(e=e, by_i=by_i, point=[round((b[0] + b[2]) / 2), round((b[1] + b[3]) / 2)])
            sim.click(x, y, button="right" if step["do"] == "right" else "left", count=2 if step["do"] == "double" else 1)
            history.append({"click": "click", "double": "double-click", "right": "right-click"}[step["do"]] + " " + step["say"])
        elif step["do"] == "type":
            rec["text"] = step["text"]
            sim.type(step["text"])
            history.append(step["say"])
        else:
            rec["keys"] = step["keys"]
            sim.key(step["keys"])
            history.append(step["say"])
        steps.append(rec)
    final, scale = sim.shot()
    state, errors = sim.state(), sim.errors()
    try:
        ok = bool(t["check"](state)) and not errors
    except Exception as err:                                  # a checker that cannot read the state is a failed task
        ok, errors = False, errors + [f"check: {err}"]
    if not ok:
        return None, f"{name}: checker says not done {errors[:1]}"
    return {"task": name, "app": app, "request": t["request"], "steps": steps, "final": final, "state": st, "history": history}, "ok"
