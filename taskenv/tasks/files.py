"""Files (a Finder-like file browser): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.
"""
import datetime

from ..oracle import Click, Drag, Key, Reveal, Type
from . import pools
from .base import Spec, by_id, cond, norm, only, say, task, unchanged, verdict

SIZE = (900, 560)
WIN = '.win[data-app="files"] '
ROOTS = {"desktop": "Desktop", "documents": "Documents", "downloads": "Downloads", "pictures": "Pictures"}
TODAY = datetime.date(2026, 11, 14)


def default(rng):
    items, used = [], set()

    def add(kind, parent, name=None):
        if name is None:
            for _ in range(200):
                if kind == "folder":
                    name = rng.choice(pools.FOLDER_NAMES)
                else:
                    name = rng.choice(pools.FILE_NAMES[kind]) + rng.choice(["", "", "", "-v2", "-final", "-2025", "-scan", "-draft", "-old", " (1)"]) + "." + pools.EXT[kind]
                if name.lower() not in used:
                    break
        used.add(name.lower())
        days = rng.randint(0, 700)
        d = TODAY - datetime.timedelta(days=days)
        b = 0 if kind == "folder" else int(10 ** rng.uniform(3.8, 7.6))
        size = "--" if kind == "folder" else (f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{round(b / 1e3)} KB")
        it = {"id": f"f{len(items) + 1}", "name": name, "kind": kind, "parent": parent,
              "date": f"{d.day} {pools.MONTHS[d.month - 1]} {d.year}", "ts": -days, "size": size, "bytes": b}
        items.append(it)
        return it

    kinds = ["pdf", "doc", "sheet", "image", "audio", "zip", "slides"]
    weights = [5, 4, 3, 4, 1, 1, 2]
    for _ in range(5):
        f = add("folder", "documents")
        for _ in range(rng.randint(3, 6)):
            add(rng.choices(kinds, weights)[0], f["id"])
    for _ in range(7):
        add(rng.choices(kinds, weights)[0], "documents")
    add("folder", "desktop")
    for _ in range(4):
        add(rng.choices(kinds, weights)[0], "desktop")
    for _ in range(48):
        add(rng.choices(kinds, weights)[0], "downloads")
    add("folder", "pictures")
    for _ in range(10):
        add("image", "pictures")
    return {"items": items, "next": 1,
            "ui": {"path": "documents", "sel": None, "view": "icons", "sort": {"key": "name", "dir": 1}, "back": [], "fwd": [],
                   "search": "", "rename": None, "renameText": "", "preview": None}}


def inside(s, parent, folders=None):
    return [i for i in s["items"] if i["parent"] == parent and (folders is None or (i["kind"] == "folder") == folders)]


def cell(i):
    return WIN + f'[data-drag="{i["id"]}"]'


def fresh_name(rng, s, kind):
    """A name no item has yet: (name without extension, full name)."""
    taken = {i["name"].lower() for i in s["items"]}
    pool = pools.FOLDER_NAMES if kind == "folder" else pools.FILE_NAMES[kind]
    for n in range(600):
        name = rng.choice(pool) + ("" if n < 200 else rng.choice(["-new", "-2026", "-clean", "-signed", "-b", "-short", "-print", "-reviewed"]))
        full = name if kind == "folder" else name + "." + pools.EXT[kind]
        if full.lower() not in taken and not any(t.startswith(name.lower()) for t in taken):
            return name, full
    raise RuntimeError("no free name")


def item(st, i):
    return by_id(st["apps"]["files"]["items"], i)


@task("files.open_folder", "single")
def open_folder(S):
    s = S.apps["files"]
    f = S.rng.choice(inside(s, "documents", True))
    S.open("files")
    return Spec(request=say(S.rng, f"Open the {f['name']} folder.", f"Show me what's inside the “{f['name']}” folder."),
                steps=[Click(cell(f), f"Double-click the folder named “{f['name']}”", count=2)],
                check=lambda st, init: verdict(cond(st["apps"]["files"]["ui"]["path"] == f["id"], "the window does not show that folder"),
                                               unchanged(st, init)))


@task("files.list_view", "single")
def list_view(S):
    S.open("files")
    return Spec(request=say(S.rng, "Show these files as a list.", "Switch this Files window to list view."),
                steps=[Click(WIN + '.tb-btn[data-arg="list"]', "Click the list view button in the toolbar")],
                check=lambda st, init: verdict(cond(st["apps"]["files"]["ui"]["view"] == "list", "the window is not in list view"),
                                               unchanged(st, init)))


@task("files.move_into_folder", "drag")
def move_into_folder(S):
    s = S.apps["files"]
    f = S.rng.choice(inside(s, "documents", False))
    d = S.rng.choice(inside(s, "documents", True))
    S.open("files")
    return Spec(request=say(S.rng, f"Move {f['name']} into the {d['name']} folder.", f"Put the file {f['name']} in “{d['name']}”."),
                steps=[Drag(cell(f), cell(d), f"the file “{f['name']}”", f"the folder “{d['name']}”")],
                check=lambda st, init: verdict(cond(item(st, f["id"])["parent"] == d["id"], "the file is not in that folder"),
                                               only(st, init, f"files.items.{f['id']}.parent")))


@task("files.rename", "menu")
def rename(S):
    s = S.apps["files"]
    it = S.rng.choice(inside(s, "documents"))
    base, full = fresh_name(S.rng, s, it["kind"])
    S.open("files")
    return Spec(request=say(S.rng, f"Rename {it['name']} to {full}.", f"Change the name of “{it['name']}” to “{full}”."),
                steps=[Click(cell(it), f"Right-click “{it['name']}”", button="right"),
                       Click('.menu-item:has-text("Rename")', "Click “Rename” in the menu"),
                       Type(base), Key("enter")],
                check=lambda st, init: verdict(cond(norm(item(st, it["id"])["name"]) == norm(full), f"the name is “{item(st, it['id'])['name']}”"),
                                               only(st, init, f"files.items.{it['id']}.name")))


@task("files.trash", "shortcut")
def trash(S):
    s = S.apps["files"]
    it = S.rng.choice(inside(s, "documents", False))
    S.open("files")
    return Spec(request=say(S.rng, f"Move {it['name']} to the Trash.", f"Delete the file {it['name']}."),
                steps=[Click(cell(it), f"Click the file “{it['name']}”"), Key("cmd+backspace")],
                check=lambda st, init: verdict(cond(item(st, it["id"])["parent"] == "trash", "the file is not in the Trash"),
                                               only(st, init, f"files.items.{it['id']}.parent", f"files.items.{it['id']}.from")))


@task("files.new_folder", "menu")
def new_folder(S):
    s = S.apps["files"]
    where = S.rng.choice(["documents", "desktop", "pictures"])
    s["ui"]["path"] = where
    name, _ = fresh_name(S.rng, s, "folder")
    S.open("files")

    def check(st, init):
        new = [i for i in st["apps"]["files"]["items"] if norm(i["name"]) == norm(name) and i["kind"] == "folder"]
        return verdict(cond(len(new) == 1, f"there is no folder called “{name}”"),
                       cond(new and new[0]["parent"] == where, f"the new folder is not in {ROOTS[where]}"),
                       only(st, init, "files.items.+*", "files.next"))
    return Spec(request=say(S.rng, f"Create a new folder called {name} in {ROOTS[where]}.", f"Make a folder named “{name}” here in {ROOTS[where]}."),
                steps=[Click('.mb-item:text-is("File")', "Click “File” in the menu bar"),
                       Click('.menu-item:has-text("New Folder")', "Click “New Folder” in the menu"),
                       Type(name), Key("enter")],
                check=check)


@task("files.find_download", "scroll")
def find_download(S):
    s = S.apps["files"]
    s["ui"]["view"] = "list"
    rows = sorted(inside(s, "downloads"), key=lambda i: i["name"].lower())
    it = S.rng.choice(rows[26:])
    S.open("files")
    return Spec(request=say(S.rng, f"Open {it['name']} from my Downloads folder.", f"Find {it['name']} in Downloads and open it."),
                steps=[Click(WIN + '.sb-item[data-arg="downloads"]', "Click “Downloads” in the sidebar"),
                       Reveal(cell(it)),
                       Click(cell(it), f"Double-click the file “{it['name']}”", count=2)],
                check=lambda st, init: verdict(cond(st["apps"]["files"]["ui"]["preview"] == it["id"], "that file is not open"),
                                               unchanged(st, init)))


@task("files.duplicate_move", "chain")
def duplicate_move(S):
    s = S.apps["files"]
    f = S.rng.choice(inside(s, "documents", False))
    d = S.rng.choice(inside(s, "documents", True))
    base, ext = f["name"].rsplit(".", 1)
    copy = f"{base} copy.{ext}"
    S.open("files")

    def check(st, init):
        c = [i for i in st["apps"]["files"]["items"] if i["name"] == copy]
        return verdict(cond(len(c) == 1, f"there is no “{copy}”"),
                       cond(c and c[0]["parent"] == d["id"], f"“{copy}” is not in {d['name']}"),
                       only(st, init, "files.items.+*", "files.next"))
    return Spec(request=say(S.rng, f"Duplicate {f['name']} and move the copy into the {d['name']} folder.",
                            f"Make a copy of {f['name']} and put the copy in “{d['name']}”. Leave the original where it is."),
                steps=[Click(cell(f), f"Right-click the file “{f['name']}”", button="right"),
                       Click('.menu-item:has-text("Duplicate")', "Click “Duplicate” in the menu"),
                       Drag(WIN + f'.f-cell:has-text("{copy}")', cell(d), f"the file “{copy}”", f"the folder “{d['name']}”")],
                check=check)


@task("files.sort_by_size", "chain")
def sort_by_size(S):
    s = S.apps["files"]
    s["ui"]["view"] = "list"
    s["ui"]["path"] = S.rng.choice(["documents", "pictures"])
    S.open("files")
    return Spec(request=say(S.rng, "Sort these files by size, largest first.", "Order this list by file size with the biggest at the top."),
                steps=[Click(WIN + '.f-head .c-size', "Click the “Size” column header"),
                       Click(WIN + '.f-head .c-size', "Click the “Size” column header again")],
                check=lambda st, init: verdict(cond(st["apps"]["files"]["ui"]["sort"] == {"key": "size", "dir": -1}, "the list is not sorted by size, largest first"),
                                               unchanged(st, init)))


@task("files.put_back", "menu")
def put_back(S):
    s = S.apps["files"]
    gone = S.rng.sample(inside(s, "documents", False), 2)
    for g in gone:
        g["from"], g["parent"] = "documents", "trash"
    it = gone[0]
    S.open("files")
    return Spec(request=say(S.rng, f"Take {it['name']} back out of the Trash.", f"I deleted {it['name']} by mistake. Restore it from the Trash."),
                steps=[Click(WIN + '.sb-item[data-arg="trash"]', "Click “Trash” in the sidebar"),
                       Click(cell(it), f"Right-click the file “{it['name']}”", button="right"),
                       Click('.menu-item:has-text("Put Back")', "Click “Put Back” in the menu")],
                check=lambda st, init: verdict(cond(item(st, it["id"])["parent"] == "documents", "the file is not back in Documents"),
                                               only(st, init, f"files.items.{it['id']}.parent", f"files.items.{it['id']}.from")))


@task("files.already_there", "already_done")
def already_there(S):
    s = S.apps["files"]
    d = S.rng.choice(inside(s, "documents", True))
    f = S.rng.choice(inside(s, d["id"], False))
    s["ui"]["path"] = d["id"]
    s["ui"]["back"] = ["documents"]
    S.open("files")
    return Spec(request=say(S.rng, f"Make sure {f['name']} is in the {d['name']} folder.", f"{f['name']} should be in the “{d['name']}” folder. Move it there if it isn't."),
                steps=[], kind="already_done", check=unchanged)


@task("files.missing_file", "infeasible")
def missing_file(S):
    s = S.apps["files"]
    kind = S.rng.choice(["pdf", "doc", "sheet"])
    _, ghost = fresh_name(S.rng, s, kind)
    d = S.rng.choice(inside(s, "documents", True))
    S.open("files")
    return Spec(request=say(S.rng, f"Move {ghost} from Documents into the {d['name']} folder.", f"Rename the file {ghost} in this folder to final-{ghost}."),
                steps=[], kind="infeasible", check=unchanged)
