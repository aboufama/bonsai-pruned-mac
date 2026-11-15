"""One computer-use action per step: cases from recorded trajectories, chat samples, a scorer.

The loop we train for: the model sees a screenshot, the goal and a short history, and answers with
ONE call of the `computer_use` tool; the harness executes it and takes the next screenshot.
docs/ACTION_FORMAT.md says where the schema comes from: the Qwen family's own `computer_use`
function, plus `start_coordinate` so that a drag is one call with both ends.

    case     {"id", "image", "width", "height", "goal", "history": [...], "action": {"name",
             "arguments"}, "split", "app", "meta"}. Points are in pixels of the recorded screenshot.
    sample   action_case(case): what TaskTuner, chat.score and chat.generate take ("kind": "action_call")
    answer   the text a model generated; parse_answer() reads it, score_answer() judges it

A sample carries a screenshot, which the tool-call branch of chat.supervise cannot pass on (it builds
text-only messages). So this module has its own supervise() with the same return value, and install()
makes chat.supervise hand action samples to it, in the running process only. action_case() calls
install(); without it chat.supervise stops with KeyError 'messages' instead of training blind.

The cases come from AgentNet's macOS trajectories (docs/MAC_DATA.md). On the Spark, CPU only:

    python weightlab/actions.py convert --raw ~/bonsai/data/mac/raw/agentnet \\
        --out ~/bonsai/data/mac/agentnet/cases_actions.jsonl \\
        --pointing ~/bonsai/data/mac/agentnet/cases.jsonl
    python weightlab/actions.py need --raw ~/bonsai/data/mac/raw/agentnet \\
        --cases ~/bonsai/data/mac/agentnet/cases_actions.jsonl --out ~/bonsai/data/mac/raw/agentnet_actions_fetch

`convert` writes one case per step that is exactly one action (and stats_actions.json beside it).
`need` lists the screenshots of those cases that are not on disk yet, in the folder layout
data/mac/scripts/agentnet_fetch.py reads; it downloads nothing itself.
"""
import ast
import collections
import hashlib
import json
import math
import os
import random
import re
import sys

try:
    from . import chat
except ImportError:                                # run as a plain script: the converter needs no lab code
    chat = None

TOOL = "computer_use"
KIND = "action_call"
STEP_TOOL = "next_step"       # the orchestrator's tool: the next step in words, no coordinates
STEP_KIND = "step_call"
GRID = 1000                   # the family's screen: "The screen's resolution is 1000x1000"
TOL_PX = 24                   # scoring: a point counts within this distance of the recorded point
POINT_TOL = 0.012             # training: half-width of the accepted band, share of image width (as core.POINT_TOL)
HISTORY_N = 8                 # previous steps shown to the model
HISTORY_KEEP = 20             # previous steps stored with a case
MAX_SIDE = 1280
RESERVED_MOD = 10             # a trajectory is reserved for testing when sha1(task_id) % 10 == 0
POINTING_TEST_MOD = 50        # the pointing set (data/mac/agentnet/cases.jsonl) tests on sha1(task_id) % 50 == 0
DIGIT0 = 15                   # token ids 15..24 are the digits 0..9

CLICKS = ("left_click", "double_click", "right_click", "triple_click", "middle_click")
POINTS = CLICKS + ("mouse_move",)
SCROLLS = ("scroll", "hscroll")
ACTIONS = ("key", "type", "mouse_move", "left_click", "left_click_drag", "right_click", "middle_click",
           "double_click", "triple_click", "scroll", "hscroll", "wait", "terminate", "answer")
ORDER = ("start_coordinate", "coordinate", "keys", "text", "pixels", "time", "status")   # arguments, as written

# The Qwen family's function (Qwen3-VL cookbook, cookbooks/utils/agent_function_call.py), with three
# changes listed in docs/ACTION_FORMAT.md: `start_coordinate`, a newline that ends typed text, "macOS".
COMPUTER_USE_TOOL = {"type": "function", "function": {
    "name": TOOL,
    "description": (
        "Use a mouse and keyboard to interact with a computer, and take screenshots.\n"
        "* This is an interface to a macOS desktop.\n"
        "* Some applications may take time to start or process actions, so you may need to wait and take "
        "successive screenshots to see the results of your actions.\n"
        f"* The screen's resolution is {GRID}x{GRID}.\n"
        "* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. "
        "Don't click boxes on their edges unless asked."),
    "parameters": {"type": "object", "required": ["action"], "properties": {
        "action": {"type": "string", "enum": list(ACTIONS), "description": (
            "The action to perform. The available actions are:\n"
            "* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order.\n"
            "* `type`: Type a string of text on the keyboard.\n"
            "* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.\n"
            "* `left_click`: Click the left mouse button at a specified (x, y) pixel coordinate on the screen.\n"
            "* `left_click_drag`: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.\n"
            "* `right_click`: Click the right mouse button at a specified (x, y) pixel coordinate on the screen.\n"
            "* `middle_click`: Click the middle mouse button at a specified (x, y) pixel coordinate on the screen.\n"
            "* `double_click`: Double-click the left mouse button at a specified (x, y) pixel coordinate on the screen.\n"
            "* `triple_click`: Triple-click the left mouse button at a specified (x, y) pixel coordinate on the screen.\n"
            "* `scroll`: Performs a scroll of the mouse scroll wheel.\n"
            "* `hscroll`: Performs a horizontal scroll.\n"
            "* `wait`: Wait specified seconds for the change to happen.\n"
            "* `terminate`: Terminate the current task and report its completion status.\n"
            "* `answer`: Answer a question.")},
        "keys": {"type": "array", "description": "Required only by `action=key`."},
        "text": {"type": "string", "description": "Required only by `action=type` and `action=answer`. "
                                                  "A newline at the end of typed text presses Return."},
        "start_coordinate": {"type": "array", "description": "(x, y): Where a drag starts. Only for `action=left_click_drag`; "
                                                             "without it the drag starts at the current cursor position."},
        "coordinate": {"type": "array", "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) "
                                                       "coordinates to move the mouse to."},
        "pixels": {"type": "number", "description": "The amount of scrolling to perform. Positive values scroll up, negative values "
                                                    "scroll down. Required only by `action=scroll` and `action=hscroll`."},
        "time": {"type": "number", "description": "The seconds to wait. Required only by `action=wait`."},
        "status": {"type": "string", "enum": ["success", "failure"],
                   "description": "The status of the task. Required only by `action=terminate`."}}}}}

REQUEST = ("\nPlease generate the next move according to the UI screenshot, instruction and previous actions.\n\n"
           "Instruction: {goal}\n\nPrevious actions:\n{history}")        # the wording of the Qwen agents


# ------------------------------------------------------------------ coordinates, keys, history lines
def to_grid(v, size):
    """A pixel position as the integer the model writes: 0..999 on the 1000-wide screen."""
    return max(0, min(GRID - 1, round(GRID * v / size)))


def on_grid(arguments, width, height):
    """Arguments with every point moved from pixels to the grid."""
    return {k: ([to_grid(v[0], width), to_grid(v[1], height)] if k in ("coordinate", "start_coordinate") else v)
            for k, v in arguments.items()}


def to_pixels(arguments, width, height):
    """Arguments of a parsed answer with every point moved from the grid to pixels (for the harness and the scorer)."""
    return {k: ([v[0] * width / GRID, v[1] * height / GRID] if k in ("coordinate", "start_coordinate") else v)
            for k, v in arguments.items()}


MODIFIERS = ("cmd", "ctrl", "alt", "shift", "fn")
KEY_ALIASES = {"command": "cmd", "meta": "cmd", "super": "cmd", "win": "cmd", "control": "ctrl", "option": "alt",
               "opt": "alt", "return": "enter", "escape": "esc", "del": "delete", "pgup": "pageup", "pgdn": "pagedown",
               "page_up": "pageup", "page_down": "pagedown", "caps_lock": "capslock", "spacebar": "space"}
NAMED_KEYS = ({"enter", "backspace", "space", "tab", "esc", "delete", "up", "down", "left", "right", "home", "end",
               "pageup", "pagedown", "capslock", "media_volume_up", "media_volume_down", "media_volume_mute"}
              | {f"f{i}" for i in range(1, 13)})


