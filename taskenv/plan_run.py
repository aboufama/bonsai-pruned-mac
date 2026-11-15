"""Run a planner model in format v1 (control list, no screenshot) on simulator tasks. For a pod.

    # the honest numbers (never trained on): held-out task templates of the training apps, and the test apps
    python -m taskenv.plan_run --model qwen35-9b --set held_out test_apps --out /root/te-runs/pl-parent
    python -m taskenv.plan_run --model bonsai9b-new --patch <file> --tag orch-u3000 --set held_out test_apps --out /root/te-runs/pl-orch-u3000

    # rollouts for training (DAgger): fresh episodes on the training apps, new seeds
    python -m taskenv.plan_run --model bonsai9b-new --patch <file> --set train --singles 4 --pairs 300 --triples 100 --seed0 30001 --out /root/te-runs/roll-<name>

Per episode the oracle first solves it as planner steps (so that states can be recognised), then the model runs:
each turn it gets the system text, the user message of format v1 and the next_step tool; its step is carried out
by planmode.execute; a step that changes nothing is marked " (nothing changed)" in "Done so far", as the app does.
Output in --out (a run resumes from episodes.jsonl):
    episodes.jsonl        one line per episode: verdict of the checker, why, every turn (controls shown, raw answer,
                          parsed step, valid, changed, the oracle's step from that state or null, agreement)
    turns_rollout.jsonl   neutral planner rows of the states the model reached where the oracle knows the next step
                          (answer = the oracle's step); `meta.agrees` says whether the model did the same.
    turns_success.jsonl   the model's own turns from episodes the checker accepted (demonstrations)
    summary.json          success with a 95% interval by set, app and category; steps; invalid and no-effect steps
Rows carry split "train" only for --set train; for held_out and test_apps the split is "eval" (never train on them).
A state is one "the oracle knows" when the oracle's own run passes through it (same data and view of every app, same
front app), or when the goal is already reached (the right step is then `done`).
"""
import argparse
import collections
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * max(0, c - h), 1), round(100 * min(1, c + h), 1))


def sampled(model, messages, tools, k, temperature):
    """One answer drawn at a temperature (the wrapper of bench/models.py answers greedily)."""
    orig = model._generate

    def gen(inputs, max_new_tokens):
        n = inputs["input_ids"].shape[1]
        with model.torch.inference_mode():
            out = model.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, temperature=temperature, top_p=1.0, top_k=0, use_cache=True, eos_token_id=model.stop_ids)
        return out[0, n:], n
    model._generate = gen
    try:
        return model.chat(messages, tools=tools, max_new_tokens=k)
    finally:
        model._generate = orig


def episodes(a):
    from taskenv import planmode
    from taskenv.tasks import base
    sets, out = planmode.task_sets(), []
    for name in a.set:
        if name in ("held_out", "test_apps"):
            for tid in sets[name]:
                for seed in a.seeds or base.TEST_SEEDS:
                    out.append((name, [tid], int(seed)))
        else:
            assert a.seed0 >= 30001, "rollouts for training use seeds from 30001 (20001 up are the oracle rows)"
            import types
            from taskenv import plan_gen
            for tids, seed, _ in plan_gen.jobs(types.SimpleNamespace(split="train", seed0=a.seed0, singles=a.singles, pairs=a.pairs, triples=a.triples)):
                out.append(("train", tids, seed))
    if "train" in a.set:                                     # single tasks and chains mixed from the first episode on: a round can be cut short
        random.Random(a.seed0).shuffle(out)
    if a.shard:
        i, n = map(int, a.shard.split("/"))
        out = out[i::n]
    return out


