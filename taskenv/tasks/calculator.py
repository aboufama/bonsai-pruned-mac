"""Calculator (basic and scientific keypads): start state and tasks.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

A calculation counts when it was finished with = : the display shows the result and the last
entry of the tape (the list of finished calculations) has that result and the numbers asked for.
"""
import re

from ..oracle import Click, Type
from .base import Spec, cond, only, say, task, unchanged, verdict

SIZE = (248, 418)
SCI_W = 422                     # width of the window in scientific mode (calculator.js)
WIN = '.win[data-app="calculator"] '
SYMBOL = {"+": "+", "-": "−", "*": "×", "/": "÷"}
KEY_NAME = {"+": "+ (plus)", "−": "− (minus)", "×": "× (multiply)", "÷": "÷ (divide)", "=": "= (equals)", "pct": "% (percent)", ".": ". (decimal point)"}
# What the calculation may change: the screen, the pending operation and one or more tape entries.
CALC = ("calculator.display", "calculator.acc", "calculator.op", "calculator.fresh", "calculator.tape.+*", "calculator.next")


def fmt(x):
    """A number as the calculator shows it: at most 9 significant digits, no trailing zeros."""
    r = float(f"{x:.9g}")
    return str(int(r)) if r == int(r) else repr(r)


def default(rng):
    tape = []
    for i in range(rng.choice([0, 1, 1, 2])):
        op = rng.choice("+-*/")
        if op == "/":
            b = rng.randint(2, 12)
            a = b * rng.randint(3, 60)
        else:
            a, b = rng.randint(12, 950), rng.randint(3, 90)
        tape.append({"id": f"t{i + 1}", "expr": f"{a}{SYMBOL[op]}{b}", "result": fmt({"+": a + b, "-": a - b, "*": a * b, "/": a / b}[op])})
    display = tape[-1]["result"] if tape and rng.random() < 0.75 else "0"
    return {"display": display, "acc": None, "op": None, "fresh": True, "mode": "basic", "tape": tape, "next": 1,
            "ui": {"toks": [], "expr": "", "label": "", "wait": False}}


# ------------------------------------------------------------------ helpers
def key(k):
    return WIN + f'.ck[data-arg="{k}"]'


def presses(text):
    """Click steps for a string of keys: digits, the point, the operators, pct and =."""
    steps = []
    for k in text:
        k = "pct" if k == "%" else k
        steps.append(Click(key(k), f"Click the {KEY_NAME.get(k, k)} key of the calculator"))
    return steps


def app(st):
    return st["apps"]["calculator"]


def numbers(expr):
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", expr)]


def has(nums, x):
    return any(abs(n - x) < 1e-9 for n in nums)


def finished(st, init, result, groups, steps=False):
    """The display shows `result`, the last calculation on the tape is new and gave it, and it
    contains one number of every group (a group lists equivalent spellings: 15% or 0.15). With
    `steps` the numbers may be spread over the new calculations (240×15 = 3600, then 3600÷100)."""
    s, old = app(st), {t["id"] for t in app(init)["tape"]}
    new = [t for t in s["tape"] if t["id"] not in old]
    nums = [n for t in (new if steps else new[-1:]) for n in numbers(t["expr"])]
    return verdict(cond(s["display"] == result, f"the display shows {s['display']}, not {result}"),
                   cond(new and s["tape"][-1]["id"] not in old and s["tape"][-1]["result"] == result, "the last calculation did not give that result"),
                   cond(all(any(has(nums, x) for x in g) for g in groups), "the calculation does not use the numbers asked for"),
                   cond(s["op"] is None, "a calculation is still pending"),
                   only(st, init, *CALC))


# ------------------------------------------------------------------ tasks
@task("calculator.two_numbers", "chain")
def two_numbers(S):
    if S.rng.random() < 0.5:
        a, b = S.rng.sample(range(12, 100), 2)
        op, result = "×", fmt(a * b)
        request = say(S.rng, f"What is {a} times {b}? Work it out on the calculator.", f"Multiply {a} by {b} with the calculator.")
    else:
        a, b = S.rng.randint(105, 989), S.rng.randint(12, 98)
        op, result = "+", fmt(a + b)
        request = say(S.rng, f"What is {a} plus {b}? Work it out on the calculator.", f"Add {a} and {b} with the calculator.")
    S.open("calculator")
    return Spec(request=request, steps=presses(f"{a}{op}{b}="),
                check=lambda st, init: finished(st, init, result, [[a], [b]]))


