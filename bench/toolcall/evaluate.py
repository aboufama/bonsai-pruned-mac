#!/usr/bin/env python3
"""Evaluate a model served behind an OpenAI-compatible endpoint.

    python3 evaluate.py --cases runs/dev_20261114 --base-url http://127.0.0.1:8121/v1 --label bonsai9b

Reads DIR/cases.jsonl, writes DIR/results_<label>.jsonl (one line per case,
appended as cases finish, so an interrupted run can be resumed by running the
same command again) and prints overall accuracy plus accuracy per category.
"""
import argparse
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scoring import run_case  # noqa: E402


def make_chat(base_url, model, max_tokens, timeout, extra, api_key=None):
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    def chat(messages, tools):
        body = {"model": model, "messages": messages, "tools": tools, "temperature": 0,
                "max_tokens": max_tokens, "parallel_tool_calls": True,
                "chat_template_kwargs": {"enable_thinking": False}}
        body.update(extra)
        data = json.dumps(body).encode()
        last = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, data, headers)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    out = json.load(r)
                return out["choices"][0]["message"]
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}"
                if e.code < 500 and e.code != 429:
                    break
            except Exception as e:  # noqa: BLE001  (timeouts, connection resets)
                last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(last)

    return chat


def case_sha(case):
    """Fingerprint of a case. Stored with each result so that a result is only reused on resume
    if the case it was computed for is still exactly the same."""
    return hashlib.sha256(json.dumps(case, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def detail(case):
    """Finer-grained label inside a category, taken from the case's meta."""
    m, cat = case["meta"], case["category"]
    if cat == "b_selection":
        return f"twin={m.get('twin', 'none')}"
    if cat == "c_parallel":
        return f"{m.get('n_calls')} calls"
    if cat == "d_multistep":
        return f"{m.get('n_steps')} steps" + (", list result" if m.get("list_results") else "")
    if cat == "f_irrelevant":
        return m.get("variant", "?")
    if cat == "g_typing":
        return m.get("trap", "?")
    if cat == "h_computer":
        return m.get("intent", "?")
    return "all"


def summarise(cases, results):
    """Accuracy tables over the given cases. Missing results are not counted."""
    by_id = {r["id"]: r for r in results}
    rows = [(c, by_id[c["id"]]) for c in cases if c["id"] in by_id]

    def table(key):
        agg = {}
        for c, r in rows:
            k = key(c)
            n, p = agg.get(k, (0, 0))
            agg[k] = (n + 1, p + (1 if r["pass"] else 0))
        return {k: {"n": n, "pass": p, "accuracy": round(p / n, 4)} for k, (n, p) in sorted(agg.items())}

    total = len(rows)
    passed = sum(1 for _, r in rows if r["pass"])
    return {
        "n": total, "pass": passed, "accuracy": round(passed / total, 4) if total else None,
        "errors": sum(1 for _, r in rows if r.get("error")),
        "by_category": table(lambda c: c["category"]),
        "by_style": table(lambda c: c["meta"].get("style", "?")),
        "by_trap": table(lambda c: c["meta"].get("trap", "-")),
        "by_detail": table(lambda c: f"{c['category']} / {detail(c)}"),
        "fail_kinds": _count(r["kind"] for _, r in rows if not r["pass"]),
    }


def _count(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def print_summary(label, s, verbose=False):
    print(f"\n== {label}: {s['pass']}/{s['n']} correct = {100 * (s['accuracy'] or 0):.1f}%"
          + (f"   ({s['errors']} request errors counted as failures)" if s["errors"] else ""))
    print(f"{'category':<16}{'n':>5}{'correct':>9}{'accuracy':>10}")
    for k, v in s["by_category"].items():
        print(f"{k:<16}{v['n']:>5}{v['pass']:>9}{100 * v['accuracy']:>9.1f}%")
    print("by phrasing style: " + ", ".join(f"{k} {100 * v['accuracy']:.0f}% (n={v['n']})"
                                            for k, v in s["by_style"].items()))
    traps = {k: v for k, v in s["by_trap"].items() if k != "-"}
    if traps:
        print("by typing trap:    " + ", ".join(f"{k} {100 * v['accuracy']:.0f}% (n={v['n']})"
                                                for k, v in traps.items()))
    if s["fail_kinds"]:
        print("failure kinds:     " + ", ".join(f"{k} {v}" for k, v in s["fail_kinds"].items()))
    if verbose:
        print("detail:")
        for k, v in s["by_detail"].items():
            print(f"  {k:<44}{v['pass']:>4}/{v['n']:<4}{100 * v['accuracy']:>6.0f}%")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True, help="directory that contains cases.jsonl")
    ap.add_argument("--base-url", required=True, help="e.g. http://127.0.0.1:8121/v1")
    ap.add_argument("--label", required=True, help="name used in the results file")
    ap.add_argument("--limit", type=int, default=None, help="only the first N cases")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--model", default=None, help="model name sent to the server (default: the label)")
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--extra-body", default="{}", help="JSON object merged into every request body")
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    ap.add_argument("--retry-errors", action="store_true", help="re-run cases whose request failed")
    ap.add_argument("--detail", action="store_true", help="also print accuracy per sub-type inside each category")
    args = ap.parse_args()

    cases = load_jsonl(os.path.join(args.cases, "cases.jsonl"))
    if args.limit is not None:
        cases = cases[:args.limit]
    out_path = os.path.join(args.cases, f"results_{args.label}.jsonl")
    results = load_jsonl(out_path) if os.path.exists(out_path) else []
    shas = {c["id"]: case_sha(c) for c in cases}
    all_ids = {c["id"]: case_sha(c) for c in load_jsonl(os.path.join(args.cases, "cases.jsonl"))}
    # keep a stored result only if it belongs to the current version of its case
    kept = [r for r in results if all_ids.get(r["id"]) == r.get("case_sha")
            and not (args.retry_errors and r.get("error"))]
    if len(kept) != len(results):
        print(f"dropping {len(results) - len(kept)} stored results (case changed, or request error)", flush=True)
        results = kept
        with open(out_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    done = {r["id"] for r in results}
    todo = [c for c in cases if c["id"] not in done]
    print(f"{len(cases)} cases, {len(cases) - len(todo)} already done, {len(todo)} to run -> {out_path}",
          flush=True)

    chat = make_chat(args.base_url, args.model or args.label, args.max_tokens, args.timeout,
                     json.loads(args.extra_body), args.api_key)
    lock = threading.Lock()
    started = time.time()

    def work(case):
        t0 = time.time()
        try:
            r = run_case(case, chat)
        except Exception as e:  # noqa: BLE001  request failed after retries
            r = {"id": case["id"], "category": case["category"], "pass": False, "kind": "request_error",
                 "reason": str(e)[:500], "turns": [], "error": True}
        r["seconds"] = round(time.time() - t0, 2)
        r["case_sha"] = shas[case["id"]]
        return r

    if todo:
        with open(out_path, "a", encoding="utf-8") as f, ThreadPoolExecutor(args.concurrency) as pool:
            futures = [pool.submit(work, c) for c in todo]
            for n, fut in enumerate(as_completed(futures), 1):
                r = fut.result()
                with lock:
                    results.append(r)
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
                if n % 25 == 0 or n == len(todo):
                    ok = sum(1 for x in results if x["pass"])
                    print(f"  {n}/{len(todo)} done, running accuracy {100 * ok / len(results):.1f}%, "
                          f"{time.time() - started:.0f}s", flush=True)

    s = summarise(cases, results)
    print_summary(args.label, s, args.detail)
    with open(os.path.join(args.cases, f"summary_{args.label}.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
