"""Task registry, start states and checker helpers.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

A task is a function of a start-state builder `S`:

    @task("mail.archive", "chain")
    def archive(S):
        m = S.rng.choice(inbox(S))
        S.open("mail")
        return Spec(request=f"Archive the email from {m['from']}.",
                    steps=[Click(...), Click(...)],
                    check=lambda st, init: verdict(...))

`S.apps[name]` is the seeded default state of every app (so any app can be opened from the Dock),
which the task changes to set its scene. The checker sees the final and the initial state.

Seeds: DEV_SEEDS are for developing tasks, prompts and agents. TEST_SEEDS are reserved for the
reported runs; nothing may be tuned on them.
"""
import copy
import fnmatch
import importlib
import os
import random
import re
import sys
from dataclasses import dataclass, field

DEV_SEEDS = list(range(1, 6))
TEST_SEEDS = [9101, 9102, 9103]
CATEGORIES = ["single", "chain", "typing", "drag", "scroll", "menu", "shortcut", "already_done", "infeasible"]
APP_MODULES = ["files", "settings", "mail", "notes", "reminders", "calendar", "music", "browser", "sheet", "calculator"]
DOCK = ["files", "browser", "mail", "calendar", "notes", "reminders", "music", "sheet", "calculator", "settings", "|", "trash"]

TASKS = {}
_loaded = {}


@dataclass
class Spec:
    request: str
    steps: list
    check: object
    kind: str = "act"            # "act" | "already_done" (stop, change nothing) | "infeasible" (say so, change nothing)
    limit: int = 0               # step limit of agent mode; 0 = the default of taskenv/run.py (1.5 x the solution's steps + 3)


@dataclass
class Episode:
    task: str
    seed: int
    app: str
    category: str
    request: str
    state: dict
    steps: list
    check: object
    kind: str
    limit: int
    info: dict = field(default_factory=dict)


def task(tid, category):
    assert category in CATEGORIES, category

    def deco(fn):
        assert tid not in TASKS, tid
        TASKS[tid] = {"id": tid, "app": tid.split(".")[0], "category": category, "fn": fn}
        return fn
    return deco


def modules():
    """Import every app module that exists (apps are added one file at a time)."""
    for name in APP_MODULES:
        if name not in _loaded:
            try:
                _loaded[name] = importlib.import_module(f"taskenv.tasks.{name}")
            except ModuleNotFoundError as e:
                if e.name != f"taskenv.tasks.{name}":
                    raise
                _loaded[name] = None
            except Exception as e:                      # a module that is still being written
                if os.environ.get("TASKENV_STRICT", "0") == "1":
                    raise
                print(f"taskenv: skipping app {name!r}: {type(e).__name__}: {e}", file=sys.stderr)
                for tid in [t for t in TASKS if t.startswith(name + ".")]:
                    del TASKS[tid]
                _loaded[name] = None
    return {k: v for k, v in _loaded.items() if v}


class Builder:
    """Start state of one episode."""

    def __init__(self, seed, mods, tid=""):
        # the scene of a task depends on the seed AND the task, so that the tasks of one seed do
        # not all share a wallpaper, a window position and "the third item"
        self.seed, self.rng, self.mods = seed, random.Random(f"{seed}/{tid}"), mods
        clock = self.rng.choice(["Mon 2 Nov  9:41 AM", "Tue 3 Nov  10:12 AM", "Wed 4 Nov  2:26 PM", "Thu 5 Nov  4:03 PM",
                                 "Fri 6 Nov  11:48 AM", "Mon 9 Nov  8:57 AM", "Tue 10 Nov  3:15 PM", "Thu 12 Nov  1:30 PM"])
        self.state = {"seed": seed, "wallpaper": self.rng.randrange(4), "status": {"clock": clock},
                      "dock": [d for d in DOCK if d in mods or d in ("|", "trash")], "windows": [], "apps": {}, "events": []}
        for name, m in list(mods.items()):
            try:
                self.state["apps"][name] = m.default(random.Random(f"{seed}/{name}"))
            except Exception as e:
                if os.environ.get("TASKENV_STRICT", "0") == "1":
                    raise
                print(f"taskenv: app {name!r} has no usable start state yet: {type(e).__name__}: {e}", file=sys.stderr)
                self.mods = mods = {k: v for k, v in mods.items() if k != name}
                self.state["dock"] = [d for d in self.state["dock"] if d != name]
        self.apps = self.state["apps"]
        cal = self.apps.get("calendar") or {}
        if isinstance(cal.get("today"), str):              # one "today" for the menu bar and the Calendar app
            import datetime
            d = datetime.date.fromisoformat(cal["today"])
            self.state["status"]["clock"] = f"{d.strftime('%a')} {d.day} {d.strftime('%b')}  {clock.split('  ')[1]}"

    def open(self, app, at=None):
        """Put the app's window on screen, in front of the ones opened before. Position is seeded."""
        w, h = self.mods[app].SIZE
        x = self.rng.randint(16, max(16, 1440 - w - 16))
        y = self.rng.randint(36, max(36, 900 - 84 - h))
        if at:
            x, y = at
        self.state["windows"] = [v for v in self.state["windows"] if v["app"] != app] + [{"app": app, "x": x, "y": y, "w": w, "h": h}]

    def behind(self, front_app):
        """Sometimes another app's window sits behind the one the task is about."""
        others = [a for a in self.mods if a != front_app]
        if self.rng.random() < 0.4 and others:
            other = self.rng.choice(others)
            cur = self.state["windows"]
            self.state["windows"] = []
            self.open(other)
            self.state["windows"] += cur


