#!/usr/bin/env python3
"""Planner turns written by rule (no model writes anything) from real Mac control lists.

  python3 tools/planner_rule_turns.py <folder with shards/real_*.jsonl> <out folder>

15 Nov 06:00: the Fable-written planner lessons are held out of training, so the planner
lanes get turns built by code from the 601 real control lists (Screen2AX screens: sid, window, controls
[{n, role, name}], split train or dev). Same neutral row format as those lessons (id, source "rule",
split, task, apps, front_app, window, done, answer, sid), rendered by weightlab/planner.py in format v1.
Per screen, with wordings drawn from templates (seeded by the screen's id):
  click   press a named control; controls that share their role with others on the screen are preferred,
          so the model must pick by name; the name must be unique on the screen     -> click + id
  type    type a text into a named field; the text ends with a newline when the field's name contains
          "search" or the request says search or send                               -> type + id + text
  done    the history already shows the request carried out                          -> done + a sentence
  open    the request names another app from the Apps list                           -> open_app + app
  look    the request names a control that is not in the list                        -> look + target
The out folder gets turns_rule.jsonl and a copy of the shards, so weightlab.planner.load(out) works.
"""
import collections
import glob
import json
import os
import random
import shutil
import sys

src, out = sys.argv[1:3]
screens = [json.loads(l) for p in sorted(glob.glob(f"{src}/shards/real_*.jsonl")) for l in open(p)]
APPS = ["Finder", "Safari", "Mail", "Notes", "Messages", "Calendar", "Reminders", "Music", "Maps", "Photos", "System Settings", "Preview",
        "TextEdit", "Pages", "Numbers", "Keynote", "Terminal", "Zoom", "Slack", "Microsoft Word", "Google Chrome", "FaceTime", "Podcasts", "Books"]
GENERIC = {"close button", "minimize button", "zoom button", "close", "minimize", "zoom", "button", "", "toolbar", "full screen button"}
CLICKABLE = {"button": "button", "checkbox": "checkbox", "radio": "option", "link": "link", "menu button": "menu", "pop-up button": "menu", "menu item": "menu item"}
CLICK_T = {"button": ['Press {n}', 'Click the {n} button', 'I want {n}', 'Hit "{n}"', 'Click {n}', 'Please press the "{n}" button'],
           "checkbox": ['Turn on {n}', 'Tick {n}', 'Check the "{n}" box', 'Enable {n}', 'I want {n} on'],
           "option": ['Select {n}', 'Choose {n}', 'Pick the {n} option', 'Switch to {n}'],
           "link": ['Open the {n} link', 'Follow {n}', 'Click the "{n}" link'],
           "menu": ['Open the {n} menu', 'Click {n}', 'Show me the {n} menu'],
           "menu item": ['Choose {n}', 'Pick {n} from the menu']}
TEXTS = ["quarterly report", "hello", "meeting notes", "invoice 2041", "budget", "Anna", "project plan", "flight to Lisbon", "todo", "draft v2",
         "birthday", "tax form", "recipe", "summary", "42", "new folder", "holiday photos", "address", "backup", "password reset"]
TYPE_T = ['Type {t} into {n}', 'Put "{t}" in the {n} field', 'Enter {t} in {n}', 'Fill {n} with {t}', 'Write {t} in the {n} box']
SEARCH_T = ['Search for {t}', 'Find {t}', 'Look up {t} in the search field', 'Search {t}']
DONE_T = ['{n} is pressed.', 'Done: I clicked {n}.', 'I pressed {n} for you.', '{n} is selected now.']
OPEN_T = ['Open {a}', 'Switch to {a}', 'Go to {a}', 'I need {a}', 'Launch {a}', 'Bring up {a}']
LOOK_T = ['Click the {n} button', 'Press {n}', 'Find {n} and click it', 'I want {n}']


def app_name(key):
    last = str(key or "App").split("_")[-1]
    return {"eclipse": "Eclipse", "jabref": "JabRef"}.get(last.lower(), last[:1].upper() + last[1:])


all_names = sorted({c["name"] for s in screens for c in s["controls"] if c.get("name") and c["name"].lower() not in GENERIC and len(c["name"]) <= 30})
rows, counts = [], collections.Counter()
for s in screens:
    rng = random.Random(s["sid"])
    front = app_name(s.get("app_key"))
    apps = rng.sample([a for a in APPS if a != front], rng.randint(6, 12)) + [front]
    rng.shuffle(apps)
    names = collections.Counter(c.get("name") for c in s["controls"])
    roles = collections.Counter(c["role"] for c in s["controls"])
    ok = [c for c in s["controls"] if c.get("name") and c["name"].lower() not in GENERIC and names[c["name"]] == 1 and len(c["name"]) <= 40]
    clickable = [c for c in ok if c["role"] in CLICKABLE]
    clickable.sort(key=lambda c: (-min(roles[c["role"]], 3), rng.random()))      # those with same-role company first
    fields = [c for c in ok if c["role"] in ("text field", "text area")]
    base = {"source": "rule", "split": s.get("split", "train"), "apps": apps, "front_app": front, "window": s.get("window") or "", "sid": s["sid"]}
    hist = lambda: rng.choice([[], [], [f"open_app {front}"], [f"open_app {front}", "key cmd+comma"]])

    def add(kind, task, answer, done=None):
        rows.append(dict(base, id=f"rule-{s['sid']}-{kind}{counts[(s['sid'], kind)]}", task=task, done=hist() if done is None else done, answer=answer))
        counts[(s["sid"], kind)] += 1; counts[kind] += 1

    for c in clickable[:3]:
        add("click", rng.choice(CLICK_T[CLICKABLE[c["role"]]]).format(n=c["name"]), {"action": "click", "id": c["n"]})
    for c in rng.sample(fields, min(len(fields), 2)):
        t = rng.choice(TEXTS)
        if "search" in c["name"].lower():
            add("type", rng.choice(SEARCH_T).format(t=t), {"action": "type", "id": c["n"], "text": t + "\n"})
        else:
            add("type", rng.choice(TYPE_T).format(t=t, n=c["name"]), {"action": "type", "id": c["n"], "text": t})
    if clickable:
        c = clickable[-1] if len(clickable) > 3 else clickable[0]
        add("done", rng.choice(CLICK_T[CLICKABLE[c["role"]]]).format(n=c["name"]), {"action": "done", "text": rng.choice(DONE_T).format(n=c["name"])},
            done=hist() + [f"click \"{c['name']}\""])
    other = rng.choice([a for a in apps if a != front])
    add("open", rng.choice(OPEN_T).format(a=other), {"action": "open_app", "app": other}, done=[])
    absent = [n for n in rng.sample(all_names, 12) if names[n] == 0]
    if absent:
        add("look", rng.choice(LOOK_T).format(n=absent[0]), {"action": "look", "target": f"the {absent[0]} button"})
os.makedirs(f"{out}/shards", exist_ok=True)
for p in glob.glob(f"{src}/shards/real_*.jsonl"):
    shutil.copy(p, f"{out}/shards/")
with open(f"{out}/turns_rule.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("%d turns on %d screens: %s; split: %s" % (len(rows), len(screens), {k: v for k, v in counts.items() if isinstance(k, str)},
                                               dict(collections.Counter(r["split"] for r in rows))))
