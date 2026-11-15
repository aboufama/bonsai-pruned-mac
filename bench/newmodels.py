"""Table for the dated section "15 Nov, new models" of docs/BENCHMARK.md.

    python3 bench/newmodels.py --runs ~/Bonsai-demo/benchruns

For each model and set at 1280 px: share on target and share within 20 px of the box (measured
with the long side at 1280 px), each with a 95% bootstrap interval, for one look and, where it
was run, for a second look on a 640 px window of the original screenshot shown at twice the size.
The 158-case report slice of ScreenSpot-v2 is given as a check against the lanes' own numbers.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bench import stats  # noqa: E402
from bench.report import load  # noqa: E402

ROWS = [("bonsai9b-new@pair-nb-l7-best", "9B, pointing decoder (pair nb-l7-best)"),
        ("bonsai9b-new@pair-s2-s5000", "9B, pointing decoder (pair s2-s5000)"),
        ("bonsai4b-new@pair-s12500", "4B, pointing decoder (pair s12500)"),
        ("bonsai9b-new@v3-mixed896", "9B, written answer (v3-mixed896)"),
        ("bonsai9b-new@orch-v1-u3000", "9B, written answer (orchestrator u3000)")]
SETS = [("ssv2", "ScreenSpot-v2", 1272), ("mac", "macOS app windows", 2106), ("neighbour", "Neighbour slice", 600)]


def cell(recs, key):
    a = stats.accuracy([bool(r.get(key)) for r in recs])
    return f"{a['acc']:.1f} ({a['lo']:.1f}–{a['hi']:.1f})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    args = ap.parse_args()
    runs = load(args.runs)
    out, summary = [], []
    out.append("| Model | Set | Looks | Cases | On target (95% interval) | Within 20 px (95% interval) |")
    out.append("|---|---|---|---|---|---|")
    for name, label in ROWS:
        for set_name, set_label, want in SETS:
            for job, looks in ((f"{set_name}:s1280", "one"), (f"{set_name}:s1280:looks2:win640", "two")):
                recs = list(runs.get(name, {}).get(job, {}).values())
                if not recs:
                    if looks == "one":
                        out.append(f"| {label} | {set_label} | one | 0 of {want} | not run | not run |")
                    continue
                part = "" if len(recs) >= want else f" †{len(recs)} of {want}"
                out.append(f"| {label} | {set_label} | {looks} | {len(recs)}{part} | {cell(recs, 'hit')} | {cell(recs, 'near20')} |")
                summary.append({"run": name, "job": job, "n": len(recs), "hit": stats.accuracy([bool(r["hit"]) for r in recs]),
                                "near20": stats.accuracy([bool(r.get("near20")) for r in recs])})
    out.append("")
    out.append("Check against the lanes' own numbers, the 158-case report slice of ScreenSpot-v2, one look:")
    out.append("")
    out.append("| Model | On target | Within 20 px |")
    out.append("|---|---|---|")
    for name, label in ROWS:
        recs = [r for r in runs.get(name, {}).get("ssv2:s1280", {}).values() if r["flags"]["report"] and not r["flags"]["overlap"]]
        if recs:
            out.append(f"| {label} | {100 * sum(r['hit'] for r in recs) / len(recs):.1f} ({sum(r['hit'] for r in recs)} of {len(recs)}) | "
                       f"{100 * sum(r['near20'] for r in recs) / len(recs):.1f} |")
    print("\n".join(out))
    json.dump(summary, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "new_models_20261115.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
