"""Planner mode: the desktop as a numbered list of controls, one `next_step` per turn, no screenshot.

Format v1, as the assistant sends it (assistant/Sources/AssistantCore/Planner.swift at e751270) and as
weightlab/planner.py renders it for training. This module gives the simulator's side:

    controls(env)             the front window's pressable and editable elements with names, at most 80
    execute(env, answer, view)  carry out one next_step (open_app, open_url, click, double_click, right_click,
                              type, key, menu, scroll, drag, look, done)
    oracle_rows(env, ep)      the oracle's solution of a task as planner turns (neutral rows)
    replay(env, ep, rows)     the same turns through execute() only; kept when the checker says done
    rollout(env, ep, model)   a model in this format on a task: every state it reaches, the oracle's
                              next step from that state where the oracle can tell, the checker's verdict

THE SPLIT. Since 15 Nov 2026 the environment is split by app. TRAIN_APPS may be used to make planner
training data (new seeds, see SEEDS); TEST_APPS are never trained on. On the training apps the task
templates in HELD_OUT and the seeds 9101 to 9103 stay out of training too.
"""
import hashlib
import json
import math
import random
import re

from . import oracle
from .tasks import base

TRAIN_APPS = ["files", "settings", "mail", "notes", "reminders", "calendar", "browser"]
TEST_APPS = ["music", "sheet", "calculator"]
TRAIN_SEED0 = 20001              # training episodes use seeds from here up; 1 to 5 and 9101 to 9103 are never used for training
MAX_CONTROLS, MAX_STEPS = 80, 15

# ---- format v1, word for word as weightlab/planner.py and Planner.swift (e751270) have it
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
        "target": {"type": "string", "description": "Plain words: what to click when it has no id, where a drag starts, or for look what to find."},
        "target_end": {"type": "string", "description": "For drag: where it ends, in plain words."},
        "text": {"type": "string", "description": "For type: the text; a final newline presses Return. For done: one sentence for the user."},
        "keys": {"type": "string", "description": "For key: the keys pressed together, like cmd+n."},
        "path": {"type": "string", "description": "For menu: the path through the menu bar, like File > New Message."},
        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "For scroll."}}}}}
ALIAS = {"press": "click", "tap": "click", "select": "click", "left_click": "click", "doubleclick": "double_click", "rightclick": "right_click", "write": "type", "input": "type", "hotkey": "key", "keys": "key",
         "launch": "open_app", "open": "open_app", "open_application": "open_app", "browse": "open_url", "navigate": "open_url", "goto": "open_url", "find": "look", "see": "look", "finish": "done", "terminate": "done",
         "stop": "done", "answer": "done"}


def control_line(c):
    out = f"[{c['n']}] {c['role']}"
    if c.get("name"):
        out += f" \"{c['name']}\""
    if c.get("value") == "selected":
        out += " selected"
    elif c.get("value") not in (None, ""):
        out += f" = \"{c['value']}\""
    return out


def user_text(task, apps, front_app, window, done, controls):
    lines = ["Task: " + str(task).strip(), "Apps: " + ", ".join(apps), "Front app: " + (front_app or "none") + " | Window: " + (window or "none")]
    lines += ["Done so far: nothing"] if not done else ["Done so far:"] + [f"{i + 1}. {s}" for i, s in enumerate(done)]
    lines += ["Controls: none"] if not controls else ["Controls:"] + [control_line(c) for c in controls[:MAX_CONTROLS]]
    return "\n".join(lines)


def done_line(a, control=None):
    """The line a finished step leaves in "Done so far" (Planner.doneLine)."""
    named = (f"\"{control['name']}\"" if control.get("name") else control["role"]) if control else (f"\"{a['target']}\"" if a.get("target") else "")
    act = a["action"]
    if act == "open_app":
        return f"open_app {a.get('app', '')}"
    if act == "open_url":
        return f"open_url {a.get('url', '')}" + (f" in {a['app']}" if a.get("app") else "")
    if act in ("click", "double_click", "right_click"):
        return f"{act} {named}"
    if act == "type":
        t = a.get("text", "")
        shown = t.strip("\n") if len(t) <= 60 else t[:57] + "..."
        return "type " + json.dumps(shown, ensure_ascii=False) + (f" into {named}" if named else "") + (" and Return" if t.endswith("\n") else "")
    if act == "key":
        return "key " + keys_text(a.get("keys"))
    if act == "menu":
        return f"menu {a.get('path', '')}"
    if act == "scroll":
        return f"scroll {a.get('direction', 'down')}"
    if act == "drag":
        return f"drag {named} to \"{a.get('target_end', '')}\""
    if act == "look":
        return f"look \"{a.get('target', '')}\""
    return "done"


def keys_text(keys):
    return "+".join(keys) if isinstance(keys, (list, tuple)) else str(keys or "")


def parse(msg):
    """The step in a model's answer, read leniently: the API's tool call, the Qwen call as the template writes it,
    or a JSON object in the text. None when there is none."""
    args = None
    for call in (msg.get("tool_calls") or []):
        f = call.get("function", call)
        a = f.get("arguments")
        if isinstance(a, str):
            try:
                a = json.loads(a)
            except Exception:
                a = None
        if isinstance(a, dict) and a.get("action"):
            args = a
            break
    text = re.sub(r"<think>.*?</think>", "", str(msg.get("raw") or msg.get("content") or ""), flags=re.S)
    if args is None:
        m = re.search(r"<function=next_step>(.*?)(?:</function>|$)", text, flags=re.S)
        if m:
            args = {k.strip(): v for k, v in re.findall(r"<parameter=([^>\n]+)>\n?(.*?)\n?</parameter>", m.group(1), flags=re.S)}
    if args is None or not args.get("action"):
        for m in re.finditer(r"\{[^{}]*\}", text):
            try:
                d = json.loads(m.group(0))
            except Exception:
                continue
            d = d.get("arguments", d) if isinstance(d, dict) else None
            if isinstance(d, dict) and d.get("action"):
                args = d
                break
    if not args or not args.get("action"):
        return None
    act = str(args["action"]).strip().lower().replace(" ", "_")
    act = ALIAS.get(act, act)
    if act not in ACTIONS:
        return None
    out = {"action": act}
    for k in ORDER:
        v = args.get(k)
        if v in (None, ""):
            continue
        if k == "id":
            try:
                out["id"] = int(float(str(v).strip("[] \n")))
            except Exception:
                pass
        elif k == "keys":
            out["keys"] = keys_text(v).strip().lower().replace(" ", "")
        else:
            out[k] = str(v) if k == "text" else str(v).strip()
    return out


