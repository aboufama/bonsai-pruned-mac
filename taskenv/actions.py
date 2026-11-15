"""Actions: the internal form the environment executes, and how a model's tool call becomes one.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

The model's side is the schema of docs/ACTION_FORMAT.md: one tool, `computer_use`, written in the
Qwen3.5 chat template, coordinates as integers on a 1000 x 1000 grid over the screenshot. The
definition, the parser of the model's text and the history lines live in weightlab/actions.py and
are used from there, so that the test asks exactly what training teaches. This file turns a parsed
call into the internal action of taskenv/env.py (points of the 1440 x 900 desktop).

    schema                                  internal
    left_click / double_click / right_click / triple_click / middle_click [x, y]   click (button, count)
    left_click_drag start_coordinate, coordinate     drag (without start: from where the pointer is)
    mouse_move                              move
    type text                               type (a newline presses Return)
    key keys                                key
    scroll / hscroll pixels, coordinate     scroll (positive pixels = up / right; see SCROLL below)
    wait                                    wait
    terminate success | failure             done: "done" | "infeasible" (failure = it cannot be done)
    answer text                             say (a message to the user; does not end the episode)
"""
from .env import H, W, key_combo

GRID = 1000
# `pixels` of a scroll is a number of wheel clicks in the family's harnesses (passed to
# pyautogui.scroll) and in AgentNet; some models write a distance in pixels instead. Up to 30 it
# is read as clicks of 60 points each, above that as points; one action moves at most one screen.
SCROLL_CLICK, SCROLL_CLICKS_MAX, SCROLL_MAX = 60, 30, 800


def to_points(x, y):
    return x / GRID * W, y / GRID * H


def to_grid(x, y):
    return max(0, min(GRID - 1, round(x / W * GRID))), max(0, min(GRID - 1, round(y / H * GRID)))


def from_call(call, pointer):
    """A parsed computer_use call ({"name", "arguments"}, points on the grid) as an internal action.
    Raises ValueError when the call cannot be executed (unknown action, missing or bad argument)."""
    name, a = call["name"], call["arguments"]

    def point(key="coordinate"):
        c = a.get(key)
        if not (isinstance(c, (list, tuple)) and len(c) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in c)):
            raise ValueError(f"{name} needs {key} as [x, y]")
        if not all(-5 <= v <= GRID + 5 for v in c):
            raise ValueError(f"{key} {list(c)} is outside the 0-1000 grid")
        return to_points(c[0], c[1])

    clicks = {"left_click": ("left", 1), "double_click": ("left", 2), "triple_click": ("left", 3), "right_click": ("right", 1), "middle_click": ("middle", 1)}
    if name in clicks:
        x, y = point()
        return {"type": "click", "x": x, "y": y, "button": clicks[name][0], "count": clicks[name][1]}
    if name == "left_click_drag":
        x2, y2 = point()
        x1, y1 = point("start_coordinate") if "start_coordinate" in a else pointer
        return {"type": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
    if name == "mouse_move":
        x, y = point()
        return {"type": "move", "x": x, "y": y}
    if name == "type":
        if not isinstance(a.get("text"), str) or a["text"] == "":
            raise ValueError("type needs text")
        return {"type": "type", "text": a["text"]}
    if name == "key":
        keys = a.get("keys")
        if isinstance(keys, str):
            keys = [k for k in keys.replace(" ", "+").split("+") if k] if len(keys) > 1 else [keys]
        if not isinstance(keys, list) or not keys:
            raise ValueError("key needs keys")
        key_combo(keys)                                    # raises on an unknown key
        return {"type": "key", "keys": "+".join(str(k) for k in keys)}
    if name in ("scroll", "hscroll"):
        n = a.get("pixels")
        if not isinstance(n, (int, float)) or isinstance(n, bool) or n == 0:
            raise ValueError(f"{name} needs a non-zero number of pixels")
        x, y = point() if "coordinate" in a else pointer
        d = n * SCROLL_CLICK if abs(n) <= SCROLL_CLICKS_MAX else n
        d = max(-SCROLL_MAX, min(SCROLL_MAX, d))
        return {"type": "scroll", "x": x, "y": y, "dx": d if name == "hscroll" else 0, "dy": -d if name == "scroll" else 0}
    if name == "wait":
        return {"type": "wait"}
    if name == "terminate":
        status = str(a.get("status", "")).strip().lower()
        if status not in ("success", "failure"):
            raise ValueError("terminate needs status success or failure")
        return {"type": "done", "status": "done" if status == "success" else "infeasible"}
    if name == "answer":
        return {"type": "say", "text": str(a.get("text", ""))}
    raise ValueError(f"unknown action {name!r}")


def describe(a):
    """One line of plain text for an internal action (viewer and logs; points shown on the grid)."""
    if a is None:
        return "(no valid action)"
    t = a["type"]
    g = lambda x, y: "[%d, %d]" % to_grid(x, y)
    if t == "click":
        kind = {("left", 1): "click", ("left", 2): "double-click", ("left", 3): "triple-click", ("right", 1): "right-click", ("middle", 1): "middle-click"}.get((a.get("button", "left"), a.get("count", 1)), "click")
        return f"{kind} {g(a['x'], a['y'])}"
    if t == "drag":
        return f"drag {g(a['x1'], a['y1'])} to {g(a['x2'], a['y2'])}"
    if t == "move":
        return f"move to {g(a['x'], a['y'])}"
    if t == "type":
        return f"type {a['text']!r}"
    if t == "key":
        return f"press {a['keys']}"
    if t == "scroll":
        d = "down" if a.get("dy", 0) > 0 else "up" if a.get("dy", 0) < 0 else "right" if a.get("dx", 0) > 0 else "left"
        return f"scroll {d} {abs(round(a.get('dy') or a.get('dx') or 0))} at {g(a['x'], a['y'])}"
    if t == "wait":
        return "wait"
    if t == "say":
        return f"say {a.get('text', '')!r}"
    if t == "done":
        return "done: it cannot be done" if a.get("status") == "infeasible" else "done"
    return t


def validate(a):
    """Raises ValueError unless `a` is an executable internal action."""
    t = a.get("type")
    num = lambda *ks: all(isinstance(a.get(k), (int, float)) and not isinstance(a.get(k), bool) for k in ks)
    if t == "click":
        ok = num("x", "y") and a.get("button", "left") in ("left", "right", "middle") and a.get("count", 1) in (1, 2, 3)
    elif t == "drag":
        ok = num("x1", "y1", "x2", "y2")
    elif t == "move":
        ok = num("x", "y")
    elif t == "type":
        ok = isinstance(a.get("text"), str) and a["text"] != ""
    elif t == "key":
        key_combo(a.get("keys") or "")
        ok = True
    elif t == "scroll":
        ok = num("x", "y") and bool(a.get("dx") or a.get("dy"))
    elif t in ("wait", "done", "say"):
        ok = True
    else:
        ok = False
    if not ok:
        raise ValueError(f"not a valid action: {a}")
    return a