def norm_keys(keys):
    """Key names in one spelling, modifiers first: ["Command", "s"] -> ["cmd", "s"]. A lone capital
    letter is kept as written, because pressing it is not pressing the plain letter."""
    if isinstance(keys, str):
        keys = re.split(r"\s*\+\s*", keys.strip()) if len(keys.strip()) > 1 else [keys]
    names = []
    for k in keys:
        k = str(k).strip() if len(str(k)) > 1 else str(k)
        k = k.lower() if len(k) > 1 or not k.isupper() else k          # a lone capital stays: it is not the plain letter
        names.append(KEY_ALIASES.get(k, k))
    return [m for m in MODIFIERS if m in names] + [k for k in names if k not in MODIFIERS]


def valid_keys(keys):
    """A shortcut we can state exactly: any modifiers and one other key, all with known names."""
    rest = [k for k in keys if k not in MODIFIERS]
    return (len(rest) == 1 and len(set(keys)) == len(keys)
            and (rest[0] in NAMED_KEYS or (len(rest[0]) == 1 and rest[0].isascii() and rest[0].isprintable()
                                           and not rest[0].isupper() and rest[0] != " ")))


def describe(name, arguments, repeat=1):
    """The history line for an executed action. Points must already be on the grid (see on_grid).
    The harness has to build its history with this function too, so that use matches training."""
    a = arguments
    at = lambda p: f"[{p[0]}, {p[1]}]"
    if name in POINTS:
        line = f"{name} {at(a['coordinate'])}"
    elif name == "left_click_drag":
        line = f"{name} {at(a['start_coordinate'])} to {at(a['coordinate'])}" if "start_coordinate" in a else f"{name} to {at(a['coordinate'])}"
    elif name in SCROLLS:
        line = f"{name} {a.get('pixels', 0)}" + (f" at {at(a['coordinate'])}" if "coordinate" in a else "")
    elif name in ("type", "answer"):
        text = a.get("text", "")
        line = f"{name} " + json.dumps(text if len(text) <= 80 else text[:77] + "...", ensure_ascii=False)
    elif name == "key":
        line = "key " + "+".join(a.get("keys", []))
    elif name == "wait":
        line = f"wait {a.get('time', '')}".rstrip()
    elif name == "terminate":
        line = f"terminate {a.get('status', '')}".rstrip()
    else:
        line = name
    return line + (f" x{repeat}" if repeat > 1 else "")


def request_text(goal, history, first=1, history_n=HISTORY_N):
    """The user's text: the goal and the last `history_n` steps. `first` is the number of history[0]."""
    lines = [f"Step {first + i}: {h}" for i, h in enumerate(history)][-history_n:] if history_n else []
    return REQUEST.format(goal=goal.strip(), history="\n".join(lines) if lines else "None")


# ------------------------------------------------------------------ rendering a case as a chat sample
def render(name, arguments, width, height, tol=POINT_TOL):
    """(call text, pieces). pieces = [[text, None] or [digits, [lo, hi]]]: the call cut at every
    coordinate, with the range of values that still land near the recorded point."""
    grid = on_grid(arguments, width, height)
    call = {"action": name}
    call.update({k: grid[k] for k in ORDER if k in grid})
    text = chat.render_call(TOOL, call)
    band = tol * width * (4 if name in SCROLLS else 1)                  # where to scroll is a loose target
    pieces = [[f"<tool_call>\n<function={TOOL}>\n<parameter=action>\n{name}\n</parameter>\n", None]]
    for k in ORDER:
        if k not in grid:
            continue
        if k in ("coordinate", "start_coordinate"):
            (px, py), (gx, gy) = arguments[k], grid[k]
            pieces += [[f"<parameter={k}>\n[", None],
                       [str(gx), [GRID * (px - band) / width, GRID * (px + band) / width]], [", ", None],
                       [str(gy), [GRID * (py - band) / height, GRID * (py + band) / height]], ["]\n</parameter>\n", None]]
        else:
            v = grid[k] if isinstance(grid[k], str) else json.dumps(grid[k], ensure_ascii=False)
            pieces.append([f"<parameter={k}>\n{v}\n</parameter>\n", None])
    pieces.append(["</function>\n</tool_call>", None])
    merged = []
    for t, b in pieces:
        if b is None and merged and merged[-1][1] is None:
            merged[-1][0] += t
        else:
            merged.append([t, b])
    assert "".join(t for t, _ in merged) == text, "the pieces do not add up to the rendered call"
    return text, merged


def action_case(case, base=None, history_n=HISTORY_N, max_side=MAX_SIDE, tol=POINT_TOL, rng=None):
    """A case as a chat sample: tool_case's fields (id, tools, category, kind, target) and, like
    point_call, the screenshot as `item` with `system` and `request`. Deterministic per case.
    `base` is the folder that relative image paths start from (the folder of cases_actions.jsonl)."""
    install()
    rng = rng or random.Random(case["id"])
    name, arguments = case["action"]["name"], case["action"]["arguments"]
    target, pieces = render(name, arguments, case["width"], case["height"], tol)
    history = case.get("history") or []
    first = (case.get("meta") or {}).get("step", len(history)) - len(history) + 1
    return {"kind": KIND, "id": case["id"], "category": f"action:{name}", "tools": [COMPUTER_USE_TOOL],
            "system": rng.choice(chat.SYSTEMS), "request": request_text(case["goal"], history, first, history_n),
            "target": target, "pieces": pieces, "case": case, "item": _item(case, base, max_side)}


def _item(case, base, max_side):
    """The screenshot of a case the way lab.image() takes it."""
    path = case["image"] if base is None or os.path.isabs(case["image"]) else os.path.normpath(os.path.join(base, case["image"]))
    return {"id": case["id"], "path": path, "max_side": max_side, "size": (case["width"], case["height"])}


def family_drag(case):
    """A drag case as the two steps of the family schema: mouse_move to the start, then
    left_click_drag to the end. Both keep the recorded screenshot (there is no second one)."""
    a = case["action"]["arguments"]
    if case["action"]["name"] != "left_click_drag" or "start_coordinate" not in a:
        return [case]
    move = dict(case, id=case["id"] + "-move", action={"name": "mouse_move", "arguments": {"coordinate": a["start_coordinate"]}})
    line = describe("mouse_move", on_grid(move["action"]["arguments"], case["width"], case["height"]))
    drag = dict(case, id=case["id"] + "-drag", history=list(case.get("history") or []) + [line],
                action={"name": "left_click_drag", "arguments": {"coordinate": a["coordinate"]}},
                meta=dict(case.get("meta") or {}, step=(case.get("meta") or {}).get("step", len(case.get("history") or [])) + 1))
    return [move, drag]


def supervise(lab, model, sample):
    """chat.supervise for an action sample: (inputs, spans, allowed, places). Coordinate digits accept
    every digit that keeps the point near the recorded one; every other token is exact."""
    tok = lab.processor.tokenizer
    messages = [{"role": "system", "content": [{"type": "text", "text": sample["system"]}]},
                {"role": "user", "content": [{"type": "image", "image": lab.image(sample["item"])},
                                             {"type": "text", "text": sample["request"]}]}]
    inputs = lab.processor.apply_chat_template(messages, tools=sample["tools"], add_generation_prompt=True, tokenize=True,
                                               return_dict=True, return_tensors="pt",
                                               enable_thinking=bool(sample.get("thinking"))).to(model.device)
    start = inputs["input_ids"].shape[1]
    pieces = [list(p) for p in sample["pieces"]]
    pieces[-1][0] += "<|im_end|>"
    allowed, places = [], []
    for text, band in pieces:
        ids = tok(text, add_special_tokens=False)["input_ids"]
        if band is None:
            allowed += [[i] for i in ids]
            places += [None] * len(ids)
        else:
            assert len(ids) == len(text) and all(DIGIT0 <= i < DIGIT0 + 10 for i in ids), "a coordinate was not tokenised digit by digit"
            for c, ok in zip(text, chat._digit_sets(text, band[0], band[1])):
                written = DIGIT0 + int(c)                               # first, so chat.score's per-token loss reads it
                allowed.append([written] + [i for i in ok if i != written])
            places += [("units", "tens", "hundreds", "thousands")[len(text) - 1 - d] for d in range(len(text))]
    n = lab._append(inputs, "".join(t for t, _ in pieces))
    assert n == len(allowed), f"piecewise tokenisation ({len(allowed)}) differs from the whole answer ({n})"
    return inputs, [(start, n)], allowed, places


