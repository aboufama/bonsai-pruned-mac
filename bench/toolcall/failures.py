#!/usr/bin/env python3
"""Print failed cases of an evaluation run next to what the model did.

    python3 failures.py --cases runs/dev_20261114 --label bonsai2-9b [--category g_typing] [--limit 20]
"""
import argparse
import json
import os


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def short(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n] + "..."


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--category", default=None)
    ap.add_argument("--kind", default=None, help="only this failure kind, e.g. wrong_value")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--width", type=int, default=700)
    args = ap.parse_args()
    cases = {c["id"]: c for c in load(os.path.join(args.cases, "cases.jsonl"))}
    shown = 0
    for r in load(os.path.join(args.cases, f"results_{args.label}.jsonl")):
        c = cases.get(r["id"])
        if c is None or r["pass"]:
            continue
        if args.category and c["category"] != args.category:
            continue
        if args.kind and r["kind"] != args.kind:
            continue
        m = c["meta"]
        print(f"--- {c['id']} [{c['category']}] {m.get('intent')} style={m.get('style')} "
              f"{'trap=' + m['trap'] if 'trap' in m else ''} today={m.get('today')}")
        print("user:    ", short(c["messages"][1]["content"], args.width))
        print("expected:", short(json.dumps(c["expected"], ensure_ascii=False), args.width))
        for i, t in enumerate(r["turns"], 1):
            calls = "; ".join(f"{x['name']}({x['arguments']})" for x in t["tool_calls"]) or "(no call)"
            print(f"turn {i}:  ", short(calls, args.width), "| text:", short(t.get("content") or "", 200))
        print(f"verdict:  {r['kind']}: {short(r['reason'], 300)}")
        shown += 1
        if shown >= args.limit:
            break
    print(f"({shown} shown)")


if __name__ == "__main__":
    main()