@task("calculator.type_decimal", "typing")
def type_decimal(S):
    kind = S.rng.choice(["+", "-", "*"])
    if kind == "*":
        a, b = S.rng.randint(12, 240), S.rng.choice([0.5, 1.5, 2.5, 3.5, 0.25, 0.75, 1.25, 4.5, 7.5, 12.5])
        result = fmt(a * b)
        request = say(S.rng, f"What is {a} times {fmt(b)}? Work it out on the calculator.", f"Use the calculator to multiply {a} by {fmt(b)}.")
    else:
        a = S.rng.randint(400, 4800)
        b = S.rng.randint(11, 380) + S.rng.choice([0.5, 0.25, 0.75, 0.4, 0.6, 0.9, 0.15, 0.35])
        if kind == "+":
            result = fmt(a + b)
            request = say(S.rng, f"What is {a} plus {fmt(b)}? Work it out on the calculator.", f"Use the calculator to add {fmt(b)} to {a}.")
        else:
            result = fmt(a - b)
            request = say(S.rng, f"What is {a} minus {fmt(b)}? Work it out on the calculator.", f"Use the calculator to take {fmt(b)} away from {a}.")
    S.open("calculator")
    return Spec(request=request,
                steps=[Click(WIN + ".calc-display", "Click the display of the calculator"), Type(f"{a}{kind}{fmt(b)}=")],
                check=lambda st, init: finished(st, init, result, [[a], [b]]))


@task("calculator.percent", "chain")
def percent(S):
    pct = S.rng.choice([12, 15, 18, 20, 25, 30, 35, 40, 45, 60, 75, 80])
    base = S.rng.choice([n for n in range(120, 960, 20) if n != pct * 10])
    result = fmt(base * float(fmt(pct / 100)))
    S.open("calculator")
    return Spec(request=say(S.rng, f"What is {pct}% of {base}? Work it out on the calculator.", f"Use the calculator to find {pct} percent of {base}."),
                steps=presses(f"{base}×{pct}%="),
                check=lambda st, init: finished(st, init, result, [[base], [pct, pct / 100]], steps=True))


@task("calculator.clear", "single")
def clear(S):
    s = S.apps["calculator"]
    if s["display"] == "0":
        s["display"] = str(S.rng.randint(13, 9800))
        s["fresh"] = S.rng.random() < 0.5
    S.open("calculator")

    def check(st, init):
        c = app(st)
        return verdict(cond(c["display"] == "0", f"the display shows {c['display']}"),
                       cond(c["op"] is None and c["acc"] is None, "a calculation is still pending"),
                       only(st, init, "calculator.display", "calculator.acc", "calculator.op", "calculator.fresh"))
    return Spec(request=say(S.rng, "Clear the calculator.", "Reset the calculator so that it shows 0."),
                steps=[Click(key("clear"), "Click the C key at the top left of the calculator's keypad")],
                check=check)


@task("calculator.scientific", "menu")
def scientific(S):
    S.open("calculator")
    return Spec(request=say(S.rng, "Switch the calculator to scientific mode.", "I need the sin and cos keys. Show the scientific calculator."),
                steps=[Click('.mb-item:text-is("View")', "Click “View” in the menu bar"),
                       Click('.menu-item:has(.mi-label:text-is("Scientific"))', "Click “Scientific” in the menu")],
                check=lambda st, init: verdict(cond(app(st)["mode"] == "scientific", "the calculator is not in scientific mode"),
                                               only(st, init, "calculator.mode")))


@task("calculator.already_mode", "already_done")
def already_mode(S):
    S.open("calculator")
    if S.rng.random() < 0.6:
        S.apps["calculator"]["mode"] = "scientific"
        win = S.state["windows"][-1]
        win["w"], win["x"] = SCI_W, min(win["x"], 1440 - SCI_W - 16)
        request = say(S.rng, "Switch the calculator to scientific mode.", "Make sure the calculator is showing the scientific keypad.")
    else:
        request = say(S.rng, "Put the calculator in basic mode.", "Make sure the calculator is showing the basic keypad, not the scientific one.")
    return Spec(request=request, steps=[], kind="already_done", check=unchanged)


@task("calculator.no_such_feature", "infeasible")
def no_such_feature(S):
    S.open("calculator")
    if S.rng.random() < 0.5:
        amount = S.rng.choice([40, 75, 120, 250, 600, 1500])
        request = say(S.rng, f"Convert {amount} US dollars to euros with the currency converter of the calculator.",
                      f"Use the calculator's Convert menu to change {amount} dollars into euros at today's rate.")
    else:
        request = say(S.rng, "Switch the calculator to programmer mode.", "Put the calculator in its Programmer view so that I can enter hexadecimal numbers.")
    return Spec(request=request, steps=[], kind="infeasible", check=unchanged)