def install():
    """Make chat.supervise pass action samples to supervise() above. Every other sample goes to the
    original function untouched. Reloading chat (weightlab.hot) undoes this; action_case() redoes it."""
    if chat is None:
        raise RuntimeError("weightlab.actions was run as a script; import it as weightlab.actions to build samples")
    if getattr(chat.supervise, "_takes_actions", False):
        return
    original = chat.supervise

    def supervise_any(lab, model, sample):
        if sample.get("kind") in (KIND, STEP_KIND):
            return sys.modules[__name__].supervise(lab, model, sample)
        return original(lab, model, sample)

    supervise_any._takes_actions = True
    supervise_any.__doc__ = original.__doc__
    chat.supervise = supervise_any


def generate(lab, model, sample, max_new_tokens=128):
    """Let the model answer an action sample. Returns (text, parsed action or None)."""
    install()
    text, _ = chat.generate(lab, model, sample, max_new_tokens=max_new_tokens)
    return text, parse_answer(text)


# ------------------------------------------------------------------ reading and scoring an answer
def _call_arguments(text, tool):
    """The parameters of the first call of `tool` in a generated answer, values as written (text or
    JSON); None if there is no such call. Reads the Qwen3.5 form exactly as the chat template writes
    it (one newline around each value is the template's, anything more is the value's), and the
    older JSON form {"name": tool, "arguments": {...}} too."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.search(rf"<function={tool}>(.*?)(?:</function>|$)", text, flags=re.S)
    if m:
        raw = {}
        for k, v in re.findall(r"<parameter=([^>\n]+)>(.*?)</parameter>", m.group(1), flags=re.S):
            v = v[1:] if v.startswith("\n") else v
            raw[k.strip()] = v[:-1] if v.endswith("\n") else v
        return raw
    m = re.search(r"\{.*\}", text, flags=re.S)
    try:
        obj = json.loads(m.group(0)) if m else None
    except ValueError:
        obj = None
    if isinstance(obj, dict) and obj.get("name") == tool and isinstance(obj.get("arguments"), dict):
        return obj["arguments"]
    return None


def parse_answer(text):
    """The first computer_use call in a generated answer as {"name", "arguments"}, points still on
    the grid; None if there is no such call."""
    raw = _call_arguments(text, TOOL)
    if raw is None:
        return None
    name = str(raw.get("action", "")).strip()
    if not name:
        return None
    arguments = {}
    for k, v in raw.items():
        if k == "action":
            continue
        if k == "text":
            arguments[k] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            continue
        if isinstance(v, str):
            try:
                v = json.loads(v.strip())
            except ValueError:
                v = v.strip()
        if k in ("coordinate", "start_coordinate"):
            if not (isinstance(v, list) and len(v) == 2 and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v)):
                continue                                               # an unreadable point is a missing point
        arguments[k] = v
    return {"name": name, "arguments": arguments}


def score_answer(case, answer, tol_px=TOL_PX):
    """Judge one answer (text, or an action from parse_answer) against a case.

    AgentNet records the point a person clicked, not the element's box, so a point counts when it
    is within `tol_px` of the recorded point, in pixels of the recorded screenshot.
      clicks, mouse_move   name, and the point
      left_click_drag      name, and both ends (a missing start_coordinate fails)
      type                 name, and the text exactly (a final newline is part of it)
      key                  name, and the same keys after norm_keys
      scroll, hscroll      name, and the direction
      terminate            name, and the status
      wait, answer         name
    Returns {"ok", "name_ok", "parsed", "expected", "got", "dist" (px, one per point), "why"}."""
    got = parse_answer(answer) if isinstance(answer, str) else answer
    want, wa = case["action"]["name"], case["action"]["arguments"]
    r = {"ok": False, "name_ok": False, "parsed": got is not None, "expected": want, "got": got and got["name"], "dist": [], "why": ""}
    if got is None:
        r["why"] = "no computer_use call"
        return r
    r["name_ok"] = got["name"] == want
    if not r["name_ok"]:
        r["why"] = "another action"
        return r
    ga = to_pixels(got["arguments"], case["width"], case["height"])
    points = [k for k in ("start_coordinate", "coordinate") if k in wa] if want in POINTS + ("left_click_drag",) else []
    for k in points:
        if k not in ga:
            r["why"] = f"{k} missing"
            return r
        r["dist"].append(round(math.hypot(ga[k][0] - wa[k][0], ga[k][1] - wa[k][1]), 1))
    if any(d > tol_px for d in r["dist"]):
        r["why"] = "point too far"
    elif want == "type" and ga.get("text") != wa.get("text"):
        r["why"] = "other text"
    elif want == "key" and (not isinstance(ga.get("keys"), (list, str))
                            or [k.lower() for k in norm_keys(ga["keys"])] != [k.lower() for k in norm_keys(wa["keys"])]):
        r["why"] = "other keys"
    elif want in SCROLLS and not (isinstance(ga.get("pixels"), (int, float)) and ga["pixels"] * wa["pixels"] > 0):
        r["why"] = "other direction"
    elif want == "terminate" and ga.get("status") != wa.get("status"):
        r["why"] = "other status"
    else:
        r["ok"] = True
    return r


def score_answers(cases, answers, tol_px=TOL_PX):
    """Totals over many cases: share correct, share with the right action name, and both per action."""
    rows = [score_answer(c, a, tol_px) for c, a in zip(cases, answers)]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["expected"]].append(r)
    share = lambda rs, key: round(sum(r[key] for r in rs) / len(rs), 4) if rs else None
    dist = sorted(d for r in rows for d in r["dist"])
    return {"n": len(rows), "correct": share(rows, "ok"), "name": share(rows, "name_ok"), "parsed": share(rows, "parsed"),
            "median_dist_px": dist[len(dist) // 2] if dist else None, "tol_px": tol_px,
            "by_action": {k: {"n": len(v), "correct": share(v, "ok"), "name": share(v, "name_ok")} for k, v in sorted(by.items())},
            "why": dict(collections.Counter(r["why"] for r in rows if not r["ok"]))}


# ------------------------------------------------------------------ loading cases for training and tests
DEFAULT_SHARE = {"left_click": 0.34, "left_click_drag": 0.16, "type": 0.16, "key": 0.10, "scroll": 0.09, "terminate": 0.06,
                 "double_click": 0.04, "right_click": 0.03, "triple_click": 0.01, "hscroll": 0.01}


def load_cases(path, split=None, on_disk=True, never_trained=False):
    """Cases of cases_actions.jsonl; `split` is "train" or "reserved". With on_disk, only cases whose
    screenshot file exists (the screenshots of some action types are fetched separately). With
    never_trained, only trajectories that are test sessions of the pointing set as well: the part
    of "reserved" whose screens no pointing run can have seen."""
    base, out = os.path.dirname(os.path.abspath(path)), []
    for line in open(path):
        c = json.loads(line)
        if ((split is None or c["split"] == split) and (not never_trained or c["meta"]["pointing_session"] == "test")
                and (not on_disk or os.path.exists(os.path.join(base, c["image"])))):
            out.append(c)
    return out


def pick(cases, n, share=None, seed=10, name=lambda c: c["action"]["name"]):
    """n cases with the given share per action (clicks are 80 % of the recording, far more than we
    want). Actions that have too few cases give their places to the others, in proportion."""
    share = dict(share or DEFAULT_SHARE)
    rng, by = random.Random(seed), collections.defaultdict(list)
    for c in sorted(cases, key=lambda c: c["id"]):
        by[name(c)].append(c)
    for v in by.values():
        rng.shuffle(v)
    out, left = [], n
    while left > 0 and any(by[k] and share.get(k, 0) > 0 for k in by):
        total = sum(share.get(k, 0) for k in by if by[k])
        took = 0
        for k in sorted(by):
            want = min(len(by[k]), left - took, math.ceil(left * share.get(k, 0) / total)) if by[k] else 0
            out += by[k][:want]
            by[k] = by[k][want:]
            took += want
        left -= took
    rng.shuffle(out)
    return out


def samples(lab, split="train", n=3000, share=None, seed=10, never_trained=False, **render_options):
    """Chat samples for training or scoring, from the cases on this machine."""
    path = f"{lab.root}/data/mac/agentnet/cases_actions.jsonl"
    chosen = pick(load_cases(path, split, never_trained=never_trained), n, share, seed)
    return [action_case(c, base=os.path.dirname(path), **render_options) for c in chosen]


# ------------------------------------------------------------------ AgentNet steps -> actions
PYAUTOGUI_CLICKS = {"click": "left_click", "doubleClick": "double_click", "rightClick": "right_click",
                    "tripleClick": "triple_click", "middleClick": "middle_click"}


def _calls(code):
    """The pyautogui / computer calls of a step as (name, args, keyword args). Nothing is executed:
    the code is parsed and only literal values are read."""
    out = []
    for node in ast.parse(code).body:
        call = node.value if isinstance(node, ast.Expr) else None
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
                and call.func.value.id in ("pyautogui", "computer")):
            raise ValueError("not a pyautogui or computer call")
        out.append((call.func.attr, [ast.literal_eval(a) for a in call.args],
                    {k.arg: ast.literal_eval(k.value) for k in call.keywords}))
    return out


def step_actions(code):
    """What a recorded step did, as a list of {"name", "arguments", "repeat"} with points still
    normalised (0-1). A step is usable as a case when this list has one entry with repeat 1.
    Raises ValueError for code that is not understood.

      moveTo + dragTo            one left_click_drag with both ends
      moveTo + scroll / hscroll  one scroll at that point; a swipe on both axes counts as the
                                 larger one when it is at least twice the other
      write + press('enter')     one type whose text ends with a newline
      press(k, presses=n)        key with repeat n (not a single action when n > 1)
    """
    calls, out, i = _calls(code), [], 0
    xy = lambda kw: [float(kw["x"]), float(kw["y"])]
    act = lambda name, repeat=1, **arguments: {"name": name, "arguments": arguments, "repeat": repeat}
    while i < len(calls):
        name, args, kw = calls[i]
        following = calls[i + 1][0] if i + 1 < len(calls) else None
        if name in PYAUTOGUI_CLICKS:
            out.append(act(PYAUTOGUI_CLICKS[name], coordinate=xy(kw)))
        elif name == "moveTo" and following == "dragTo":
            if calls[i + 1][2].get("button", "left") != "left":
                raise ValueError("drag with another button")
            out.append(act("left_click_drag", start_coordinate=xy(kw), coordinate=xy(calls[i + 1][2])))
            i += 1
        elif name == "moveTo" and following in SCROLLS:
            amount = {"scroll": 0, "hscroll": 0}
            while i + 1 < len(calls) and calls[i + 1][0] in SCROLLS:
                amount[calls[i + 1][0]] += calls[i + 1][1][0]
                i += 1
            v, h = amount["scroll"], amount["hscroll"]
            if not v and not h:
                raise ValueError("scroll by nothing")
            if abs(v) >= 2 * abs(h):
                out.append(act("scroll", coordinate=xy(kw), pixels=v))
            elif abs(h) >= 2 * abs(v):
                out.append(act("hscroll", coordinate=xy(kw), pixels=h))
            else:
                out += [act("scroll", coordinate=xy(kw), pixels=v), act("hscroll", coordinate=xy(kw), pixels=h)]
        elif name == "moveTo":
            out.append(act("mouse_move", coordinate=xy(kw)))
        elif name == "write":
            out.append(act("type", text=str(kw["message"] if "message" in kw else args[0])))
        elif name == "press":
            keys = kw["keys"] if "keys" in kw else args[0]
            for k in (keys if isinstance(keys, list) else [keys]):
                out.append(act("key", repeat=int(kw.get("presses", 1)), keys=norm_keys([k])))
        elif name == "hotkey":
            out.append(act("key", keys=norm_keys(args[0] if len(args) == 1 and isinstance(args[0], list) else args)))
        elif name == "terminate":
            status = str(kw.get("status", args[0] if args else ""))
            out.append(act("terminate", status={"fail": "failure", "failed": "failure"}.get(status, status)))
        elif name == "wait":
            out.append(act("wait", time=5))
        else:
            raise ValueError(f"unknown call {name}")
        i += 1
    merged = []
    for a in out:
        if (a["name"] == "key" and a["repeat"] == 1 and a["arguments"]["keys"] == ["enter"] and merged
                and merged[-1]["name"] == "type" and not merged[-1]["arguments"]["text"].endswith("\n")):
            merged[-1]["arguments"]["text"] += "\n"
        else:
            merged.append(a)
    return merged


def _unusable(action, width, height, task_completed):
    """Why a single recorded action is not used as a case; None if it is usable."""
    name, a = action["name"], action["arguments"]
    for k in ("start_coordinate", "coordinate"):
        if k in a and (min(a[k]) <= 0.002 or max(a[k]) >= 0.998):
            return "a point on the screen edge"                        # clamped coordinates, not a target
    if name == "left_click_drag":
        (x0, y0), (x1, y1) = a["start_coordinate"], a["coordinate"]
        if math.hypot((x1 - x0) * width, (y1 - y0) * height) < TOL_PX:
            return f"a drag shorter than {TOL_PX} px"                  # the scorer could not tell it from a click
    if name == "key" and not valid_keys(a["keys"]):
        return "key names not understood"
    if name == "type":
        body = a["text"][:-1] if a["text"].endswith("\n") else a["text"]
        if not body.strip() or len(body) > 300 or any(ord(c) < 32 for c in body):
            return "typed text empty, very long or with control characters"
    if name == "terminate":
        if a["status"] not in ("success", "failure"):
            return "end status not understood"
        if a["status"] == "success" and task_completed is False:
            return "ended as a success in a trajectory judged not completed"
    return None


def _png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def _mac_trajectories(raw):
    """AgentNet's macOS trajectories (meta `system` == "Darwin"), each once, with its meta row."""
    meta = {}
    for line in open(os.path.join(raw, "meta_data_merged.jsonl")):
        m = json.loads(line)
        meta[m["task_id"]] = m
    seen = set()
    for line in open(os.path.join(raw, "agentnet_win_mac_18k.jsonl")):
        t = json.loads(line)
        m = meta.get(t["task_id"])
        if m and m.get("system") == "Darwin" and t["task_id"] not in seen:
            seen.add(t["task_id"])
            yield t, m


