"""Real-Mac tasks with checkers that read the guest's state (no screenshots, no model).

TEST ENVIRONMENT ONLY. Every task has: a reset (the guest is brought to a known state, plus the
task's own setup), a request in plain words (one of several paraphrases), and a checker that
returns (passed, detail) from guest commands: files, `defaults`, and AppleScript queries of
Finder, Notes, Reminders, Calendar, TextEdit, Safari, Contacts and System Events.

    instances()            every task instance (template x parameters x paraphrase), in a fixed order
    reset(task)            bring the guest to the task's start state
    task["check"]()        (bool, str)
    task["oracle"]         optional guest script that does the task directly (used only to test the checker)

Wording: the assistant app answers a request that starts with a question word or "show me", or ends with "?",
by pointing or in words and never acts on it (Commands.isQuestion), so no request here is phrased that way.
"""
import json
import random
import re
import time

import vm

SEP = "\x1e"


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ----------------------------------------------------------------- reading the guest

PROBLEMS = []          # reads that got no answer (an app with an open menu or sheet does not answer AppleScript); the runner stores them


def _osa(script, timeout=20):
    """An AppleScript read. An app that has a menu or a modal sheet open does not answer: Escape is pressed once
    (through VNC) and the read is tried again; if there is still no answer the read is recorded as a problem."""
    ok, out = vm.osa(script, timeout=timeout)
    if not ok and ("timeout" in out.lower() or "-1712" in out):
        vm.key(["escape"])
        time.sleep(0.8)
        ok, out = vm.osa(script, timeout=timeout)
        if not ok and ("timeout" in out.lower() or "-1712" in out):
            PROBLEMS.append(script.split("\n")[0][:80] + ": no answer")
    return ok, out

def front_app():
    out = vm.sh("lsappinfo info -only name $(lsappinfo front)")
    m = re.search(r'"LSDisplayName"="(.*)"', out)
    return m.group(1) if m else ""


def running(app):
    return vm.g("/usr/bin/pgrep", "-x", app)[0] == 0


def visible_apps():
    ok, out = _osa('tell application "System Events" to get name of every process whose background only is false')
    return [n.strip() for n in out.split(",")] if ok else []


def safari_urls():
    if not running("Safari"):
        return []
    ok, out = _osa('tell application "Safari"\nset out to ""\nrepeat with w in windows\nrepeat with t in tabs of w\ntry\n'
                     'set out to out & (URL of t) & linefeed\nend try\nend repeat\nend repeat\nreturn out\nend tell')
    return [u for u in out.splitlines() if u.strip()] if ok else []


def safari_front_url():
    if not running("Safari"):
        return ""
    ok, out = _osa('tell application "Safari" to get URL of front document')
    return out if ok else ""


def notes():
    """[(name, plaintext)] of every note outside Recently Deleted."""
    ok, out = _osa('tell application "Notes"\nset out to ""\nrepeat with f in folders\nif name of f is not "Recently Deleted" then\n'
                     'repeat with n in notes of f\nset out to out & (name of n) & tab & (plaintext of n) & (ASCII character 30)\nend repeat\n'
                     'end if\nend repeat\nreturn out\nend tell', timeout=40)
    if not ok:
        return []
    return [tuple((x.split("\t", 1) + [""])[:2]) for x in out.split(SEP) if x.strip()]


def note_folders():
    ok, out = _osa('tell application "Notes" to get name of every folder')
    return [n.strip() for n in out.split(",")] if ok else []


def reminders():
    """[(name, completed, list)]"""
    ok, out = _osa('tell application "Reminders"\nset out to ""\nrepeat with r in reminders\n'
                     'set out to out & (name of r) & tab & (completed of r as string) & tab & (name of container of r) & linefeed\n'
                     'end repeat\nreturn out\nend tell', timeout=40)
    rows = []
    for line in out.splitlines() if ok else []:
        p = line.split("\t")
        if len(p) >= 3:
            rows.append((p[0], p[1] == "true", p[2]))
    return rows


def reminder_lists():
    ok, out = _osa('tell application "Reminders" to get name of every list')
    return [n.strip() for n in out.split(",")] if ok else []


def events():
    """[(summary, 'Y-M-D', hour, calendar)] of every event in the writable calendars."""
    ok, out = _osa('tell application "Calendar"\nset out to ""\nrepeat with c in calendars\ntry\nif writable of c then\n'
                     'repeat with e in (every event of c)\nset d to start date of e\n'
                     'set out to out & (summary of e) & tab & (year of d) & "-" & ((month of d) as integer) & "-" & (day of d) & tab & (hours of d) & tab & (name of c) & linefeed\n'
                     'end repeat\nend if\nend try\nend repeat\nreturn out\nend tell', timeout=40)
    rows = []
    for line in out.splitlines() if ok else []:
        p = line.split("\t")
        if len(p) >= 4:
            rows.append((p[0], p[1], p[2], p[3]))
    return rows


def contacts():
    ok, out = _osa('tell application "Contacts" to get name of every person')
    return [n.strip() for n in out.split(",")] if ok else []


def dark_mode():
    ok, out = _osa('tell application "System Events" to tell appearance preferences to get dark mode')
    return out.strip() == "true"


def dock():
    ok, out = _osa('tell application "System Events" to tell dock preferences to get {autohide, screen edge, magnification, dock size}')
    p = [x.strip() for x in out.split(",")]
    if not ok or len(p) < 4:
        return {}
    return {"autohide": p[0] == "true", "edge": p[1], "magnification": p[2] == "true", "size": float(p[3])}