# ------------------------------------------------------------------ the control list
# The front window's pressable and editable elements that are in view, in page order, then what an open menu
# offers first. Names: the element's own text; a field's placeholder or the label of its row; for an icon-only
# button the name of what it does. The test apps are read by the same rule (their code is not touched).
CONTROLS_JS = """() => {
  const NICE = {trash: 'Delete', del: 'Delete', delete: 'Delete', fwd: 'Forward', forward: 'Forward', playpause: 'Play', prev: 'Previous', next: 'Next', newfolder: 'New Folder', compose: 'New Message', newtab: 'New Tab',
    closepreview: 'Close Preview', love: 'Favourite', add: 'Add', new: 'New', back: 'Back', reload: 'Reload', bookmark: 'Bookmark', flag: 'Flag', archive: 'Archive', reply: 'Reply', send: 'Send', discard: 'Discard',
    shuffle: 'Shuffle', repeat: 'Repeat', today: 'Today', clear: 'Clear', subscribe: 'Subscribe', toggle: 'Mark', select: 'Select'};
  const front = TE.front(), win = front ? document.querySelector(`.win[data-app="${front}"]`) : null;
  const lines = el => (el.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
  const cap = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
  const nice = s => { s = String(s || '').replace(/[_-]+/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').trim(); return s ? s[0].toUpperCase() + s.slice(1) : ''; };
  const seen = el => { const r = el.getBoundingClientRect(); if (r.width < 4 || r.height < 4) return null; const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return null; const t = document.elementFromPoint(x, y); return t && (t === el || el.contains(t)) ? r : null; };
  const els = [], out = [];
  const add = (el, role, name, value) => { const r = seen(el); if (!r) return; els.push(el); out.push({n: els.length, role, name: cap(String(name || '').replace(/\\s+/g, ' ').trim(), 70), value: value == null ? '' : cap(String(value), 60), box: [r.left, r.top, r.right, r.bottom]}); };
  for (const el of document.querySelectorAll('#overlays .menu .menu-item:not(.disabled)')) add(el, 'menu item', (el.querySelector('.mi-label') || el).innerText, el.querySelector('.mi-check svg') ? 'selected' : '');
  if (win) for (const el of win.querySelectorAll('[data-tl],[data-act],[data-dbl],[data-ctx],[data-drag],[data-slider],[data-select],input,textarea')) {
    const d = el.dataset, tag = el.tagName, own = lines(el), cls = ' ' + (el.getAttribute('class') || '') + ' ';
    const label = () => { for (let p = el.parentElement, k = 0; p && k < 3 && p !== win; p = p.parentElement, k++) { const l = lines(p).filter(s => !own.includes(s) && s !== el.value); if (l.length && l[0].length <= 60) return l[0]; } return ''; };
    const row = () => { const p = el.parentElement && el.parentElement.closest('[data-dbl],[data-ctx],[data-drag],li'); return p && win.contains(p) ? (lines(p)[0] || '') : ''; };
    if (d.tl) add(el, 'button', {close: 'Close', min: 'Minimise', zoom: 'Zoom'}[d.tl]);
    else if (tag === 'INPUT' || tag === 'TEXTAREA') add(el, tag === 'INPUT' ? 'text field' : 'text area', el.getAttribute('aria-label') || el.placeholder || label() || nice(d.input), el.value);
    else if (d.select !== undefined) add(el, 'popup', label() || nice(d.select), d.value || own[0] || '');
    else if (d.slider !== undefined) add(el, 'slider', label() || nice(d.slider), Math.round(100 * parseFloat(el.style.getPropertyValue('--v') || 0)) + '%');
    else if (/ (toggle|check) /.test(cls)) add(el, 'checkbox', own[0] || label() || nice(d.act), / on /.test(cls) ? 'on' : 'off');
    else if (el.parentElement && / seg /.test(' ' + (el.parentElement.getAttribute('class') || '') + ' ')) add(el, 'radio', own[0] || nice(d.arg), / on /.test(cls) ? 'selected' : '');
    else {
      const rowish = d.dbl !== undefined || d.ctx !== undefined || d.drag !== undefined;
      const role = tag === 'A' || d.act === 'link' ? 'link' : / [a-z-]*tab /.test(cls) || d.act === 'tab' ? 'tab' : rowish ? 'cell' : 'button';
      const holds = rowish && el.querySelector('[data-act],[data-dbl],[data-ctx],[data-drag]') && el.querySelectorAll('[data-dbl],[data-ctx],[data-drag]').length > 1;
      let name = holds ? 'empty space in the list' : own.length ? (role === 'cell' ? own.slice(0, 3).join(', ') : own[0]) : '';
      if (!name) { const base = NICE[d.act] !== undefined ? NICE[d.act] : nice(d.act), r = row(); name = r ? (base + ' ' + r).trim() : base + (d.arg && NICE[d.act] === undefined && /^[A-Za-z][A-Za-z ]{1,18}$/.test(d.arg) ? ' ' + d.arg : ''); }
      add(el, role, name, / (on|sel|selected|active|current) /.test(cls) && role !== 'button' && role !== 'link' ? 'selected' : '');
    }
  }
  window._ctl = els;
  const dock = {}; TE.state.dock.forEach(a => { if (TE.apps[a]) dock[TE.apps[a].title] = a; });
  // What the assistant's change check sees besides the list: the full content of the front window and of what is open on top.
  const html = (win ? win.innerHTML : '') + '\u0001' + document.getElementById('overlays').innerHTML; let h = 0; for (let i = 0; i < html.length; i++) h = (h * 31 + html.charCodeAt(i)) | 0;
  return {controls: out.slice(0, 80), total: out.length, front: front ? TE.apps[front].title : '', key: front || '', dock, apps: Object.keys(dock), detail: html.length + ':' + h};
}"""

# What is at a point: the control (index into the list just made), a menu-bar title, a Dock icon, a menu item.
AT_JS = """([x, y]) => { const t = document.elementFromPoint(x, y); if (!t) return null; let best = -1; (window._ctl || []).forEach((el, i) => { if (el === t || el.contains(t)) best = i; });
  const mb = t.closest('.mb-item'), dk = t.closest('.dock-item'), mi = t.closest('.menu-item');
  return {ctl: best, mb: mb ? mb.innerText.trim() : null, dock: dk ? dk.dataset.dock : null, mi: mi ? (mi.querySelector('.mi-label') || mi).innerText.trim() : null}; }"""

MENU_JS = """label => { const norm = s => s.trim().replace(/\\.\\.\\.$/, '…').toLowerCase(), menus = [...document.querySelectorAll('#overlays .menu')];
  const box = el => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  if (!menus.length) { for (const m of document.querySelectorAll('.mb-item')) if (norm(m.innerText) === norm(label)) return box(m); return null; }
  for (const it of menus[menus.length - 1].querySelectorAll('.menu-item:not(.disabled)')) if (norm((it.querySelector('.mi-label') || it).innerText) === norm(label)) return box(it);
  return null; }"""

SCROLL_JS = """dir => { const f = TE.front(), win = f && document.querySelector(`.win[data-app="${f}"]`); if (!win) return null; const v = dir === 'up' || dir === 'down'; let best = null;
  for (const el of win.querySelectorAll('*')) { const cs = getComputedStyle(el);
    if (v ? !(el.scrollHeight > el.clientHeight + 1 && /(auto|scroll)/.test(cs.overflowY)) : !(el.scrollWidth > el.clientWidth + 1 && /(auto|scroll)/.test(cs.overflowX))) continue;
    const can = dir === 'down' ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : dir === 'up' ? el.scrollTop > 0 : dir === 'right' ? el.scrollLeft + el.clientWidth < el.scrollWidth - 1 : el.scrollLeft > 0;
    const r = el.getBoundingClientRect(); if (can && (!best || r.width * r.height > best.a)) best = {a: r.width * r.height, x: r.left + r.width / 2, y: r.top + r.height / 2, w: el.clientWidth, h: el.clientHeight}; }
  return best; }"""


def controls(env):
    return env.page.evaluate(CONTROLS_JS)


def signature(view):
    return view["front"] + "\x01" + "\x02".join(f"{c['role']}|{c['name']}|{c['value']}" for c in view["controls"])