def convert(raw, out, pointing=None):
    """AgentNet macOS trajectories -> cases_actions.jsonl. Returns the statistics it also writes.

    One case per step that is exactly one action, not flagged incorrect or redundant by the
    dataset, and passes _unusable(). Every executed step, used or not, becomes a history line of
    the steps after it. The goal is the trajectory's human-written `instruction`.
    Split by trajectory: reserved when sha1(task_id) % 10 == 0, which contains the test sessions
    of the pointing set (sha1 % 50 == 0; meta.pointing_session says which side a trajectory is
    on there). `pointing` is that set's cases.jsonl; it marks cases whose screenshot is also a
    pointing case (meta.pointing = its split). Reserved cases of pointing-train sessions show
    screens that pointing training may have used; those of pointing-test sessions never were.
    """
    images = os.path.join(raw, "images")
    on_disk = set(os.listdir(images))
    out_dir = os.path.dirname(os.path.abspath(out))
    seen_in_pointing = {}
    if pointing:
        for line in open(pointing):
            c = json.loads(line)
            seen_in_pointing[os.path.basename(c["image"])] = c["split"]
    count = collections.Counter()
    by_action = collections.defaultdict(collections.Counter)
    trajectories = collections.defaultdict(set)
    with open(out + ".tmp", "w") as f:
        for t, m in _mac_trajectories(raw):
            count["trajectories"] += 1
            goal = (t.get("instruction") or "").strip()
            digest = int(hashlib.sha1(t["task_id"].encode()).hexdigest(), 16)
            split = "reserved" if digest % RESERVED_MOD == 0 else "train"
            session = "test" if digest % POINTING_TEST_MOD == 0 else "train"      # which side of the pointing set it is on
            steps = sorted(t["traj"], key=lambda s: s["index"])
            sizes = {s["image"]: _png_size(os.path.join(images, s["image"])) for s in steps if s["image"] in on_disk}
            common = collections.Counter(sizes.values()).most_common(1)
            apps = [a for a in (m.get("applications") or []) if a]
            lines = []
            for s in steps:
                count["steps"] += 1
                v = s["value"]
                code = v.get("code") or ""
                try:
                    acts = step_actions(code)
                except (ValueError, SyntaxError, KeyError, IndexError, TypeError):
                    acts = None
                size = sizes.get(s["image"]) or (common[0][0] if common else None)
                if acts is None:
                    why = "code not understood"
                elif len(acts) != 1 or acts[0]["repeat"] != 1:
                    why = "more than one action in the step"
                elif not goal:
                    why = "trajectory without an instruction"
                elif v.get("last_step_correct") is False:
                    why = "flagged incorrect by the dataset"
                elif v.get("last_step_redundant"):
                    why = "flagged redundant by the dataset"
                elif size is None:
                    why = "no screenshot of the trajectory on disk yet (size unknown)"
                else:
                    why = _unusable(acts[0], size[0], size[1], t.get("task_completed"))
                if why is None:
                    name, w, h = acts[0]["name"], size[0], size[1]
                    arguments = {k: ([round(a[0] * w, 1), round(a[1] * h, 1)] if k in ("coordinate", "start_coordinate") else a)
                                 for k, a in acts[0]["arguments"].items()}
                    case = {"id": f"agentnet-{t['task_id']}-s{int(s['index']):03d}-act",
                            "image": os.path.relpath(os.path.join(images, s["image"]), out_dir), "width": w, "height": h,
                            "goal": goal, "history": lines[-HISTORY_KEEP:], "action": {"name": name, "arguments": arguments},
                            "split": split, "app": apps[0] if len(apps) == 1 else ("; ".join(apps) or None),
                            "meta": {"source": "xlangai/AgentNet", "task_id": t["task_id"], "step": len(lines), "steps": len(steps),
                                     "code": code, "sentence": (v.get("action") or "").strip(),
                                     "natural_goal": (t.get("natural_language_task") or "").strip(), "apps": apps,
                                     "websites": m.get("websites") or [], "domain": m.get("domains"),
                                     "task_completed": t.get("task_completed"), "pointing_session": session,
                                     "pointing": seen_in_pointing.get(s["image"])}}
                    f.write(json.dumps(case, ensure_ascii=False) + "\n")
                    have = "on disk" if s["image"] in on_disk else "screenshot not fetched"
                    count["cases"] += 1
                    count[f"cases {split}"] += 1
                    count[f"cases {have}"] += 1
                    by_action[name][split] += 1
                    by_action[name][have] += 1
                    by_action[name][f"{split}, {have}"] += 1
                    trajectories[split].add(t["task_id"])
                    if split == "reserved":
                        count[f"reserved cases, pointing {session} session"] += 1
                        if case["meta"]["pointing"]:
                            count[f"reserved cases, screenshot is a pointing {case['meta']['pointing']} case"] += 1
                else:
                    count[f"no case: {why}"] += 1
                # the step happened, so later steps see it, on the grid the model reads
                if acts is None:
                    lines.append("(unreadable action)")
                else:
                    lines.append("; ".join(describe(a["name"], on_grid(a["arguments"], 1, 1), a["repeat"]) for a in acts))
    os.replace(out + ".tmp", out)
    stats = {"source": "xlangai/AgentNet, macOS trajectories (meta system == Darwin)",
             "trajectories": count["trajectories"], "steps": count["steps"], "cases": count["cases"],
             "trajectories_with_cases": {k: len(v) for k, v in sorted(trajectories.items())},
             "by_split": {k: count[f"cases {k}"] for k in ("train", "reserved")},
             "screenshots": {k: count[f"cases {k}"] for k in ("on disk", "screenshot not fetched")},
             "by_action": {k: dict(sorted(v.items())) for k, v in sorted(by_action.items())},
             "steps_without_case": {k[9:]: n for k, n in sorted(count.items()) if k.startswith("no case: ")},
             "reserved_cases_and_pointing": {k: n for k, n in sorted(count.items()) if k.startswith("reserved cases, ")},
             "rule": {"reserved": f"sha1(task_id) % {RESERVED_MOD} == 0", "tol_px": TOL_PX, "history_kept": HISTORY_KEEP}}
    with open(os.path.join(out_dir, "stats_actions.json"), "w") as f:
        json.dump(stats, f, indent=1, ensure_ascii=False)
    return stats


