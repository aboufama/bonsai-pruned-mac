"""macsim.check_heldout: the training simulator must share no content with the test environment.

    python -m macsim.check_heldout          # exit code 1 and a list when something is shared

Compared: every content string of macsim/world.py (people, events, files, folders, mail, notes, reminders, lists,
sites, headlines, products, chat lines, songs, artists, albums, playlists, calendars) and the request texts of
macsim/steps.py, against every string literal in taskenv/tasks/*.py and taskenv/web/apps/*.js. A pool entry fails when
it equals a test string, or (two words or more) is contained in one. The names macOS itself gives things (Inbox,
Documents, Wi-Fi, the app names, the menu items) are the operating system's, not the test's, and are not compared.
"""
import glob
import os
import re
import sys

from . import steps, world

HERE = os.path.dirname(os.path.abspath(__file__))
TEST = os.path.join(os.path.dirname(HERE), "taskenv")


def literals(path):
    text = open(path, encoding="utf-8").read()
    return [m.group(2) for m in re.finditer(r"""(["'`])((?:\\.|(?!\1).){2,200}?)\1""", text)]


def pools():
    w = world
    out = {"first name": w.FIRST, "last name": w.LAST, "calendar": [c[0] for c in w.CALS], "event": w.EVENTS, "folder": w.FOLDERS, "file": [f[0] for f in w.FILES], "mail subject": [s[0] for s in w.SUBJECTS],
           "mail body": [s[1] for s in w.SUBJECTS], "note title": [n[0] for n in w.NOTES], "note line": [l for n in w.NOTES for l in n[1]], "reminder": w.REMS, "reminder list": [l[0] for l in w.LISTS], "site": [s[0] for s in w.SITES],
           "host": [s[1] for s in w.SITES], "headline": w.HEADLINES, "paragraph": w.PARAS, "product": w.PRODUCTS, "chat line": w.CHAT, "song": w.SONGS, "artist": w.ARTISTS, "album": w.ALBUMS, "playlist": w.PLAYLISTS, "alert": [x[0] for x in w.ALERTS], "note folder": w.NOTE_FOLDERS, "note tag": w.NOTE_TAGS, "group chat": w.GROUPS, "search query": w.QUERIES, "mail account": [a for a in w.ACCOUNTS if a not in ("iCloud", "On My Mac")], "typed subject": steps.MAIL_SUBJECTS, "typed message": steps.CHAT_TEXTS}
    return out


def main():
    test = set()
    for f in glob.glob(os.path.join(TEST, "tasks", "*.py")) + glob.glob(os.path.join(TEST, "web", "apps", "*.js")) + glob.glob(os.path.join(TEST, "web", "*.js")):
        test |= {s.lower().strip() for s in literals(f)}
    words = set()
    for s in test:
        words |= set(re.findall(r"[a-zà-ÿ][a-zà-ÿ'’-]+", s))
    bad = []
    for kind, pool in pools().items():
        for entry in pool:
            e = entry.lower().strip().replace("[ ] ", "").replace("[x] ", "")
            many = len(e.split()) >= 2
            if e in test or (many and any(e in s for s in test)) or (kind in ("first name", "last name", "artist", "site") and not many and e in words):
                bad.append((kind, entry))
    # the requests of the step tasks: no fixed run of five words may be a test request's
    strip = lambda s: [frag.strip() for frag in re.split(r"\{[^}]*\}", s)]
    theirs = {frag.lower() for s in test for frag in strip(s) if len(frag.split()) >= 5}
    for m in re.finditer(r'"request": f?"((?:\\.|[^"])*)"', open(os.path.join(HERE, "steps.py"), encoding="utf-8").read()):
        for frag in strip(m.group(1)):
            w5 = frag.lower().split()
            if any(" ".join(w5[i:i + 5]) in s for i in range(max(0, len(w5) - 4)) for s in theirs):
                bad.append(("request wording", frag))
    print(f"{sum(len(p) for p in pools().values())} macsim strings against {len(test)} test strings: {len(bad)} shared")
    for kind, entry in bad:
        print(f"  {kind}: {entry}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