def textedit_texts():
    if not running("TextEdit"):
        return []
    ok, out = _osa('tell application "TextEdit"\nset out to ""\nrepeat with d in documents\nset out to out & (text of d) & (ASCII character 30)\nend repeat\nreturn out\nend tell')
    return [x for x in out.split(SEP) if x.strip()] if ok else []


def file_text(path):
    return vm.sh(f'f={path}; case "$f" in *.rtf|*.rtfd|*.doc|*.docx|*.odt|*.html) textutil -convert txt -stdout "$f" 2>/dev/null;; *) cat "$f" 2>/dev/null;; esac')


def find_named(stem):
    """Paths in Documents, Desktop, Downloads or the home folder whose file name starts with the stem (any extension)."""
    out = vm.sh(f'find ~/Documents ~/Desktop ~/Downloads ~ -maxdepth 1 -iname {q(stem + "*")} 2>/dev/null | sort -u')
    return [p for p in out.splitlines() if p.strip()]


def exists(path, kind="e"):
    return vm.sh_full(f"test -{kind} {path}")[0] == 0


def settings_window():
    """The pane System Settings shows: the window's title, or (some panes, such as General, leave the title empty)
    the name of the selected row of the sidebar."""
    if not running("System Settings"):
        return ""
    ok, out = _osa('tell application "System Events" to get name of window 1 of process "System Settings"')
    if ok and out.strip():
        return out.strip()
    ok, out = _osa('tell application "System Events" to tell process "System Settings" to get value of static text 1 of UI element 1 of '
                   '(first row of outline 1 of scroll area 1 of group 1 of splitter group 1 of group 1 of window 1 whose selected is true)')
    return out.strip() if ok else ""


def finder_front_path():
    ok, out = _osa('tell application "Finder" to get POSIX path of (target of front Finder window as alias)')
    return out.strip().rstrip("/") if ok else ""


def calculator_texts():
    """What the Calculator window shows (the expression and the result), read through the accessibility helper with
    Calculator in front. Marks and separators are removed: "1,234" -> "1234"."""
    if not running("Calculator"):
        return []
    vm.sh("open -a Calculator")
    time.sleep(0.8)
    out = vm.sh("~/bin/axtool texts", timeout=20)
    try:
        texts = json.loads(out).get("texts", [])
    except Exception:
        texts = []
    clean = []
    for t in texts:
        t = "".join(ch for ch in t if ch not in "\u200e\u200f\u202a\u202c\u2066\u2069, \u00a0")
        clean.append(t.replace("\u00d7", "*").replace("\u00f7", "/").replace("\u2212", "-"))
    return clean


# ----------------------------------------------------------------- reset

SCRIPTABLE = ["Safari", "Notes", "Reminders", "Calendar", "Contacts", "System Settings", "Terminal", "Calculator", "Maps", "Preview", "Mail", "Music"]
KEEP = {"Finder", "bonsai-assistant"}


def quit_apps():
    names = [n for n in visible_apps() if n and n not in KEEP]
    if not names:
        return
    if "TextEdit" in names:
        vm.osa('tell application "TextEdit" to close every document saving no', timeout=10)
        vm.osa('tell application "TextEdit" to quit', timeout=10)
    for n in names:
        if n in SCRIPTABLE:
            vm.osa(f"tell application {q(n)} to quit", timeout=8)
    time.sleep(0.6)
    left = [n for n in visible_apps() if n and n not in KEEP]
    for n in left:
        vm.g("/usr/bin/pkill", "-x", n)
    if left:
        time.sleep(0.5)
        for n in [n for n in visible_apps() if n and n not in KEEP]:
            vm.g("/usr/bin/pkill", "-9", "-x", n)


CLEAN = {
    "files": lambda: vm.sh("find ~/Desktop ~/Documents ~/Downloads ~/.Trash -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null; true"),
    "notes": lambda: vm.osa('tell application "Notes"\nrepeat with f in folders\ntry\nif name of f is not "Recently Deleted" then delete notes of f\nend try\nend repeat\n'
                            'set doomed to {}\nrepeat with f in folders\nif (name of f) is not in {"Notes", "Recently Deleted", "All on My Mac"} then set end of doomed to (name of f)\nend repeat\n'
                            'repeat with n in doomed\ntry\ndelete folder (n as string)\nend try\nend repeat\nend tell', timeout=40),
    "reminders": lambda: vm.osa('tell application "Reminders"\ntry\ndelete every reminder\nend try\nset doomed to {}\nrepeat with l in lists\n'
                                'if (name of l) is not "Reminders" then set end of doomed to (name of l)\nend repeat\n'
                                'repeat with n in doomed\ntry\ndelete list (n as string)\nend try\nend repeat\nend tell', timeout=40),
    "calendar": lambda: vm.osa('tell application "Calendar"\nrepeat with c in calendars\ntry\nif writable of c then delete (every event of c)\nend try\nend repeat\nend tell', timeout=40),
    "contacts": lambda: vm.osa('tell application "Contacts"\ntry\ndelete (every person whose name is not "Managed via Tart")\nsave\nend try\nend tell', timeout=40),
    "dark": lambda: (vm.osa('tell application "System Events" to tell appearance preferences to set dark mode to false'),
                     # macOS 26 has a separate "Icon & widget style" (Default, Dark, Clear, Tinted); a run that picked Dark there leaves dark icons behind
                     vm.sh("if defaults read -g AppleIconAppearanceTheme >/dev/null 2>&1; then defaults delete -g AppleIconAppearanceTheme; "
                           "defaults delete -g AppleIconAppearanceTintColor 2>/dev/null; defaults delete -g AppleIconAppearanceCustomTintColor 2>/dev/null; "
                           "killall Dock; killall NotificationCenter 2>/dev/null; sleep 2; fi; true")),
    "dock": lambda: vm.osa('tell application "System Events" to tell dock preferences\nset autohide to false\nset screen edge to bottom\nset magnification to false\nset dock size to 0.32\nend tell'),
    "finderprefs": lambda: vm.sh("defaults write com.apple.finder ShowPathbar -bool false; defaults write com.apple.finder ShowStatusBar -bool false; killall Finder; sleep 1.5"),
    "clipboard": lambda: vm.sh("printf '' | pbcopy"),
}