def need(raw, cases, out):
    """List the screenshots of the cases that are not on disk, for data/mac/scripts/agentnet_fetch.py.
    `out` becomes a folder that script can be pointed at: need_images.tsv plus links to the raw
    folder's zip directory, last zip segment and images folder (fetched files land in the raw
    folder). Nothing is downloaded here. Returns (files, compressed bytes)."""
    raw, out = os.path.abspath(raw), os.path.abspath(out)
    on_disk = set(os.listdir(os.path.join(raw, "images")))
    wanted = {os.path.basename(json.loads(line)["image"]) for line in open(cases)} - on_disk
    os.makedirs(out, exist_ok=True)
    for name in ("cd_index.tsv", "win_mac_images", "images"):
        if not os.path.lexists(os.path.join(out, name)):
            os.symlink(os.path.join(raw, name), os.path.join(out, name))
    rows = []
    for line in open(os.path.join(raw, "cd_index.tsv")):
        name, disk, off, csize, usize, crc = line.rstrip("\n").split("\t")[:6]
        if name in wanted:
            rows.append((int(disk), int(off), name, csize, usize, crc))
    with open(os.path.join(out, "need_images.tsv"), "w") as f:
        for disk, off, name, csize, usize, crc in sorted(rows):
            f.write(f"{name}\t{disk}\t{off}\t{csize}\t{usize}\t{crc}\n")
    return len(rows), sum(int(r[3]) for r in rows)


# ------------------------------------------------------------------ orchestrator steps: the next step in words
# A second kind of case from the same recordings. The answer is ONE call of `next_step` that says
# what to do and describes the target in plain words; a separate pointer finds it. The recorded
# points stay in the case (`point`, `point_end`), never in the answer.
STEP_ACTIONS = ("click", "double_click", "right_click", "drag", "type", "key", "scroll", "done")
STEP_ORDER = ("target", "target_end", "text", "keys", "direction")
STEP_HISTORY = 4
STEP_NAME = {"left_click": "click", "double_click": "double_click", "right_click": "right_click", "left_click_drag": "drag",
             "type": "type", "key": "key", "scroll": "scroll", "hscroll": "scroll", "terminate": "done"}
STEP_SHARE = {"click": 0.40, "type": 0.16, "drag": 0.12, "key": 0.10, "scroll": 0.09, "done": 0.06, "double_click": 0.04, "right_click": 0.03}

NEXT_STEP_TOOL = {"type": "function", "function": {
    "name": STEP_TOOL,
    "description": ("Say the next single step to take on the screen. Describe the target plainly enough that someone "
                    "could point at it: what it is, what it says, where it is. Do not give coordinates."),
    "parameters": {"type": "object", "required": ["action"], "properties": {
        "action": {"type": "string", "enum": list(STEP_ACTIONS),
                   "description": "What to do. `done` ends the task."},
        "target": {"type": "string", "description": "The element to act on, in plain words. For `drag`, where the drag starts. "
                                                     "Required by `click`, `double_click`, `right_click` and `drag`."},
        "target_end": {"type": "string", "description": "Where the drag ends, in plain words. Only for `drag`."},
        "text": {"type": "string", "description": "For `type`: the text to type; a newline at the end presses Return. "
                                                   "For `done`: one sentence for the user about the result."},
        "keys": {"type": "array", "description": "For `key`: the keys to press together, for example [\"cmd\", \"s\"]."},
        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "For `scroll`."}}}}}

_STOPWORDS = set("a an the of in on at to for and or with by from into onto this that these those is are be it its as "
                 "which near next located labeled labelled named called".split())
_NOT_A_PURPOSE = {"next", "close", "adjacent", "up", "due", "according", "prior", "back", "similar", "relative", "belonging",
                  "attached", "corresponding", "related", "equal", "down", "over", "closer", "nearest", "opposite", "connected",
                  "linked", "leading", "pointing", "set", "from"}
_DETERMINERS = {"the", "a", "an", "its", "this", "that", "these", "those", "my", "your", "his", "her", "their", "our", "each",
                "all", "another", "any", "some", "one", "both", "either"}
_VAGUE = ("it", "here", "there", "anywhere", "the screen", "the page", "the mouse", "the cursor", "the mouse cursor",
          "the mouse pointer", "the pointer", "the current position", "the current location", "the same position", "the same location")
