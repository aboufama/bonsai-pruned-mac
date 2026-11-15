"""Checks of the environment itself, no model needed.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python -m taskenv.selftest [--seeds 1 2 9101 ...] [--quick]

1. No two apps style the same CSS class (an app's stylesheet must not change another app).
2. Every task file says that it is test-only.
3. The oracle solves every task on every given seed, with no script error in the page.
4. The agent that does nothing passes exactly the tasks that are already done.
5. Episodes are reproducible: building the same task and seed twice gives the same start state
   and the same request.
6. Every action form of docs/ACTION_FORMAT.md is read and executed.
Exit code 0 only if everything holds.
"""
import argparse
import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TASKENV_STRICT", "1")
from taskenv import actions as A  # noqa: E402
from taskenv import agents, tasks  # noqa: E402
from taskenv.env import WEB, Env  # noqa: E402
from taskenv.run import run_episode  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def css_classes(path):
    css = re.sub(r"/\*.*?\*/", "", open(path).read(), flags=re.S)
    return {c for sel in re.findall(r"([^{}]+)\{", css) for c in re.findall(r"\.([a-zA-Z_][\w-]*)", sel)}


def check_css():
    shell = css_classes(os.path.join(WEB, "shell.css"))
    apps = {f[:-4]: css_classes(os.path.join(WEB, "apps", f)) - shell for f in sorted(os.listdir(os.path.join(WEB, "apps"))) if f.endswith(".css")}
    bad = []
    for a, b in itertools.combinations(apps, 2):
        # state words used only together with an app's own class (".bw-tab.on") are fine; a shared word of four letters or more with a dash is not
        both = {c for c in apps[a] & apps[b] if "-" in c}
        if both:
            bad.append(f"{a} and {b} both style {sorted(both)}")
    return bad


def check_notice():
    bad = []
    for d in ("", "tasks", "web", "web/apps"):
        for f in sorted(os.listdir(os.path.join(HERE, d))):
            p = os.path.join(HERE, d, f)
            if os.path.isfile(p) and f.endswith((".py", ".js", ".css", ".md", ".sh")) and "TEST" not in open(p).read(1500).upper():
                bad.append(f"{os.path.join(d, f)} does not say it is test-only near its top")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="*", type=int, default=tasks.DEV_SEEDS[:2] + tasks.TEST_SEEDS)
    ap.add_argument("--quick", action="store_true", help="one seed only")
    args = ap.parse_args()
    seeds = args.seeds[:1] if args.quick else args.seeds
    problems = check_css() + check_notice()
    ids = tasks.all_tasks()
    env, oracle, noop = Env(), agents.OracleAgent(), agents.NoopAgent()
    n = 0
    for seed in seeds:
        for tid in ids:
            ep = tasks.build(tid, seed)
            again = tasks.build(tid, seed)
            if json.dumps(ep.state, sort_keys=True) != json.dumps(again.state, sort_keys=True) or ep.request != again.request:
                problems.append(f"{tid} seed {seed}: not reproducible")
            o = run_episode(env, ep, oracle, 60)
            if not o["success"] or o["page_errors"]:
                problems.append(f"{tid} seed {seed}: oracle failed: {o['why']} {o['page_errors']}")
            z = run_episode(env, tasks.build(tid, seed), noop, 3)
            if z["success"] != (ep.kind == "already_done"):
                problems.append(f"{tid} seed {seed}: doing nothing {'passes' if z['success'] else 'fails'} a task of kind {ep.kind}")
            n += 1
    # every action form, on a live page
    ep = tasks.build(ids[0], seeds[0])
    env.reset(ep.state)
    from weightlab import actions as WA
    call = lambda **kw: "<tool_call>\n<function=computer_use>\n" + "".join(f"<parameter={k}>\n{v}\n</parameter>\n" for k, v in kw.items()) + "</function>\n</tool_call>"
    forms = [call(action="left_click", coordinate="[500, 500]"), call(action="double_click", coordinate="[500, 500]"), call(action="right_click", coordinate="[500, 500]"),
             call(action="triple_click", coordinate="[500, 500]"), call(action="middle_click", coordinate="[500, 500]"), call(action="mouse_move", coordinate="[400, 400]"),
             call(action="left_click_drag", start_coordinate="[300, 300]", coordinate="[600, 600]"), call(action="left_click_drag", coordinate="[300, 300]"),
             call(action="key", keys='["esc"]'), call(action="key", keys='["cmd", "shift", "n"]'), call(action="type", text="abc\n"),
             call(action="scroll", coordinate="[500, 500]", pixels="-5"), call(action="hscroll", coordinate="[500, 500]", pixels="3"), call(action="wait", time="1"),
             call(action="answer", text="hello"), call(action="terminate", status="success"), call(action="terminate", status="failure")]
    for text in forms:
        try:
            a = A.validate(A.from_call(WA.parse_answer(text), env.pointer))
            env.step(a)
        except Exception as e:
            problems.append(f"action form not executed: {text!r}: {e}")
    if env.errors():
        problems.append(f"page errors after the action forms: {env.errors()}")
    env.close()
    cats = {c: sum(1 for t in ids if tasks.TASKS[t]["category"] == c) for c in tasks.CATEGORIES}
    print(f"{len(ids)} tasks, {n} episodes on seeds {seeds}; by kind: {cats}")
    for p in problems:
        print("PROBLEM:", p)
    print("selftest:", "OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
