"""Planner turns in format v1 as chat cases (no screenshot): the next step from a list of controls.

Mirrors assistant/Sources/AssistantCore/Planner.swift at commit fb93b8b (the frozen planner; e751270 plus
the fuller description of `target`): the fixed system text, the
`next_step` tool as the app declares it, the user message (Task / Apps / Front app | Window / Done so
far / Controls) and one `next_step` call as the answer. The neutral data (written by Fable over real Mac
control lists, or by the simulator's oracle) lives in a folder with `turns_*.jsonl` (one turn per line:
id, source, split, task, apps, front_app, window, done, answer, and `sid` or its own `controls`) and
`shards/real_*.jsonl` (screens: sid, controls [{n, role, name, value?, state?}]).

    cases = planner.load(folder, "train")          # chat samples for TaskTuner / chat.score (kind "tool_call")
    planner.score(sample, text)                    # is a generated answer the turn's step?
"""
import glob
import json
import os
import re

from . import chat

SYSTEM = ("You operate a Mac for the user, one step at a time. Reply with exactly one next_step call. "
          "Prefer open_app, open_url, key and menu over clicking. To press or fill a control from the list, give its id. "
          "Use look only when the control you need is not in the list. When the task is finished, call done with one sentence for the user.")
ACTIONS = ["open_app", "open_url", "click", "double_click", "right_click", "type", "key", "menu", "scroll", "drag", "look", "done"]
ORDER = ("app", "url", "id", "target", "target_end", "text", "keys", "path", "direction")
TOOL = {"type": "function", "function": {
    "name": "next_step",
    "description": "The next single step on the Mac.",
    "parameters": {"type": "object", "required": ["action"], "properties": {
        "action": {"type": "string", "enum": ACTIONS, "description": "What to do. `done` ends the task."},
        "app": {"type": "string", "description": "For open_app: the app's name, from Apps. Optional for open_url: the browser to open it in."},
        "url": {"type": "string", "description": "For open_url: a web address, or a mailto: link to draft an email."},
        "id": {"type": "number", "description": "A number from Controls: the control to press, or the field to type into."},
        "target": {"type": "string", "description": "Plain words: what to click when it has no id, where a drag starts, or for look what to find. "
                                                     "Say what kind of thing it is, what it says, where it is and what is beside it, "
                                                     "for example \"the Today button in the toolbar, between the two arrow buttons\"."},
        "target_end": {"type": "string", "description": "For drag: where it ends, in plain words."},
        "text": {"type": "string", "description": "For type: the text; a final newline presses Return. For done: one sentence for the user."},
        "keys": {"type": "string", "description": "For key: the keys pressed together, like cmd+n."},
        "path": {"type": "string", "description": "For menu: the path through the menu bar, like File > New Message."},
        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "For scroll."}}}}}
ROLES = {"pop-up button": "popup", "popup button": "popup", "menu button": "popup", "switch": "checkbox", "row": "cell"}
MAX_CONTROLS, MAX_APPS = 80, 60


def control_line(c):
    """`[3] button "Today"`, `[4] text field "Search" = "value"`, `[5] radio "Month" selected`."""
    role = ROLES.get(str(c.get("role", "")).lower(), str(c.get("role", "")))
    out = f"[{c.get('n', c.get('id'))}] {role}"
    if c.get("name"):
        out += f" \"{c['name']}\""
    value, st = c.get("value"), c.get("state")
    if str(value) == "selected" or str(st).lower() in ("selected", "on", "checked", "true"):
        out += " selected"
    elif value not in (None, ""):
        out += f" = \"{value}\""
    return out


def user_text(turn, controls):
    lines = ["Task: " + str(turn["task"]).strip(), "Apps: " + ", ".join((turn.get("apps") or [])[:MAX_APPS]),
             "Front app: " + (turn.get("front_app") or "none") + " | Window: " + (turn.get("window") or "none")]
    done = turn.get("done") or []
    lines += ["Done so far: nothing"] if not done else ["Done so far:"] + [f"{i + 1}. {s}" for i, s in enumerate(done)]
    lines += ["Controls: none"] if not controls else ["Controls:"] + [control_line(c) for c in controls[:MAX_CONTROLS]]
    return "\n".join(lines)


def call_text(answer):
    """The answer's arguments as one next_step call, action first, then the app's argument order."""
    args = {"action": answer["action"]}
    for k in ORDER:
        if answer.get(k) not in (None, ""):
            v = answer[k]
            args[k] = "+".join(v) if k == "keys" and isinstance(v, (list, tuple)) else v
    return chat.render_call("next_step", args)


def case(turn, screens=None):
    """A planner turn as a chat sample: text only, every token of the call supervised."""
    controls = turn.get("controls")
    if controls is None and turn.get("sid") is not None:
        controls = ((screens or {}).get(turn["sid"]) or {}).get("controls")
        if controls is None:
            return None                                  # its screen is not on this machine
    target = call_text(turn["answer"])
    return {"kind": "tool_call", "id": turn["id"], "category": "planner:" + turn["answer"]["action"], "tools": [TOOL],
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text(turn, controls or [])}],
            "target": target, "turn": turn}


def load(folder, split="train", drop=("drag",)):
    """Chat samples of the turns of one split (the dev split is for scoring only)."""
    screens = {}
    for path in sorted(glob.glob(f"{folder}/shards/*.jsonl")):
        for line in open(path):
            s = json.loads(line)
            screens[s["sid"]] = s
    out = []
    for path in sorted(glob.glob(f"{folder}/turns_*.jsonl")):
        for line in open(path):
            t = json.loads(line)
            if t.get("split", "train") == split and t["answer"].get("action") in ACTIONS and t["answer"]["action"] not in drop:
                c = case(t, screens)
                if c:
                    out.append(c)
    return out


def parse(text):
    """The arguments of the first next_step call in a generated answer; None if there is none."""
    m = re.search(r"<function=next_step>(.*?)</function>", text, flags=re.S)
    if not m:
        return None
    return {k: v for k, v in re.findall(r"<parameter=(\w+)>\n?(.*?)\n?</parameter>", m.group(1), flags=re.S)}


def score(sample, text):
    """{"parsed", "action", "ok"}: ok = the same action and the same id, app, url, keys, path, direction
    and typed text as the turn's answer (the words of target, target_end and of a done sentence are free)."""
    got, want = parse(text), sample["turn"]["answer"]
    r = {"parsed": got is not None, "action": False, "ok": False}
    if got is None:
        return r
    r["action"] = got.get("action", "").strip() == want["action"]
    norm = lambda v: "+".join(v) if isinstance(v, (list, tuple)) else str(v)
    keys = ("id", "app", "url", "keys", "path", "direction") + (("text",) if want["action"] == "type" else ())
    same = all(norm(got.get(k, "")).strip().lower() == norm(want.get(k, "")).strip().lower() if k != "text"
               else got.get(k, "") == norm(want.get(k, "")) for k in keys if want.get(k) not in (None, "") or got.get(k))
    r["ok"] = bool(r["action"] and same)
    return r
