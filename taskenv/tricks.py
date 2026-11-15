"""Harness-only aids for the planner: no weights change. They wrap the function that asks the model
for its next step (plan_run's `chat`), so they work with every loop (plain, --app-rules, --assistant).

  verify_done   when the model says done, it is asked once more with a check line added to the user
                message ("go through the task part by part ..."). If the second answer is a step and not
                done, that step is used. Aimed at "done said too early / one part missed".
  split_chains  a request made of several tasks joined by "Then", "Next,", "After that,", "Finally," ...
                is cut into its parts by rule and the model is shown one part at a time; when it says
                done for a part that is not the last, the next part is put in the Task line and the model
                is asked again at once. The simulator's chains are joined with a fixed set of phrases
                (planmode.JOIN, JOIN3), so on its tasks the cut is exact; on free text it is a heuristic.

  precheck      at the first turn of a request that is one part, the model is first asked with a line added: "if the
                Task is already as asked, or the thing it names does not exist here, call done and say so".
                A done answer ends the episode; any other answer is dropped and the model is asked as usual.
                Aimed at "already done" and "cannot be done" requests, where the model acts anyway.
  unstick       when the last step changed nothing (its Done-so-far line says so) and the model gives the very
                same step again, it is asked once more with a line saying so ("choose a different control, a
                menu, a scroll, or call done ..."); if the answer is still the same step, up to three answers
                are drawn at temperature 0.7 and the first different one is used. Aimed at "the same dead
                step three times".

    chat = tricks.wrap(chat, verify_done=True, split_chains=True, unstick=True)     # a fresh wrap for every episode
"""
import re

from . import planmode

CHECK = ("\nBefore you finish: go through the Task part by part and compare it with Done so far. "
         "If any part has not been carried out yet, reply with the next step for that part. "
         "Call done only when every part is finished.")
PRE = ("\nBefore the first step, check the Controls: if the Task is already as asked, or the thing the Task names does "
       "not exist here, call done and say so. Otherwise give the first step.")
DEAD = ("\nThe last step changed nothing. Do not give that step again. Choose a different step: another control, "
        "a menu, a scroll, or, if the task is already as asked or cannot be carried out, call done and say so.")
_CUT = re.compile(r"(?<=[.!?])\s+(?:Then|After that,|When that is done,|Next,|And then|And when both are done,|Once you have done that,|"
                  r"Finally,|Second,|Third,|Last,|And)\s+")
_HEAD = re.compile(r"^(?:First,|Two things:|Three things:)\s+")


def parts_of(task):
    """The request cut into its parts; one part when no joining phrase is found."""
    out = [p.strip() for p in _CUT.split(_HEAD.sub("", task.strip())) if p.strip()]
    return [p[0].upper() + p[1:] for p in out] or [task]


def _task(messages):
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].startswith("Task: "):
            return m, m["content"].split("\n", 1)[0][len("Task: "):]
    return None, None


def _with(messages, user, text):
    return [dict(m, content=text) if m is user else m for m in messages]


def _dead(content):
    """True when the last line under "Done so far" says the step had no effect."""
    lines = [l for l in content.split("\nControls")[0].split("\n") if l.strip()]
    return bool(lines) and ("(nothing changed)" in lines[-1] or "(not carried out" in lines[-1])


def wrap(chat, verify_done=False, split_chains=False, unstick=False, precheck=False, log=None):
    state = {"task": None, "parts": None, "i": 0, "last": None}
    inner = chat

    def chat(messages, tools, k, **kw):                # the model's answer, with the dead step refused
        msg = inner(messages, tools, k, **kw)
        if not unstick or isinstance(msg, list):
            return msg
        step = planmode.parse(msg)
        user = next((m for m in messages if m.get("role") == "user" and isinstance(m.get("content"), str)), None)
        if step and user and step.get("action") != "done" and step == state["last"] and _dead(user["content"]):
            again = inner(_with(messages, user, user["content"] + DEAD), tools, k)
            step2 = planmode.parse(again)
            if step2 and step2 != step:
                msg, step = again, step2
            else:
                for _ in range(3):
                    draw = inner(_with(messages, user, user["content"] + DEAD), tools, k, temperature=0.7)
                    step3 = planmode.parse(draw)
                    if step3 and step3 != step:
                        msg, step = draw, step3
                        break
            if log is not None:
                log.append(("unstick", step != state["last"]))
        state["last"] = step
        return msg

    def ask(messages, tools, k, **kw):
        user, task = _task(messages)
        if user is None:
            return chat(messages, tools, k, **kw)
        if task != state["task"]:
            state.update(task=task, parts=parts_of(task) if split_chains else [task], i=0)
        parts = state["parts"]
        rest = user["content"].split("\n", 1)[1] if "\n" in user["content"] else ""
        for _ in range(len(parts) + 2):
            text = "Task: " + parts[state["i"]] + ("\n" + rest if rest else "")
            if precheck and "\nDone so far: nothing" in text and len(parts) == 1:      # first turn: already as asked, or impossible?
                first = chat(_with(messages, user, text + PRE), tools, k)
                step0 = planmode.parse(first) if not isinstance(first, list) else None
                if step0 and step0.get("action") == "done":
                    if log is not None:
                        log.append(("precheck_done", 0))
                    return first
            msg = chat(_with(messages, user, text), tools, k, **kw)
            step = planmode.parse(msg) if not (isinstance(msg, list)) else None
            if isinstance(msg, list) or not step or step.get("action") != "done":
                return msg
            if verify_done:
                again = chat(_with(messages, user, text + CHECK), tools, k, **{x: y for x, y in kw.items() if x != "count"})
                step2 = planmode.parse(again) if not isinstance(again, list) else None
                if step2 and step2.get("action") != "done":
                    if log is not None:
                        log.append(("verify_changed", state["i"]))
                    return again
            if state["i"] + 1 < len(parts):            # this part is finished: show the next one and ask again
                state["i"] += 1
                if log is not None:
                    log.append(("next_part", state["i"]))
                continue
            return msg
        return msg
    return ask