_CLICK_VERB = re.compile(r"^(?:left[- ]click|double[- ]click|right[- ]click|click|tap|select|choose|press|open|check|uncheck|toggle|"
                         r"close|expand|collapse|focus)\b\s*(?:(?:on|at|inside|in|into|within)\s+)?", re.I)
_BREAK = re.compile(r"\s+(?:in order to|so that|so as to|which|because|since|and then|then|while)\b|[,;:]\s|\s+[-–—]\s|\s+to\s+(?=[a-z])"
                    r"|\s+and\s+(?:press|hit|click|submit|drag|scroll|type|select|release)\b")


def _first_sentence(text):
    text = " ".join((text or "").split())
    m = re.search(r'(?<=[.!?])\s+(?=[A-Z"(])', text)
    return (text[:m.start()] if m else text).rstrip(" .!")


def _thing(text):
    """The thing itself: cut at a purpose ("to open ..."), a reason or a second clause, outside quotes."""
    for m in _BREAK.finditer(text):
        before = text[:m.start()]
        if before.count('"') % 2:                                        # inside a quoted label
            continue
        if m.group().strip() == "to":
            words, after = before.split(), text[m.end():].split()
            if (words and words[-1].lower() in _NOT_A_PURPOSE) or (after and after[0].lower() in _DETERMINERS):
                continue                                                 # "next to the logo", "the link to the report"
        text = before
        break
    return text.strip(" .,;:")


def content_words(text):
    return [w for w in re.findall(r"\w+", (text or "").lower()) if w not in _STOPWORDS]


def _names_a_target(text):
    """A description someone could point with: words of its own, no coordinates, not "it" or "the screen"."""
    low = text.lower()
    return bool(text and len(text.split()) <= 30 and content_words(text) and low not in _VAGUE
                and not low.startswith(("the current position", "the current location", "the same "))
                and not re.search(r"coordinate|pixel|\(\s*\d*\.?\d+\s*,\s*\d*\.?\d+\s*\)", low)
                and not re.match(r"(?:i|we)\b|to\b|and\b", low))


def _drag_ends(sentence):
    """(start, end) of a drag as the description words them, or None."""
    toward = r"(?:to|toward|towards|onto|into|until)"
    for pattern in (rf"^(?:click and\s+)?drag\s+(?!from\b)(.+?)\s+from\s+.+?\s+{toward}\s+(.+)$",      # "drag X from A to B": X, B
                    rf"\bfrom\s+(.+?)\s+(?:(?:down|up|over|across|back|all the way)\s+)?{toward}\s+(.+)$",
                    rf"\bclick(?:ing)?\s+(?:at|on)\s+(.+?)\s+and\s+drag(?:ging)?\s+(?:it\s+)?{toward}\s+(.+)$",
                    rf"^(?:click and\s+)?drag\s+(.+?)\s+(?:over\s+|down\s+|up\s+)?{toward}\s+(.+)$"):
        m = re.search(pattern, sentence, flags=re.I)
        # the end has to be a thing ("the Trash icon"), not a purpose ("to reposition it")
        if m and (m.group(2).split()[0].lower() in _DETERMINERS or re.match(r'["A-Z0-9]', m.group(2))):
            side = r"\s+(?:up|down|left|right)(?:ward|wards)?$"
            return re.sub(side, "", _thing(m.group(1))), re.sub(side, "", _thing(m.group(2)))
    return None


def step_from(action, sentence):
    """(step, None) or (None, why not). `action` is a recorded single action ({"name", "arguments"}),
    `sentence` the dataset's own description of that step. The target is the description without
    its verb and its purpose; text, keys and direction come from the recording."""
    name, a = STEP_NAME.get(action["name"]), action["arguments"]
    first = _first_sentence(sentence)
    if name is None:
        return None, "an action the orchestrator does not use"
    if not first:
        return None, "no description"
    if name in ("click", "double_click", "right_click"):
        m = _CLICK_VERB.match(first)
        target = _thing(first[m.end():]) if m else ""
        if not m:
            return None, "the description starts with another verb"
        return ({"action": name, "target": target}, None) if _names_a_target(target) else (None, "the description names no target")
    if name == "drag":
        ends = _drag_ends(first)
        if not ends or not all(_names_a_target(e) and len(content_words(e)) >= 2 for e in ends):   # "the beginning" is too little
            return None, "the description does not name both ends of the drag"
        return {"action": name, "target": ends[0], "target_end": ends[1]}, None
    if name == "type":
        m = re.match(r'^(?:type|write|enter|input)\s+(?:the\s+[\w ]{0,30}?)?"[^"]*"\s+(?:in|into|inside|within|on)\s+(.+)$', first, flags=re.I)
        target = _thing(m.group(1)) if m else ""
        step = {"action": name, "target": target, "text": a["text"]} if _names_a_target(target) else {"action": name, "text": a["text"]}
        return step, None
    if name == "key":
        return {"action": name, "keys": a["keys"]}, None
    if name == "scroll":
        said = {w for w in ("up", "down", "left", "right") if re.search(rf"\b{w}(?:ward|wards)?\b", first, flags=re.I)}
        if action["name"] == "hscroll":
            if len(said & {"left", "right"}) != 1:
                return None, "a sideways scroll whose direction the description does not give"
            direction = (said & {"left", "right"}).pop()
        else:
            direction = "up" if a["pixels"] > 0 else "down"
            if said & {"up", "down"} and direction not in said:
                return None, "the description gives another scroll direction than the recording"
        m = (re.match(r"^scroll\b(?:\s+\w+){0,3}?\s+(?:in|on|within|inside|through|over)\s+(.+)$", first, flags=re.I)
             or re.match(r"^(?:move|position|place|hover)\b.*?\b(?:to|over|on|onto|in|at|near)\s+(.+?)\s+and\s+scroll", first, flags=re.I))
        target = _thing(m.group(1)) if m else ""
        return ({"action": name, "target": target, "direction": direction} if _names_a_target(target)
                else {"action": name, "direction": direction}), None
    m = re.search(r"\b(?:as|since|because)\s+(.+)$", first)                # done: what the description says was achieved
    text = m.group(1).strip() if m else ""
    if text and len(text.split()) <= 40:
        return {"action": "done", "text": text[0].upper() + text[1:] + "."}, None
    return {"action": "done"}, None


THOUGHT_WORDS = 25
_PAST = re.compile(r"^(?:after|once|from there|then|later|the previous|this confirms|clicked|so far|let's assess|according to our earlier|"
                   r"looking at (?:our|my|the) (?:overall |current )?progress|"
                   r"we(?:'ve| have)? (?:clicked|opened|went|navigated|typed|accessed|successfully|already|searched|selected))\b"
                   r"|(?:previous|former|last) action|\bsuccessfully\b|\bredundant\b", re.I)
_SEEN = re.compile(r"\b(?:i can see|i notice|i see|is (?:now |currently |already )?(?:visible|open|displayed|showing|shown|selected|highlighted|"
                   r"available|active|empty)|has (?:opened|appeared|loaded)|appears|shows|displays|contains|there (?:is|are))\b", re.I)
_WHY = re.compile(r"\b(?:needs? to|should|so (?:that|we|i)|in order to|because|since|next|will|"
                  r"to (?:open|access|find|select|view|continue|complete|enter|add|change|set|create|save|search|see|proceed|start|confirm))\b", re.I)
_LEAD = re.compile(r"^(?:(?:however|now|so|next|then|but first|therefore|thus|also|first|finally|additionally|currently|here|indeed)\b,?\s+"
                   r"|(?:i can (?:also |now )?see|i notice|i see|i observe|i think|it (?:seems|appears|looks like))(?: that)?\s+"
                   r"|(?:i|we)(?: now| still| also| first)? (?:need|have|want) to |(?:i|we) (?:should|must|can|could|will)(?: now| first| then)? "
                   r"|(?:i'll|we'll|let me|let's|i'm going to|we're going to|i am going to) "
                   r"|the (?:most |next )?(?:logical |appropriate |obvious )?(?:next )?(?:step|action|move)(?: here| now)? (?:would be|is|will be|should be) to "
                   r"|(?:looking (?:carefully |closely )?at|based on) [^,]{0,60},\s+)", re.I)
_STEP_VERB = r"(?:click|double-click|right-click|drag|type|enter|press|scroll|select|open|use|paste|copy|save|terminate|end|complete)\b"
_PRIVATE = re.compile(r"@|https?:|www\.|\d{5,}|\b[A-Z][a-z]+'s\b")


