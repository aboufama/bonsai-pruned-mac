"""Run an agent through the tasks and save every step.

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python -m taskenv.run --agent oracle --seeds dev --out runs/oracle-dev
    python -m taskenv.run --agent random --seeds test --out runs/random
    python -m taskenv.run --agent guided --model bonsai9b-new --input s1280 --seeds test --out runs/guided-bonsai9b-new-s1280
    python -m taskenv.run --agent agent  --model qwen35-9b   --input s1280 --seeds test --out runs/agent-qwen35-9b-s1280

--tasks takes fnmatch patterns ("files.*"); --seeds takes "dev", "test" or numbers.
Output in --out:
    episodes.jsonl   one line per episode: request, every step (raw model output, parsed action,
                     seconds, error), final verdict and the checker's reason
    shots/           the screenshot before every step and after the last one (JPEG, 1440 x 900)
    meta.json        command, agent, model, input size, git commit, host
A run resumes: episodes already in episodes.jsonl are skipped.

Before a model is run on an episode the oracle solves the same episode in the same browser; an
episode the oracle cannot solve stops the run (the fault is then in the task or the environment,
not in the model). Its action count is recorded as the number of steps the task needs.
"""
import argparse
import fnmatch
import json
import math
import os
import platform
import subprocess
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv import actions as A  # noqa: E402
from taskenv import agents, tasks  # noqa: E402
from taskenv.env import Env  # noqa: E402
from taskenv.oracle import Reveal  # noqa: E402

SHOT_SIZE, SHOT_QUALITY = (1152, 720), 66        # the saved copy of each screenshot (the model is shown the full one)
STUCK = 3                                        # agent mode: identical actions in a row on an unchanged screen before the episode is cut


def default_limit(ep):
    """Step limit of agent mode: one and a half times the steps of the solution, plus three
    (a Reveal counts as two wheel moves). A one-click task gets 5 steps, a seven-step task 14."""
    n = sum(2 if isinstance(s, Reveal) else 1 for s in ep.steps)
    return ep.limit or math.ceil(1.5 * n) + 3


def run_episode(env, ep, agent, limit, shots=None):
    env.reset(ep.state)
    init = env.state()
    agent.start(ep, env)
    steps, final, t0 = [], None, time.time()
    tag = f"{ep.task}__{ep.seed}"

    def shot(k):
        if not shots and not getattr(agent, "needs_image", True):
            return None, None                                   # the scripted agents do not look
        image = env.screenshot()
        name = None
        if shots:
            name = f"{tag}__{k:02d}.jpg"
            image.resize(SHOT_SIZE, Image.BILINEAR).save(os.path.join(shots, name), quality=SHOT_QUALITY)
        return image, name

    stuck, seen = False, []
    for k in range(limit):
        image, name = shot(k)
        if getattr(agent, "name", "") == "agent":
            # Greedy decoding on an unchanged screen: once the model has written the same action
            # three times in a row without the apps changing, it is shown the same screen again.
            # The episode ends there, as if it had run out of steps.
            snap = env.state()
            snap.pop("events", None)
            seen.append(json.dumps(snap, sort_keys=True))
            last = [json.dumps(s["action"], sort_keys=True) for s in steps[-STUCK:]]
            if len(last) == STUCK and len(set(last)) == 1 and steps[-1]["action"] is not None and len(set(seen[-STUCK - 1:])) == 1:
                stuck = True
                break
        t = time.perf_counter()
        try:
            r = agent.act(image, k)
        except StopIteration:
            break
        except Exception as e:                                  # the oracle could not find its element, or a model call failed
            steps.append({"k": k, "shot": name, "seconds": round(time.perf_counter() - t, 3), "raw": "", "action": None,
                          "error": f"{type(e).__name__}: {e}", "fatal": True})
            break
        seconds = time.perf_counter() - t
        a, err = r.get("action"), r.get("error")
        if a is not None:
            try:
                A.validate(a)
            except ValueError as e:
                a, err = None, str(e)
        step = {"k": k, "shot": name, "seconds": round(seconds, 3), "raw": r.get("raw", ""), "action": a, "error": err}
        step.update({key: r[key] for key in ("instruction", "inside", "boxes", "scripted", "model_seconds", "prompt_tokens", "new_tokens", "call", "snapped", "check", "retry", "read_tps", "write_tps", "peak_memory_gb", "think_tokens", "thinking", "read_seconds", "head_ms", "click_logit", "pre", "planner_seconds", "pointer_seconds") if key in r})
        steps.append(step)
        if a is None:
            continue
        if a["type"] == "done":
            final = a
            break
        t = time.perf_counter()
        try:
            env.step(a)
        except Exception as e:                                  # an action the browser refused
            step["error"] = f"{type(e).__name__}: {e}"
        step["env_seconds"] = round(time.perf_counter() - t, 3)
    _, last = shot(len(steps))
    st = env.state()
    ok, why = ep.check(st, init)
    why = "" if ok else why
    if steps and steps[-1].get("fatal"):
        ok, why = False, steps[-1]["error"]
    stopped = final is not None
    status = final.get("status", "done") if final else None
    if ep.kind == "already_done":
        if ok and not stopped:
            ok, why = False, "did not stop"
        elif ok and status == "infeasible":
            ok, why = False, "said it cannot be done; it was already done"
    elif ep.kind == "infeasible":
        if ok and status != "infeasible":
            ok, why = False, "did not say that it cannot be done"
    acted = [s for s in steps if s["action"] and s["action"]["type"] != "done"]
    return {"task": ep.task, "seed": ep.seed, "app": ep.app, "category": ep.category, "kind": ep.kind, "request": ep.request,
            "limit": limit, "success": bool(ok), "why": why, "stopped": stopped, "status": status, "stuck": stuck,
            "n_steps": len(steps), "n_actions": len(acted), "invalid": sum(1 for s in steps if s["action"] is None),
            "seconds": round(time.time() - t0, 2), "steps": steps, "last_shot": last, "page_errors": env.errors(),
            "events": st.get("events", [])[-40:]}


