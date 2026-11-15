"""Models in the loop.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

The models are the benchmark's (bench/models.py): any key that `bench.models.load` knows can be
run here, with the same weights, patch handling, image preparation and decoding (greedy).

Guided mode (Pointer): one question per position, either
    ask="point"   the Qwen3.5-family grounding prompt, answer "[x, y]" on the 0-1000 scale
                  (the prompt the pointing benchmark uses), or
    ask="tool"    the lab's `point` tool call (weightlab/chat.py), the form the "tools" patches write.
Agent mode (ModelAgent): the `computer_use` tool of docs/ACTION_FORMAT.md. The model is shown the
current screenshot, the request and its own last eight actions as text, and must write one call.
    prompt="plain"     system line and request exactly as in ACTION_FORMAT.md (what an
                       action-trained model saw in training)
    prompt="rules"     the same plus four sentences on when to stop (for models that were never
                       taught this loop)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv import actions as A  # noqa: E402
from taskenv.env import H, W  # noqa: E402

SYSTEM = "Screen assistant on a Mac. Look at the screenshot and act on the request with the tools."          # weightlab.chat.SYSTEMS[2]
RULES = (" You control the Mac through the computer_use tool. Reply with exactly one computer_use call and nothing else; "
         "you will then get a new screenshot. Coordinates are on a 1000 x 1000 grid over the screenshot. "
         "When the request has been carried out, or the screen shows it is already satisfied, call terminate with status success. "
         "If the request cannot be carried out, for example because what it names is not there, change nothing and call terminate with status failure.")


def load(key, root, patch=None, head=None):
    if key.startswith("mlx-") and key.endswith("-head"):   # the pointing decoder on the first 20 layers (taskenv/mlx_head.py)
        from taskenv.mlx_head import HeadModel
        return HeadModel(key, root, patch=patch, head=head)
    if key.startswith("mlx-"):                       # Bonsai in MLX on a Mac (taskenv/mlx_model.py)
        from taskenv.mlx_model import MLXModel
        return MLXModel(key, root, patch=patch)
    from bench import models
    return models.load(key, root, patch=patch)


CHECK = ("This step was just attempted on the screen: {step}\nLook at the screenshot. Has the step taken effect? "
         "Answer with one word: yes, no, or unsure.")


class Pointer:
    def __init__(self, model, input_policy="s1280", ask="point"):
        from bench import models
        from weightlab import chat
        self.model, self.input, self.ask, self.models = model, input_policy, ask, models
        self.system = chat.SYSTEMS[0]
        self.tools = [chat.OTHER_TOOLS[1], chat.POINT_TOOL, chat.OTHER_TOOLS[3], chat.OTHER_TOOLS[0]]

    def __call__(self, image, instruction):
        sent = self.models.prepare(image, self.input)
        if self.ask == "point":
            r = self.model.point(sent, instruction)
            pt, _ = self.models.parse_point(r["raw"])
        else:
            messages = [{"role": "system", "content": self.system}, {"role": "user", "content": instruction}]
            r = self.model.chat(messages, tools=self.tools, max_new_tokens=64, image=sent)
            m = re.search(r"<function=point>.*?<parameter=x>\s*(-?\d+).*?<parameter=y>\s*(-?\d+)", r["raw"], flags=re.S)
            pt = (float(m.group(1)), float(m.group(2))) if m else None
        if pt and not (0 <= pt[0] <= 1000 and 0 <= pt[1] <= 1000):
            pt = None
        return dict({k: r[k] for k in ("read_tps", "write_tps", "peak_memory_gb", "read_seconds", "head_ms", "click_logit") if k in r}, point=A.to_points(*pt) if pt else None, raw=r["raw"],
                    seconds=r.get("seconds", 0.0), prompt_tokens=r.get("prompt_tokens"), new_tokens=r.get("new_tokens"), sent=list(sent.size))


    def confirm(self, image, step):
        """Ask whether a step took effect on the screenshot. ok is True, False or None (unsure, or no clear answer)."""
        sent = self.models.prepare(image, self.input)
        r = self.model.chat([{"role": "user", "content": CHECK.format(step=step)}], max_new_tokens=4, image=sent)
        word = r["raw"].strip().lower()
        return {"ok": True if word.startswith("yes") else False if word.startswith("no") else None, "raw": r["raw"].strip(), "seconds": r.get("seconds", 0.0)}


class ModelAgent:
    name = "agent"

    def __init__(self, model, input_policy="s1280", prompt="rules", max_new_tokens=192, thinking=False):
        self.thinking = thinking                              # MLX models only: let the model reason before the call
        from bench import models
        from weightlab import actions as WA
        self.model, self.input, self.models, self.WA = model, input_policy, models, WA
        self.system = SYSTEM + (RULES if prompt == "rules" else "")
        self.max_new_tokens = max_new_tokens

    def start(self, ep, env):
        self.goal, self.env, self.history = ep.request, env, []

    def act(self, image, k):
        WA = self.WA
        sent = self.models.prepare(image, self.input)
        text = WA.request_text(self.goal, self.history)
        messages = [{"role": "system", "content": self.system}, {"role": "user", "content": text}]
        r = self.model.chat(messages, tools=[WA.COMPUTER_USE_TOOL], max_new_tokens=self.max_new_tokens, image=sent, **({"thinking": True} if self.thinking else {}))
        out = {"raw": r["raw"], "model_seconds": r.get("seconds", 0.0), "prompt_tokens": r.get("prompt_tokens"), "new_tokens": r.get("new_tokens")}
        out.update({k: r[k] for k in ("think_tokens", "thinking", "read_tps", "write_tps", "peak_memory_gb") if k in r})
        call = WA.parse_answer(r["raw"])
        if call is None:
            return dict(out, action=None, error="no computer_use call in the answer")
        try:
            action = A.from_call(call, self.env.pointer)
        except ValueError as e:
            return dict(out, action=None, error=str(e), call=call)
        try:
            self.history.append(WA.describe(call["name"], call["arguments"]))
        except Exception:
            self.history.append(call["name"])
        return dict(out, action=action, call=call)


CANNOT = re.compile(r"\b(cannot|can't|can not|unable|not possible|impossible|no such|does not exist|doesn't exist|not found|could not find|couldn't find|is not (?:there|available|present)|there is no)\b", re.I)


class OrchestratedAgent:
    """Two models: an orchestrator that says the next step in words (the `next_step` tool of
    docs/ACTION_FORMAT.md, "Orchestrator steps": action, target description, text or keys, no
    coordinates) and a pointer that turns each target description into a point. The pointer can
    be the same model asked again, another model, or the pointing decoder.

    One step may need two things from the environment (click a field, then type into it): the
    click is executed here and the typing is returned as the step's action. A `done` whose
    sentence says the request cannot be carried out counts as "it cannot be done"."""
    name = "agent"

    def __init__(self, planner, pointer, input_policy="s1280", snap=False):
        from bench import models
        from weightlab import actions as WA
        self.planner, self.pointer, self.input, self.models, self.WA, self.snap = planner, pointer, input_policy, models, WA, snap

    def start(self, ep, env):
        self.goal, self.env, self.history = ep.request, env, []

    def _point(self, image, words, out):
        from taskenv.agents import snap
        r = self.pointer(image, words)
        out["model_seconds"] = round(out["model_seconds"] + r.get("seconds", 0.0), 3)
        out["pointer_seconds"] = round(out.get("pointer_seconds", 0.0) + r.get("seconds", 0.0), 3)
        out["raw"] += f"\n[pointer] {words} -> {r['raw']}"
        pt = r["point"]
        if pt and self.snap and not self.env.on_content(*pt):
            pt, _ = snap(pt, self.env.elements())
        if pt is None:
            raise ValueError(f"the pointer gave no point for {words!r}")
        return pt

    def act(self, image, k):
        WA = self.WA
        sent = self.models.prepare(image, self.input)
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": WA.request_text(self.goal, self.history, 1, WA.STEP_HISTORY)}]
        r = self.planner.chat(messages, tools=[WA.NEXT_STEP_TOOL], max_new_tokens=160, image=sent)
        out = {"raw": r["raw"], "model_seconds": r.get("seconds", 0.0), "planner_seconds": r.get("seconds", 0.0), "prompt_tokens": r.get("prompt_tokens"), "new_tokens": r.get("new_tokens")}
        step = WA.parse_step(r["raw"])
        if step is None:
            return dict(out, action=None, error="no next_step call in the answer")
        out["call"] = {"name": "next_step", "arguments": step}
        a = step["action"]
        try:
            if a in ("click", "double_click", "right_click"):
                x, y = self._point(image, step.get("target") or "", out)
                action = {"type": "click", "x": x, "y": y, "button": "right" if a == "right_click" else "left", "count": 2 if a == "double_click" else 1}
            elif a == "drag":
                (x1, y1), (x2, y2) = self._point(image, step.get("target") or "", out), self._point(image, step.get("target_end") or "", out)
                action = {"type": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
            elif a == "type":
                if not step.get("text"):
                    raise ValueError("type needs text")
                if step.get("target"):                       # click the field first, then type
                    x, y = self._point(image, step["target"], out)
                    self.env.step({"type": "click", "x": x, "y": y, "button": "left", "count": 1})
                    out["pre"] = {"type": "click", "x": x, "y": y}
                action = {"type": "type", "text": step["text"]}
            elif a == "key":
                keys = step.get("keys")
                keys = [keys] if isinstance(keys, str) else keys
                if not keys:
                    raise ValueError("key needs keys")
                action = {"type": "key", "keys": "+".join(str(v) for v in keys)}
            elif a == "scroll":
                x, y = self._point(image, step["target"], out) if step.get("target") else self.env.pointer
                d = {"down": (0, 300), "up": (0, -300), "right": (300, 0), "left": (-300, 0)}.get(step.get("direction", "down"))
                if d is None:
                    raise ValueError(f"unknown scroll direction {step.get('direction')!r}")
                action = {"type": "scroll", "x": x, "y": y, "dx": d[0], "dy": d[1]}
            elif a == "done":
                action = {"type": "done", "status": "infeasible" if CANNOT.search(step.get("text") or "") else "done", "message": step.get("text") or ""}
            else:
                raise ValueError(f"unknown action {a!r}")
        except ValueError as e:
            return dict(out, action=None, error=str(e))
        try:
            self.history.append(WA.describe_step(step))
        except Exception:
            self.history.append(a)
        return dict(out, action=action)


class ScriptedModel:
    """A stand-in with the interface of bench.models, for testing the loop without a GPU: it
    answers pointing questions with a fixed point and agent turns with a fixed list of calls."""

    def __init__(self, calls=(), point="[500, 500]"):
        self.calls, self.point_text, self.i = list(calls), point, 0

    def describe(self):
        return {"kind": "scripted"}

    def point(self, image, instruction, max_new_tokens=32):
        return {"raw": self.point_text, "seconds": 0.0}

    def chat(self, messages, tools=None, max_new_tokens=512, image=None):
        raw = self.calls[min(self.i, len(self.calls) - 1)] if self.calls else ""
        self.i += 1
        return {"raw": raw, "seconds": 0.0}

    def close(self):
        pass
