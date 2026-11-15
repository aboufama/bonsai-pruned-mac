"""Record videos of real guided episodes (the same environment, model call and checker as a run).

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    python -m taskenv.record --model mlx-9b --patch <file> --label "Bonsai 2 9B, repaired (v3-gentle)" --name 9b-v3-gentle \
        --root ~/bonsai --input s1280 --out ~/bonsai/videos --episodes files.move_into_folder:9101 mail.reply:9101
    python -m taskenv.record --index ~/bonsai/videos          # (re)write index.html from the recorded episodes

The page is recorded by Playwright in real time; nothing is sped up, so the pauses are the model
thinking. A ring shows where the model pointed (it pulses on the click, a dotted line shows a
drag) and a bar below the desktop shows the model, the step and the seconds the model took. The
ring and the bar are never in the screenshot the model is shown. Guided mode, plain: the step is
given in words, the model points; typing, keys and scrolling are done by the harness.
"""
import argparse
import html
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taskenv import actions as A  # noqa: E402
from taskenv import policy, tasks  # noqa: E402
from taskenv.agents import screen_changed, snap, zoom  # noqa: E402
from taskenv.env import H, W  # noqa: E402
from taskenv.env import Env  # noqa: E402


def record(pointer, label, name, tid, seed, out, aids=False):
    """aids: snap a point in a gap onto the nearest control, and take a second, enlarged look when
    nothing visible changed after the action (the two aids of taskenv/agents.py that help)."""
    tmp = tempfile.mkdtemp(prefix="taskenv-video-")
    env = Env(video_dir=tmp)
    ep = tasks.build(tid, seed)
    env.reset(ep.state)
    init, pause, steps = env.state(), env.page.wait_for_timeout, []
    env.caption(label, "Request: " + ep.request)
    pause(2500)
    for step in ep.steps:
        if not step.pointing:
            try:
                for a in step.actions(env):
                    env.caption(label, A.describe(a), "done by the harness")
                    pause(500)
                    env.step(a)
                    pause(500)
            except Exception:
                env.caption(label, "(this step is no longer possible on this screen)")
                pause(900)
            continue
        says = [step.say] + ([step.say_to] if hasattr(step, "say_to") else [])
        boxes = step.targets(env) if getattr(pointer, "oracle", False) else None

        def look(image, around=None, note="model is looking"):
            pts, secs = [], 0.0
            elements = env.elements() if aids else None
            for n, text in enumerate(says):
                env.caption(label, text, note)
                if boxes is not None:
                    r = {"point": ((boxes[n][0] + boxes[n][2]) / 2, (boxes[n][1] + boxes[n][3]) / 2), "seconds": 0.0}
                elif around and around[n]:
                    crop, (x0, y0, w, h) = zoom(image, around[n])
                    r = pointer(crop, text)
                    if r["point"]:
                        r["point"] = (x0 + r["point"][0] / W * w, y0 + r["point"][1] / H * h)
                else:
                    r = pointer(image, text)
                pt, moved = r["point"], False
                if pt and elements is not None and not env.on_content(*pt):
                    pt, moved = snap(pt, elements)
                secs += r.get("seconds", 0.0)
                env.caption(label, text, f"{r.get('seconds', 0.0):.1f} s" + (", snapped to the nearest control" if moved else ""))
                pts.append(pt)
                if pt:
                    if len(pts) == 2 and pts[0]:
                        env.show_line(*pts[0], *pt)
                    env.show_pointer(*pt)
                    pause(650)
            return pts, secs

        before = env.screenshot()
        pts, secs = look(before)
        steps.append({"say": step.say, "seconds": round(secs, 2), "points": pts})
        if any(p is None for p in pts):
            env.caption(label, step.say, "no point in the answer")
            pause(900)
            continue
        env.show_pointer(*pts[-1], pulse=True)
        env.step(step.build(pts))
        pause(900)
        env.show_line()
        if aids and not screen_changed(before, env.screenshot()):
            pts2, secs2 = look(before, around=pts, note="nothing changed: second look, enlarged")
            steps[-1]["second_look"] = round(secs2, 2)
            if all(pts2) and any(abs(p[0] - q[0]) + abs(p[1] - q[1]) > 12 for p, q in zip(pts, pts2)):
                env.show_pointer(*pts2[-1], pulse=True)
                env.step(step.build(pts2))
                pause(900)
                env.show_line()
    ok, why = ep.check(env.state(), init)
    env.caption(label, ("DONE: " if ok else "NOT DONE: ") + ep.request + ("" if ok else "  (" + why + ")"), "pass" if ok else "fail")
    pause(2500)
    video = env.page.video.path()
    env.close()
    os.makedirs(out, exist_ok=True)
    file = f"{name}__{tid}__{'pass' if ok else 'fail'}.webm"
    shutil.move(video, os.path.join(out, file))
    shutil.rmtree(tmp, ignore_errors=True)
    entry = {"file": file, "model": label, "name": name, "task": tid, "seed": seed, "request": ep.request, "category": ep.category, "ok": bool(ok),
             "why": "" if ok else why, "steps": steps, "mb": round(os.path.getsize(os.path.join(out, file)) / 1e6, 2)}
    with open(os.path.join(out, "videos.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"{file}: {'pass' if ok else 'fail'} {why}  {entry['mb']} MB", flush=True)
    return bool(ok)


def index(out):
    rows = {}
    for line in open(os.path.join(out, "videos.jsonl")):
        e = json.loads(line)
        if os.path.exists(os.path.join(out, e["file"])):
            rows[(e["name"], e["task"])] = e
    rows = sorted(rows.values(), key=lambda e: (e["task"], e["name"]))
    cards = "".join(
        f"<section><video controls preload='metadata' src='{html.escape(e['file'])}'></video><h2><span class='{'ok' if e['ok'] else 'bad'}'>{'DONE' if e['ok'] else 'NOT DONE'}</span> "
        f"{html.escape(e['model'])}</h2><p class='req'>“{html.escape(e['request'])}”</p><p>{html.escape(e['task'])}, {html.escape(e['category'].replace('_', ' '))}, "
        f"{len(e['steps'])} pointing step{'s' if len(e['steps']) != 1 else ''}, model time {sum(s['seconds'] for s in e['steps']):.1f} s"
        f"{'. ' + html.escape(e['why']) if e['why'] else ''}</p></section>" for e in rows)
    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Task runs on the Mac mini</title><style>"
            "body{margin:0;padding:28px 16px 60px;background:#f4f4f1;color:#1c1c1a;font:15px/1.5 -apple-system,'Helvetica Neue',Arial,sans-serif}"
            "@media (prefers-color-scheme: dark){body{background:#161615;color:#ecebe6}section{background:#1f1f1d!important;border-color:#33332f!important}}"
            "main{max-width:1100px;margin:0 auto}h1{font-size:22px;margin:0 0 4px}.lead{color:#77766f;margin:0 0 22px}"
            "section{background:#fff;border:1px solid #dddcd6;border-radius:10px;padding:12px;margin:0 0 18px}video{width:100%;border-radius:6px;background:#000;display:block}"
            "h2{font-size:16px;margin:10px 0 2px}p{margin:2px 0}.req{font-weight:600}.ok,.bad{color:#fff;border-radius:999px;padding:1px 9px;font-size:12.5px;margin-right:6px}.ok{background:#1f8a4c}.bad{background:#c8372d}"
            "</style></head><body><main><h1>Task runs on the Mac mini, recorded as they happened</h1>"
            "<p class='lead'>Bonsai 2 in MLX on a Mac mini M6 (16 GB), guided mode at 1280 px: each step is given to the model in words and it answers with a point. "
            "The repaired models run with two aids (a point in a gap is moved to the nearest control; when nothing changed after a click the model looks again at the enlarged area); the original models run plain. "
            "Nothing is sped up; the pauses are the model reading the screenshot. The pink ring is where the model pointed; typing and key presses are done by the harness. "
            "The apps are web replicas of Mac apps, not macOS.</p>" + cards + "</main></body></html>")
    open(os.path.join(out, "index.html"), "w").write(page)
    print(f"{len(rows)} videos -> {os.path.join(out, 'index.html')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index")
    ap.add_argument("--model")
    ap.add_argument("--patch")
    ap.add_argument("--label")
    ap.add_argument("--name")
    ap.add_argument("--root", default="~/bonsai")
    ap.add_argument("--input", default="s1280")
    ap.add_argument("--out")
    ap.add_argument("--episodes", nargs="*", default=[])
    ap.add_argument("--aids", action="store_true", help="snap to the nearest control and a second look when nothing changed")
    ap.add_argument("--fails", type=int, default=0, help="how many failed episodes are wanted in all")
    ap.add_argument("--more", nargs="*", default=[], help="further episodes, recorded one by one and kept only if they fail, until --fails is reached")
    args = ap.parse_args()
    if args.index:
        return index(os.path.expanduser(args.index))
    out = os.path.expanduser(args.out)
    if args.model == "oracle":                                  # for testing the recording itself: points from the page
        class P:
            oracle = True
        pointer = P()
    else:
        model = policy.load(args.model, os.path.expanduser(args.root), patch=args.patch)
        pointer = policy.Pointer(model, args.input, "point")
    fails = 0
    for item in args.episodes:
        tid, seed = item.split(":")
        fails += not record(pointer, args.label, args.name, tid, int(seed), out, aids=args.aids)
    for item in args.more:                                      # make up the number of failures asked for
        if fails >= args.fails:
            break
        tid, seed = item.split(":")
        ok = record(pointer, args.label, args.name, tid, int(seed), out, aids=args.aids)
        if ok:                                                  # it passed: not what this slot is for
            os.remove(os.path.join(out, f"{args.name}__{tid}__pass.webm"))
        fails += not ok
    index(out)


if __name__ == "__main__":
    main()