def fingerprint(state, front):
    """A state as the oracle recognises it: every app's data and view, and which app is in front."""
    return hashlib.sha1(json.dumps([state["apps"], front], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def public(view):
    return [{k: c[k] for k in ("n", "role", "name", "value") if k != "value" or c[k] != ""} for c in view["controls"]]


# ------------------------------------------------------------------ carrying out a step
STOP = {"the", "a", "an", "in", "on", "of", "to", "at", "button", "icon", "field", "item", "row", "toolbar", "sidebar", "window", "list", "and", "with", "for", "its", "it"}
tokens = lambda s: {w for w in re.findall(r"[a-z0-9]+", str(s).lower()) if w not in STOP}


def by_id(view, n):
    return next((c for c in view["controls"] if c["n"] == n), None)


def fuzzy(view, words):
    """The control whose name shares most words with a target in plain words (for a click without id, the end of
    a drag, and `look` when no pointer model is given)."""
    want, best = tokens(words), (0, None)
    for c in view["controls"]:
        got = tokens(c["name"]) | tokens(c["role"])
        score = len(want & got) / (len(want | tokens(c["name"])) or 1)
        if want & tokens(c["name"]) and score > best[0]:
            best = (score, c)
    return best[1]


def center(c):
    b = c["box"]
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def mac_keys(keys):
    """taskenv's key names -> the Mac's ("cmd+shift+n", "return", "delete" for the delete key)."""
    names = {"meta": "cmd", "command": "cmd", "enter": "return", "backspace": "delete", "delete": "forwarddelete", "control": "ctrl", "option": "alt", "escape": "esc"}
    return "+".join(names.get(k.lower(), k.lower()) for k in str(keys).replace(" ", "").split("+") if k)


def env_keys(keys):
    names = {"return": "enter", "delete": "backspace", "forwarddelete": "delete", "opt": "alt", "option": "alt", "command": "cmd"}
    return "+".join(names.get(k, k) for k in keys_text(keys).lower().replace(" ", "").split("+") if k)


def menu_path(env, path):
    labels = [p.strip() for p in str(path).split(">") if p.strip()]
    if len(labels) < 2:
        return False
    for label in labels:
        at = env.page.evaluate(MENU_JS, label)
        if at is None:
            if env.page.evaluate("() => document.querySelectorAll('#overlays .menu').length"):
                env.step({"type": "key", "keys": "esc"})
            return False
        env.step({"type": "click", "x": at[0], "y": at[1]})
    return True


def execute(env, a, view, hint=None, pointer=None):
    """Carry out one step. Returns (valid, control it acted on or None). `hint` holds the oracle's own points for
    what a list of names cannot say (look, the end of a drag); `pointer(image, words)` finds a look target on a screenshot."""
    act, hint = a.get("action"), hint or {}
    c = by_id(view, a.get("id")) if a.get("id") is not None else None
    if act == "open_app":
        key = next((k for t, k in view["dock"].items() if t.lower() == str(a.get("app", "")).strip().lower()), None)
        box = key and env.box(f'.dock-item[data-dock="{key}"]')
        if not box:
            return False, None
        env.step({"type": "click", "x": (box[0] + box[2]) / 2, "y": (box[1] + box[3]) / 2})
        return True, None
    if act == "open_url":
        key = view["dock"].get("Browser") or next((k for t, k in view["dock"].items() if k == "browser"), None)
        if not key or not a.get("url") or str(a["url"]).lower().startswith("mailto:"):       # no mail drafts by link in this simulator
            return False, None
        box = env.box(f'.dock-item[data-dock="{key}"]')
        env.step({"type": "click", "x": (box[0] + box[2]) / 2, "y": (box[1] + box[3]) / 2})
        field = env.box(f'.win[data-app="{key}"] input[data-input="address"]')
        if not field:
            return False, None
        env.step({"type": "click", "x": (field[0] + field[2]) / 2, "y": (field[1] + field[3]) / 2})
        env.step({"type": "key", "keys": "cmd+a"})
        env.step({"type": "type", "text": re.sub(r"^https?://", "", a["url"]).rstrip("/") + "\n"})
        return True, None
    if act in ("click", "double_click", "right_click"):
        if a.get("id") is not None and c is None:
            return False, None
        c = c or (fuzzy(view, a["target"]) if a.get("target") else None)
        if c is None:
            return False, None
        x, y = center(c)
        env.step({"type": "click", "x": x, "y": y, "button": "right" if act == "right_click" else "left", "count": 2 if act == "double_click" else 1})
        return True, c
    if act == "type":
        if a.get("id") is not None:
            if c is None:
                return False, None
            x, y = center(c)
            env.step({"type": "click", "x": x, "y": y})
        if not a.get("text"):
            return False, c
        env.step({"type": "type", "text": a["text"]})
        return True, c
    if act == "key":
        try:
            env.step({"type": "key", "keys": env_keys(a.get("keys"))})
        except Exception:
            return False, None
        return True, None
    if act == "menu":
        return menu_path(env, a.get("path", "")), None
    if act == "scroll":
        d = a.get("direction", "down")
        s = env.page.evaluate(SCROLL_JS, d) if d in ("up", "down", "left", "right") else None
        if s:
            amount = round(0.8 * (s["h"] if d in ("up", "down") else s["w"]))
            env.step({"type": "scroll", "x": s["x"], "y": s["y"], "dx": {"left": -amount, "right": amount}.get(d, 0), "dy": {"up": -amount, "down": amount}.get(d, 0)})
        return d in ("up", "down", "left", "right"), None
    if act == "drag":
        c = c or (fuzzy(view, a["target"]) if a.get("target") else None)
        start = hint.get("from") or (center(c) if c else None)
        end_c = fuzzy(view, a.get("target_end", "")) if not hint.get("to") else None
        end = hint.get("to") or (center(end_c) if end_c else None)
        if not start or not end:
            return False, c
        env.step({"type": "drag", "x1": start[0], "y1": start[1], "x2": end[0], "y2": end[1]})
        return True, c
    if act == "look":
        if not a.get("target"):
            return False, None
        point = hint.get("point")
        if point is None and pointer is not None:
            point = pointer(env.screenshot(), a["target"])
        if point is None:
            c = fuzzy(view, a["target"])
            point = center(c) if c else None
        if point is not None:
            env.step({"type": "click", "x": point[0], "y": point[1], "button": hint.get("button", "left"), "count": hint.get("count", 1)})
        return True, None
    return act == "done", None


# ------------------------------------------------------------------ tasks: the split, chains, paraphrases
def held_out():
    """Two task templates of every training app that are never used for training (the two whose id hashes lowest)."""
    out = []
    for app in TRAIN_APPS:
        ids = sorted((t for t in base.all_tasks() if t.startswith(app + ".")), key=lambda t: hashlib.sha1(t.encode()).hexdigest())
        out += ids[:2]
    return sorted(out)


def task_sets():
    """{"train": templates for training data, "held_out": templates of training apps kept out, "test_apps": every task of the test apps}"""
    tasks, held = base.all_tasks(), set(held_out())
    return {"train": [t for t in tasks if t.split(".")[0] in TRAIN_APPS and t not in held], "held_out": sorted(held), "test_apps": [t for t in tasks if t.split(".")[0] in TEST_APPS]}


class OpenApp(oracle.Step):
    """Chain glue: bring another app to the front through the Dock."""

    def __init__(self, app):
        self.app = app


JOIN = ["{a} Then {b}", "{a} After that, {b}", "First, {a} Then {b}", "{a} When that is done, {b}", "{a} Next, {b}", "Two things: {a} And {b}", "{a} Once you have done that, {b}", "{a} And then {b}"]
JOIN3 = ["{a} Then {b} Finally, {c}", "First, {a} Second, {b} Third, {c}", "{a} After that, {b} And when both are done, {c}", "Three things: {a} Then {b} Last, {c}"]
WRAP = ["Please {x}", "Can you {x}?", "Could you {x}?", "I need you to {x}", "{x}, please.", "I'd like you to {x}", "Would you {x}?", "Go ahead and {x}"]
DONE = {"act": ["Done.", "That's done.", "All set.", "It's done.", "Finished.", "Done, that's taken care of."],
        "already_done": ["That was already the case, so I left it as it is.", "It's already like that; nothing needed changing.", "Nothing to do: it was already set that way."],
        "infeasible": ["I can't do that here, so I changed nothing.", "That isn't possible on this Mac as it is; I left everything alone.", "I couldn't find a way to do that, so nothing was changed."]}


def low(s):
    """A request as the tail of a sentence: "Flag the email." -> "flag the email."."""
    w = s.split(" ", 1)[0]
    return s if not w[:1].isupper() or w in ("I", "I'm", "I'd") or (len(w) > 1 and w[1:].lower() != w[1:]) else s[0].lower() + s[1:]


def sentence(s):
    s = s.strip()
    return s if s[-1:] in ".!?" else s + "."


VERBS = {"Delete ": ["Remove ", "Get rid of ", "Trash "], "Open ": ["Go to ", "Bring up ", "Show me "], "Turn on ": ["Switch on ", "Enable "], "Turn off ": ["Switch off ", "Disable "], "Create ": ["Make "],
         "Set ": ["Change "], "Show ": ["Display ", "Let me see "], "Find ": ["Look up ", "Search for "], "Switch on ": ["Turn on "], "Switch off ": ["Turn off "], "Remove ": ["Delete "], "Make ": ["Create "]}


def rephrase(req, rng, verbs=True):
    """Now and then another verb, or a politer or vaguer wrapping, for the same request."""
    if verbs and rng.random() < 0.35:
        for v, others in VERBS.items():
            if req.startswith(v):
                req = rng.choice(others) + req[len(v):]
                break
    if rng.random() < 0.6 or not re.match(r"^[A-Z][a-z]+ ", req) or "?" in req:
        return req
    form = rng.choice(WRAP)
    x = low(req).strip().rstrip(".!")
    out = form.format(x=x) if form.endswith(("?", ".")) else sentence(form.format(x=x))
    return out[0].upper() + out[1:]


def mask(st, init, keep):
    """The final state with every app but `keep` put back as it began (a chained task's checker sees only its own app)."""
    out = dict(st, apps=dict(st["apps"]))
    for name in out["apps"]:
        if name != keep:
            out["apps"][name] = init["apps"][name]
    return out


def build(tids, seed):
    """An episode of one task or of a chain of tasks in different apps (one Builder, the first task's app in front)."""
    if isinstance(tids, str):
        tids = [tids]
    if len(tids) == 1:
        return base.build(tids[0], seed)
    mods = base.modules()
    S = base.Builder(seed, mods, "+".join(tids))
    specs = [base.TASKS[t]["fn"](S) for t in tids]
    apps = [base.TASKS[t]["app"] for t in tids]
    assert len(set(apps)) == len(apps) and all(s.kind == "act" for s in specs), "a chain takes act tasks of different apps"
    S.state["windows"].sort(key=lambda w: -apps.index(w["app"]) if w["app"] in apps else -99)           # first task's app in front, the others behind in order
    steps = []
    for k, (app, spec) in enumerate(zip(apps, specs)):
        steps += ([OpenApp(app)] if k else []) + list(spec.steps)
    reqs = [sentence(rephrase(s.request, S.rng) if S.rng.random() < 0.5 else s.request) for s in specs]
    reqs = [r if r.endswith((".", "!")) else r.rstrip("?") + "." for r in reqs]
    form = S.rng.choice(JOIN if len(reqs) == 2 else JOIN3)
    request = form.format(a=reqs[0] if form.startswith("{a}") else low(reqs[0]), b=low(reqs[1]), c=low(reqs[2]) if len(reqs) > 2 else "")

    def check(st, init):
        for app, spec in zip(apps, specs):
            ok, why = spec.check(mask(st, init, app), init)
            if not ok:
                return False, f"{app}: {why}"
        return True, ""
    return base.Episode(task="+".join(tids), seed=seed, app=apps[0], category="chain", request=request, state=S.state, steps=steps, check=check, kind="act", limit=0)


# ------------------------------------------------------------------ the oracle as a planner
class Untranslatable(Exception):
    pass


WORDS = re.compile(r"^(double[- ]click|right[- ]click|click on|click|drag|press|select|choose|open|tick|untick|check|uncheck)\s+", re.I)


def words(say):
    return WORDS.sub("", str(say or "").strip()).rstrip(".")


ADDRESS = "Search or enter website name"


def oracle_rows(env, ep, rng, variant="front", drop_rate=0.0, use_open_url=True):
    """Play the oracle's solution as planner steps and return the turns (state before each step, the step).
    variant: "front" (the task's app is in front), "closed" (its window is not open: open_app comes first),
    "behind" (another app is in front). drop_rate: the share of click steps whose control is taken out of the list,
    so that the right answer is `look` (an app that names nothing)."""
    state = base.clone(ep.state)
    wins = state["windows"]
    if variant == "closed" and wins:
        state["windows"] = wins[:-1]
    elif variant == "behind" and wins:
        other = [a for a in TRAIN_APPS if a in state["apps"] and all(w["app"] != a for w in wins)]
        if other:
            a = rng.choice(other)
            w, h = base.modules()[a].SIZE
            state["windows"] = wins + [{"app": a, "x": rng.randint(16, max(16, 1440 - w - 16)), "y": rng.randint(36, max(36, 900 - 84 - h)), "w": w, "h": h}]
    env.reset(state)
    init = env.state()
    rows, done, steps = [], [], list(ep.steps)
    title = lambda app: env.page.evaluate("a => TE.apps[a].title", app)
    view = controls(env)

    def emit(answer, view, hint=None, executed=False, hide=None):
        shown = [c for c in view["controls"] if c["n"] != hide] if hide else view["controls"]
        row = {"task": ep.request, "apps": view["apps"], "front_app": view["front"], "window": view["front"], "done": list(done), "controls": public(dict(view, controls=shown)), "answer": answer,
               "state": fingerprint(env.state() if not executed else emit.before, view["key"])}
        if hint:
            row["hint"] = hint
        if hide:
            row["hidden"] = hide
        control = by_id(view, answer.get("id")) if answer.get("id") is not None else None
        if not executed and answer["action"] != "done":
            ok, _ = execute(env, answer, view, hint)
            if not ok:
                raise Untranslatable(f"the executor cannot do {answer}")
        after = controls(env) if answer["action"] != "done" else view
        done.append(done_line(answer, control) + (" (nothing changed)" if answer["action"] != "done" and signature(after) == signature(view) else ""))
        rows.append(row)
        return after

    if steps or ep.kind != "act":
        if view["key"] != ep.app and not (steps and isinstance(steps[0], OpenApp)):
            view = emit({"action": "open_app", "app": title(ep.app)}, view)
    i = 0
    while i < len(steps):
        st, nxt = steps[i], steps[i + 1] if i + 1 < len(steps) else None
        enter = lambda s: isinstance(s, oracle.Key) and str(s.keys).lower() in ("enter", "return")
        if isinstance(st, OpenApp):
            view = emit({"action": "open_app", "app": title(st.app)}, view)
        elif isinstance(st, oracle.Reveal):
            for _ in range(14):
                r = env.page.locator(st.sel).first.evaluate(oracle.REVEAL_JS)
                if not r or abs(r["dy"]) < 1:
                    break
                view = emit({"action": "scroll", "direction": "down" if r["dy"] > 0 else "up"}, view)
                r2 = env.page.locator(st.sel).first.evaluate(oracle.REVEAL_JS)
                if r2 and abs(r2["dy"] - r["dy"]) < 1:
                    raise Untranslatable("scroll moves another box than the one the oracle needs")
            else:
                raise Untranslatable("scrolling does not reveal the target")
        elif isinstance(st, oracle.Click):
            if st.mods:
                raise Untranslatable("a click with a modifier key")
            x, y = oracle._point(env, st.sel, st.at)
            at = env.page.evaluate(AT_JS, [x, y]) or {}
            if at.get("mb") is not None:                       # the menu bar: this click and the menu items after it are one `menu` step
                emit.before, view0, path = env.state(), view, [at["mb"]]
                env.step(st.build([(x, y)]))
                while i + 1 < len(steps) and isinstance(steps[i + 1], oracle.Click):
                    try:
                        px, py = oracle._point(env, steps[i + 1].sel, steps[i + 1].at)
                    except LookupError:
                        break
                    mi = (env.page.evaluate(AT_JS, [px, py]) or {}).get("mi")
                    if mi is None:
                        break
                    path.append(mi)
                    env.step(steps[i + 1].build([(px, py)]))
                    i += 1
                if len(path) < 2:
                    raise Untranslatable("a menu was opened and nothing chosen")
                view = emit({"action": "menu", "path": " > ".join(path)}, view0, executed=True)
                view = controls(env)
            elif at.get("dock"):
                view = emit({"action": "open_app", "app": title(at["dock"])}, view)
            else:
                n = at["ctl"] + 1 if 0 <= at.get("ctl", -1) < MAX_CONTROLS else None
                c = by_id(view, n) if n else None
                kind = "right_click" if st.button == "right" else "double_click" if st.count == 2 else "click"
                hint = {"point": [x, y], "button": st.button, "count": st.count}
                if c and c["role"] in ("text field", "text area") and isinstance(nxt, oracle.Type) and kind == "click":
                    text = nxt.text
                    i += 1
                    if i + 1 < len(steps) and enter(steps[i + 1]) and not text.endswith("\n"):
                        text, i = text + "\n", i + 1
                    if use_open_url and view["key"] == "browser" and c["name"] == ADDRESS and text.endswith("\n") and re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/\S*)?$", text.strip()):
                        view = emit({"action": "open_url", "url": "https://" + text.strip()}, view)
                    else:
                        view = emit({"action": "type", "id": n, "text": text}, view)
                elif c and kind == "click" and rng.random() < drop_rate and c["role"] in ("button", "cell", "link", "tab") and words(st.say):
                    view = emit({"action": "look", "target": words(st.say)}, view, hint=hint, hide=n)
                elif c:
                    view = emit({"action": kind, "id": n}, view)
                elif words(st.say):
                    view = emit({"action": "look", "target": words(st.say)}, view, hint=hint)
                else:
                    raise Untranslatable("a click on something without a control or a description")
        elif isinstance(st, oracle.Type):
            text = st.text
            if enter(nxt) and not text.endswith("\n"):
                text, i = text + "\n", i + 1
            view = emit({"action": "type", "text": text}, view)
        elif isinstance(st, oracle.Key):
            view = emit({"action": "key", "keys": mac_keys(st.keys)}, view)
        elif isinstance(st, oracle.Drag):
            (x1, y1), (x2, y2) = oracle._point(env, st.src, st.src_at), oracle._point(env, st.dst, st.dst_at)
            at = env.page.evaluate(AT_JS, [x1, y1]) or {}
            n = at["ctl"] + 1 if 0 <= at.get("ctl", -1) < MAX_CONTROLS else None
            a = {"action": "drag", "target": words(st.say), "target_end": words(st.say_to)}
            if n:
                a["id"] = n
            view = emit(a, view, hint={"from": [x1, y1], "to": [x2, y2]})
        else:
            raise Untranslatable(f"step {type(st).__name__}")
        i += 1
    emit({"action": "done", "text": rng.choice(DONE[ep.kind])}, view)
    ok, why = ep.check(env.state(), init)
    return rows, state, ok, why


def replay(env, ep, state, rows):
    """The turns again from the start, through execute() alone. True when every list is the one recorded and the
    checker accepts the end: then the rows are what the rollout harness would show and do."""
    env.reset(base.clone(state))
    init = env.state()
    for row in rows:
        view = controls(env)
        shown = [c for c in view["controls"] if c["n"] != row.get("hidden")]
        if public(dict(view, controls=shown)) != row["controls"]:
            return False, "the control list differs on replay"
        if row["answer"]["action"] == "done":
            break
        ok, _ = execute(env, row["answer"], view, row.get("hint"))
        if not ok:
            return False, f"replay cannot do {row['answer']}"
    return ep.check(env.state(), init)


# ------------------------------------------------------------------ a model on a task
def same_step(a, b):
    """Two steps that do the same thing (words of target and of the done sentence are free)."""
    if not a or not b or a["action"] != b["action"]:
        return False
    keys = ("id", "app", "url", "keys", "path", "direction") + (("text",) if a["action"] == "type" else ())
    return all(str(a.get(k, "")).strip().lower() == str(b.get(k, "")).strip().lower() if k != "text" else a.get(k, "") == b.get(k, "") for k in keys)


def relabel(row, view):
    """An oracle turn's answer for the list shown now: the same control by role, name and value (ids move when the
    page is scrolled). None when the control is not in the list."""
    a = dict(row["answer"])
    if a.get("id") is None:
        return a
    c = next((c for c in row["controls"] if c["n"] == a["id"]), None)
    if c is None:
        return None
    same = lambda x: (x["role"], x["name"], x.get("value", "")) == (c["role"], c["name"], c.get("value", ""))
    k = [x["n"] for x in row["controls"] if same(x)].index(a["id"])
    now = [x["n"] for x in public(view) if same(x)]
    if k >= len(now):
        return None
    a["id"] = now[k]
    return a


def rollout(env, ep, chat, oracle_rows_=None, pointer=None, max_steps=MAX_STEPS, max_new_tokens=160, system=None, app_rules=False):
    """Run a planner on one task. `chat(messages, tools)` -> assistant message. Returns the episode record: every
    turn (what the model saw, what it answered, what happened, the oracle's step from that state when the state is
    one the oracle's own run passes through) and the verdict of the checker.
    system: another system text than the shipped one. app_rules: the two rules of the app's own loop (AppController):
    Return is not pressed right after a step that pressed it (the planner is told; asked twice, the task stops), and a
    click or look without effect is done once more before the step is marked "(nothing changed)"."""
    by_state = {}
    for row in (oracle_rows_ or []):
        by_state.setdefault(row["state"], []).append(row)

    def oracle_step(fp, view):
        """The oracle's turn for this state. Scrolling and an open menu are not part of the state, so several of its
        turns can share one: take the turn whose list is the one shown now, else the first later step whose control
        is in view, else the first."""
        rows = by_state.get(fp) or []
        now = [(c["role"], c["name"], c.get("value", "")) for c in public(view)]
        for row in rows:
            if [(c["role"], c["name"], c.get("value", "")) for c in row["controls"]] == now:
                return row, relabel(row, view)
        for row in rows:
            if row["answer"]["action"] != "scroll" and row["answer"].get("id") is not None and relabel(row, view):
                return row, relabel(row, view)
        return (rows[0], relabel(rows[0], view)) if rows else (None, None)
    env.reset(base.clone(ep.state))
    init = env.state()
    done, turns, finished, said, same, pressed_return, refused = [], [], False, None, 0, False, 0
    need = len(oracle_rows_ or []) or 4
    limit = min(max_steps, max(6, 2 * need + 3))             # the app stops at 15; a short task is cut sooner: twice the oracle's steps plus three
    for k in range(limit):
        view = controls(env)
        st = env.state()
        fp = fingerprint(st, view["key"])
        user = user_text(ep.request, view["apps"], view["front"], view["front"], done, view["controls"])
        msg = chat([{"role": "system", "content": system or SYSTEM}, {"role": "user", "content": user}], [TOOL], max_new_tokens)
        a = parse(msg)
        orow, want = oracle_step(fp, view)
        if want is None and ep.kind == "act" and ep.check(st, init)[0]:
            want = {"action": "done", "text": "Done."}       # the goal is reached: the right step is to say so
        turn = {"k": k + 1, "front_app": view["front"], "apps": view["apps"], "done": list(done), "controls": public(view), "raw": str(msg.get("raw") or msg.get("content") or "")[:600], "answer": a,
                "oracle": want, "oracle_known": want is not None, "agrees": same_step(a, want) if want else None, "seconds": msg.get("seconds")}
        turns.append(turn)
        if a is None:
            turn.update(valid=False, changed=False)
            done.append("(no step could be read from the answer) (nothing changed)")
            continue
        if a["action"] == "done":
            finished, said = True, a.get("text", "")
            turn.update(valid=True, changed=False)
            break
        is_return = a["action"] == "key" and env_keys(a.get("keys")) == "enter"
        if app_rules and is_return and pressed_return:
            refused += 1
            turn.update(valid=True, changed=False, refused=True)
            done.append(done_line(a) + " (not pressed: the step before already pressed Return)")
            if refused >= 2:
                break
            continue
        # A list of names cannot say where a `look` target or the end of a drag is. With a pointer model, it finds them on
        # a screenshot. Without one the harness stands in as a perfect pointer, but only when the oracle's step from this
        # state is the same kind of step (so the planner is judged on planning, and pointing is measured elsewhere).
        hint = None
        if pointer is None and orow is not None and want and a["action"] in ("look", "drag") and want["action"] == a["action"]:
            if a["action"] == "look" or a.get("id") in (None, want.get("id")):
                hint = orow.get("hint")
        turn["perfect_pointer"] = hint is not None
        try:
            ok, c = execute(env, a, view, hint=hint, pointer=pointer)
        except Exception as err:
            ok, c = False, None
            turn["error"] = f"{type(err).__name__}: {err}"[:200]
        pressed_return, refused = is_return or (a["action"] == "type" and str(a.get("text", "")).endswith("\n")), 0
        after = controls(env)
        changed = signature(after) != signature(view)
        if app_rules and ok and not changed and a["action"] in ("click", "double_click", "right_click", "look"):
            try:
                execute(env, a, view, hint=hint, pointer=pointer)       # nothing changed: the same step once more, as the app does
            except Exception:
                pass
            after = controls(env)
            changed, turn["again"] = signature(after) != signature(view), True
        turn.update(valid=bool(ok), changed=changed)
        done.append(done_line(a, c) + ("" if changed else " (nothing changed)"))
        same = same + 1 if not changed and len(turns) > 1 and turns[-2]["answer"] == a else 0
        if same >= 2:                                         # the same step three times with no effect: the model is stuck
            break
    final = env.state()
    ok, why = ep.check(final, init)
    if ep.kind != "act":
        ok, why = (ok and finished), (why if not ok else "" if finished else "did not say done")
    elif ok and not finished:
        ok, why = False, "the goal was reached but the model never said done"
    return {"task": ep.task, "seed": ep.seed, "app": ep.app, "category": ep.category, "kind": ep.kind, "request": ep.request, "ok": bool(ok), "why": why, "finished": finished, "said": said, "steps": len(turns), "limit": limit, "stuck": same >= 2,
            "invalid": sum(not t.get("valid", True) for t in turns), "unchanged": sum(t.get("valid") and not t.get("changed") and (t["answer"] or {}).get("action") != "done" for t in turns),
            "oracle_known": sum(t["oracle_known"] for t in turns), "agrees": sum(bool(t["agrees"]) for t in turns), "turns": turns, "errors": env.errors()[:3]}


# ------------------------------------------------------------------ a planner inside the assistant (build b336837)
# The rules the assistant's own loop puts around the planner (assistant/Sources: AppController.runPlanner, Repair,
# StepBudget), mirrored so that "the planner inside the assistant" can be measured on the same episodes.
UNFINISHED = [r"\b(?:now|next|then),?\s+i(?:'ll|\s+will|\s+need|\s+have|\s+must|\s+should|\s+am\s+going)\b", r"\bi\s+(?:still\s+)?need\s+to\b", r"\bi\s+(?:will|'ll)\s+(?:now|next)\b", r"\bnext\s+step\b",
              r"\bstill\s+(?:need|have)\s+to\b", r"\b(?:i'm|i\s+am)\s+sorry\b", r"\bsorry,", r"\bcould\s+you\b", r"\bcan\s+you\s+(?:clarify|tell|confirm|provide)\b", r"\bplease\s+(?:clarify|provide|tell|confirm|specify)\b",
              r"\bwhat\s+would\s+you\s+like\b", r"\bwould\s+you\s+like\s+me\b", r"\b(?:is|are|was)\s+not\s+available\b", r"\b(?:isn't|aren't)\s+available\b", r"\bnot\s+(?:be\s+)?found\b",
              r"\bi\s+(?:don't|do\s+not|can't|cannot|couldn't|could\s+not)\s+(?:see|find|locate)\b", r"\bi\s+(?:can't|cannot|am\s+unable|was\s+unable|couldn't|could\s+not)\b", r"\bunable\s+to\b", r"\bthere\s+is\s+no\b"]
ONE_LINE_JS = """() => { const a = document.activeElement; if (!a || a.tagName !== 'INPUT' || !a.value) return false; const w = a.closest('.win'); return !!w && !(w.dataset.app === 'browser' && a.dataset.input !== 'address'); }"""


def seen(view):
    """The screen as the assistant's change check reads it: the list and the content behind it (AppController's
    signature adds the screen's detail to the list, so a click that changes a display or an icon counts as a change)."""
    return signature(view) + "\x01" + view.get("detail", "")


def unfinished(sentence):
    """Does the sentence given with `done` itself say the task is not done (more to do, a question, giving up)?"""
    t = str(sentence).lower().replace("’", "'")
    return any(re.search(p, t) for p in UNFINISHED)


def apps_named(task, apps):
    """The apps a task speaks of, by their names as people say them."""
    t = " " + re.sub(r"[^a-z0-9]+", " ", str(task).lower()) + " "
    said = {"System Settings": ["system settings", "settings"], "Sheets": ["sheets", "the sheet", "spreadsheet"], "Browser": ["browser"], "Files": ["files app", "in files"]}
    return [a for a in apps if any(f" {w} " in t for w in said.get(a, [a.lower()]))]


def repair(a, view, task):
    """What is not in doubt about an unusable call is put right (Repair.step)."""
    a, listed = dict(a), lambda n: n is not None and by_id(view, n) is not None
    empty = lambda k: not str(a.get(k) or "").strip()
    if a["action"] == "open_app" and empty("app"):
        named = apps_named(task, view["apps"])
        if len(named) == 1 and named[0] != view["front"]:
            return dict(a, app=named[0])
    if a["action"] in ("open_app", "open_url", "look") and empty({"open_app": "app", "open_url": "url", "look": "target"}[a["action"]]) and listed(a.get("id")):
        return dict(a, action="click")
    if a["action"] == "menu" and empty("path"):
        if not empty("text"):
            return {k: v for k, v in dict(a, path=a["text"]).items() if k != "text"}
        if listed(a.get("id")):
            return dict(a, action="click")
    if a["action"] == "key" and empty("keys") and not (empty("text") and empty("target")):
        return {k: v for k, v in dict(a, keys=str(a.get("text") or a.get("target")).strip().lower().replace(" ", "")).items() if k != "text"}
    if a["action"] in ("click", "double_click", "right_click") and a.get("id") is not None and not listed(a["id"]) and not empty("target"):
        return {k: v for k, v in a.items() if k != "id"}
    return a


def missing(a, view):
    """Exactly what an unusable step lacks, for the planner to read (Repair.missing); None when it can be carried out."""
    empty = lambda k: not str(a.get(k) or "").strip()
    n = len(view["controls"])
    rng = "Controls is empty" if not n else f"the ids go from 1 to {n}"
    act = a["action"]
    if a.get("id") is not None and by_id(view, a["id"]) is None and act in ("click", "double_click", "right_click", "type"):
        return f"there is no control {a['id']} in Controls; {rng}"
    if act == "open_app" and empty("app"):
        return "open_app needs the app's name in app"
    if act == "open_url" and empty("url"):
        return "open_url needs the address in url"
    if act in ("click", "double_click", "right_click") and a.get("id") is None and empty("target"):
        return f"{act} needs the id of a control from Controls"
    if act == "type" and empty("text"):
        return "type needs the text in text"
    if act == "key" and empty("keys"):
        return "key needs keys, like cmd+n or return"
    if act == "menu" and empty("path"):
        return "menu needs the path, like File > New Window"
    if act == "look" and empty("target"):
        return "look needs a target in words"
    if act == "drag" and ((a.get("id") is None and empty("target")) or empty("target_end")):
        return "drag needs where it starts (id or target) and target_end"
    return None


class StepBudget:
    """Counts steps that had no effect (the assistant's StepBudget): the very same step right after it changed nothing
    is not carried out; a fourth scroll in a row is not; after two clicks (or scrolls) without effect no more of that
    kind until a step of another kind has had an effect. Three refusals in a row end the task."""

    def __init__(self):
        self.last_key, self.last_changed, self.ineffective, self.scrolls, self.refusals = "", True, {}, 0, 0

    @staticmethod
    def kind(action):
        return "click" if action in ("click", "double_click", "right_click", "look") else action

    @staticmethod
    def key(a):
        return "\x01".join("" if a.get(k) is None else str(a.get(k)) for k in ("action", "id", "target", "target_end", "text", "keys", "path", "direction", "app", "url"))

    def refusal(self, a):
        kind, why = self.kind(a["action"]), None
        if self.key(a) == self.last_key and not self.last_changed:
            why = "the same step changed nothing just before; do something different"
        elif kind == "scroll" and self.scrolls >= 3:
            why = "scrolled 3 times in a row; press a control from Controls, use menu or key, or look for what you need"
        elif kind in ("scroll", "click") and self.ineffective.get(kind, 0) >= 2:
            why = f"{'scrolling' if kind == 'scroll' else 'clicking'} has changed nothing {self.ineffective[kind]} times; use a different kind of step (key, menu, type, open_app)"
        if why:
            self.refusals += 1
        return why

    def record(self, a, changed):
        kind = self.kind(a["action"])
        self.last_key, self.last_changed, self.refusals = self.key(a), changed, 0
        self.scrolls = self.scrolls + 1 if kind == "scroll" else 0
        if not changed:
            self.ineffective[kind] = self.ineffective.get(kind, 0) + 1
        elif kind in ("scroll", "click"):
            self.ineffective[kind] = 0
        else:
            self.ineffective = {}


def vote_key(a):
    """What two answers must share to count as the same step (the words of a done sentence or a look target are free)."""
    return "\x01".join("" if a.get(k) is None else str(a.get(k)).strip().lower() for k in ("action", "id", "keys", "path", "direction", "app", "url")) + ("\x01" + str(a.get("text", "")) if a["action"] == "type" else "")


def rollout_app(env, ep, chat, oracle_rows_=None, pointer=None, max_new_tokens=160, system=None, resample=False, vote=False):
    """A planner on one task with the assistant's rules around it (build b336837). Mirrored:
      (e) before the first call, an app that is the only one the task names and is not in front is opened;
      (c) an unusable call is put right where there is no doubt, otherwise the planner is told what is missing
          (three in a row end the task);
      (a) a `done` whose sentence says more is needed or gives up is not counted: asked once more; said again,
          the task ends as not finished;
      (d) before a counted `done`, Return is pressed when the last step typed into a one-line field without it;
      (b) the step budget (StepBudget); and the two loop rules (no second Return in a row; a click or look without
          effect once more before it is marked).
    vote: at every turn three answers are drawn and the step two of them share is taken (the greedy one otherwise).
    resample: a rule the assistant does not have: when the answer is the step that just changed nothing, ask again at
    temperature 0.7 up to three times and take the first different answer. The app's limit of 15 steps applies."""
    by_state = {}
    for row in (oracle_rows_ or []):
        by_state.setdefault(row["state"], []).append(row)

    def oracle_step(fp, view):
        rows = by_state.get(fp) or []
        now = [(c["role"], c["name"], c.get("value", "")) for c in public(view)]
        for row in rows:
            if [(c["role"], c["name"], c.get("value", "")) for c in row["controls"]] == now:
                return row, relabel(row, view)
        for row in rows:
            if row["answer"]["action"] != "scroll" and row["answer"].get("id") is not None and relabel(row, view):
                return row, relabel(row, view)
        return (rows[0], relabel(rows[0], view)) if rows else (None, None)
    env.reset(base.clone(ep.state))
    init = env.state()
    done, turns, finished, gave_up, said, ending = [], [], False, False, None, "out of steps"
    asked_again, unusable, pressed_return, refused_returns, budget, last, last_changed, counts = False, 0, False, 0, StepBudget(), None, False, collections_counter()
    view = controls(env)
    named = apps_named(ep.request, view["apps"])
    if len(named) == 1 and named[0] != view["front"]:
        if execute(env, {"action": "open_app", "app": named[0]}, view)[0]:
            done.append(f"open_app {named[0]}")
            counts["opened_first"] += 1
    for k in range(MAX_STEPS):
        view = controls(env)
        st = env.state()
        fp = fingerprint(st, view["key"])
        messages = [{"role": "system", "content": system or SYSTEM}, {"role": "user", "content": user_text(ep.request, view["apps"], view["front"], view["front"], done, view["controls"])}]
        orow, want = oracle_step(fp, view)
        if want is None and ep.kind == "act" and ep.check(st, init)[0]:
            want = {"action": "done", "text": "Done."}
        if hasattr(chat, "peek"):
            chat.peek(view, want, last, last_changed)          # a scripted planner looks at the oracle's step for this state
        msg = chat(messages, [TOOL], max_new_tokens)
        a = parse(msg)
        repeat = a is not None and last is not None and not last_changed and StepBudget.key(a) == StepBudget.key(last)      # the dead step again
        if vote:                                             # a vote of three: the greedy answer and two drawn at temperature 0.6
            extra = chat(messages, [TOOL], max_new_tokens, 0.6, 2)
            cands = [a, parse(extra)] + [parse({"raw": text}) for text in (extra.get("more") or [])]
            keys = [vote_key(c) if c else None for c in cands]
            top = collections_counter()
            top.update(k for k in keys if k is not None)
            best = top.most_common(1)
            counts["votes"] += 1
            if best and best[0][1] >= 2:
                if best[0][0] != keys[0]:
                    a = next(c for c, key in zip(cands, keys) if key == best[0][0])
                    counts["vote_changed"] += 1
            else:
                counts["vote_no_agreement"] += 1
        if resample and a is not None and last is not None and not last_changed and StepBudget.key(a) == StepBudget.key(last):
            for _ in range(3):
                again = chat(messages, [TOOL], max_new_tokens, 0.7)
                b = parse(again)
                counts["resampled"] += 1
                if b is not None and StepBudget.key(b) != StepBudget.key(last):
                    a, msg = b, again
                    counts["resample_differs"] += 1
                    break
        turn = {"k": k + 1, "front_app": view["front"], "apps": view["apps"], "done": list(done), "controls": public(view), "raw": str(msg.get("raw") or msg.get("content") or "")[:600], "answer": a,
                "oracle": want, "oracle_known": want is not None, "agrees": same_step(a, want) if want else None, "seconds": msg.get("seconds"), "repeat": bool(repeat)}
        turns.append(turn)
        if a is not None:
            a = repair(a, view, ep.request)
            if a != turn["answer"]:
                turn["repaired"] = a
                counts["repaired"] += 1
        why = "no next_step call could be read" if a is None else missing(a, view)
        if why:
            done.append((a["action"] if a else "an answer") + f" (not carried out: {why})")
            turn.update(valid=False, changed=False, rule="unusable")
            unusable += 1
            counts["unusable"] += 1
            if unusable >= 3:
                ending = "three unusable answers in a row"
                break
            continue
        unusable = 0
        control = by_id(view, a.get("id")) if a.get("id") is not None else None
        line = done_line(a, control)
        if a["action"] == "done":
            text = str(a.get("text", "")).strip()
            turn.update(valid=True, changed=False)
            if unfinished(text):
                counts["done_unfinished"] += 1
                if not asked_again:
                    asked_again, turn["rule"] = True, "done not counted: asked once more"
                    continue
                gave_up, said, ending = True, text, "not finished"
                break
            if last is not None and last["action"] == "type" and not str(last.get("text", "")).endswith("\n") and last_changed and env.page.evaluate(ONE_LINE_JS):
                env.step({"type": "key", "keys": "enter"})
                turn["rule"] = "Return pressed before done"
                counts["return_before_done"] += 1
            finished, said, ending = True, text, "done"
            break
        is_return = a["action"] == "key" and env_keys(a.get("keys")) == "enter"
        if is_return and pressed_return:
            refused_returns += 1
            counts["return_refused"] += 1
            turn.update(valid=True, changed=False, rule="second Return not pressed")
            done.append(line + " (not pressed: the step before already pressed Return)")
            if refused_returns >= 2:
                ending = "kept asking for Return"
                break
            continue
        why = budget.refusal(a)
        if why:
            done.append(line + f" (not carried out: {why})")
            turn.update(valid=True, changed=False, rule="refused: " + why.split(";")[0])
            counts["refused"] += 1
            if budget.refusals >= 3:
                ending = "kept repeating steps that have no effect"
                break
            continue
        hint = None
        if pointer is None and orow is not None and want and a["action"] in ("look", "drag") and want["action"] == a["action"]:
            if a["action"] == "look" or a.get("id") in (None, want.get("id")):
                hint = orow.get("hint")
        try:
            ok, c = execute(env, a, view, hint=hint, pointer=pointer)
        except Exception as err:
            ok, c = False, None
            turn["error"] = f"{type(err).__name__}: {err}"[:200]
        pressed_return, refused_returns = is_return or (a["action"] == "type" and str(a.get("text", "")).endswith("\n")), 0
        changed = seen(controls(env)) != seen(view)
        if ok and not changed and a["action"] in ("click", "double_click", "right_click", "look"):
            try:
                execute(env, a, view, hint=hint, pointer=pointer)
            except Exception:
                pass
            changed, turn["again"] = seen(controls(env)) != seen(view), True
            counts["once_more"] += 1
            counts["once_more_changed"] += changed
        turn.update(valid=bool(ok), changed=changed)
        done.append(line + ("" if changed else " (nothing changed)"))
        budget.record(a, changed)
        last, last_changed = a, changed
    final = env.state()
    ok, why = ep.check(final, init)
    if ep.kind == "infeasible":
        ok, why = (ok and (finished or gave_up)), (why if not ok else "" if (finished or gave_up) else "did not say done")
    elif ep.kind != "act":
        ok, why = (ok and finished), (why if not ok else "" if finished else "did not say done")
    elif ok and not finished:
        ok, why = False, "the goal was reached but the model never said done"
    return {"task": ep.task, "seed": ep.seed, "app": ep.app, "category": ep.category, "kind": ep.kind, "request": ep.request, "ok": bool(ok), "why": why, "finished": finished, "gave_up": gave_up, "said": said, "ending": ending,
            "steps": len(turns), "limit": MAX_STEPS, "stuck": ending in ("kept repeating steps that have no effect", "three unusable answers in a row", "kept asking for Return"), "rules": dict(counts),
            "invalid": sum(not t.get("valid", True) for t in turns), "unchanged": sum(t.get("valid") and not t.get("changed") and (t["answer"] or {}).get("action") != "done" for t in turns),
            "oracle_known": sum(t["oracle_known"] for t in turns), "agrees": sum(bool(t["agrees"]) for t in turns), "turns": turns, "errors": env.errors()[:3]}


def collections_counter():
    import collections
    return collections.Counter()


class NoisyOracle:
    """A scripted planner for training rows that carry the assistant's feedback lines: it takes the oracle's step,
    and now and then (rate, at most `most` times an episode) a wrong one of the kinds a planner makes: the last step
    again, a click on another control, a scroll, a control number that does not exist, a call with its argument
    missing. The assistant's loop answers as it would to a model; the oracle's step from the state reached is the
    label. When a wrong step changes the task's state the oracle no longer knows the way and the episode ends."""

    def __init__(self, rng, rate=0.3, most=3):
        self.rng, self.rate, self.left, self.injected = rng, rate, most, 0

    def peek(self, view, want, last, last_changed):
        self.view, self.want, self.last = view, want, last

    def __call__(self, messages, tools, k, temperature=None):
        a = self.want
        if a is None:
            a = {"action": "done", "text": "I could not find a way to finish this."}
        elif self.left > 0 and self.rng.random() < self.rate:
            a, self.left, self.injected = self.wrong(), self.left - 1, self.injected + 1
        return {"tool_calls": [{"function": {"name": "next_step", "arguments": a}}], "raw": "noisy oracle"}

    def wrong(self):
        r, cs = self.rng, self.view["controls"]
        kind = r.choices(["repeat", "other", "scroll", "no_such_id", "missing"], [3 if self.last else 0, 3 if cs else 0, 1, 1, 1])[0]
        if kind == "repeat":
            return dict(self.last)
        if kind == "other":
            calm = [c for c in cs if c["role"] in ("text field", "text area") or c.get("value") == "selected"] or cs
            c = r.choice(calm if r.random() < 0.7 else cs)
            return {"action": "click", "id": c["n"]}
        if kind == "scroll":
            return {"action": "scroll", "direction": r.choice(["down", "down", "up"])}
        if kind == "no_such_id":
            return {"action": r.choice(["click", "click", "type"]), "id": len(cs) + r.randint(1, 9), **({"text": "x"} if r.random() < 0.3 else {})}
        return {"action": r.choice(["open_app", "menu", "key", "look", "type"])}