def short_thought(thought, about, goal=""):
    """One sentence of a step's long recorded thought, at most 25 words, or None.

    The dataset's thought runs to some 300 words: a check of the last action, a progress list, then
    the reasoning for the next step. Kept is the sentence that best says what on the screen matters
    and why the step follows: it shares words with `about` (the step's target or description),
    states something seen or a reason, and is not about what was done before. Its preamble
    ("I can see that", "I need to", "The next logical step would be to") is cut. Sentences with
    coordinates, list markers, addresses, links, long numbers, a possessive name or a capitalised
    name the task's own instruction does not contain are not used. This is a choice by rules, not
    a rewrite: names inside quoted labels can remain."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"(])', " ".join((thought or "").split()))
    wanted, best = set(content_words(about)), None
    for i, sentence in enumerate(sentences):
        if (_PAST.search(sentence) or re.search(r"[✓✔✗✘⬜☐•:]|\b\d+\.$|\(\s*\d*\.?\d+\s*,|coordinate|pixel|\bstep \d", sentence, flags=re.I)
                or re.match(r"(?:i expect|i anticipate|specifically|for example)\b", sentence, flags=re.I)
                or re.search(r"\s(?:Now|Next|Then|So|Looking|According|However)\s", sentence)):            # two sentences run together
            continue
        text = sentence.rstrip(" .!")
        for _ in range(4):
            text = _LEAD.sub("", text, count=1)
        text = re.split(r"\s+[-–—]\s", text, maxsplit=1)[0]                                           # an aside after a dash
        for cut in (r";\s", r",\s+(?:which|so|allowing|and|but|as)\b", r",\s"):                      # too long: keep the first clause
            if len(text.split()) > THOUGHT_WORDS:
                text = re.split(cut, text, maxsplit=1)[0]
        words = text.split()
        names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", re.sub(r'"[^"]*"', '""', " ".join(words[1:])))
        if (not 6 <= len(words) <= THOUGHT_WORDS or _PRIVATE.search(text) or any(n.lower() not in goal.lower() for n in names)
                or re.match(r"(?:it|this|that|these|those|they|he|she|which|and|but|or|by|if|while)\b", text, flags=re.I)
                or (re.match(r"(?:since|given|because|although|when|as)\b", text, flags=re.I) and "," not in text)):   # half a sentence
            continue
        # the call itself says what is done: a sentence that only repeats it, with no reason, is worth little
        repeats = re.match(_STEP_VERB, text, flags=re.I) and not re.search(r"\b(?:to|so|since|because|as)\b", " ".join(words[1:]))
        score = (3 * len(wanted & set(content_words(text))) / max(1, len(wanted)) + 3 * bool(_SEEN.search(sentence))
                 + 2 * bool(_WHY.search(sentence)) + (i >= len(sentences) / 2) - 3 * bool(repeats))
        if score >= 3 and (best is None or score > best[0]):
            best = (score, text[0].upper() + text[1:] + ".")
    return best[1] if best else None


def describe_step(step):
    """The history line of a step, built from the step itself so that the harness can build the same."""
    a, target = step["action"], step.get("target")
    if a in ("click", "double_click", "right_click"):
        return f"{a.replace('_', '-')} {target}"
    if a == "drag":
        return f"drag {target} to {step.get('target_end')}"
    if a == "type":
        text = step.get("text", "")
        line = "type " + json.dumps(text.rstrip("\n") if len(text) <= 80 else text[:77] + "...", ensure_ascii=False)
        return line + (f" in {target}" if target else "") + (" and press Return" if text.endswith("\n") else "")
    if a == "key":
        return "press " + "+".join(step.get("keys", []))
    if a == "scroll":
        return f"scroll {step.get('direction', '')}".rstrip() + (f" in {target}" if target else "")
    return "done"


def render_step(step):
    """The next_step call of a step, as the chat template writes it."""
    call = {"action": step["action"]}
    call.update({k: step[k] for k in STEP_ORDER if step.get(k) not in (None, "")})
    return chat.render_call(STEP_TOOL, call)


def step_case(case, base=None, history_n=STEP_HISTORY, max_side=MAX_SIDE, rng=None, thought=False):
    """A step case as a chat sample (kind "step_call"): same fields as action_case, every token exact.

    thought=False: the answer is the call alone and the prompt has thinking switched off.
    thought=True:  the prompt has thinking switched on (it ends with the opening tag) and the answer
                   is the case's short thought, the closing tag, then the call. A case without a
                   thought is rendered as with thought=False."""
    install()
    rng = rng or random.Random(case["id"])
    target, history = render_step(case["step"]), case.get("history") or []
    thinking = bool(thought and case.get("thought"))
    if thinking:
        target = case["thought"] + "\n</think>\n\n" + target
    first = (case.get("meta") or {}).get("step", len(history)) - len(history) + 1
    return {"kind": STEP_KIND, "id": case["id"], "category": f"step:{case['step']['action']}", "tools": [NEXT_STEP_TOOL],
            "system": rng.choice(chat.SYSTEMS), "request": request_text(case["goal"], history, first, history_n),
            "target": target, "pieces": [[target, None]], "thinking": thinking, "case": case, "item": _item(case, base, max_side)}


def parse_step(text):
    """The first next_step call of a generated answer as a step; None if there is none."""
    raw = _call_arguments(text, STEP_TOOL)
    if raw is None or not str(raw.get("action", "")).strip():
        return None
    step = {"action": str(raw["action"]).strip()}
    for k in ("target", "target_end", "direction"):
        if k in raw:
            step[k] = str(raw[k]).strip()
    if "text" in raw:
        step["text"] = raw["text"] if isinstance(raw["text"], str) else json.dumps(raw["text"], ensure_ascii=False)
    if "keys" in raw:
        keys = raw["keys"]
        if isinstance(keys, str):
            try:
                keys = json.loads(keys.strip())
            except ValueError:
                keys = keys.strip()
        step["keys"] = keys
    return step


def overlap(answer, reference):
    """How much two descriptions share: F1 over their sets of content words, 0 to 1. Rough: it knows
    no synonyms ("gear icon" and "settings button" share nothing) and ignores word order."""
    a, r = set(content_words(answer)), set(content_words(reference))
    common = len(a & r)
    return round(2 * common / (len(a) + len(r)), 3) if common else 0.0


def score_step(case, answer, min_overlap=0.5):
    """Judge one orchestrator answer (text, or a step from parse_step) against a step case.

      action                           must be the recorded one
      type                             the text exactly (a final newline is part of it)
      key                              the same keys after norm_keys
      scroll                           the same direction
      click, double_click,             the target description shares at least `min_overlap` of its content
      right_click, drag                words with the dataset's description (both ends for drag)
      done                             the action alone; its sentence is free
    The target test is a word count, not a judgement of meaning; a pointer run on the answer and
    scored against step_points(case) is the better test.
    Returns {"ok", "action_ok", "parsed", "expected", "got", "target", "target_end", "why"}."""
    got = parse_step(answer) if isinstance(answer, str) else answer
    want = case["step"]
    r = {"ok": False, "action_ok": False, "parsed": got is not None, "expected": want["action"], "got": got and got["action"],
         "target": None, "target_end": None, "why": ""}
    if got is None:
        r["why"] = "no next_step call"
        return r
    r["action_ok"] = got["action"] == want["action"]
    for k in ("target", "target_end"):
        if want.get(k):
            r[k] = overlap(got.get(k, ""), want[k])
    if not r["action_ok"]:
        r["why"] = "another action"
    elif want["action"] == "type" and got.get("text") != want.get("text"):
        r["why"] = "other text"
    elif want["action"] == "key" and (not isinstance(got.get("keys"), (list, str))
                                      or [k.lower() for k in norm_keys(got["keys"])] != [k.lower() for k in norm_keys(want["keys"])]):
        r["why"] = "other keys"
    elif want["action"] == "scroll" and got.get("direction") != want.get("direction"):
        r["why"] = "other direction"
    elif want["action"] in ("click", "double_click", "right_click", "drag") and min(v for v in (r["target"], r["target_end"]) if v is not None) < min_overlap:
        r["why"] = "another target, by its words"
    else:
        r["ok"] = True
    return r


def score_steps(cases, answers, min_overlap=0.5):
    """Totals over many step cases: share correct, share with the right action, mean target overlap."""
    rows = [score_step(c, a, min_overlap) for c, a in zip(cases, answers)]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["expected"]].append(r)
    share = lambda rs, key: round(sum(r[key] for r in rs) / len(rs), 4) if rs else None
    words = [r["target"] for r in rows if r["target"] is not None and r["action_ok"]]
    return {"n": len(rows), "correct": share(rows, "ok"), "action": share(rows, "action_ok"), "parsed": share(rows, "parsed"),
            "mean_target_overlap": round(sum(words) / len(words), 3) if words else None, "min_overlap": min_overlap,
            "by_action": {k: {"n": len(v), "correct": share(v, "ok"), "action": share(v, "action_ok")} for k, v in sorted(by.items())},
            "why": dict(collections.Counter(r["why"] for r in rows if not r["ok"]))}


def step_points(case):
    """What a pointer has to find on this step: [(description, [x, y])] with the recorded points in
    pixels of the screenshot (one pair for a click, two for a drag, none for type, key and done).
    A pointer's answer counts within TOL_PX of the point, as in score_answer."""
    step = case["step"]
    pairs = [(step.get("target"), case.get("point")), (step.get("target_end"), case.get("point_end"))]
    return [(text, point) for text, point in pairs if text and point]