APP_DATA = {"notes": "Notes", "reminders": "Reminders", "calendar": "Calendar", "contacts": "Contacts"}


def reset(task, park=(640, 420)):
    """Known start state. Always: open menus and sheets dismissed (Escape), every app quit, test files gone, light mode,
    Dock as shipped, no Finder window. App data (notes, reminders, events, contacts) is cleared when the task's checker
    reads it or when that app was running (so anything an earlier run left behind is gone). Then the task's own setup."""
    vm.key(["escape"])
    time.sleep(0.3)
    vm.key(["escape"])
    names = visible_apps()
    uses = set(task.get("uses", ()))
    quit_apps()                                             # nothing modal survives this; the cleaning below gets answers
    for u in ("files", "dark", "dock"):
        CLEAN[u]()
    if "finderprefs" not in uses and vm.sh("defaults read com.apple.finder ShowPathbar 2>/dev/null; defaults read com.apple.finder ShowStatusBar 2>/dev/null").replace("0", "").strip():
        CLEAN["finderprefs"]()                              # an earlier run switched a Finder bar on
    empty = {"notes": lambda: not notes(), "reminders": lambda: not reminders() and reminder_lists() == ["Reminders"],
             "calendar": lambda: not events(), "contacts": lambda: contacts() == ["Managed via Tart"]}
    for u, app in APP_DATA.items():
        if u in uses or app in names:
            CLEAN[u]()
            if u in uses and not empty[u]():                # the checker reads this: make sure it really is empty
                time.sleep(1.0)
                CLEAN[u]()
    for u in uses - {"files", "dark", "dock"} - set(APP_DATA):
        CLEAN[u]()
    quit_apps()                                             # the apps the cleaning started
    vm.osa('tell application "Finder" to close every window', timeout=10)
    for s in task.get("setup", ()):
        if callable(s):
            s()
        else:
            vm.sh(s)
    vm.osa('tell application "Finder" to activate', timeout=10)
    if park:
        vm.move(park[0], park[1], 0.1)


# ----------------------------------------------------------------- parameters

APPS = ["Calculator", "Notes", "Reminders", "Calendar", "TextEdit", "Safari", "Contacts", "System Settings", "Maps", "Dictionary", "Stickies",
        "Clock", "Terminal", "Activity Monitor", "Font Book", "Chess", "Books", "Podcasts", "Stocks", "Shortcuts", "Disk Utility", "Console",
        "Script Editor", "QuickTime Player", "Photo Booth", "Preview", "Weather", "Music", "App Store", "Freeform"]
SITES = [("apple.com", "apple.com"), ("wikipedia.org", "wikipedia.org"), ("example.com", "example.com"), ("github.com", "github.com"),
         ("nasa.gov", "nasa.gov"), ("python.org", "python.org"), ("duckduckgo.com", "duckduckgo.com"), ("archive.org", "archive.org"),
         ("openstreetmap.org", "openstreetmap.org"), ("mozilla.org", "mozilla.org"), ("news.ycombinator.com", "ycombinator.com"), ("bbc.com", "bbc.")]
SEARCHES = ["weather in Paris", "pizza dough recipe", "how tall is Mount Everest", "macOS keyboard shortcuts", "bonsai tree care", "train from Rome to Florence"]
FOLDERS = ["Projects", "Invoices", "Trip Photos", "Recipes", "Taxes", "Design Drafts", "Meeting Notes", "Archive", "Budget", "Client Files"]
FILES = ["report.txt", "notes.txt", "budget.csv", "todo.txt", "draft.md", "packing-list.txt"]
NOTE_TEXTS = ["Buy oat milk and eggs", "Call the dentist on Monday", "Ideas for the garden", "Pack charger and passport", "Book flights to Lisbon",
              "Water the plants twice a week", "Return library books", "Gift ideas for Dana"]