def summarise(eps):
    def rate(xs):
        k, n = sum(e["ok"] for e in xs), len(xs)
        return {"n": n, "ok": k, "rate": round(100 * k / n, 1) if n else None, "ci95": wilson(k, n)}
    group = lambda key, xs: {k: rate([e for e in xs if key(e) == k]) for k in sorted({key(e) for e in xs})}
    out = {}
    for s in sorted({e["set"] for e in eps}):
        xs = [e for e in eps if e["set"] == s]
        turns = [t for e in xs for t in e["turns"]]
        known = [t for t in turns if t["oracle_known"]]
        secs = [t["seconds"] for t in turns if t.get("seconds")]
        out[s] = dict(rate(xs), by_app=group(lambda e: e["app"], xs), by_category=group(lambda e: e["category"], xs), by_kind=group(lambda e: e["kind"], xs),
                      steps_mean=round(sum(e["steps"] for e in xs) / max(1, len(xs)), 2), said_done=sum(e["finished"] for e in xs), turns=len(turns),
                      invalid_steps=sum(not t.get("valid", True) for t in turns), no_effect_steps=sum(bool(t.get("valid")) and not t.get("changed") and (t["answer"] or {}).get("action") != "done" for t in turns),
                      unreadable_answers=sum(t["answer"] is None for t in turns), oracle_known_turns=len(known), agrees_with_oracle=round(100 * sum(bool(t["agrees"]) for t in known) / max(1, len(known)), 1),
                      seconds_per_step=round(sum(secs) / max(1, len(secs)), 2), actions=dict(collections.Counter((t["answer"] or {}).get("action", "none") for t in turns).most_common()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="a key of bench/models.py, or 'oracle' (replays the oracle's steps: must score 100%%)")
    ap.add_argument("--patch")
    ap.add_argument("--tag", default="")
    ap.add_argument("--root", default=os.environ.get("BONSAI_ROOT", os.path.expanduser("~/bonsai")))
    ap.add_argument("--set", nargs="+", default=["held_out", "test_apps"], choices=["held_out", "test_apps", "train"])
    ap.add_argument("--seeds", nargs="*", default=[])
    ap.add_argument("--singles", type=int, default=2)
    ap.add_argument("--pairs", type=int, default=0)
    ap.add_argument("--triples", type=int, default=0)
    ap.add_argument("--seed0", type=int, default=30001)
    ap.add_argument("--max-steps", type=int, default=15)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    ap.add_argument("--pointer-model", help="finds `look` targets on a screenshot; without it a look is matched to the control names")
    ap.add_argument("--pointer-patch")
    ap.add_argument("--pointer-input", default="s1280")
    ap.add_argument("--shard", default="")
    ap.add_argument("--system-file", help="a file whose text replaces the shipped system text")
    ap.add_argument("--app-rules", action="store_true", help="the app's loop rules: no second Return in a row, a click without effect once more")
    ap.add_argument("--assistant", action="store_true", help="the planner inside the assistant: all the rules of build b336837 around it (planmode.rollout_app)")
    ap.add_argument("--noise", type=float, default=0.3, help="--model noisy-oracle: the chance of a wrong step at each turn (at most three an episode)")
    ap.add_argument("--resample", action="store_true", help="with --assistant: an answer equal to the step that just changed nothing is asked again at temperature 0.7")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from taskenv import planmode, policy
    from taskenv.env import Env
    out = os.path.expanduser(a.out)
    os.makedirs(out, exist_ok=True)
    todo = episodes(a)
    path = os.path.join(out, "episodes.jsonl")
    have = set()
    if os.path.exists(path):
        for l in open(path):
            e = json.loads(l)
            have.add((e["set"], e["task"], e["seed"]))
    name = a.model + ("+" + (a.tag or os.path.basename(a.patch)) if a.patch else "")
    json.dump({"argv": sys.argv, "model": name, "episodes": len(todo), "format": "planner v1 (e751270)", "system_file": a.system_file, "app_rules": a.app_rules, "assistant": "b336837" if a.assistant else None, "resample": a.resample, "host": os.uname().nodename}, open(os.path.join(out, "meta.json"), "w"), indent=1)
    system = open(os.path.expanduser(a.system_file)).read().strip() if a.system_file else None
    model = None if a.model in ("oracle", "noisy-oracle") else policy.load(a.model, a.root, patch=a.patch)
    pointer = None
    if a.pointer_model:
        p = policy.Pointer(policy.load(a.pointer_model, a.root, patch=a.pointer_patch), a.pointer_input)

        def pointer(image, words):
            r = p(image, words)
            return r.get("point") if isinstance(r, dict) else r
    env = Env()
    f, fr, fs = open(path, "a", buffering=1), open(os.path.join(out, "turns_rollout.jsonl"), "a", buffering=1), open(os.path.join(out, "turns_success.jsonl"), "a", buffering=1)
    t0 = time.time()
    for n, (set_, tids, seed) in enumerate(todo):
        task = "+".join(tids)
        if (set_, task, seed) in have:
            continue
        try:
            ep = planmode.build(tids, seed)
            try:
                rows, _, ok, _ = planmode.oracle_rows(env, ep, random.Random(f"plan_run/{task}/{seed}"), "front", 0.0)
                rows = rows if ok else []
            except planmode.Untranslatable:
                rows = []
            if a.model == "noisy-oracle":
                chat = planmode.NoisyOracle(random.Random(f"noisy/{task}/{seed}"), rate=a.noise)
            elif model is None:
                script, final = iter(rows), (rows[-1] if rows else {"answer": {"action": "done", "text": "Done."}})
                chat = lambda messages, tools, k, temperature=None: {"tool_calls": [{"function": {"name": "next_step", "arguments": next(script, final)["answer"]}}], "raw": "oracle"}
            else:
                def chat(messages, tools, k, temperature=None):
                    for attempt in range(40):             # the GPU is shared: when another job fills it, wait and ask again
                        try:
                            if temperature:
                                return sampled(model, messages, tools, k, temperature)
                            return model.chat(messages, tools=tools, max_new_tokens=k)
                        except RuntimeError as err:
                            if "out of memory" not in str(err).lower() or attempt == 39:
                                raise
                            import torch
                            torch.cuda.empty_cache()
                            print(f"GPU full, waiting ({attempt + 1})", file=sys.stderr, flush=True)
                            time.sleep(30)
            if a.assistant:
                e = planmode.rollout_app(env, ep, chat, rows, pointer=pointer, max_new_tokens=a.max_new_tokens, system=system, resample=a.resample)
            else:
                e = planmode.rollout(env, ep, chat, rows, pointer=pointer, max_steps=a.max_steps, max_new_tokens=a.max_new_tokens, system=system, app_rules=a.app_rules)
        except Exception as err:
            print(f"{task} seed {seed}: {type(err).__name__}: {err}"[:300], file=sys.stderr, flush=True)
            try:
                env.close()
            except Exception:
                pass
            env = Env()
            continue
        e.update(set=set_, model=name, oracle_steps=len(rows))
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        split = "train" if set_ == "train" else "eval"
        for t in e["turns"]:
            row = {"id": f"roll-{name}-{task}-{seed}-{t['k']}", "split": split, "task": e["request"], "apps": t["apps"], "front_app": t["front_app"], "window": t["front_app"], "done": t["done"], "controls": t["controls"],
                   "meta": {"tasks": tids, "seed": seed, "step": t["k"], "set": set_, "model": name, "model_answer": t["answer"], "agrees": t["agrees"], "episode_ok": e["ok"]}}
            if t["oracle_known"]:
                fr.write(json.dumps(dict(row, source="taskenv-noisy-oracle" if a.model == "noisy-oracle" else "taskenv-rollout", answer=t["oracle"]), ensure_ascii=False) + "\n")
            if e["ok"] and t["answer"] and a.model != "noisy-oracle":
                fs.write(json.dumps(dict(row, source="taskenv-rollout-success", answer=t["answer"]), ensure_ascii=False) + "\n")
        print(f"{n + 1}/{len(todo)} {set_} {task} seed {seed}: {'ok' if e['ok'] else 'FAIL'} in {e['steps']} steps ({e['why'][:60]}) {time.time() - t0:.0f}s", flush=True)
    env.close()
    eps = [json.loads(l) for l in open(path)]
    summary = dict(summarise(eps), model=name)
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1, ensure_ascii=False)
    for s, d in summary.items():
        if isinstance(d, dict):
            print(f"done: {name} {s}: {d['ok']}/{d['n']} = {d['rate']}% (95% {d['ci95'][0]} to {d['ci95'][1]}), {d['steps_mean']} steps, {d['seconds_per_step']} s/step, agrees with the oracle on {d['agrees_with_oracle']}% of {d['oracle_known_turns']} known states")


if __name__ == "__main__":
    main()
