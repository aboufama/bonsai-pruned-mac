"""Agents: who decides the next action.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    oracle   executes the task's own solution steps through the page (must pass everything)
    noop     says it is done at once (passes only the tasks that are already done)
    random   left-clicks random points until the step limit (the floor)
    guided   the task supplies each step in words, the model only points (GuidedAgent)
    agent    the model gets the request and its own action history and chooses every action

Every agent has start(ep, env) and act(image, k) -> {"action": dict | None, "raw": str, ...}.
`action` is None when the model's output could not be read as an action; the step is then lost.
"""
import random

from . import actions as A
from .env import H, W
from .oracle import Reveal


class OracleAgent:
    name = "oracle"
    needs_image = False

    def start(self, ep, env):
        self.ep, self.env = ep, env
        self.gen = self._run()

    def _run(self):
        for step in self.ep.steps:
            for a in step.actions(self.env):
                yield a, getattr(step, "say", None) or type(step).__name__
        yield {"type": "done", "status": "infeasible" if self.ep.kind == "infeasible" else "done"}, "done"

    def act(self, image, k):
        a, note = next(self.gen)
        return {"action": a, "raw": note}


class NoopAgent:
    name = "noop"
    needs_image = False

    def start(self, ep, env):
        pass

    def act(self, image, k):
        return {"action": {"type": "done", "status": "done"}, "raw": "done"}


class RandomAgent:
    name = "random"
    needs_image = False

    def start(self, ep, env):
        self.rng = random.Random(f"{ep.task}/{ep.seed}")

    def act(self, image, k):
        a = {"type": "click", "x": self.rng.randint(0, W - 1), "y": self.rng.randint(0, H - 1), "button": "left", "count": 1}
        return {"action": a, "raw": f"random click {a['x']},{a['y']}"}


def snap(point, elements, reach=20):
    """A point in a gap (on no control) is moved onto the nearest control, if one is within
    `reach` points. Only controls that contain no other control are candidates. Returns
    (point, moved). Second version, after the first run showed what hurt: the first one reached
    48 points, took containers as candidates and moved points that were on text or on a display."""
    x, y = point
    boxes = [e["box"] for e in elements if e["box"][2] - e["box"][0] >= 6 and e["box"][3] - e["box"][1] >= 6]
    if any(b[0] <= x < b[2] and b[1] <= y < b[3] for b in boxes):
        return point, False
    leaves = [b for b in boxes if not any(o is not b and o[0] >= b[0] and o[1] >= b[1] and o[2] <= b[2] and o[3] <= b[3] for o in boxes)]
    best, dist = None, reach
    for b in leaves:
        d = (max(b[0] - x, 0, x - b[2]) ** 2 + max(b[1] - y, 0, y - b[3]) ** 2) ** 0.5
        if d < dist:
            best, dist = b, d
    if best is None:
        return point, False
    third = lambda v, a, b: min(max(v, a + (b - a) / 3), b - (b - a) / 3)
    return (third(x, best[0], best[2]), third(y, best[1], best[3])), True


def screen_changed(a, b):
    """Did anything visible change between two screenshots? Compared on a grid of 8 x 8 pixel
    blocks; a blinking text cursor alone (a handful of blocks) does not count."""
    import numpy as np
    from PIL import Image
    x = np.asarray(a.convert("L").resize((360, 225), Image.BILINEAR), dtype=np.int16)
    y = np.asarray(b.convert("L").resize((360, 225), Image.BILINEAR), dtype=np.int16)
    return int((np.abs(x - y) > 12).sum()) >= 6


def zoom(image, point, share=3, side=1024):
    """The part of the screenshot around a point (a third of each side), enlarged for a second
    look. Returns (crop, (x0, y0, w, h)) with the window in points."""
    from PIL import Image
    w, h = W / share, H / share
    x0, y0 = min(max(point[0] - w / 2, 0), W - w), min(max(point[1] - h / 2, 0), H - h)
    f = image.width / W
    crop = image.crop((round(x0 * f), round(y0 * f), round((x0 + w) * f), round((y0 + h) * f)))
    k = side / max(crop.size)
    return crop.resize((round(crop.width * k), round(crop.height * k)), Image.LANCZOS), (x0, y0, w, h)