NOTE_TITLES = ["Groceries", "Travel plans", "Reading list", "Workout plan", "House chores", "Birthday ideas"]
REMINDERS = ["Pay rent", "Call mom", "Renew passport", "Send invoice", "Pick up dry cleaning", "Book dentist", "Water plants", "Submit report"]
LISTS = ["Groceries", "Work", "Errands", "Travel", "Home", "Books to read"]
EVENTS = ["Team sync", "Lunch with Sam", "Dentist", "Project review", "Yoga class", "Budget meeting", "Coffee with Maya", "Flight to Boston"]
PEOPLE = [("Ada", "Lovelace"), ("Alan", "Turing"), ("Grace", "Hopper"), ("Marie", "Curie"), ("Nikola", "Tesla"), ("Rosalind", "Franklin")]
CALC = [(12, "+", 30, "42"), (7, "*", 8, "56"), (144, "/", 12, "12"), (95, "-", 37, "58"), (25, "*", 4, "100"), (81, "/", 9, "9"), (123, "+", 456, "579")]
PANES = ["Appearance", "Displays", "Sound", "Keyboard", "Desktop & Dock", "Wallpaper", "Notifications", "General", "Accessibility", "Network",
         "Bluetooth", "Privacy & Security", "Focus", "Screen Time"]
TEXTS = ["Hello from Bonsai", "Meeting moved to Friday", "The quick brown fox", "Remember to breathe", "Draft agenda for Monday", "Thanks for the update"]
DOCS = ["agenda", "letter", "minutes", "shopping", "poem", "summary"]
PLACES = [("Documents", "Documents"), ("Downloads", "Downloads"), ("Applications", "/Applications"), ("Desktop", "Desktop")]
WORD_OP = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}


def home(p):
    return p if p.startswith("/") else "/Users/admin/" + p


# ----------------------------------------------------------------- checkers (each returns (bool, detail))

def c_front(app):
    def f():
        a = front_app()
        return a == app, f"front app {a!r}"
    return f


def c_url(part, front=True):
    def f():
        us = [safari_front_url()] if front else safari_urls()
        return any(part in (u or "").lower() for u in us), f"Safari {us}"
    return f


def c_search(query):
    def f():
        u = safari_front_url().lower()
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower())]
        hit = sum(w in u for w in words)
        engine = any(e in u for e in ("google.", "duckduckgo.", "bing.", "search.yahoo", "ecosia."))
        return engine and hit >= max(1, len(words) - 1), f"Safari {u!r}"
    return f


def c_dir(path):
    def f():
        ok = exists(q(home(path)), "d")
        if ok:
            return True, f"folder {path} exists"
        seen = vm.sh("find ~/Desktop ~/Documents ~/Downloads -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sed 's|/Users/admin/||' | head -8").replace("\n", "; ")
        return False, f"folder {path} missing; folders found: {seen or 'none'}"
    return f


def c_moved(name, folder):
    def f():
        inside, outside = exists(q(home(f"Desktop/{folder}/{name}")), "f"), exists(q(home(f"Desktop/{name}")), "f")
        return inside and not outside, f"in folder: {inside}, still on Desktop: {outside}"
    return f


def c_renamed(old, new):
    def f():
        a, b = exists(q(home(f"Desktop/{new}")), "f"), exists(q(home(f"Desktop/{old}")), "f")
        ls = vm.sh("ls ~/Desktop").replace("\n", "; ")
        return a and not b, f"new name exists: {a}, old name exists: {b}; Desktop holds: {ls or 'nothing'}"
    return f


def c_trashed(name):
    def f():
        gone = not exists(q(home(f"Desktop/{name}")), "e")
        trash = vm.sh("ls ~/.Trash")
        return gone and name in trash, f"gone from Desktop: {gone}, Trash: {trash[:80]!r}"
    return f


def c_duplicated(name):
    def f():
        stem, ext = name.rsplit(".", 1)
        ls = vm.sh("ls ~/Desktop").splitlines()
        copies = [x for x in ls if x != name and x.startswith(stem) and x.endswith("." + ext)]
        return name in ls and bool(copies), f"Desktop: {ls}"
    return f


def c_finder_at(path):
    def f():
        p = finder_front_path()
        return p == home(path).rstrip("/"), f"front Finder window at {p!r}"
    return f


def c_textedit(text):
    def f():
        ts = textedit_texts()
        return any(text.lower() in t.lower() for t in ts), f"TextEdit documents: {[t[:60] for t in ts]}"
    return f


def c_saved(stem, text):
    def f():
        paths = find_named(stem)
        for p in paths:
            if text.lower() in file_text(q(p)).lower():
                return True, f"{p} holds the text"
        return False, f"files named {stem}*: {paths}"
    return f


def c_note(text, title=None):
    def f():
        ns = notes()
        for name, body in ns:
            if text.lower() in (name + "\n" + body).lower() and (title is None or name.strip().lower() == title.lower()):
                return True, f"note {name!r}"
        return False, f"notes: {[(n, b[:40]) for n, b in ns][:5]}"
    return f


def c_note_folder(name):
    def f():
        fs = note_folders()
        return name in fs, f"Notes folders: {fs}"
    return f


def c_reminder(name, completed=False, in_list=None):
    def f():
        rs = reminders()
        for n, done, lst in rs:
            if n.strip().lower() == name.lower() and done == completed and (in_list is None or lst == in_list):
                return True, f"reminder {n!r} in {lst!r}, completed {done}"
        return False, f"reminders: {rs[:6]}"
    return f


def c_list(name):
    def f():
        ls = reminder_lists()
        return name in ls, f"Reminders lists: {ls}"
    return f


def c_event(title, date=None):
    def f():
        es = events()
        for s, d, h, cal in es:
            if s.strip().lower() == title.lower() and (date is None or d == date):
                return True, f"event {s!r} on {d} at {h}h in {cal!r}"
        return False, f"events: {es[:6]}"
    return f


