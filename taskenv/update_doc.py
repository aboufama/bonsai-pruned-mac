"""Put the tables of taskenv/report.py into docs/TASKENV.md (between the RESULTS markers).

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python taskenv/update_doc.py ~/Bonsai-demo/taskenv-runs/reported "state of the runs, one line"
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv import report  # noqa: E402
from taskenv.tasks.base import TEST_SEEDS  # noqa: E402

runs, note = os.path.expanduser(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "")
here = os.path.dirname(os.path.abspath(__file__))
doc = os.path.join(here, "..", "docs", "TASKENV.md")
summaries = [report.summarise(r) for r in report.load_runs(runs, set(TEST_SEEDS))]
extra, speed = None, ""
try:                                                     # timings measured on the Mac mini (taskenv/mini_timing.py, mini_drafting.py)
    rows = json.load(open(os.path.expanduser("~/bonsai/time_refs.json")))
    dec = {r["side"]: r for r in rows if "request_and_decoder_ms" in r}
    if dec:
        extra = {"decoder_ms": dec[1280]["request_and_decoder_ms"], "decoder_ms_896": dec[896]["request_and_decoder_ms"], "read20_ms": dec[1280]["image_through_layer_20_ms"],
                 "read20_ms_896": dec[896]["image_through_layer_20_ms"], "vision_ms": dec[1280]["vision_ms"], "vision_ms_896": dec[896]["vision_ms"]}
    speed = ("### Speed on the Mac mini (M6, 16 GB): ternary Bonsai against ordinary 4-bit and 8-bit builds of the same designs\n\n"
             "One pointing answer on the same screenshot (11 tokens written), best of three, nothing else running. UI-Venus-2-9B has the parent's shape, so the 9B rows stand for it.\n\n"
             "| Model | Seconds per answer, 1280 px | 896 px | Tokens read per second | Tokens written per second | Peak memory | Size on disk |\n|---|---|---|---|---|---|---|\n")
    by = {}
    for r in rows:
        if "seconds" in r:
            by.setdefault(r["model"], {})[r["side"]] = r
    for name, d in by.items():
        a = d[1280]
        speed += f"| {name} | {a['seconds']:.2f} | {d[896]['seconds']:.2f} | {a['prompt_tps']:.0f} | {a['generation_tps']:.0f} | {a['peak_memory_gb']:.1f} GB | {a['disk_gb']:.1f} GB |\n"
    d = json.load(open(os.path.expanduser("~/bonsai/time_drafting.json")))
    speed += ("\n### Drafting head (the pack's MTP speculative decoding) on the Mac mini\n\nGenerated tokens per second, greedy, about 150 tokens; "
              "\"same\" means the text is identical to plain decoding. It works with mlx-vlm 0.7.8 as installed.\n\n"
              "| Model | Weights | Output | Plain | Block 2 | Block 3 | Block 4 | Text identical |\n|---|---|---|---|---|---|---|---|\n")
    for r in d:
        speed += (f"| {r['model']} | {r['state']} | {r['output']} | {r['plain_tps']:.0f} | {r.get('draft2_tps', 'n/a')} | {r.get('draft3_tps', 'n/a')} | {r.get('draft4_tps', 'n/a')} | "
                  f"{'yes' if all(r.get(f'draft{b}_same_text') for b in (2, 3, 4)) else 'no'} |\n")
except (OSError, KeyError, ValueError):
    pass
md = report.tables(summaries, extra) + ("\n" + speed if speed else "")
os.makedirs(os.path.join(here, "results"), exist_ok=True)
open(os.path.join(here, "results", "summary.md"), "w").write(md)
json.dump(summaries, open(os.path.join(here, "results", "summary.json"), "w"), indent=1)
text = open(doc).read()
a, b = text.index("<!-- RESULTS:BEGIN -->"), text.index("<!-- RESULTS:END -->")
head = (f"## Results\n\nState at {time.strftime('%H:%M')} EST on 15 Nov 2026. {note}\n\n"
        "Reserved seeds only. \"Tasks done\" is decided by the state of the apps at the end. Intervals are 95% bootstrap intervals over tasks. "
        "Every run can be replayed step by step (see \"Replay pages\" below).\n\n")
open(doc, "w").write(text[:a] + "<!-- RESULTS:BEGIN -->\n" + head + md + text[b:])
print(md[:3000])
