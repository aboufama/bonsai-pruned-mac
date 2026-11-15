"""Does the pack's drafting head (MTP speculative decoding) make text faster, and does it survive our patch?

TEST ENVIRONMENT ONLY. Nothing in taskenv/ may ever enter a training mix.

    ~/bonsai/venv/bin/python taskenv/mini_drafting.py      # on the Mac mini, with nothing else running

For the 9B and the 4B, original and with our pointing patch: two outputs of about 150 tokens (a
tool-call style answer and a short piece of reasoning), greedy, generated plainly and with the
drafter at block sizes 2, 3 and 4. Reports generated tokens per second and whether the text is
identical to plain decoding. JSON lines, and ~/bonsai/time_drafting.json.
"""
import gc
import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_vlm import load, stream_generate

HOME = Path.home() / "bonsai"
TOOLS = [{"type": "function", "function": {"name": "next_step", "description": "Do the next step on the user's screen.", "parameters": {
    "type": "object", "required": ["action", "target"], "properties": {
        "action": {"type": "string", "enum": ["click", "double_click", "right_click", "drag", "type", "key", "scroll", "done"]},
        "target": {"type": "string", "description": "A description of the thing to act on, at least fifteen words, naming where it is on the screen."},
        "text": {"type": "string"}}}}}]
PROMPTS = {
    "tool call": ([{"role": "system", "content": "You are a screen assistant on a Mac. Act with the tools provided."},
                   {"role": "user", "content": "In Mail, archive the email from Dana Whitfield, then flag the one from Marcus Okafor, then open the Sent mailbox. "
                                               "Call next_step once for each of the five steps this takes, all in this one reply."}], TOOLS),
    "reasoning": ([{"role": "user", "content": "In about 130 words, explain why the total at the bottom of a spreadsheet column can be wrong after a row is deleted, and how to check it."}], None),
}
MODELS = [("9B", "bonsai2-9b-point-v3-mixed896.patch.safetensors"), ("4B", "bonsai2-4b-point-v3-mixed.patch.safetensors")]


def run(model, processor, prompt, **kw):
    text, n, t0, first = "", 0, time.perf_counter(), None
    last = None
    for chunk in stream_generate(model, processor, prompt, max_tokens=150, temperature=0.0, **kw):
        if first is None:
            first = time.perf_counter()
        text += chunk.text
        last = chunk
    total = time.perf_counter() - (first or t0)
    n = int(getattr(last, "generation_tokens", 0) or 0)
    tps = float(getattr(last, "generation_tps", 0) or 0) or (n / total if total else 0)
    return text, n, round(tps, 1)


def main():
    rows = []
    for size, patch in MODELS:
        pack = HOME / "models" / f"Ternary-Bonsai-2-{size}-mlx-2bit"
        model, processor = load(str(pack))
        try:
            from mlx_vlm.speculative.drafters import load_drafter
            drafter, kind = load_drafter(str(pack / "mtp"), kind="mtp")
            problem = None
        except Exception as e:                                        # the installed mlx-vlm may not load this drafter
            drafter, kind, problem = None, None, f"{type(e).__name__}: {e}"
        for state in ("original", "patched"):
            if state == "patched":
                model.load_weights(list(mx.load(str(HOME / "patches" / patch)).items()), strict=False)
                mx.eval(model.parameters())
            for name, (messages, tools) in PROMPTS.items():
                prompt = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False, enable_thinking=False, **({"tools": tools} if tools else {}))
                run(model, processor, prompt)                                        # warm-up
                plain, n, tps = max((run(model, processor, prompt) for _ in range(2)), key=lambda r: r[2])
                row = {"model": f"Bonsai 2 {size}", "state": state, "output": name, "tokens": n, "plain_tps": tps}
                for block in (2, 3, 4):
                    if drafter is None:
                        row[f"draft{block}"] = problem
                        continue
                    try:
                        text, n2, tps2 = max((run(model, processor, prompt, draft_model=drafter, draft_kind=kind, draft_block_size=block) for _ in range(2)), key=lambda r: r[2])
                        row[f"draft{block}_tps"], row[f"draft{block}_same_text"] = tps2, text == plain
                    except Exception as e:
                        row[f"draft{block}"] = f"{type(e).__name__}: {str(e)[:120]}"
                rows.append(row)
                print(json.dumps(row), flush=True)
        del model, processor, drafter
        gc.collect()
        mx.clear_cache()
    json.dump(rows, open(HOME / "time_drafting.json", "w"), indent=1)


if __name__ == "__main__":
    main()