def build(tid, seed):
    mods = modules()
    t = TASKS[tid]
    S = Builder(seed, mods, tid)
    spec = t["fn"](S)
    if len(S.state["windows"]) == 1:
        S.behind(S.state["windows"][0]["app"])
    return Episode(task=tid, seed=seed, app=t["app"], category=t["category"], request=spec.request, state=S.state,
                   steps=spec.steps, check=spec.check, kind=spec.kind, limit=spec.limit)


def all_tasks():
    modules()
    return list(TASKS)


# ------------------------------------------------------------------ checker helpers
SKIP_TOP = ("ui",)


def data(state, volatile=()):
    """The apps' persistent data: no window positions, no selection, scroll or open panels."""
    def walk(v):
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items() if k not in SKIP_TOP and k not in volatile}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    return {name: walk(s) for name, s in state["apps"].items()}


def diff(a, b, path=""):
    """Paths at which two values differ. Lists of records with an "id" are compared by id:
    `path.+id` added in a, `path.-id` missing from a, `path.<order>` same members in another order."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in a or k not in b:
                out.append(p)
            else:
                out += diff(a[k], b[k], p)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if all(isinstance(x, dict) and "id" in x for x in a + b) and (a or b):
            ia, ib = {x["id"]: x for x in a}, {x["id"]: x for x in b}
            out = [f"{path}.+{i}" for i in ia if i not in ib] + [f"{path}.-{i}" for i in ib if i not in ia]
            for i in ia:
                if i in ib:
                    out += diff(ia[i], ib[i], f"{path}.{i}")
            if [i for i in ia if i in ib] != [i for i in ib if i in ia]:
                out.append(f"{path}.<order>")
            return out
        if len(a) != len(b):
            return [path]
        out = []
        for n, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}.{n}")
        return out
    if isinstance(a, float) or isinstance(b, float):
        try:
            return [] if abs(float(a) - float(b)) < 1e-6 else [path]
        except (TypeError, ValueError):
            return [path]
    return [] if a == b else [path]


def changes(st, init, volatile=("unread",)):
    return diff(data(st, volatile), data(init, volatile))


def only(st, init, *allowed, volatile=("unread",)):
    """(ok, why): nothing changed in any app's data besides paths matching `allowed` (fnmatch)."""
    extra = [p for p in changes(st, init, volatile) if not any(fnmatch.fnmatchcase(p, a) for a in allowed)]
    return (not extra, "something else changed: " + ", ".join(extra[:4]))


def unchanged(st, init, volatile=("unread",)):
    return only(st, init, volatile=volatile)


def cond(ok, why):
    return (bool(ok), why)


def verdict(*conds):
    """All conditions must hold; the first that does not gives the reason."""
    for ok, why in conds:
        if not ok:
            return False, why
    return True, ""


def norm(s):
    """Text as compared by checkers: case, repeated spaces and a final full stop do not matter."""
    return re.sub(r"\s+", " ", str(s or "")).strip().rstrip(".!").strip().lower().replace("’", "'").replace("“", '"').replace("”", '"')


def by_id(items, i):
    return next((x for x in items if x.get("id") == i), None)


def say(rng, *phrasings):
    return rng.choice(phrasings)


def clone(v):
    return copy.deepcopy(v)
