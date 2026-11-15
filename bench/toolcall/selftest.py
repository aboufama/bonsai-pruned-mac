#!/usr/bin/env python3
"""Self-test of the generator and the scorer. Uses no model and no network.

    python3 selftest.py            # pure in-process checks
    python3 selftest.py --http     # also runs the oracle through a local HTTP endpoint

Checks
  1. split pools are disjoint; breadth minimums hold
  2. generation is deterministic (same bytes twice; a case does not depend on --n)
  3. every generated case is internally consistent
  4. an oracle that replays the expected behaviour scores 100%
  5. a model that never calls a tool scores exactly the share of "no call" cases
  6. harmless variations of a correct answer still pass
  7. every kind of wrong answer fails
"""
import copy
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import generate  # noqa: E402
from scoring import run_case, validate_case  # noqa: E402

SEEDS = (7, 20261114)
N = 1200


def tool_call(name, args, n=0):
    return {"id": f"call_{n}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def turn_plan(case):
    """The expected calls of each turn, as a list of lists."""
    exp = case["expected"]
    if exp.get("no_call"):
        return []
    if "calls" in exp:
        return [exp["calls"]]
    return [st["calls"] for st in exp["steps"]]


class Scripted:
    """A fake model that answers turn k with the k-th list of calls (then with text)."""

    def __init__(self, turns):
        self.turns, self.k = turns, 0

    def __call__(self, messages, tools):
        calls = self.turns[self.k] if self.k < len(self.turns) else []
        self.k += 1
        return {"role": "assistant", "content": "" if calls else "Done.",
                "tool_calls": [tool_call(c["name"], c["arguments"], i) for i, c in enumerate(calls)]}


def oracle(case):
    return Scripted(copy.deepcopy(turn_plan(case)))


def never(messages, tools):
    return {"role": "assistant", "content": "Could you tell me more?"}


def schema_of(case, name):
    return next(t for t in case["tools"] if t["function"]["name"] == name)["function"]["parameters"]


# ---- variations that must still pass ---------------------------------------

def harmless(case, rng_i):
    """Yield (label, turns) variants that are equivalent to the expected behaviour."""
    plan = turn_plan(case)
    if not plan:
        return
    # 1. scalar types as strings, enums upper-cased, strings padded with blanks
    v = copy.deepcopy(plan)
    for turn in v:
        for c in turn:
            props = schema_of(case, c["name"])["properties"]
            for k, val in list(c["arguments"].items()):
                t = props[k]["type"]
                rule = case["arg_match"].get(c["name"], {}).get(k, {})
                if t in ("integer", "number"):
                    c["arguments"][k] = str(val)
                elif t == "boolean":
                    c["arguments"][k] = "true" if val else "false"
                elif t == "string" and "enum" in props[k]:
                    c["arguments"][k] = "  " + val.upper() + " "
                elif t == "string" and rule.get("mode") == "contains":
                    c["arguments"][k] = "Note: " + val.upper() + "!!"
                elif t == "string":
                    c["arguments"][k] = "  " + val.replace(" ", "   ") + " "
                elif t == "array" and rule.get("unordered", True):
                    c["arguments"][k] = list(reversed(val))
    yield "types-as-strings/enum-case/whitespace/array-order", v
    # 2. reversed order of independent calls
    if any(len(t) > 1 for t in plan):
        yield "parallel-order", [list(reversed(t)) for t in copy.deepcopy(plan)]
    # 3. optional arguments: defaults filled in, default-valued ones left out, null for the rest
    v = copy.deepcopy(plan)
    changed = False
    for turn in v:
        for c in turn:
            params = schema_of(case, c["name"])
            for k, rule in case["arg_match"].get(c["name"], {}).items():
                if not rule.get("optional"):
                    continue
                if k not in c["arguments"]:
                    c["arguments"][k] = rule["default"] if "default" in rule else None
                    changed = True
                elif "default" in rule and rule["default"] == c["arguments"][k]:
                    del c["arguments"][k]
                    changed = True
            assert params
    if changed:
        yield "optional-defaults", v


# ---- variations that must fail ----------------------------------------------

def harmful(case):
    plan = turn_plan(case)
    if not plan:
        some = case["tools"][0]["function"]["name"]
        yield "call-when-none-expected", [[{"name": some, "arguments": {}}]]
        return
    first = plan[0][0]
    props = schema_of(case, first["name"])["properties"]
    required = schema_of(case, first["name"]).get("required", [])

    def variant(mutate):
        v = copy.deepcopy(plan)
        mutate(v[0][0], v)
        return v

    yield "wrong-name", variant(lambda c, v: c.update(name=c["name"] + "_x"))
    yield "unknown-argument", variant(lambda c, v: c["arguments"].update(zzz_extra=1))
    yield "extra-call", variant(lambda c, v: v[0].append(copy.deepcopy(c)))
    if len(plan[0]) > 1:
        yield "missing-call", variant(lambda c, v: v[0].pop())
    if len(plan) > 1:
        yield "stops-early", copy.deepcopy(plan[:-1])
        yield "extra-call-after-last-step", copy.deepcopy(plan) + [[copy.deepcopy(plan[-1][0])]]
        skip = copy.deepcopy(plan)
        skip[0], skip[1] = skip[1], skip[0]
        yield "steps-out-of-order", skip
    # multi-step: use the id of a different entry of a returned candidate list
    if "steps" in case["expected"]:
        steps = case["expected"]["steps"]
        for si in range(1, len(steps)):
            for value in steps[si - 1]["tool_results"][0].values():
                if isinstance(value, list):
                    args = steps[si]["calls"][0]["arguments"]
                    for k, v in args.items():
                        others = [x for e in value for kk, x in e.items()
                                  if kk.lower().endswith("id") and x != v]
                        if isinstance(v, str) and len(others) == len(value) - 1:
                            w = copy.deepcopy(plan)
                            w[si][0]["arguments"][k] = others[0]
                            yield "wrong-list-entry", w
    yield "no-call-at-all", []
    yield "arguments-not-json", "RAW"
    for k, val in first["arguments"].items():
        rule = case["arg_match"].get(first["name"], {}).get(k, {})
        t = props[k]["type"]
        if k in required:
            yield f"missing-required:{t}", variant(lambda c, v, k=k: c["arguments"].pop(k))
        if rule.get("mode") == "any":
            continue
        if t in ("integer", "number"):
            yield f"wrong-value:{t}", variant(lambda c, v, k=k: c["arguments"].update({k: c["arguments"][k] + 1}))
        elif t == "boolean":
            yield "wrong-value:boolean", variant(lambda c, v, k=k: c["arguments"].update({k: not c["arguments"][k]}))
        elif t == "string" and "enum" in props[k]:
            other = next(e for e in props[k]["enum"] if e != val)
            yield "wrong-value:enum", variant(lambda c, v, k=k, o=other: c["arguments"].update({k: o}))
            yield "not-in-enum", variant(lambda c, v, k=k: c["arguments"].update({k: "zzz"}))
        elif t == "string":
            yield "wrong-value:string", variant(lambda c, v, k=k: c["arguments"].update({k: "zzz"}))
        elif t == "array":
            yield "wrong-value:array", variant(lambda c, v, k=k: c["arguments"].update({k: c["arguments"][k][:-1]}))
            yield "array-as-string", variant(
                lambda c, v, k=k: c["arguments"].update({k: json.dumps(c["arguments"][k])}))
            if not rule.get("unordered", True):
                yield "ordered-array-reversed", variant(
                    lambda c, v, k=k: c["arguments"].update({k: list(reversed(c["arguments"][k]))}))
        elif t == "object":
            def drop(c, v, k=k):
                obj = c["arguments"][k]
                obj.pop(sorted(obj)[0])
            yield "wrong-value:object", variant(drop)
    # an optional argument the user never mentioned, filled with a non-default value
    for k, rule in case["arg_match"].get(first["name"], {}).items():
        if rule.get("optional") and k not in first["arguments"] and props[k]["type"] in ("integer", "string"):
            bad = 987654 if props[k]["type"] == "integer" else "zzz"
            yield "invented-optional", variant(lambda c, v, k=k, b=bad: c["arguments"].update({k: b}))


def check_list_results(case):
    """When a tool result is a list of candidates, the id used next must occur in exactly one entry."""
    steps = case["expected"]["steps"]
    for prev, st in zip(steps, steps[1:]):
        for res in prev["tool_results"]:
            for value in res.values():
                if isinstance(value, list):
                    used = {v for v in st["calls"][0]["arguments"].values() if isinstance(v, str)}
                    hits = [e for e in value
                            if used & {v for k, v in e.items() if k.lower().endswith("id")}]
                    assert len(hits) == 1 and 3 <= len(value) <= 4, case["id"]


def run_scripted(case, turns):
    if turns == "RAW":
        first = turn_plan(case)[0][0]

        def chat(messages, tools):
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"id": "c", "type": "function",
                                    "function": {"name": first["name"], "arguments": "{not json"}}]}
        return run_case(case, chat)
    return run_case(case, Scripted(turns))