def pick_tasks(patterns):
    ids = tasks.all_tasks()
    if not patterns:
        return ids
    return [i for i in ids if any(fnmatch.fnmatchcase(i, p) for p in patterns)]


def pick_seeds(spec):
    out = []
    for s in spec:
        out += tasks.DEV_SEEDS if s == "dev" else tasks.TEST_SEEDS if s == "test" else [int(s)]
    return out


def git_commit():
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        return open(os.path.join(here, "COMMIT")).read().strip()
    except OSError:
        return subprocess.run(["git", "-C", here, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["oracle", "noop", "random", "guided", "agent", "orch"],
                    help="orch = agent mode with two models: --model is the orchestrator (next_step calls), the pointer is --pointer-model or the same model")
    ap.add_argument("--pointer-model")
    ap.add_argument("--pointer-patch")
    ap.add_argument("--pointer-head")
    ap.add_argument("--pointer-input", help="input size for the pointer when it differs from the orchestrator's (--input)")
    ap.add_argument("--tasks", nargs="*", default=[])
    ap.add_argument("--seeds", nargs="*", default=["dev"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--model")
    ap.add_argument("--root", default=os.environ.get("BONSAI_ROOT", os.path.expanduser("~/bonsai")))
    ap.add_argument("--patch")
    ap.add_argument("--head", help="the pointing decoder file, for --model mlx-4b-head")
    ap.add_argument("--tag", default="")
    ap.add_argument("--input", default="s1280")
    ap.add_argument("--ask", default="point", choices=["point", "tool"], help="guided mode: plain pointing prompt or the point tool call")
    ap.add_argument("--prompt", default="rules", choices=["rules", "plain"], help="agent mode: see taskenv/policy.py")
    ap.add_argument("--thinking", action="store_true", help="agent mode, MLX models: let the model reason before each action")
    ap.add_argument("--snap", action="store_true", help="guided mode: move a point that is on no control onto the nearest control")
    ap.add_argument("--check", nargs="?", const="ask", default=None, choices=["ask", "effect"],
                    help="guided mode, after each pointing step: ask = the model answers yes / no / unsure and points once more on no; "
                         "effect = when nothing visible changed, a second look at the enlarged area around the first point")
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--no-oracle-check", action="store_true")
    ap.add_argument("--needed-from", help="episodes.jsonl of an oracle run of the same code on the same machine: its step counts are used "
                                          "and the oracle is not run again before each episode (every episode must be in it, passed)")
    ap.add_argument("--shard", default="", help="i/n: run every n-th episode starting at i")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    shots = None if args.no_shots else os.path.join(args.out, "shots")
    if shots:
        os.makedirs(shots, exist_ok=True)
    path = os.path.join(args.out, "episodes.jsonl")
    done = set()
    if os.path.exists(path):
        for line in open(path):
            try:
                r = json.loads(line)
                done.add((r["task"], r["seed"]))
            except ValueError:
                pass
    todo = [(t, s) for s in pick_seeds(args.seeds) for t in pick_tasks(args.tasks)]
    if args.agent == "guided":                                  # only tasks whose solution has something to point at
        points = {t: any(step.pointing for step in tasks.build(t, tasks.DEV_SEEDS[0]).steps) for t in {t for t, _ in todo}}
        todo = [(t, s) for t, s in todo if points[t]]
    if args.shard:
        i, n = (int(v) for v in args.shard.split("/"))
        todo = todo[i::n]

    model = None
    if args.agent == "orch":
        from taskenv import policy
        model = policy.load(args.model, args.root, patch=args.patch)
        pm = policy.load(args.pointer_model, args.root, patch=args.pointer_patch, **({"head": args.pointer_head} if args.pointer_head else {})) if args.pointer_model else model
        agent = policy.OrchestratedAgent(model, policy.Pointer(pm, args.pointer_input or args.input, "point"), args.input, snap=args.snap)
        args.agent = "agent"                                      # same limits, cut-off and tables as agent mode
        orch = {"orchestrated": True, "pointer_model": args.pointer_model or args.model, "pointer_patch": args.pointer_patch if args.pointer_model else args.patch,
                "pointer_head": args.pointer_head, "pointer_input": args.pointer_input or args.input}
    elif args.agent in ("guided", "agent"):
        from taskenv import policy
        model = policy.ScriptedModel() if args.model == "scripted" else policy.load(args.model, args.root, patch=args.patch, **({"head": args.head} if args.head else {}))
        agent = (agents.GuidedAgent(policy.Pointer(model, args.input, args.ask), snap=args.snap, check=args.check) if args.agent == "guided"
                 else policy.ModelAgent(model, args.input, args.prompt, thinking=args.thinking))
    else:
        agent = {"oracle": agents.OracleAgent, "noop": agents.NoopAgent, "random": agents.RandomAgent}[args.agent]()
    orch = locals().get("orch") or {}
    meta = {"argv": sys.argv, **orch, "agent": args.agent, "model": args.model, "patch": args.patch, "head": args.head, "tag": args.tag, "input": args.input, "ask": args.ask, "prompt": args.prompt, "snap": args.snap, "check": args.check, "aids_version": 2, "thinking": args.thinking, "shard": args.shard,
            "seeds": pick_seeds(args.seeds), "n_episodes": len(todo), "host": platform.node(), "git_commit": git_commit(),
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model_info": model.describe() if model else None}
    known = {}
    if args.needed_from:
        for line in open(args.needed_from):
            r = json.loads(line)
            if r["success"] and not r["page_errors"]:
                known[(r["task"], r["seed"])] = (r["n_actions"], r["request"])
        meta["needed_from"] = args.needed_from
    meta["tasks"] = len({t for t, _ in todo})
    json.dump(meta, open(os.path.join(args.out, "meta.json"), "w"), indent=1, default=str)
    env, oracle = Env(), agents.OracleAgent()
    n = wins = 0
    t0 = time.time()
    with open(path, "a") as f:
        for tid, seed in todo:
            if (tid, seed) in done:
                continue
            ep = tasks.build(tid, seed)
            needed = None
            if (tid, seed) in known and args.agent != "oracle":
                needed, request = known[(tid, seed)]
                if request != ep.request:
                    raise SystemExit(f"{tid} seed {seed}: the oracle run was made on a different episode ({request!r} / {ep.request!r})")
            elif args.needed_from and args.agent != "oracle":
                raise SystemExit(f"{tid} seed {seed} is not in {args.needed_from}, or the oracle failed on it")
            elif not args.no_oracle_check or args.agent == "oracle":
                o = run_episode(env, ep, oracle, 60, shots if args.agent == "oracle" else None)
                needed = o["n_actions"]
                if not o["success"] or o["page_errors"]:
                    print(f"ORACLE FAILED {tid} seed {seed}: {o['why']} {o['page_errors']}", flush=True)
                    if args.agent != "oracle":
                        raise SystemExit(2)
            if args.agent == "oracle":
                r = o
            else:
                limit = agents.guided_limit(ep, bool(args.check)) if args.agent == "guided" else default_limit(ep)
                r = run_episode(env, ep, agent, limit, shots)
            r["needed"] = needed
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            wins += r["success"]
            print(f"[{args.agent}{' ' + args.model if args.model else ''}] {tid} seed {seed}: {'PASS' if r['success'] else 'FAIL'}"
                  f" ({r['n_actions']} actions, {r['seconds']} s){'' if r['success'] else '  ' + r['why']}   running {wins}/{n}", flush=True)
    env.close()
    if model:
        model.close()
    print(f"done: {wins}/{n} in {time.time() - t0:.0f} s -> {path}", flush=True)


if __name__ == "__main__":
    main()