def c_contact(first, last):
    def f():
        cs = contacts()
        return f"{first} {last}" in cs, f"contacts: {cs}"
    return f


def c_dark(want):
    def f():
        d = dark_mode()
        return d == want, f"dark mode {d}"
    return f


def c_dock(key, want):
    def f():
        d = dock()
        return d.get(key) == want, f"dock {d}"
    return f


def c_dock_size(smaller):
    def f():
        d = dock()
        s = d.get("size", 0.32)
        return (s < 0.27) if smaller else (s > 0.40), f"dock size {s:.2f} (start 0.32)"
    return f


def c_pane(name):
    def f():
        w = settings_window()
        return w.lower() == name.lower(), f"System Settings window {w!r}"
    return f


def c_calc(result):
    def f():
        ts = calculator_texts()
        return result in ts, f"Calculator shows {ts[:6]}"
    return f


def c_default(domain, key, want):
    def f():
        v = vm.sh(f"defaults read {domain} {key} 2>/dev/null")
        return v.strip() == want, f"{domain} {key} = {v.strip()!r}"
    return f


def c_file(path):
    def f():
        ok = exists(q(home(path)), "e")
        return ok, f"{path} " + ("exists" if ok else "missing")
    return f


def c_screenshot():
    def f():
        ls = vm.sh("ls ~/Desktop")
        return "Screenshot" in ls or "Screen Shot" in ls, f"Desktop: {ls[:120]!r}"
    return f


def c_windows(app_running, n=1):
    def f():
        ok, out = _osa('tell application "Finder" to count Finder windows')
        return ok and int(out or 0) >= n, f"Finder windows: {out}"
    return f


def c_all(*checks):
    def f():
        out = [c() for c in checks]
        return all(ok for ok, _ in out), " | ".join(("PASS " if ok else "FAIL ") + d for ok, d in out)
    return f


def tomorrow():
    out = vm.sh("date -v+1d '+%Y-%-m-%-d'")
    return out.strip()


def today():
    return vm.sh("date '+%Y-%-m-%-d'").strip()


# ----------------------------------------------------------------- templates