class GuidedAgent:
    """The task's steps are followed in order. For a step that needs a position the model is
    shown the screenshot and the step in words and its point is used; typing, key presses and
    scrolling are executed as written. One wrong point is not corrected: the next step is asked
    on whatever screen results.

    Options (the "guard rails" assembly): `snap` moves a point that is on no control onto the
    nearest control of the apps' element list; `check` asks the model on the next screenshot
    whether the step took effect (one word, yes or no) and on "no" asks for the point once more."""
    name = "guided"

    def __init__(self, pointer, snap=False, check=None):
        # check: None | "ask" (the model says yes, no or unsure; on no it points once more) | "effect" (nothing visible
        # changed after the action: a second look at the enlarged area around the first point)
        self.pointer, self.snap, self.check = pointer, snap, ("ask" if check is True else check or None)

    def start(self, ep, env):
        self.ep, self.env = ep, env
        self.gen = self._run()
        self.image = None

    def _ask(self, step, retry=False, around=None):
        says = [step.say] + ([step.say_to] if hasattr(step, "say_to") else [])
        try:
            boxes = step.targets(self.env)
        except Exception:
            boxes = [None] * len(says)
        elements = self.env.elements() if self.snap else None
        pts, raws, secs, inside, moved, extra = [], [], 0.0, [], [], {}
        for n, (text, box) in enumerate(zip(says, boxes)):
            if around and around[n]:                           # second look: the enlarged area around the first answer
                crop, (x0, y0, w, h) = zoom(self.image, around[n])
                r = self.pointer(crop, text)
                if r["point"]:
                    r["point"] = (x0 + r["point"][0] / W * w, y0 + r["point"][1] / H * h)
            else:
                r = self.pointer(self.image, text)
            raws.append(r["raw"])
            secs += r.get("seconds", 0.0)
            extra = {k: r[k] for k in ("prompt_tokens", "new_tokens", "read_tps", "write_tps", "peak_memory_gb") if r.get(k) is not None}
            pt, m = r["point"], False
            if pt and elements is not None and not self.env.on_content(*pt):
                pt, m = snap(pt, elements)
            pts.append(pt)
            moved.append(m)
            inside.append(bool(pt and box and box[0] <= pt[0] < box[2] and box[1] <= pt[1] < box[3]))
        out = dict(extra, raw=" | ".join(raws), instruction=" -> ".join(says), inside=inside, boxes=boxes, model_seconds=round(secs, 3))
        if self.snap:
            out["snapped"] = moved
        if retry:
            out["retry"] = True
        if any(p is None for p in pts):
            return dict(out, action=None, error="no point in the answer"), pts
        return dict(out, action=step.build(pts)), pts

    def _run(self):
        for step in self.ep.steps:
            if not step.pointing:
                try:
                    for a in step.actions(self.env):
                        yield {"action": a, "raw": "(scripted) " + A.describe(a), "scripted": True}
                except Exception as e:                      # an earlier miss left nothing to scroll to
                    yield {"action": None, "raw": "(scripted step impossible)", "error": f"{type(e).__name__}: {e}", "scripted": True}
                continue
            before = self.image
            out, pts = self._ask(step)
            yield out
            far = lambda p, q: p is None or q is None or abs(p[0] - q[0]) + abs(p[1] - q[1]) > 12
            if self.check == "effect" and out["action"] is not None and not screen_changed(before, self.image):
                again, pts2 = self._ask(step, retry=True, around=pts)
                if again["action"] is not None and any(far(p, q) for p, q in zip(pts, pts2)):
                    again["raw"] = "(nothing visible changed; second look) " + again["raw"]
                    again["check"] = False
                    yield again
            elif self.check == "ask" and out["action"] is not None:
                c = self.pointer.confirm(self.image, step.say + (" to " + step.say_to if hasattr(step, "say_to") and step.say_to else ""))
                out2 = {"raw": "(check) " + c["raw"], "scripted": False, "check": c["ok"], "model_seconds": c.get("seconds", 0.0), "instruction": "Did it take effect? " + step.say}
                if c["ok"] is False:
                    again, pts2 = self._ask(step, retry=True)
                    if again["action"] is not None and any(far(p, q) for p, q in zip(pts, pts2)):
                        again["raw"] = out2["raw"] + " | " + again["raw"]
                        again["model_seconds"] = round(again["model_seconds"] + out2["model_seconds"], 3)
                        again["check"] = False
                        yield again
                        continue
                yield dict(out2, action={"type": "wait"})
        yield {"action": {"type": "done", "status": "done"}, "raw": "(end of the guided steps)", "scripted": True}

    def act(self, image, k):
        self.image = image
        return next(self.gen)


def guided_limit(ep, check=False):
    """Guided mode is given exactly the steps of the solution (a Reveal may take several; with
    the check every pointing step has one more turn for the check or the retry)."""
    return sum(12 if isinstance(s, Reveal) else (2 if check and s.pointing else 1) for s in ep.steps) + 1
