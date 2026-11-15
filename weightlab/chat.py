"""Pointing and tool calling as one skill: supervised samples in the model's own chat format.

The Clicky-style assistant we are building is one model that reads the screen once and then
decides: answer, call a tool, or point. So pointing is trained here as a tool call, next to
ordinary tool calls, with the same weights:

    system    a short orchestrator instruction; the chat template lists the tools
    user      [screenshot] + what the person asked
    assistant <tool_call>
              <function=point>
              <parameter=x>
              512
              </parameter>
              <parameter=y>
              87
              </parameter>
              </function>
              </tool_call>

Numbers are written one digit per token, so the land-in-the-box loss of tune.py carries over: at
each coordinate digit, the probability mass on digits that keep the point inside the target box.
Every other token of the answer is ordinary cross-entropy.

A sample is a dict with "kind":
    "point_call"   built from a pointing case (lab.data item) by `point_call()`
    "tool_call"    built from a case of bench/toolcall by `tool_case()`
`supervise()` turns either into model inputs plus, for each answer token, the token ids that
count as correct. `TaskTuner` trains on these as well as on plain pointing cases.
"""
import json
import random

DIGIT0 = 15                                   # token ids 15..24 are the digits 0..9

SYSTEMS = (
    "You are a screen assistant. You can see the user's screen. Act with the tools provided.",
    "You help the user with what is on their screen. Use a tool when one fits the request.",
    "Screen assistant on a Mac. Look at the screenshot and act on the request with the tools.",
)
POINT_TOOL = {"type": "function", "function": {
    "name": "point", "description": "Point at one spot on the screen for the user.",
    "parameters": {"type": "object", "required": ["x", "y"], "properties": {
        "x": {"type": "integer", "description": "Horizontal position, 0 (left edge) to 1000 (right edge)."},
        "y": {"type": "integer", "description": "Vertical position, 0 (top edge) to 1000 (bottom edge)."}}}}}