def templates():
    """[(type, multi, uses, [(params...)], make(params) -> dict(requests=[...], check=..., setup=[...], oracle=...))]"""
    T = []

    def add(name, multi, uses, params, make):
        T.append((name, multi, uses, params, make))

    # --- one step
    add("open_app", False, (), [(a,) for a in APPS], lambda a: dict(
        requests=[f"Open {a}", f"Launch the {a} app", f"Start {a} for me", f"I need {a}, open it"],
        check=c_front(a), oracle=f"open -a {q(a)}"))
    add("open_site", False, (), SITES, lambda s, part: dict(
        requests=[f"Open {s} in Safari", f"Go to {s}", f"Take me to the website {s}", f"Visit {s} in the browser"],
        check=c_url(part), oracle=f"open -a Safari https://{s}"))
    add("web_search", False, (), [(s,) for s in SEARCHES], lambda s: dict(
        requests=[f"Search the web for {s}", f"Look up {s}", f"Google {s}"],
        check=c_search(s), oracle=f"open -a Safari 'https://www.google.com/search?q={s.replace(' ', '+')}'"))
    add("settings_pane", False, (), [(p,) for p in PANES], lambda p: dict(
        requests=[f"Open the {p} settings", f"Bring up {p} in System Settings", f"Go to System Settings and open {p}"],
        check=c_pane(p)))
    add("finder_go", False, (), PLACES, lambda label, path: dict(
        requests=[f"Open the {label} folder in Finder", f"Take me to my {label} folder in Finder", f"Open a Finder window at {label}"],
        check=c_finder_at(path), oracle=f"open {q(home(path))}"))
    add("finder_new_window", False, (), [()], lambda: dict(
        requests=["Open a new Finder window", "I need a Finder window, open one", "Open Finder and make a new window"],
        check=c_windows(True), oracle="open ~"))
    add("dark_on", True, ("dark",), [()], lambda: dict(
        requests=["Turn on dark mode", "Switch the Mac to dark mode", "Make the appearance dark", "Enable Dark Mode in settings"],
        check=c_dark(True), oracle="osascript -e 'tell application \"System Events\" to tell appearance preferences to set dark mode to true'"))
    add("dark_off", True, ("dark",), [()], lambda: dict(
        requests=["Turn off dark mode", "Switch back to light mode", "Make the appearance light again"],
        setup=["osascript -e 'tell application \"System Events\" to tell appearance preferences to set dark mode to true'"],
        check=c_dark(False)))
    add("dock_autohide_on", True, ("dock",), [()], lambda: dict(
        requests=["Hide the Dock automatically", "Turn on Dock auto-hide", "Make the Dock hide itself when I am not using it"],
        check=c_dock("autohide", True), oracle="osascript -e 'tell application \"System Events\" to tell dock preferences to set autohide to true'"))
    add("dock_autohide_off", True, ("dock",), [()], lambda: dict(
        requests=["Stop hiding the Dock automatically", "Turn off Dock auto-hide", "Keep the Dock always visible"],
        setup=["osascript -e 'tell application \"System Events\" to tell dock preferences to set autohide to true'"],
        check=c_dock("autohide", False)))
    add("dock_side", True, ("dock",), [("left",), ("right",)], lambda side: dict(
        requests=[f"Move the Dock to the {side} side of the screen", f"Put the Dock on the {side}", f"Change the Dock position to {side}"],
        check=c_dock("edge", side), oracle=f"osascript -e 'tell application \"System Events\" to tell dock preferences to set screen edge to {side}'"))
    add("dock_bottom", True, ("dock",), [()], lambda: dict(
        requests=["Move the Dock back to the bottom of the screen", "Put the Dock at the bottom"],
        setup=["osascript -e 'tell application \"System Events\" to tell dock preferences to set screen edge to left'"],
        check=c_dock("edge", "bottom")))
    add("dock_magnify", True, ("dock",), [()], lambda: dict(
        requests=["Turn on Dock magnification", "Enable magnification for the Dock", "Make Dock icons magnify when I hover over them"],
        check=c_dock("magnification", True)))
    add("dock_size", True, ("dock",), [(True,), (False,)], lambda smaller: dict(
        requests=[f"Make the Dock {'smaller' if smaller else 'bigger'}", f"{'Shrink' if smaller else 'Enlarge'} the Dock icons",
                  f"Change the Dock size to {'small' if smaller else 'large'}"],
        check=c_dock_size(smaller)))
    add("finder_pathbar", True, ("finderprefs",), [()], lambda: dict(
        requests=["Show the path bar in Finder", "Turn on Finder's path bar", "In Finder, choose View > Show Path Bar"],
        check=c_default("com.apple.finder", "ShowPathbar", "1")))
    add("finder_statusbar", True, ("finderprefs",), [()], lambda: dict(
        requests=["Show the status bar in Finder", "Turn on Finder's status bar"],
        check=c_default("com.apple.finder", "ShowStatusBar", "1")))
    add("screenshot", False, ("files",), [()], lambda: dict(
        requests=["Take a screenshot of the whole screen", "Capture the entire screen to a file", "Press the shortcut that takes a full screenshot"],
        check=c_screenshot()))

    # --- a few steps in one app
    add("finder_new_folder", True, ("files",), [(f,) for f in FOLDERS], lambda f: dict(
        requests=[f"Create a folder called {f} on the Desktop", f"Make a new folder named {f} on my Desktop", f"On the Desktop, add a folder named {f}"],
        check=c_dir(f"Desktop/{f}"), oracle=f"mkdir ~/Desktop/{q(f)}"))
    add("finder_new_folder_docs", True, ("files",), [(f,) for f in FOLDERS[:6]], lambda f: dict(
        requests=[f"Create a folder called {f} in Documents", f"Make a new folder named {f} inside my Documents folder"],
        check=c_dir(f"Documents/{f}"), oracle=f"mkdir ~/Documents/{q(f)}"))
    add("finder_move", True, ("files",), [(FILES[i], FOLDERS[i]) for i in range(6)], lambda name, folder: dict(
        requests=[f"Move the file {name} on the Desktop into the {folder} folder", f"Put {name} from the Desktop into the folder {folder}",
                  f"On the Desktop, drag {name} into {folder}"],
        setup=[f"mkdir -p ~/Desktop/{q(folder)}; echo sample > ~/Desktop/{q(name)}"],
        check=c_moved(name, folder), oracle=f"mv ~/Desktop/{q(name)} ~/Desktop/{q(folder)}/"))
    add("finder_rename", True, ("files",), [(FILES[i], "final-" + FILES[i]) for i in range(5)], lambda old, new: dict(
        requests=[f"Rename the file {old} on the Desktop to {new}", f"Change the name of {old} on my Desktop to {new}"],
        setup=[f"echo sample > ~/Desktop/{q(old)}"],
        check=c_renamed(old, new), oracle=f"mv ~/Desktop/{q(old)} ~/Desktop/{q(new)}"))
    add("finder_trash", True, ("files",), [(f,) for f in FILES[:5]], lambda name: dict(
        requests=[f"Move the file {name} on the Desktop to the Trash", f"Delete {name} from the Desktop", f"Throw away {name} that is on my Desktop"],
        setup=[f"echo sample > ~/Desktop/{q(name)}"],
        check=c_trashed(name), oracle=f"mv ~/Desktop/{q(name)} ~/.Trash/"))
    add("finder_duplicate", True, ("files",), [(f,) for f in FILES[:4]], lambda name: dict(
        requests=[f"Duplicate the file {name} on the Desktop", f"Make a copy of {name} on my Desktop"],
        setup=[f"echo sample > ~/Desktop/{q(name)}"],
        check=c_duplicated(name), oracle=f"cp ~/Desktop/{q(name)} ~/Desktop/{q(name.replace('.', ' copy.'))}"))
    add("textedit_type", True, (), [(t,) for t in TEXTS], lambda t: dict(
        requests=[f"Open TextEdit and write \"{t}\" in a new document", f"Start a new TextEdit document and type {t}", f"In TextEdit, make a new document that says {t}"],
        check=c_textedit(t)))
    add("textedit_save", True, ("files",), [(DOCS[i], TEXTS[i]) for i in range(6)], lambda name, t: dict(
        requests=[f"Create a new TextEdit document with the text \"{t}\" and save it as {name}", f"In TextEdit, write {t} and save the document under the name {name}",
                  f"Make a TextEdit file called {name} that says {t}"],
        check=c_saved(name, t)))
    add("note_new", True, ("notes",), [(t,) for t in NOTE_TEXTS], lambda t: dict(
        requests=[f"Create a new note that says {t}", f"Open Notes and write a note: {t}", f"Add a note saying \"{t}\"", f"Make a note for me: {t}"],
        check=c_note(t), oracle=f"osascript -e 'tell application \"Notes\" to make new note at folder \"Notes\" with properties {{body:{q(t)}}}'"))
    add("note_titled", True, ("notes",), [(NOTE_TITLES[i], NOTE_TEXTS[i]) for i in range(6)], lambda title, t: dict(
        requests=[f"Create a note titled {title} with the text {t}", f"In Notes, make a note whose first line is {title} and then write {t}"],
        check=c_note(t, title=title)))
    add("note_folder", True, ("notes",), [(l,) for l in LISTS[:4]], lambda name: dict(
        requests=[f"Create a new folder called {name} in Notes", f"In the Notes app, add a folder named {name}"],
        check=c_note_folder(name), oracle=f"osascript -e 'tell application \"Notes\" to make new folder with properties {{name:{q(name)}}}'"))
    add("reminder_new", True, ("reminders",), [(r,) for r in REMINDERS], lambda r: dict(
        requests=[f"Add a reminder called {r}", f"Remind me to {r[0].lower() + r[1:]}", f"Create a new reminder: {r}", f"Open Reminders and add \"{r}\""],
        check=c_reminder(r) if True else None, oracle=f"osascript -e 'tell application \"Reminders\" to make new reminder with properties {{name:{q(r)}}}'"))
    add("reminder_list", True, ("reminders",), [(l,) for l in LISTS], lambda name: dict(
        requests=[f"Create a new list called {name} in Reminders", f"In Reminders, add a list named {name}"],
        check=c_list(name), oracle=f"osascript -e 'tell application \"Reminders\" to make new list with properties {{name:{q(name)}}}'"))
    add("reminder_complete", True, ("reminders",), [(r,) for r in REMINDERS[:5]], lambda r: dict(
        requests=[f"Mark the reminder \"{r}\" as completed", f"In Reminders, tick off {r}", f"I did \"{r}\", check it off in Reminders"],
        setup=[f"osascript -e 'tell application \"Reminders\" to make new reminder with properties {{name:{q(r)}}}'"],
        check=c_reminder(r, completed=True)))
    add("event_new", True, ("calendar",), [(e,) for e in EVENTS], lambda e: dict(
        requests=[f"Add a calendar event called {e}", f"Create an event named {e} in Calendar", f"Put \"{e}\" on my calendar", f"Open Calendar and make a new event: {e}"],
        check=c_event(e)))
    add("event_tomorrow", True, ("calendar",), [(e,) for e in EVENTS[:6]], lambda e: dict(
        requests=[f"Add a calendar event called {e} for tomorrow", f"Schedule {e} tomorrow in Calendar", f"Put {e} on my calendar for tomorrow"],
        check=lambda: c_event(e, date=tomorrow())()))
    add("contact_new", True, ("contacts",), PEOPLE, lambda first, last: dict(
        requests=[f"Add a new contact named {first} {last}", f"Create a contact for {first} {last} in Contacts", f"Save {first} {last} as a new contact"],
        check=c_contact(first, last)))
    add("calculator", True, (), CALC, lambda a, op, b, res: dict(
        requests=[f"Use the Calculator to work out {a} {WORD_OP[op]} {b}", f"Open Calculator and compute {a} {op} {b}", f"Calculate {a} {WORD_OP[op]} {b} in the Calculator app"],
        check=c_calc(res)))
    add("terminal_touch", True, ("files",), [(f,) for f in ["hello.txt", "log.txt", "empty.md", "data.csv"]], lambda name: dict(
        requests=[f"Open Terminal and run: touch ~/Desktop/{name}", f"In Terminal, create an empty file on the Desktop with the command touch ~/Desktop/{name}"],
        check=c_file(f"Desktop/{name}")))
    add("terminal_mkdir", True, ("files",), [(f,) for f in ["sandbox", "builds", "scratch"]], lambda name: dict(
        requests=[f"Open Terminal and make a folder called {name} in Documents with mkdir", f"Using Terminal, run mkdir ~/Documents/{name}"],
        check=c_dir(f"Documents/{name}")))
    add("safari_two_tabs", True, (), [(SITES[i], SITES[i + 1]) for i in range(0, 8, 2)], lambda s1, s2: dict(
        requests=[f"Open {s1[0]} and {s2[0]} in two Safari tabs", f"In Safari, open {s1[0]}, then open {s2[0]} in a new tab"],
        check=c_all(c_url(s1[1], front=False), c_url(s2[1], front=False))))

    # --- chains across apps
    add("chain_note_reminder", True, ("notes", "reminders"), [(NOTE_TEXTS[i], REMINDERS[i]) for i in range(8)], lambda t, r: dict(
        requests=[f"Open Notes and write \"{t}\", then set a reminder called {r}", f"Make a note saying {t}, and after that add a reminder: {r}",
                  f"First add a note \"{t}\". Then create a reminder named {r}"],
        check=c_all(c_note(t), c_reminder(r))))
    add("chain_site_note", True, ("notes",), [(SITES[i], NOTE_TEXTS[i]) for i in range(6)], lambda s, t: dict(
        requests=[f"Open {s[0]} in Safari, then create a note that says {t}", f"Go to {s[0]} and afterwards write a note: {t}"],
        check=c_all(c_url(s[1], front=False), c_note(t))))
    add("chain_dark_app", True, ("dark",), [(a,) for a in ["Calendar", "Notes", "Calculator", "Reminders", "TextEdit", "Safari"]], lambda a: dict(
        requests=[f"Turn on dark mode and then open {a}", f"Switch to dark mode, then launch {a}"],
        check=c_all(c_dark(True), c_front(a))))
    add("chain_reminder_event", True, ("reminders", "calendar"), [(REMINDERS[i], EVENTS[i]) for i in range(8)], lambda r, e: dict(
        requests=[f"Add a reminder called {r} and a calendar event called {e}", f"Create a reminder \"{r}\", then put an event named {e} on the calendar"],
        check=c_all(c_reminder(r), c_event(e))))
    add("chain_two_reminders", True, ("reminders",), [(REMINDERS[i], REMINDERS[(i + 3) % 8]) for i in range(6)], lambda a, b: dict(
        requests=[f"Add two reminders: {a} and {b}", f"Create a reminder called {a}, then another one called {b}"],
        check=c_all(c_reminder(a), c_reminder(b))))
    add("chain_folder_move", True, ("files",), [(FOLDERS[i], FILES[i]) for i in range(6)], lambda folder, name: dict(
        requests=[f"Create a folder called {folder} on the Desktop and move {name} into it", f"On the Desktop, make a new folder named {folder}, then put the file {name} inside it"],
        setup=[f"echo sample > ~/Desktop/{q(name)}"],
        check=c_moved(name, folder)))
    add("chain_two_apps", True, (), [("Notes", "Calculator"), ("Safari", "Calendar"), ("TextEdit", "Reminders"), ("Calendar", "Notes"), ("Contacts", "Maps")], lambda a, b: dict(
        requests=[f"Open {a} and then open {b}", f"Launch {a}, then switch to {b}"],
        check=c_all(lambda: (running(a), f"{a} running: {running(a)}"), c_front(b))))
    add("chain_dock", True, ("dock",), [("left",), ("right",)], lambda side: dict(
        requests=[f"Move the Dock to the {side} and turn on auto-hide", f"Put the Dock on the {side} side and make it hide automatically"],
        check=c_all(c_dock("edge", side), c_dock("autohide", True))))
    add("chain_contact_note", True, ("contacts", "notes"), [(PEOPLE[i], NOTE_TEXTS[i]) for i in range(5)], lambda p, t: dict(
        requests=[f"Add a contact named {p[0]} {p[1]}, then make a note that says {t}"],
        check=c_all(c_contact(*p), c_note(t))))
    add("chain_three", True, ("notes", "reminders"), [(TEXTS[i], NOTE_TEXTS[i], REMINDERS[i]) for i in range(6)], lambda x, t, r: dict(
        requests=[f"Open TextEdit and type {x}. Then open Notes and add a note saying {t}. Finally set a reminder called {r}",
                  f"Three things: write \"{x}\" in a new TextEdit document, make a note \"{t}\", and add a reminder \"{r}\""],
        check=c_all(c_textedit(x), c_note(t), c_reminder(r))))
    add("chain_search_reminder", True, ("reminders",), [(SEARCHES[i], REMINDERS[i]) for i in range(5)], lambda s, r: dict(
        requests=[f"Search the web for {s}, then add a reminder called {r}"],
        check=c_all(c_search(s), c_reminder(r))))
    add("chain_event_note", True, ("calendar", "notes"), [(EVENTS[i], NOTE_TEXTS[i]) for i in range(6)], lambda e, t: dict(
        requests=[f"Create a calendar event called {e}, then write a note that says {t}"],
        check=c_all(c_event(e), c_note(t))))
    return T