def http_roundtrip(n=160):
    """Serve oracle answers over a local OpenAI-style HTTP endpoint and score them with the same
    client code evaluate.py uses. Proves request building, tool-result playback and parsing end to end."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from evaluate import make_chat

    cases = [json.loads(generate.dumps(generate.make_case(3, "dev", i))) for i in range(n)]
    by_user = {c["messages"][1]["content"]: c for c in cases}
    assert len(by_user) == len(cases)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body["temperature"] == 0 and body["tools"]
            msgs = body["messages"]
            case = by_user[msgs[1]["content"]]
            turn = sum(1 for m in msgs if m["role"] == "assistant")
            assert all(m.get("tool_call_id") for m in msgs if m["role"] == "tool")
            plan = turn_plan(case)
            calls = plan[turn] if turn < len(plan) else []
            msg = {"role": "assistant", "content": None if calls else "Done.",
                   "tool_calls": [tool_call(c["name"], c["arguments"], i) for i, c in enumerate(calls)]}
            out = json.dumps({"choices": [{"index": 0, "message": msg, "finish_reason": "stop"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        chat = make_chat(f"http://127.0.0.1:{server.server_port}/v1", "oracle", 512, 30, {})
        passed = sum(run_case(c, chat)["pass"] for c in cases)
    finally:
        server.shutdown()
    assert passed == n, (passed, n)
    print(f"[8] HTTP round trip through evaluate.py's client: oracle {passed}/{n}")


def main():
    t0 = time.time()
    inv = generate.assert_disjoint()
    st = generate.stats()
    domains = sum(v["domains"] for v in st.values())
    schemas = sum(v["base_tool_schemas"] for v in st.values())
    assert domains >= 30 and schemas >= 150, (domains, schemas)
    for name, n in (("terse", 0),):
        assert all(len(generate.vocab(s).ph["wrappers"][name]) >= 2 for s in generate.SPLITS)
    print(f"[1] splits are disjoint ({', '.join(inv['dev'])}); "
          f"{domains} domains, {schemas} hand-written base tool schemas")
    for s, v in st.items():
        print(f"      {s:5s} {v}")

    # determinism and independence from --n
    a = [generate.dumps(generate.make_case(5, "test", i)) for i in range(300)]
    b = [generate.dumps(generate.make_case(5, "test", i)) for i in range(120)]
    generate._VOCABS.clear()
    c = [generate.dumps(generate.make_case(5, "test", i)) for i in range(300)]
    assert a == c and a[:120] == b
    print("[2] deterministic: identical output on regeneration, sha256 of 300 test cases =",
          hashlib.sha256("\n".join(a).encode()).hexdigest()[:16])

    totals = {"cases": 0, "oracle": 0, "never": 0, "no_call": 0, "harmless": 0, "harmful": 0}
    seen_harmless, seen_harmful, names, signatures = {}, {}, set(), set()
    cats = {}
    for split in generate.SPLITS:
        for seed in SEEDS:
            for i in range(N):
                case = generate.make_case(seed, split, i)
                case = json.loads(generate.dumps(case))  # score what is actually written to disk
                validate_case(case)
                assert case["split"] == split and case["meta"]["seed"] == seed
                totals["cases"] += 1
                cats[case["category"]] = cats.get(case["category"], 0) + 1
                for t in case["tools"]:
                    f = t["function"]
                    names.add(f["name"])
                    for k, v in f["parameters"]["properties"].items():   # optional booleans declare a default
                        if v["type"] == "boolean" and k not in f["parameters"]["required"]:
                            assert "default" in v, (case["id"], f["name"], k)
                    signatures.add((f["name"], tuple(sorted(
                        (k, v["type"]) for k, v in f["parameters"]["properties"].items())),
                        tuple(sorted(f["parameters"]["required"]))))
                if case["category"] == "b_selection":
                    assert 7 <= len(case["tools"]) <= 13, (case["id"], len(case["tools"]))
                if case["category"] == "d_multistep":
                    check_list_results(case)
                r = run_case(case, oracle(case))
                assert r["pass"], f"oracle failed on {case['id']}: {r['reason']}"
                totals["oracle"] += 1
                no_call = bool(case["expected"].get("no_call"))
                totals["no_call"] += no_call
                r = run_case(case, never)
                assert r["pass"] == no_call, f"never-call baseline wrong on {case['id']}"
                totals["never"] += r["pass"]
                for label, turns in harmless(case, i):
                    r = run_scripted(case, turns)
                    assert r["pass"], f"harmless variant {label!r} failed on {case['id']}: {r['reason']}"
                    seen_harmless[label] = seen_harmless.get(label, 0) + 1
                    totals["harmless"] += 1
                for label, turns in harmful(case):
                    r = run_scripted(case, turns)
                    assert not r["pass"], f"harmful variant {label!r} passed on {case['id']}"
                    seen_harmful[label] = seen_harmful.get(label, 0) + 1
                    totals["harmful"] += 1
    n = totals["cases"]
    assert totals["oracle"] == n
    assert totals["never"] == totals["no_call"]
    print(f"[3] {n} cases generated and validated ({N} x {len(SEEDS)} seeds x 3 splits); "
          f"{len(names)} distinct tool names, {len(signatures)} distinct tool schemas seen")
    print("      per category:", dict(sorted(cats.items())))
    print(f"[4] oracle: {totals['oracle']}/{n} = 100.0%")
    print(f"[5] never-call baseline: {totals['never']}/{n} = {100 * totals['never'] / n:.2f}% "
          f"== share of no-call cases {100 * totals['no_call'] / n:.2f}%")
    print(f"[6] {totals['harmless']} harmless variants all pass:", dict(sorted(seen_harmless.items())))
    print(f"[7] {totals['harmful']} harmful variants all fail:")
    for k, v in sorted(seen_harmful.items()):
        print(f"      {k:<32}{v}")
    if "--http" in sys.argv:
        http_roundtrip()
    print(f"selftest OK in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