# other things a screen assistant can do; listed next to `point` so that choosing it is learnt
OTHER_TOOLS = [
    {"type": "function", "function": {"name": "say", "description": "Say something to the user out loud.",
     "parameters": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string", "description": "What to say."}}}}},
    {"type": "function", "function": {"name": "type_text", "description": "Type text at the current cursor position.",
     "parameters": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string", "description": "Text to type."}}}}},
    {"type": "function", "function": {"name": "press_keys", "description": "Press a keyboard shortcut.",
     "parameters": {"type": "object", "required": ["keys"], "properties": {"keys": {"type": "string", "description": "For example cmd+s."}}}}},
    {"type": "function", "function": {"name": "scroll", "description": "Scroll the window under the pointer.",
     "parameters": {"type": "object", "required": ["direction"], "properties": {
         "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Direction."},
         "amount": {"type": "integer", "description": "Lines to scroll."}}}}},
    {"type": "function", "function": {"name": "open_app", "description": "Open an application by name.",
     "parameters": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string", "description": "Application name."}}}}},
    {"type": "function", "function": {"name": "search_web", "description": "Search the web.",
     "parameters": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string", "description": "Search terms."}}}}},
]


def render_call(name, arguments):
    """One tool call the way the Qwen3.5 chat template writes it."""
    out = f"<tool_call>\n<function={name}>\n"
    for k, v in arguments.items():
        v = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        out += f"<parameter={k}>\n{v}\n</parameter>\n"
    return out + "</function>\n</tool_call>"


def point_call(item, rng=None):
    """A pointing case (lab.data item) as a tool-call sample. Deterministic per item unless rng is given."""
    rng = rng or random.Random(item["id"])
    tools = [POINT_TOOL] + rng.sample(OTHER_TOOLS, rng.randint(1, 4))
    rng.shuffle(tools)
    return {"kind": "point_call", "id": item["id"], "item": item, "system": rng.choice(SYSTEMS), "tools": tools,
            "request": item["instruction"]}


def tool_case(case):
    """A case of bench/toolcall as a sample.

    Cases with calls in one turn       -> "tool_call": every token of the calls is supervised
    Multi-step chains                  -> "tool_call" for the first step only
    Missing value / no tool applies    -> "no_call": the wording of a text reply is free, so the
                                          only thing supervised is that the reply does NOT begin
                                          a tool call
    """
    exp = case.get("expected") or {}
    calls = exp.get("calls") or ((exp.get("steps") or [{}])[0].get("calls"))
    base = {"id": case["id"], "messages": case["messages"], "tools": case["tools"], "category": case.get("category")}
    if calls:
        return dict(base, kind="tool_call", target="\n".join(render_call(c["name"], c["arguments"]) for c in calls))
    if exp.get("no_call"):
        return dict(base, kind="no_call")
    return None


def _digit_sets(s, lo, hi):
    """For each digit of the coordinate written as `s`: the digit tokens that keep the value
    inside [lo, hi] for some completion of the lower digits (higher digits as written)."""
    out = []
    for d in range(len(s)):
        ok = []
        for digit in range(10):
            head = s[:d] + str(digit)
            low, high = int(head + "0" * (len(s) - d - 1)), int(head + "9" * (len(s) - d - 1))
            if high >= lo and low <= hi:
                ok.append(DIGIT0 + digit)
        out.append(ok or [DIGIT0 + int(s[d])])
    return out


def supervise(lab, model, sample):
    """(inputs, spans, allowed, places): the prompt with the answer appended; spans = [(start,
    length)] of the answer; allowed[k] = token ids correct at answer token k; places[k] is
    "hundreds"/"tens"/"units" for coordinate digits and None elsewhere (for scoring)."""
    tok = lab.processor.tokenizer
    end = "<|im_end|>"
    if sample["kind"] == "point_call":
        it = sample["item"]
        messages = [{"role": "system", "content": [{"type": "text", "text": sample["system"]}]},
                    {"role": "user", "content": [{"type": "image", "image": lab.image(it)},
                                                 {"type": "text", "text": sample["request"]}]}]
        x, y = str(it["target"][0]), str(it["target"][1])
        pieces = [("<tool_call>\n<function=point>\n<parameter=x>\n", None), (x, (it["box1000"][0], it["box1000"][2])),
                  ("\n</parameter>\n<parameter=y>\n", None), (y, (it["box1000"][1], it["box1000"][3])),
                  ("\n</parameter>\n</function>\n</tool_call>" + end, None)]
    else:
        messages = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in sample["messages"]]
        pieces = [(sample.get("target", "") + end, None)]
    inputs = lab.processor.apply_chat_template(messages, tools=sample["tools"], add_generation_prompt=True, tokenize=True,
                                               return_dict=True, return_tensors="pt", enable_thinking=False).to(model.device)
    start = inputs["input_ids"].shape[1]
    if sample["kind"] == "no_call":
        # nothing is appended: the position after the prompt must not start a tool call
        return inputs, [(start, 1)], [("not", tok.convert_tokens_to_ids("<tool_call>"))], [None]
    allowed, places = [], []
    for text, box in pieces:
        ids = tok(text, add_special_tokens=False)["input_ids"]
        if box is None:
            allowed += [[i] for i in ids]
            places += [None] * len(ids)
        else:
            assert len(ids) == len(text) and all(DIGIT0 <= i < DIGIT0 + 10 for i in ids), "a coordinate was not tokenised digit by digit"
            allowed += _digit_sets(text, box[0], box[1])
            places += [("units", "tens", "hundreds", "thousands")[len(text) - 1 - d] for d in range(len(text))]
    whole = "".join(t for t, _ in pieces)
    n = lab._append(inputs, whole)
    assert n == len(allowed), f"piecewise tokenisation ({len(allowed)}) differs from the whole answer ({n})"
    return inputs, [(start, n)], allowed, places


def answer_logits(model, inputs, start, n):
    """Logits at the n positions that predict the answer tokens. The output head (about a billion
    weights) is applied to those positions only, when the model class allows it."""
    import torch
    idx = torch.arange(start - 1, start - 1 + n, device=inputs["input_ids"].device)
    if getattr(model, "_head_on_answer_only", True):
        try:
            out = model.model(**inputs, use_cache=False)
            h = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]
            return model.lm_head(h[0, idx])
        except (TypeError, AttributeError):
            model._head_on_answer_only = False
    return model(**inputs, use_cache=False).logits[0, idx]


def score(lab, model, samples, tag=""):
    """Teacher-forced scores for chat samples (one forward pass each).

    point_call: p_hit (probability that every coordinate digit is acceptable, as in Lab.digits),
                the per-place probabilities, and `format` (share of samples whose every
                non-digit token is the model's top choice).
    tool_call:  tf_exact (share of samples whose every token is the top choice) and nll per token.
    no_call:    holds_back (share where the top first token is not the start of a tool call) and
                the mean probability of starting one.
    """
    import collections
    import math
    import torch
    nll, ok, fmt, exact, tok_nll, tok_n = [], collections.defaultdict(list), [], [], 0.0, 0
    no_call, p_call = [], []
    with torch.inference_mode():
        for s in samples:
            inputs, spans, allowed, places = supervise(lab, model, s)
            a, n = spans[0]
            logits = answer_logits(model, inputs, a, n).float()
            logp = torch.log_softmax(logits, dim=-1)
            top = logp.argmax(-1).tolist()
            lab.forward_passes += 1
            if s["kind"] == "point_call":
                miss, good_format = 0.0, True
                for k, (ids, place) in enumerate(zip(allowed, places)):
                    if place is None:
                        good_format &= top[k] in ids
                    else:
                        probs = torch.softmax(logp[k, DIGIT0:DIGIT0 + 10], dim=-1)
                        good = sum(probs[i - DIGIT0].item() for i in ids)
                        ok[place].append(good)
                        miss -= math.log(good + 1e-9)
                nll.append(miss); fmt.append(good_format)
            elif s["kind"] == "no_call":
                no_call.append(top[0] != allowed[0][1])
                p_call.append(math.exp(logp[0, allowed[0][1]].item()))
            else:
                exact.append(all(top[k] in ids for k, ids in enumerate(allowed)))
                tok_nll += -sum(logp[k, ids[0]].item() for k, ids in enumerate(allowed)); tok_n += n
    r = {}
    if nll:
        r.update({"p_hit": sum(math.exp(-v) for v in nll) / len(nll), "miss_nll": sum(nll) / len(nll), "format": sum(fmt) / len(fmt),
                  **{f"p_ok_{k}": sum(v) / len(v) for k, v in sorted(ok.items())}, "n_point": len(nll)})
    if exact:
        r.update({"tf_exact": sum(exact) / len(exact), "nll_per_token": tok_nll / max(1, tok_n), "n_tool": len(exact)})
    if no_call:
        r.update({"holds_back": sum(no_call) / len(no_call), "p_starts_call": sum(p_call) / len(p_call), "n_no_call": len(no_call)})
    lab._journal("chat", tag, r, len(samples))
    return r


def generate(lab, model, sample, max_new_tokens=64):
    """Let the model answer a chat sample by itself. Returns (text, point or None): the point is
    read from a `point` tool call if the model made one."""
    import re
    import torch
    inputs, spans, _, _ = supervise(lab, model, sample)
    a, _ = spans[0]
    prompt = {k: (v[:, :a] if torch.is_tensor(v) and v.ndim == 2 and v.shape[0] == 1 and v.shape[1] == inputs["input_ids"].shape[1]
                  and not v.is_floating_point() else v) for k, v in inputs.items()}
    with torch.inference_mode():
        out = model.generate(**prompt, max_new_tokens=max_new_tokens, do_sample=False, eos_token_id=lab._stop_ids())
    text = lab.processor.decode(out[0, a:], skip_special_tokens=True)
    m = re.search(r"<function=point>.*?<parameter=x>\s*(-?\d+).*?<parameter=y>\s*(-?\d+)", text, flags=re.S)
    return text, ((float(m.group(1)), float(m.group(2))) if m else None)
