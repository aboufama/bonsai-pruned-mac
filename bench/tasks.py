"""The benchmark's tasks other than pointing. Each writes one line per case, like run_pointing.

    toolcall   our seeded tool-calling set (bench/toolcall, dev split, seed 20261114, 400 cases),
               scored by bench/toolcall/scoring.py; multi-step cases get the stored tool results
    bfcl       Berkeley Function-Calling Leaderboard v3, the five single-turn Python categories
               that are checked without running code (simple, multiple, parallel,
               parallel_multiple, irrelevance), with our own re-implementation of its AST check
    mmlu       MMLU test questions (cais/mmlu), zero-shot, answer letter only
    chartqa    ChartQA test questions (HuggingFaceM4/ChartQA), relaxed accuracy
    canary     bench/canary: 50 short questions scored teacher-forced (models held in this process)
    cost       seconds per pointing answer, prompt and generation tokens per second, peak memory,
               file sizes; run it with nothing else on the GPU

`<task>:n<limit>` takes an evenly spaced subset. Every record has "hit" (correct or not).
"""
import io
import json
import os
import re
import subprocess
import sys
import time

from bench import models, suites
from bench.run import load_done, shard_suffix

HERE = os.path.dirname(os.path.abspath(__file__))


def _loop(model, job, out_dir, shard, cases, fn, every=50):
    """Run fn(case) -> record for every case not done yet; append records; print progress."""
    path = f"{out_dir}/{job}{shard_suffix(shard)}.jsonl"
    done = load_done(path)
    todo = [c for c in cases if c["id"] not in done]
    print(f"[{model.key}] {job}: {len(cases)} cases, {len(done)} done before", flush=True)
    hits, n_new, t0 = sum(bool(r.get("hit")) for r in done.values()), 0, time.time()
    with open(path, "a") as f:
        for c in todo:
            rec = fn(c)
            rec.update(id=c["id"], model=model.key, set=job.split(":")[0])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            hits += bool(rec.get("hit"))
            n_new += 1
            if n_new % every == 0 or n_new == len(todo):
                total = len(done) + n_new
                print(f"[{model.key}] {job}: {total}/{len(cases)}  correct {100 * hits / total:.1f}%  "
                      f"{(time.time() - t0) / n_new:.2f} s/case", flush=True)
    return {"cases": len(cases), "new": n_new, "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------ our tool-calling set
def toolcall(model, spec, job, out_dir, shard):
    sys.path.insert(0, os.path.join(HERE, "toolcall"))
    from scoring import run_case
    path = f"{model.root}/benchdata/toolcall/dev_20261114/cases.jsonl"
    cases = suites.pick([json.loads(line) for line in open(path)], spec["limit"], shard)

    def one(case):
        raws, secs, toks = [], 0.0, 0

        def chat(messages, tools):
            m = model.chat(messages, tools=tools, max_new_tokens=512)
            raws.append(m["raw"])
            nonlocal secs, toks
            secs += m["seconds"]
            toks += m["new_tokens"] or 0
            return m

        try:
            r = run_case(case, chat)
        except Exception as e:                             # a reply the scorer cannot read is a miss
            r = {"pass": False, "kind": "error", "reason": repr(e)[:200], "turns": []}
        return {"hit": bool(r["pass"]), "group": case["category"], "kind": r.get("kind", ""), "reason": r.get("reason", ""),
                "raw": raws, "seconds": round(secs, 3), "new_tokens": toks, "style": (case.get("meta") or {}).get("style")}

    return _loop(model, job, out_dir, shard, cases, one)


# ------------------------------------------------------------------ BFCL v3 (single turn, AST)
BFCL_CATEGORIES = ("simple", "multiple", "parallel", "parallel_multiple", "irrelevance")
_TYPES = {"dict": "object", "float": "number", "tuple": "array", "any": "string", "integer": "integer", "boolean": "boolean",
          "array": "array", "string": "string", "number": "number", "object": "object"}


def _schema(s):
    """BFCL's Python-flavoured parameter schema as JSON Schema (what BFCL does for tool-calling models)."""
    if not isinstance(s, dict):
        return s
    out = {}
    for k, v in s.items():
        if k == "type" and isinstance(v, str):
            out[k] = _TYPES.get(v, "string")
        elif k == "properties" and isinstance(v, dict):
            out[k] = {name: _schema(p) for name, p in v.items()}
        elif k in ("items", "additionalProperties"):
            out[k] = _schema(v)
        elif k == "optional":
            continue
        else:
            out[k] = v
    return out


def _std(s):
    return re.sub(r"[ \,\.\/\-\_\*\^]", "", s).lower().replace("'", '"')


def _value_ok(value, allowed, kind):
    """BFCL's rule: the value has the declared Python type (an int may stand for a float) and
    equals one of the allowed values; strings are compared without case, spaces and ,./-_*^."""
    if kind == "float" and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    want = {"integer": int, "float": float, "string": str, "boolean": bool, "array": list, "tuple": list, "dict": dict}.get(kind)
    if want is not None:
        if not isinstance(value, want) or (want in (int, float) and isinstance(value, bool)):
            return False
    if isinstance(value, list):
        allowed = [list(a) if isinstance(a, tuple) else a for a in allowed]
    if isinstance(value, str):
        return _std(value) in [_std(a) for a in allowed if isinstance(a, str)]
    if isinstance(value, list):
        norm = lambda L: [_std(x) if isinstance(x, str) else x for x in L]
        return any(isinstance(a, list) and norm(a) == norm(value) for a in allowed)
    if isinstance(value, dict):
        for a in allowed:
            if not isinstance(a, dict):
                continue
            if all((k in value and _value_ok(value[k], opts, None)) or (k not in value and "" in opts) for k, opts in a.items()) \
                    and all(k in a for k in value):
                return True
        return False
    return value in allowed


def _call_ok(name, args, truth, functions):
    (fname, params), = truth.items()
    if name != fname or not isinstance(args, dict):
        return False
    spec = next(f for f in functions if f["name"] == fname)
    props, required = spec["parameters"].get("properties", {}), spec["parameters"].get("required", [])
    if any(r not in args for r in required) or any(a not in params for a in args):
        return False
    for p, allowed in params.items():
        if p not in args:
            if "" not in allowed:
                return False
            continue
        if not _value_ok(args[p], allowed, (props.get(p) or {}).get("type")):
            return False
    return True


def bfcl(model, spec, job, out_dir, shard):
    base = f"{model.root}/pub/bfcl"
    cases = []
    for cat in BFCL_CATEGORIES:
        truth = {}
        ans = f"{base}/possible_answer/BFCL_v3_{cat}.json"
        if os.path.exists(ans):
            truth = {r["id"]: r["ground_truth"] for r in map(json.loads, open(ans))}
        for line in open(f"{base}/BFCL_v3_{cat}.json"):
            r = json.loads(line)
            cases.append({"id": r["id"], "category": cat, "question": r["question"][0], "function": r["function"],
                          "truth": truth.get(r["id"])})
    cases = suites.pick(cases, spec["limit"], shard)

    def one(c):
        back = {f["name"].replace(".", "_"): f["name"] for f in c["function"]}
        tools = [{"type": "function", "function": {"name": f["name"].replace(".", "_"), "description": f["description"],
                                                   "parameters": _schema(f["parameters"])}} for f in c["function"]]
        m = model.chat(c["question"], tools=tools, max_new_tokens=512)
        calls = []
        for tc in m["tool_calls"]:
            try:
                args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
            except ValueError:
                args = None
            calls.append((back.get(tc["function"]["name"], tc["function"]["name"]), args))
        if c["category"] == "irrelevance":
            ok = not calls
        elif len(calls) != len(c["truth"]):
            ok = False
        else:                                              # every expected call matched by a different call, any order
            left, ok = list(calls), True
            for t in c["truth"]:
                i = next((i for i, (n, a) in enumerate(left) if _call_ok(n, a, t, c["function"])), None)
                if i is None:
                    ok = False
                    break
                left.pop(i)
        return {"hit": bool(ok), "group": c["category"], "raw": m["raw"], "calls": [[n, a] for n, a in calls],
                "seconds": m["seconds"], "new_tokens": m["new_tokens"]}

    return _loop(model, job, out_dir, shard, cases, one)


# ------------------------------------------------------------------ MMLU
MMLU_PROMPT = ("The following is a multiple choice question about {subject}.\n\n{question}\n"
               "A. {a}\nB. {b}\nC. {c}\nD. {d}\n\nAnswer with the letter of the correct choice only.")


def mmlu(model, spec, job, out_dir, shard):
    import pyarrow.parquet as pq
    rows = pq.read_table(f"{model.root}/pub/mmlu/all/test-00000-of-00001.parquet").to_pylist()
    cases = suites.pick([dict(r, id=f"mmlu_{i:05d}") for i, r in enumerate(rows)], spec["limit"], shard)

    def one(c):
        ch = c["choices"]
        text = MMLU_PROMPT.format(subject=c["subject"].replace("_", " "), question=c["question"], a=ch[0], b=ch[1], c=ch[2], d=ch[3])
        m = model.chat([{"role": "user", "content": text}], max_new_tokens=8)
        got = re.search(r"\b([ABCD])\b", m["content"])
        return {"hit": bool(got and "ABCD".index(got.group(1)) == c["answer"]), "group": c["subject"], "raw": m["raw"],
                "parse": got.group(1) if got else None, "seconds": m["seconds"], "new_tokens": m["new_tokens"]}

    return _loop(model, job, out_dir, shard, cases, one, every=100)


# ------------------------------------------------------------------ ChartQA
CHARTQA_PROMPT = "{question}\nAnswer the question using a single word or phrase."


def relaxed_correct(target, prediction, tolerance=0.05):
    """ChartQA's relaxed accuracy: a number within 5% of the target, otherwise an exact match
    ignoring case."""
    def to_float(t):
        try:
            return float(t.rstrip("%")) / 100.0 if t.endswith("%") else float(t)
        except ValueError:
            return None
    p, t = to_float(prediction), to_float(target)
    if p is not None and t:
        return abs(p - t) / abs(t) <= tolerance
    return prediction.lower() == target.lower()


def chartqa(model, spec, job, out_dir, shard):
    import pyarrow.parquet as pq
    from PIL import Image
    table = pq.read_table(f"{model.root}/pub/chartqa/data/test-00000-of-00001-e2cd0b7a0f9eb20d.parquet")
    index = suites.pick([{"id": f"chartqa_{i:04d}", "row": i} for i in range(table.num_rows)], spec["limit"], shard)

    def one(c):
        r = table.slice(c["row"], 1).to_pylist()[0]
        image = Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB")
        m = model.chat([{"role": "user", "content": CHARTQA_PROMPT.format(question=r["query"])}], max_new_tokens=32,
                       image=models.prepare(image, "native"))
        pred = m["content"].strip().rstrip(".").strip()
        return {"hit": any(relaxed_correct(t, pred) for t in r["label"]), "group": "human" if r["human_or_machine"] == 0 else "augmented",
                "raw": m["raw"], "target": r["label"], "seconds": m["seconds"], "new_tokens": m["new_tokens"]}

    return _loop(model, job, out_dir, shard, index, one, every=100)


# ------------------------------------------------------------------ canary (teacher-forced)
def canary(model, spec, job, out_dir, shard):
    """bench/canary as Lab.canary scores it: the expected answer is appended and the model's
    probabilities are read. hit = every answer token is the model's top choice."""
    import torch
    items = [json.loads(line) for line in open(os.path.join(HERE, "canary", "canary.jsonl"))]
    tok = model.processor.tokenizer

    def one(it):
        prompt = model.processor.apply_chat_template([{"role": "user", "content": [{"type": "text", "text": it["prompt"]}]}],
                                                     add_generation_prompt=True, tokenize=False, enable_thinking=False)
        p = tok(prompt, add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.model.device)
        a = tok(it["answer"], add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.model.device)
        with torch.inference_mode():
            logits = model.model(input_ids=torch.cat([p, a], dim=1), use_cache=False).logits[0, p.shape[1] - 1:-1].float()
        logp = torch.log_softmax(logits, dim=-1)
        tgt = a[0]
        nll = -logp[torch.arange(len(tgt), device=logp.device), tgt].sum().item()
        return {"hit": bool((logp.argmax(-1) == tgt).all()), "group": it["skill"], "nll": nll, "tokens": int(len(tgt))}

    return _loop(model, job, out_dir, shard, items, one)


# ------------------------------------------------------------------ cost
SPEED_PROMPT = "Write a detailed, numbered checklist of forty steps for setting up a new laptop for software development."


def _dir_bytes(path, suffixes):
    return sum(os.path.getsize(os.path.join(path, f)) for f in os.listdir(path) if f.endswith(suffixes))


def cost(model, spec, job, out_dir, shard):
    """Run alone on the GPU. One record (id "cost") with:
    seconds per pointing answer on 60 ScreenSpot-v2 cases at 1280 px (median, after 3 warm-up
    cases), prompt tokens per second on those prompts, generation tokens per second over 256
    new tokens of text, peak GPU memory, and the size of the files that make up the model."""
    from PIL import Image
    rec = {"id": "cost", "hit": True, "group": "cost"}
    cases = suites.pick(suites.ssv2(model.root), 63)
    secs, ptoks = [], []
    for i, c in enumerate(cases):
        a = model.point(models.prepare(Image.open(c["image"]).convert("RGB"), "s1280"), c["instruction"])
        if i >= 3:
            secs.append(a["seconds"]); ptoks.append(a["prompt_tokens"])
    secs.sort()
    rec.update(point_seconds_median=secs[len(secs) // 2], point_seconds_mean=round(sum(secs) / len(secs), 3),
               point_prompt_tokens_mean=round(sum(ptoks) / len(ptoks)), point_cases=len(secs))
    if model.spec["kind"] == "gguf":
        m = model.chat([{"role": "user", "content": SPEED_PROMPT}], max_new_tokens=256)
        rec.update(generation_tokens_per_second=m.get("server_predicted_per_second"), generation_new_tokens=m["new_tokens"])
        c = cases[5]
        a = model.point(models.prepare(Image.open(c["image"]).convert("RGB"), "s1280"), c["instruction"] + " ")
        rec.update(prompt_tokens_per_second=round(1000 * a["prompt_tokens"] / a["server_prompt_ms"], 1) if a.get("server_prompt_ms") else None)
        q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True).stdout
        mem = [int(line.split(",")[1]) for line in q.splitlines() if line.split(",")[0].strip() == str(model.proc.pid)]
        rec.update(gpu_memory_gb=round(mem[0] / 1024, 2) if mem else None, memory_kind="llama-server process, nvidia-smi",
                   file_bytes={"gguf": os.path.getsize(model.gguf), "mmproj": os.path.getsize(model.mmproj)})
    else:
        import torch
        torch.cuda.reset_peak_memory_stats()
        # prompt processing: one forward pass over a 1280 px screenshot prompt, best of 3
        c = cases[5]
        image = models.prepare(Image.open(c["image"]).convert("RGB"), "s1280")
        messages = [{"role": "user", "content": [{"type": "image", "image": image},
                                                 {"type": "text", "text": models.point_text(model.prompt_id, c["instruction"])}]}]
        inputs = model.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True,
                                                     return_tensors="pt", enable_thinking=False).to(model.model.device)
        best = 1e9
        with torch.inference_mode():
            for _ in range(3):
                torch.cuda.synchronize(); t = time.perf_counter()
                model.model(**inputs, use_cache=True)
                torch.cuda.synchronize(); best = min(best, time.perf_counter() - t)
        n = inputs["input_ids"].shape[1]
        rec.update(prompt_tokens_per_second=round(n / best, 1), prompt_tokens=n)
        # generation: 256 new tokens of text, greedy, best of 2
        ids = model.processor.apply_chat_template([{"role": "user", "content": [{"type": "text", "text": SPEED_PROMPT}]}],
                                                  add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
                                                  enable_thinking=False).to(model.model.device)
        best = 0
        with torch.inference_mode():
            for _ in range(2):
                torch.cuda.synchronize(); t = time.perf_counter()
                out = model.model.generate(**ids, max_new_tokens=256, min_new_tokens=256, do_sample=False, use_cache=True)
                torch.cuda.synchronize(); dt = time.perf_counter() - t
                best = max(best, (out.shape[1] - ids["input_ids"].shape[1]) / dt)
        rec.update(generation_tokens_per_second=round(best, 1), generation_new_tokens=256)
        rec.update(gpu_memory_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2), memory_kind="peak allocated by PyTorch")
        if model.spec["kind"] == "bonsai":
            files = {"pack": os.path.getsize(os.path.join(model.source, "model.safetensors"))}
            if model.patch:
                files["patch"] = os.path.getsize(model.patch)
        else:
            files = {"checkpoint": _dir_bytes(model.source, (".safetensors",))}
        rec["file_bytes"] = files
    path = f"{out_dir}/{job}.jsonl"
    with open(path, "w") as f:
        f.write(json.dumps(dict(rec, model=model.key, set="cost")) + "\n")
    print(f"[{model.key}] cost: {json.dumps(rec)}", flush=True)
    return {"cases": 1, "new": 1}


TASKS = {"toolcall": toolcall, "bfcl": bfcl, "mmlu": mmlu, "chartqa": chartqa, "canary": canary, "cost": cost}