def step_samples(lab, split="train", n=3000, share=None, seed=10, never_trained=False, **render_options):
    """Chat samples of orchestrator steps for training or scoring, from the cases on this machine."""
    path = f"{lab.root}/data/mac/agentnet/cases_steps.jsonl"
    cases = [c for c in load_cases(path, split, never_trained=never_trained) if c.get("thought") or not render_options.get("thought")]
    chosen = pick(cases, n, share or STEP_SHARE, seed, name=lambda c: c["step"]["action"])
    return [step_case(c, base=os.path.dirname(path), **render_options) for c in chosen]


def convert_steps(raw, out):
    """AgentNet macOS trajectories -> cases_steps.jsonl (and stats_steps.json). Same steps, filters and
    split as convert(); a step also needs a description that step_from() can use. The history is the
    last four earlier steps in plain words: describe_step() where the step could be read, otherwise
    the start of the dataset's own sentence."""
    images = os.path.join(raw, "images")
    on_disk = set(os.listdir(images))
    out_dir = os.path.dirname(os.path.abspath(out))
    count, by_action, trajectories = collections.Counter(), collections.defaultdict(collections.Counter), collections.defaultdict(set)
    with open(out + ".tmp", "w") as f:
        for t, m in _mac_trajectories(raw):
            count["trajectories"] += 1
            goal = (t.get("instruction") or "").strip()
            digest = int(hashlib.sha1(t["task_id"].encode()).hexdigest(), 16)
            split = "reserved" if digest % RESERVED_MOD == 0 else "train"
            steps = sorted(t["traj"], key=lambda s: s["index"])
            sizes = {s["image"]: _png_size(os.path.join(images, s["image"])) for s in steps if s["image"] in on_disk}
            common = collections.Counter(sizes.values()).most_common(1)
            apps = [a for a in (m.get("applications") or []) if a]
            lines = []
            for s in steps:
                count["steps"] += 1
                v = s["value"]
                sentence = (v.get("action") or "").strip()
                try:
                    acts = step_actions(v.get("code") or "")
                except (ValueError, SyntaxError, KeyError, IndexError, TypeError):
                    acts = None
                size = sizes.get(s["image"]) or (common[0][0] if common else None)
                step = None
                if acts is None:
                    why = "code not understood"
                elif len(acts) != 1 or acts[0]["repeat"] != 1:
                    why = "more than one action in the step"
                else:
                    step, why = step_from(acts[0], sentence)
                    if why is None:
                        why = ("trajectory without an instruction" if not goal
                               else "flagged incorrect by the dataset" if v.get("last_step_correct") is False
                               else "flagged redundant by the dataset" if v.get("last_step_redundant")
                               else "no screenshot of the trajectory on disk yet (size unknown)" if size is None
                               else _unusable(acts[0], size[0], size[1], t.get("task_completed")))
                if why is None:
                    w, h = size
                    point = {k: [round(acts[0]["arguments"][k][0] * w, 1), round(acts[0]["arguments"][k][1] * h, 1)]
                             for k in ("start_coordinate", "coordinate") if k in acts[0]["arguments"]}
                    case = {"id": f"agentnet-{t['task_id']}-s{int(s['index']):03d}-step",
                            "image": os.path.relpath(os.path.join(images, s["image"]), out_dir), "width": w, "height": h,
                            "goal": goal, "history": lines[-STEP_HISTORY:], "step": step,
                            "point": point.get("start_coordinate") or point.get("coordinate"),
                            "point_end": point["coordinate"] if "start_coordinate" in point else None,
                            "split": split, "app": apps[0] if len(apps) == 1 else ("; ".join(apps) or None),
                            "meta": {"source": "xlangai/AgentNet", "task_id": t["task_id"], "step": len(lines), "steps": len(steps),
                                     "sentence": sentence, "recorded": acts[0]["name"], "status": acts[0]["arguments"].get("status"),
                                     "task_completed": t.get("task_completed"),
                                     "pointing_session": "test" if digest % POINTING_TEST_MOD == 0 else "train"}}
                    said = short_thought(v.get("thought"), " ".join(x for x in (step.get("target"), step.get("target_end")) if x)
                                         or _first_sentence(sentence), goal)
                    if said:
                        case["thought"] = said
                        count["cases with a thought"] += 1
                        by_action[step["action"]]["with a thought"] += 1
                    f.write(json.dumps(case, ensure_ascii=False) + "\n")
                    have = "on disk" if s["image"] in on_disk else "screenshot not fetched"
                    for key in ("cases", f"cases {split}", f"cases {have}"):
                        count[key] += 1
                    for key in (split, have, f"{split}, never in pointing training" if case["meta"]["pointing_session"] == "test" else None,
                                "with a target" if step.get("target") else None, "with a sentence" if step["action"] == "done" and step.get("text") else None):
                        if key:
                            by_action[step["action"]][key] += 1
                    trajectories[split].add(t["task_id"])
                else:
                    count[f"no case: {why}"] += 1
                # later steps see this one in plain words
                plain = " ".join(_thing(_first_sentence(sentence)).split()[:20])
                lines.append(describe_step(step) if step else (plain[0].lower() + plain[1:] if plain else "(a step without a description)"))
    os.replace(out + ".tmp", out)
    stats = {"source": "xlangai/AgentNet, macOS trajectories (meta system == Darwin)",
             "trajectories": count["trajectories"], "steps": count["steps"], "cases": count["cases"],
             "trajectories_with_cases": {k: len(v) for k, v in sorted(trajectories.items())},
             "by_split": {k: count[f"cases {k}"] for k in ("train", "reserved")},
             "screenshots": {k: count[f"cases {k}"] for k in ("on disk", "screenshot not fetched")},
             "with_a_thought": count["cases with a thought"],
             "by_action": {k: dict(sorted(v.items())) for k, v in sorted(by_action.items())},
             "steps_without_case": {k[9:]: n for k, n in sorted(count.items()) if k.startswith("no case: ")},
             "rule": {"reserved": f"sha1(task_id) % {RESERVED_MOD} == 0", "history_kept": STEP_HISTORY, "thought_words": THOUGHT_WORDS}}
    with open(os.path.join(out_dir, "stats_steps.json"), "w") as f:
        json.dump(stats, f, indent=1, ensure_ascii=False)
    return stats


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="AgentNet macOS trajectories as single-action cases")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("convert")
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--pointing")
    p = sub.add_parser("steps")
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("need")
    p.add_argument("--raw", required=True)
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    expand = os.path.expanduser
    if a.command == "convert":
        print(json.dumps(convert(expand(a.raw), expand(a.out), expand(a.pointing) if a.pointing else None), indent=1, ensure_ascii=False))
    elif a.command == "steps":
        print(json.dumps(convert_steps(expand(a.raw), expand(a.out)), indent=1, ensure_ascii=False))
    else:
        files, size = need(expand(a.raw), expand(a.cases), expand(a.out))
        print(f"{files} screenshots to fetch, {size / 1e9:.2f} GB compressed; list in {expand(a.out)}/need_images.tsv")
