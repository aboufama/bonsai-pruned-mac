"""Run one model on one or more test sets and save every case.

    python3 bench/run.py --model bonsai9b-new --jobs ssv2:s1280 mac:s1280 gen:s1280
    python3 bench/run.py --model venus2-9b --jobs sspro:native ssv2:native ssv2:s1280
    python3 bench/run.py --model bonsai9b-new --jobs ssv2:s1280:looks2
    python3 bench/run.py --model bonsai9b-new --jobs toolcall bfcl mmlu chartqa canary cost

A job is  <set>[:<input>][:looks2][:n<limit>]  for the pointing sets (bench/suites.py) or the
name of a task in bench/tasks.py. <input> is "native" or "sNNNN" (bench/models.py, prepare).

Output, under --out (default <root>/benchruns):
    <model>[@<tag>]/<job>.jsonl       one line per case: prompt id, raw answer, parsed point, hit, seconds
    <model>[@<tag>]/<job>.meta.json   command, git commit, library versions, GPU, model files, the prompt
A run resumes: cases already in the .jsonl are skipped. Tables are made from these files by
bench/report.py; nothing is aggregated here beyond a progress line.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bench import models, suites  # noqa: E402

ZOOM, SECOND_SIDE = 3, 1024       # the second look: a window a third of each side, shown at 1024 px


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        done = 0
        while chunk := f.read(1 << 24):
            h.update(chunk)
            done += len(chunk)
            if limit and done >= limit:
                break
    return h.hexdigest()


def environment():
    env = {"host": platform.node(), "python": platform.python_version(), "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "argv": sys.argv}
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        env["git_commit"] = open(os.path.join(here, "COMMIT")).read().strip()        # written when the code is copied to a machine
    except OSError:
        try:
            env["git_commit"] = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        except OSError:
            env["git_commit"] = None
    try:
        import torch
        import transformers
        env.update(torch=torch.__version__, transformers=transformers.__version__, cuda=torch.version.cuda,
                   cudnn=torch.backends.cudnn.version())
    except ImportError:
        pass
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                           capture_output=True, text=True).stdout.strip()
        env["gpu"] = q
    except OSError:
        env["gpu"] = None
    return env


def parse_job(job):
    parts = job.split(":")
    spec = {"name": parts[0], "input": "s1280", "looks": 1, "limit": 0}
    for p in parts[1:]:
        if p == "native" or (p.startswith("s") and p[1:].isdigit()):
            spec["input"] = p
        elif p.startswith("looks"):
            spec["looks"] = int(p[5:])
        elif p.startswith("n") and p[1:].isdigit():
            spec["limit"] = int(p[1:])
        else:
            raise ValueError(f"cannot read job part {p!r} in {job!r}")
    return spec


def shard_suffix(shard):
    """Each shard writes its own file; bench/report.py reads <job>*.jsonl together."""
    return f".shard{shard[0]}of{shard[1]}" if shard else ""


def load_done(path):
    done = {}
    if os.path.exists(path):
        for line in open(path):
            try:
                r = json.loads(line)
                done[r["id"]] = r
            except ValueError:
                pass
    return done


def run_pointing(model, spec, job, out_dir, shard):
    """One pointing set with one input policy. With looks2, a second question is asked on a
    window around the first answer (experiment 011): the window is a third of each side of the
    original screenshot, shown at 1024 px, and the second answer is mapped back."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    cases = suites.pick(suites.POINTING[spec["name"]](model.root), spec["limit"], shard)
    path = f"{out_dir}/{job}{shard_suffix(shard)}.jsonl"
    done = load_done(path)
    todo = [c for c in cases if c["id"] not in done]
    print(f"[{model.key}] {job}: {len(cases)} cases, {len(done)} done before", flush=True)
    hits = sum(r["hit"] for r in done.values())
    t0, n_new = time.time(), 0
    with open(path, "a") as f:
        for c in todo:
            full = Image.open(c["image"]).convert("RGB")
            W, H = full.size
            sent = models.prepare(full, spec["input"])
            a = model.point(sent, c["instruction"])
            point, kind = models.parse_point(a["raw"])
            rec = {"id": c["id"], "model": model.key, "set": spec["name"], "input": spec["input"], "looks": spec["looks"],
                   "prompt_id": model.prompt_id, "raw": a["raw"], "parse": kind, "point": point,
                   "prompt_tokens": a["prompt_tokens"], "new_tokens": a["new_tokens"], "seconds": a["seconds"],
                   "image_size": [W, H], "sent_size": list(sent.size)}
            if spec["looks"] == 2 and point is not None:
                cw, ch = W / ZOOM, H / ZOOM
                cx = min(max(point[0] / 1000 * W, cw / 2), W - cw / 2)
                cy = min(max(point[1] / 1000 * H, ch / 2), H - ch / 2)
                x0, y0 = cx - cw / 2, cy - ch / 2
                crop = full.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch)))
                s = SECOND_SIDE / max(crop.size)
                crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
                b = model.point(crop, c["instruction"])
                p2, kind2 = models.parse_point(b["raw"])
                rec.update(first_point=point, raw2=b["raw"], parse2=kind2, window=[x0, y0, x0 + cw, y0 + ch],
                           prompt_tokens=a["prompt_tokens"] + b["prompt_tokens"], new_tokens=a["new_tokens"] + b["new_tokens"],
                           seconds=round(a["seconds"] + b["seconds"], 3), second_size=list(crop.size))
                if p2 is not None:
                    point = (1000 * (x0 + p2[0] / 1000 * cw) / W, 1000 * (y0 + p2[1] / 1000 * ch) / H)
                # a refusal or an unreadable second answer keeps the first look's point
                rec["point"] = point
            px = None if point is None else (point[0] / 1000 * W, point[1] / 1000 * H)
            rec["hit"] = bool(suites.hit(px, c["target"]))
            rec.update(group=c["group"], ui_type=c["ui_type"], cluster=c["cluster"], flags=c.get("flags", {}),
                       target_type=c["target"]["type"])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            hits += rec["hit"]
            n_new += 1
            if n_new % 100 == 0 or n_new == len(todo):
                total = len(done) + n_new
                print(f"[{model.key}] {job}: {total}/{len(cases)}  on target {100 * hits / total:.1f}%  "
                      f"{(time.time() - t0) / n_new:.2f} s/case", flush=True)
    return {"cases": len(cases), "new": n_new, "seconds": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(models.MODELS))
    ap.add_argument("--jobs", nargs="+", required=True)
    ap.add_argument("--root", default=suites.root())
    ap.add_argument("--out", default=None)
    ap.add_argument("--patch", default=None, help="patch file for a Bonsai model (overrides the registry)")
    ap.add_argument("--gguf", default=None, help="GGUF file for a served model (overrides the registry)")
    ap.add_argument("--tag", default="", help="names this variant of the model, e.g. the patch version")
    ap.add_argument("--shard", default=None, help="k/n: every n-th case starting at k (for parallel processes)")
    ap.add_argument("--port", type=int, default=8131)
    args = ap.parse_args()
    shard = tuple(int(v) for v in args.shard.split("/")) if args.shard else None
    name = args.model + (f"@{args.tag}" if args.tag else "")
    out_dir = os.path.join(args.out or f"{args.root}/benchruns", name)
    os.makedirs(out_dir, exist_ok=True)

    model = models.load(args.model, args.root, patch=args.patch, port=args.port, gguf=args.gguf)
    env = environment()
    desc = model.describe()
    if desc.get("patch"):
        desc["patch_sha256"] = sha256(desc["patch"])
    print(f"[{name}] loaded in {model.load_seconds:.0f} s: {json.dumps({k: v for k, v in desc.items() if k != 'generation_config'})}", flush=True)
    try:
        for job in args.jobs:
            spec = parse_job(job)
            meta = {"model": args.model, "tag": args.tag, "title": models.MODELS[args.model]["title"], "job": job, "spec": spec,
                    "shard": args.shard, "environment": env, "model_files": desc, "decoding": "greedy (do_sample=False), thinking off",
                    "prompt_id": model.prompt_id, "prompt": models.PROMPTS[model.prompt_id]}
            started = time.time()
            if spec["name"] in suites.POINTING:
                meta["result"] = run_pointing(model, spec, job, out_dir, shard)
            else:
                from bench import tasks
                meta["result"] = tasks.TASKS[spec["name"]](model, spec, job, out_dir, shard)
            meta["wall_seconds"] = round(time.time() - started, 1)
            try:
                import torch
                meta["gpu_peak_allocated_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2) if model.spec["kind"] != "gguf" else None
            except ImportError:
                pass
            json.dump(meta, open(f"{out_dir}/{job}{shard_suffix(shard)}.meta.json", "w"), indent=1)
            print(f"[{name}] finished {job} in {meta['wall_seconds']:.0f} s", flush=True)
    finally:
        model.close()
    print(f"[{name}] ALL_JOBS_DONE", flush=True)


if __name__ == "__main__":
    main()