def instances():
    """Every instance: {"id", "type", "multi", "uses", "request", "paraphrase", "params", "check", "setup", "oracle"}."""
    out = []
    for name, multi, uses, params, make in templates():
        k = 0
        for p in params:
            made = make(*p)
            for j, request in enumerate(made["requests"]):
                k += 1
                out.append({"id": f"{name}-{k:03d}", "type": name, "multi": multi, "uses": tuple(uses), "request": request, "paraphrase": j,
                            "params": [str(x) for x in p], "check": made["check"], "setup": made.get("setup", ()), "oracle": made.get("oracle")})
    return out


def sample(per_type, seed=0, only=None):
    """A balanced pick: up to `per_type` instances of each template, different parameters first."""
    rng = random.Random(seed)
    by = {}
    for t in instances():
        if only and t["type"] not in only:
            continue
        by.setdefault(t["type"], []).append(t)
    out = []
    for name, lst in by.items():
        rng.shuffle(lst)
        seen, picked = set(), []
        for t in lst:                                   # one per parameter set first
            key = tuple(t["params"])
            if key not in seen:
                seen.add(key)
                picked.append(t)
        rest = [t for t in lst if t not in picked]
        out += (picked + rest)[:per_type]
    return out


if __name__ == "__main__":
    all_ = instances()
    types = sorted({t["type"] for t in all_})
    print(len(types), "templates,", len(all_), "instances")
    for name in types:
        n = [t for t in all_ if t["type"] == name]
        print(f"  {name:24s} {len(n):4d}  {'multi' if n[0]['multi'] else 'single'}  e.g. {n[0]['request']}")
