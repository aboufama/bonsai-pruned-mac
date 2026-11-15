"""Planner-mode runs side by side: python -m taskenv.plan_tally /root/te-runs/pl-a /root/te-runs/pl-b [--seeds 9101]"""
import collections
import json
import sys


def why(e):
    return "never said done" if "done" in e["why"] else "stuck on one step" if e.get("stuck") else "out of steps" if e["steps"] >= e.get("limit", 15) else "wrong result"


def main():
    args = sys.argv[1:]
    seeds = None
    if "--seeds" in args:
        k = args.index("--seeds")
        seeds, args = {int(s) for s in args[k + 1:]}, args[:k]
    for path in args:
        eps = [json.loads(l) for l in open(path.rstrip("/") + "/episodes.jsonl")]
        eps = [e for e in eps if seeds is None or e["seed"] in seeds]
        for s in ("held_out", "test_apps", "train"):
            xs = [e for e in eps if e["set"] == s]
            if not xs:
                continue
            turns = [t for e in xs for t in e["turns"]]
            known = [t for t in turns if t["oracle_known"]]
            idle = sum(bool(t.get("valid")) and not t.get("changed") and (t["answer"] or {}).get("action") != "done" for t in turns)
            acts = collections.Counter((t["answer"] or {}).get("action", "none") for t in turns)
            print(f"{path.rstrip('/').split('/')[-1]} | {s} | {sum(e['ok'] for e in xs)}/{len(xs)} | fails {dict(collections.Counter(why(e) for e in xs if not e['ok']))} | "
                  f"steps {sum(e['steps'] for e in xs) / len(xs):.1f} | no-effect steps {idle}/{len(turns)} | invalid {sum(not t.get('valid', True) for t in turns)} | said done {sum(e['finished'] for e in xs)} | "
                  f"agrees {sum(bool(t['agrees']) for t in known)}/{len(known)} | ok: {[e['task'] for e in xs if e['ok']]} | actions {dict(acts.most_common(9))}")


if __name__ == "__main__":
    main()
