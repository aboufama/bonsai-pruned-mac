"""The weight lab: models held in memory, measurements, and reversible ternary edits.

Everything an experiment needs is a method of `Lab`:

  load()            Bonsai (as TernaryLinear modules) and, on demand, the full-precision parent
                    and UI-Venus, all with the same architecture and in the same basis
  data()            pointing samples with exact target boxes
  score()           accuracy, distance and digit statistics from generated answers
  digits()          teacher-forced probability of the correct coordinate, digit by digit
  hidden()          residual-stream activations at the answer positions and over the image
  diff()            where Bonsai's activations depart from the parent's, layer by layer
  swap()            temporarily give Bonsai some of the parent's weights
  Edit              scale, delete, flip or re-fit ternary weights; apply, revert, save

Every score is appended to a journal with the stack of edits that was active, so a number can
always be traced to the exact state of the weights that produced it.
"""
import collections
import contextlib
import hashlib
import json
import os
import re
import time

import torch
from PIL import Image
from safetensors import safe_open
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

from . import ternary

PROMPT = (
    "Output the center point of the position corresponding to the following instruction: \n"
    "{instruction}. \n\n"
    "The output should just be the coordinates of a point, in the format [x,y]. "
    "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
    "the output should be [-1,-1]."
)


POINT_TOL = 0.012        # half-width of the box put around a bare click point, as a share of image width
IMAGE_CACHE = 400        # decoded screenshots kept in memory


def mem_available_gb():
    """Memory the machine can still hand out. CPU and GPU share one pool on the Spark."""
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 1048576
    return float("inf")


def need_memory(gb, what, reserve=20):
    """Refuse to start something that would leave less than `reserve` GB for the rest of the machine
    (a run that fills the memory gets every process of the session killed)."""
    avail = mem_available_gb()
    if avail - gb < reserve:
        raise MemoryError(f"{what} needs about {gb:.0f} GB but only {avail:.0f} GB is available "
                          f"({reserve} GB is kept in reserve). Free something first.")


def _fast_patch_embed(model):
    """Run the vision tower's first step as one matrix product.

    The model cuts the image into 16 x 16 px patches with a Conv3d whose stride equals its kernel,
    which is exactly a linear map of each flattened patch. On the RTX PRO 6000 pods (cuDNN 9.10,
    bfloat16) that convolution takes 8 seconds per screenshot; the matrix product takes a
    millisecond and gives the same result to bfloat16 rounding (measured: 0.03 on values up to 8).
    """
    pe = model.model.visual.patch_embed

    def forward(hidden_states, pe=pe):
        w = pe.proj.weight
        x = hidden_states.reshape(-1, w[0].numel()).to(w.dtype)
        return torch.nn.functional.linear(x, w.reshape(w.shape[0], -1), pe.proj.bias)

    pe.forward = forward


class Tensors:
    """Lazy access to a sharded safetensors checkpoint by tensor name."""

    def __init__(self, d):
        self.d = d
        self.map = json.load(open(f"{d}/model.safetensors.index.json"))["weight_map"]
        self.handles = {}

    def get(self, k):
        path = f"{self.d}/{self.map[k]}"
        if path not in self.handles:
            self.handles[path] = safe_open(path, framework="pt")
        return self.handles[path].get_tensor(k)


class Lab:
    def __init__(self, root="~/bonsai"):
        self.root = os.path.expanduser(root)
        self.dir = f"{self.root}/lab"
        os.makedirs(f"{self.dir}/edits", exist_ok=True)
        self.size = os.environ.get("BONSAI_SIZE", "9B")          # which Bonsai 2 this session works on
        self.paths = {
            "pack": f"{self.root}/hf/Ternary-Bonsai-2-{self.size}-mlx-2bit",
            "B": f"{self.root}/hf/Bonsai-2-{self.size}-dense",
            "P": f"{self.root}/hf/Qwen3.5-{self.size}",
            "V": f"{self.root}/hf/UI-Venus-2-9B",
        }
        self.models, self.tern, self.stack, self.forward_passes = {}, {}, [], 0
        self.processor = None
        self._data, self._images = {}, {}

    # ---------------------------------------------------------------- models
    def load(self, which="B"):
        """Load 'B' (Bonsai), 'P' (parent Qwen3.5-9B) or 'V' (UI-Venus-2-9B). Returns the model."""
        if which in self.models:
            return self.models[which]
        if self.processor is None:
            self.processor = AutoProcessor.from_pretrained(self.paths["B"])
        need_memory((28 if which == "B" else 19) * (0.5 if self.size != "9B" else 1), f"loading model {which}")
        t = time.time()
        m = Qwen3_5ForConditionalGeneration.from_pretrained(
            self.paths[which], dtype=torch.bfloat16, device_map="cuda").eval()
        for p in m.parameters():
            p.requires_grad_(False)
        _fast_patch_embed(m)
        if which == "B":
            self.tern = ternary.attach_ternary(m, self.paths["pack"])
        self.models[which] = m
        print(f"loaded {which} in {time.time() - t:.0f}s; GPU memory {torch.cuda.memory_allocated() / 1e9:.1f} GB")
        return m

    @property
    def B(self):
        return self.load("B")

    @property
    def P(self):
        return self.load("P")

    @property
    def V(self):
        return self.load("V")

    # ---------------------------------------------------------------- data
    def data(self, name="ssv2", n=50, max_side=1280, offset=0, mod=None):
        """Evenly spaced samples from a set. `offset` shifts the selection.

        mod=(m, r) instead takes every item whose position (after sorting by id) is r modulo m.
        Sets made with the same m and different r never share an item, which evenly spaced
        selections with different n do not guarantee.
        """
        key = (name, n, max_side, offset, mod)
        if key in self._data:
            return self._data[key]
        items = []
        if name == "ssv2":
            for split in ("desktop", "mobile", "web"):
                for i, it in enumerate(json.load(open(f"{self.root}/ssv2/screenspot_{split}_v2.json"))):
                    x, y, w, h = it["bbox"]
                    items.append({"id": f"{split}_{i:04d}", "path": f"{self.root}/ssv2/screenspotv2_image/{it['img_filename']}",
                                  "bbox": [x, y, x + w, y + h], "instruction": it["instruction"],
                                  "group": split, "ui_type": it["data_type"]})
        elif name == "sspro":
            import glob
            for path in sorted(glob.glob(f"{self.root}/sspro/annotations/*.json")):
                for it in json.load(open(path)):
                    items.append({"id": it["id"], "path": f"{self.root}/sspro/images/{it['img_filename']}",
                                  "bbox": it["bbox"], "instruction": it["instruction"],
                                  "group": it["group"], "ui_type": it["ui_type"]})
        elif name.startswith("gen:"):
            # output of bench/pointing/generate.py, e.g. "gen:benchdata/pointing/train_s101"
            base = f"{self.root}/{name[4:]}"
            for line in open(f"{base}/cases.jsonl"):
                it = json.loads(line)
                items.append({"id": it["id"], "path": f"{base}/{it['image']}", "bbox": it["bbox"],
                              "instruction": it["instruction"], "group": it["meta"].get("archetype", "gen"),
                              "ui_type": it["element"].get("ui_type", "text")})
        elif name.startswith("mac:"):
            # data/mac/<set>/cases.jsonl, e.g. "mac:agentnet:train" or "mac:screen2ax_task:test".
            # Cases with a click point but no box get a small box around the point (POINT_TOL).
            _, folder, *split = name.split(":")
            base = f"{self.root}/data/mac/{folder}"
            for line in open(f"{base}/cases.jsonl"):
                it = json.loads(line)
                if split and it.get("split") != split[0]:
                    continue
                box = it["bbox"]
                if box is None:
                    x, y = it["point"]
                    tol = POINT_TOL * it["width"]
                    box = [x - tol, y - tol, x + tol, y + tol]
                items.append({"id": it["id"], "path": f"{base}/{it['image']}", "bbox": box,
                              "instruction": it["instruction"], "group": it.get("app") or "mac",
                              "ui_type": "point" if it["bbox"] is None else "box",
                              "size": (it["width"], it["height"]),
                              "kind": (it.get("meta") or {}).get("kind"),       # e.g. direct / intent / next
                              "role": (it.get("meta") or {}).get("ax_role")})   # e.g. AXButton, where the source says
        else:
            raise ValueError(name)
        items.sort(key=lambda x: x["id"])
        if mod:
            picked = [it for i, it in enumerate(items) if i % mod[0] == mod[1]]
        else:
            step = len(items) / n
            picked = [items[(int(i * step) + offset) % len(items)] for i in range(n)]
        if name == "ssv2":
            # dropped after the selection, so which screens a set contains never shifts
            picked = [it for it in picked if it["id"] not in self.excluded()]
        out = []
        for it in picked:
            it = dict(it)
            it["max_side"] = max_side
            if "size" not in it:
                with Image.open(it["path"]) as im:
                    it["size"] = im.size               # reads the header only
            b, (w, h) = it["bbox"], it["size"]
            it["box1000"] = [1000 * b[0] / w, 1000 * b[1] / h, 1000 * b[2] / w, 1000 * b[3] / h]
            it["target"] = (round((it["box1000"][0] + it["box1000"][2]) / 2), round((it["box1000"][1] + it["box1000"][3]) / 2))
            out.append(it)
        self._data[key] = out
        return out

    def excluded(self):
        """Ids of ScreenSpot-v2 cases that are never scored, because public training data
        (OS-Atlas and ScaleCUA macOS) was captured on the same screens. See docs/MAC_DATA.md."""
        path = f"{self.root}/ssv2/excluded_overlap.json"
        if not os.path.exists(path):
            return set()
        return {f"{e['split']}_{int(e['index']):04d}" for e in json.load(open(path))}

    def image(self, it):
        """The screenshot of a sample, shrunk to its `max_side`. Decoded on demand; the most
        recently used few hundred are kept, so large training sets do not fill the memory."""
        if "image" in it:                       # samples made before images were loaded on demand
            return it["image"]
        key = (it["path"], it["max_side"])
        if key in self._images:
            self._images[key] = self._images.pop(key)            # move to the back (most recent)
            return self._images[key]
        im = Image.open(it["path"]).convert("RGB")
        scale = it["max_side"] / max(im.size) if it["max_side"] else 1
        if scale < 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        self._images[key] = im
        while len(self._images) > IMAGE_CACHE:
            self._images.pop(next(iter(self._images)))
        return im

    def _inputs(self, model, it, answer=None):
        messages = [{"role": "user", "content": [
            {"type": "image", "image": self.image(it)},
            {"type": "text", "text": PROMPT.format(instruction=it["instruction"].rstrip("."))}]}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True,
            return_tensors="pt", enable_thinking=False).to(model.device)
        n_prompt = inputs["input_ids"].shape[1]
        if answer is not None:
            self._append(inputs, answer)
        return inputs, n_prompt

    def _append(self, inputs, text):
        """Append text tokens to a prepared input; returns how many tokens were added."""
        ids = self.processor.tokenizer(text, add_special_tokens=False, return_tensors="pt")["input_ids"].to(inputs["input_ids"].device)
        n, extra = inputs["input_ids"].shape[1], ids.shape[1]
        for key, value in list(inputs.items()):
            # every per-token tensor has to grow with the appended text (text tokens: type 0).
            # Per-token tensors are integer rows of length n; the float test keeps the image patches
            # (pixel_values, 1536 wide) out even when the sequence happens to be 1536 tokens long.
            if (key != "input_ids" and torch.is_tensor(value) and value.ndim == 2 and value.shape[0] == 1
                    and value.shape[1] == n and not value.is_floating_point()):
                fill = 1 if key == "attention_mask" else 0
                inputs[key] = torch.cat([value, torch.full((value.shape[0], extra), fill, dtype=value.dtype, device=value.device)], dim=1)
        inputs["input_ids"] = torch.cat([inputs["input_ids"], ids], dim=1)
        return extra

    def _glue(self):
        """The text the chat template puts between one answer and the next (around the next
        user message), read off the template itself."""
        if getattr(self, "_glue_cache", None) is None:
            msgs = [{"role": "user", "content": [{"type": "text", "text": "@@U1@@"}]},
                    {"role": "assistant", "content": [{"type": "text", "text": "@@A1@@"}]},
                    {"role": "user", "content": [{"type": "text", "text": "@@U2@@"}]}]
            t = self.processor.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
            self._glue_cache = tuple(t.split("@@A1@@")[1].split("@@U2@@"))
        return self._glue_cache

    def _inputs_multi(self, model, items):
        """One conversation about one screenshot: the first item's question and answer, then
        every further item as another user turn and answer. All items must share the image.

        Returns (inputs, spans); spans[k] = (position of the first token of answer k, its length).
        Several questions per screenshot give several times the training signal for a little
        more compute, since the screenshot's ~1,000 tokens are processed once.
        """
        inputs, n_prompt = self._inputs(model, items[0], self.answer_text(items[0]))
        spans = [(n_prompt, inputs["input_ids"].shape[1] - n_prompt)]
        pre, post = self._glue()
        for it in items[1:]:
            self._append(inputs, pre + PROMPT.format(instruction=it["instruction"].rstrip(".")) + post)
            start = inputs["input_ids"].shape[1]
            spans.append((start, self._append(inputs, self.answer_text(it))))
        return inputs, spans

    def _stop_ids(self):
        tok = self.processor.tokenizer
        ids = {tok.eos_token_id, tok.convert_tokens_to_ids("<|im_end|>"), tok.convert_tokens_to_ids("<|endoftext|>")}
        return [i for i in ids if isinstance(i, int) and i >= 0]

    # ---------------------------------------------------------------- measurements
    @torch.inference_mode()
    def score(self, model, samples, tag=""):
        """Generate an answer per sample; return accuracy, median distance, last-digit counts."""
        hits, dist, digits, groups, answers = 0, [], collections.Counter(), collections.defaultdict(list), []
        for it in samples:
            inputs, n_prompt = self._inputs(model, it)
            out = model.generate(**inputs, max_new_tokens=16, do_sample=False, eos_token_id=self._stop_ids())
            self.forward_passes += 1
            text = self.processor.decode(out[0, n_prompt:], skip_special_tokens=True)
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
            hit = False
            if len(nums) >= 2:
                b = it["box1000"]
                hit = b[0] <= nums[0] <= b[2] and b[1] <= nums[1] <= b[3]
                dist.append(((nums[0] - it["target"][0]) ** 2 + (nums[1] - it["target"][1]) ** 2) ** 0.5)
                digits.update(str(int(v))[-1] for v in nums[:2])
            hits += hit
            groups[it["group"]].append(hit)
            answers.append(text.strip())
        dist.sort()
        r = {"acc": hits / len(samples), "median_dist": dist[len(dist) // 2] if dist else None,
             "by_group": {g: round(sum(v) / len(v), 3) for g, v in sorted(groups.items())},
             "last_digits": {d: digits.get(d, 0) for d in "0123456789"}}
        self._journal("score", tag, r, len(samples))
        r["answers"] = answers
        return r

    @torch.inference_mode()
    def digits(self, model, samples, tag=""):
        """Teacher-force the correct answer '[x,y]' (box centre) and read the model's probabilities.

        Returns, for the hundreds, tens and units digit of each coordinate, the mean probability
        given to a digit that keeps the point inside the box (more significant digits taken from
        the target), plus `p_hit`, the implied probability that every digit is acceptable, and
        `miss_nll`, its negative log.
        One forward pass per sample, no sampling: a much finer signal than hit or miss.
        """
        nll, ok = [], collections.defaultdict(list)
        for it in samples:
            answer = self.answer_text(it)
            inputs, n_prompt = self._inputs(model, it, answer)
            logits = model(**inputs).logits[0].float()
            self.forward_passes += 1
            self._digit_stats(torch.log_softmax(logits[n_prompt - 1:-1], dim=-1), inputs["input_ids"][0, n_prompt:], it, nll, ok)
        r = self._digit_summary(nll, ok)
        self._journal("digits", tag, r, len(samples))
        return r

    @staticmethod
    def _digit_stats(logp, tgt, it, nll, ok):
        """Accumulate answer NLL and, per digit place, the probability of an acceptable digit.

        `logp` holds log-probabilities at the positions that predict each answer token.
        """
        miss = 0.0
        pos = 1                                            # skip '['
        for axis, lo, hi in ((0, it["box1000"][0], it["box1000"][2]), (1, it["box1000"][1], it["box1000"][3])):
            s = str(it["target"][axis])
            for d in range(len(s)):
                place = ("units", "tens", "hundreds", "thousands")[len(s) - 1 - d]
                # distribution over the ten digit tokens (ids 15..24) at this position, so the
                # score does not depend on punctuation habits such as a space after the comma
                probs = torch.softmax(logp[pos + d, 15:25], dim=-1)
                good = 0.0
                for digit in range(10):
                    head = s[:d] + str(digit)
                    # acceptable if some completion of the lower digits lands inside the box
                    low, high = int(head + "0" * (len(s) - d - 1)), int(head + "9" * (len(s) - d - 1))
                    if high >= lo and low <= hi:
                        good += probs[digit].item()
                ok[place].append(good)
                miss -= torch.log(torch.tensor(good + 1e-9)).item()
            pos += len(s) + 2                               # the digits, then ', ' (or ']')
        nll.append(miss)

    @staticmethod
    def _digit_summary(nll, ok):
        """miss_nll: mean over samples of -log P(every digit acceptable). p_hit: mean of that
        probability. p_ok_*: mean probability of an acceptable digit at each place."""
        import math
        return {"miss_nll": sum(nll) / len(nll), "p_hit": sum(math.exp(-v) for v in nll) / len(nll),
                **{f"p_ok_{k}": sum(v) / len(v) for k, v in sorted(ok.items())}}

    @staticmethod
    def answer_text(it):
        """The teacher-forced answer: the box centre, written the way these models write it."""
        return f"[{it['target'][0]}, {it['target'][1]}]"

    @torch.inference_mode()
    def hidden(self, model, samples, where="answer"):
        """Residual-stream activations, shape (samples, layers + 1, width), float32 on the CPU.

        where = "answer": mean over the positions that predict the coordinate digits (teacher forced)
                "last":   the last prompt position
                "image":  mean over the image tokens
        """
        image_id = model.config.image_token_id
        out = []
        for it in samples:
            answer = self.answer_text(it)
            inputs, n_prompt = self._inputs(model, it, answer)
            hs = model(**inputs, output_hidden_states=True).hidden_states
            self.forward_passes += 1
            ids = inputs["input_ids"][0]
            if where == "answer":
                sel = torch.arange(n_prompt - 1, len(ids) - 1, device=ids.device)
            elif where == "last":
                sel = torch.tensor([n_prompt - 1], device=ids.device)
            else:
                sel = (ids == image_id).nonzero().flatten()
            out.append(torch.stack([h[0, sel].float().mean(0) for h in hs]).cpu())
        return torch.stack(out)

    def diff(self, samples, a="B", b="P", where="answer"):
        """Per layer: relative error and cosine similarity between two models' activations."""
        ha, hb = self.hidden(self.load(a), samples, where), self.hidden(self.load(b), samples, where)
        rel = ((ha - hb).norm(dim=-1) / hb.norm(dim=-1)).mean(0)
        cos = torch.nn.functional.cosine_similarity(ha, hb, dim=-1).mean(0)
        return [{"layer": i, "rel_err": round(rel[i].item(), 4), "cosine": round(cos[i].item(), 4)} for i in range(len(rel))]

    # ---------------------------------------------------------------- swapping in the parent
    @contextlib.contextmanager
    def swap(self, predicate, source="P"):
        """Inside the block, Bonsai uses the source model's weights for every tensor whose
        name satisfies `predicate` (a function of the transformers tensor name)."""
        src = Tensors(self.paths[source])
        model = self.B
        params = dict(model.named_parameters())
        saved, swapped = {}, 0
        for name, mod in self.tern.items():
            key = name + ".weight"
            if predicate(key):
                saved[name] = mod._folded if mod._folded is not None else mod.folded_weight()
                mod._folded = src.get(key).to(saved[name].device, saved[name].dtype)
                swapped += mod._folded.numel()
        for key, p in params.items():
            if key.endswith(".scales") or key.endswith(".gate") or not predicate(key) or key not in src.map:
                continue
            saved[key] = p.data.clone()
            p.data.copy_(src.get(key).to(p.device, p.dtype))
            swapped += p.numel()
        self.stack.append(f"swap:{source}:{swapped}")
        try:
            yield swapped
        finally:
            self.stack.pop()
            for k, v in saved.items():
                if k in self.tern:
                    self.tern[k]._folded = v
                else:
                    params[k].data.copy_(v)
            del saved
            torch.cuda.empty_cache()

    # ---------------------------------------------------------------- journal
    def _journal(self, kind, tag, result, n):
        row = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "tag": tag, "n": n,
               "edits": list(self.stack), "result": {k: v for k, v in result.items() if k != "answers"},
               "forward_passes": self.forward_passes}
        with open(f"{self.dir}/journal.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")

    def edit(self, name):
        return Edit(self, name)

    # ---------------------------------------------------------------- fast evaluation
    def fast(self, samples, which="B", every=2, keep=None):
        """A warmed FastEval for `samples` (see fast.py)."""
        from .fast import FastEval
        f = FastEval(self, which, samples, every, keep)
        f.warm()
        return f

    def try_edit(self, edit, fasts, metric="miss_nll", margin=0.0):
        """Apply `edit`, score it on every FastEval in `fasts`, keep it only if the first one
        improves by more than `margin` (lower is better for 'miss_nll', higher for 'p_hit' and 'p_ok_*').

        Returns a dict with before/after per FastEval and whether the edit was kept. The other
        FastEvals are reported, never used for the decision: use one as a held-out check.
        """
        fasts = fasts if isinstance(fasts, (list, tuple)) else [fasts]
        stats = edit.apply()
        first = edit.first_layer()
        results = [f.evaluate(first, tag=edit.name) for f in fasts]
        before, after = fasts[0].baseline[metric], results[0][metric]
        better = (before - after) > margin if metric == "miss_nll" else (after - before) > margin
        if better:
            for f, r in zip(fasts, results):
                f.commit(r)
        else:
            for f in fasts:
                f.discard()
            edit.revert()
        out = {"edit": edit.name, "kept": better, "metric": metric, "first_layer": first,
               "codes_changed": stats["codes_changed"], "scales_changed": stats["scales_changed"],
               "sets": [{"before": f.baseline if not better else None, "after": r} for f, r in zip(fasts, results)]}
        self._journal("try_edit", edit.name, {"kept": better, "before": before, "after": after,
                                              "held_out": [r[metric] for r in results[1:]]}, len(fasts[0].samples))
        return out

    # ---------------------------------------------------------------- instant regression check
    @torch.inference_mode()
    def canary(self, model, tag=""):
        """Seconds-long check that nothing else collapsed (bench/canary).

        Teacher-forces the expected answer of 50 short questions in seven skills. Returns, per
        skill and overall, `tf_exact` (share of questions where every answer token is the
        model's top choice) and `nll` (mean negative log-probability per answer token).
        """
        items = [json.loads(line) for line in open(f"{self.root}/bench/canary/canary.jsonl")]
        tok = self.processor.tokenizer
        by = collections.defaultdict(lambda: [0.0, 0, 0, 0])      # nll sum, tokens, exact, questions
        for it in items:
            prompt = self.processor.apply_chat_template(
                [{"role": "user", "content": [{"type": "text", "text": it["prompt"]}]}],
                add_generation_prompt=True, tokenize=False, enable_thinking=False)
            p = tok(prompt, add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.device)
            a = tok(it["answer"], add_special_tokens=False, return_tensors="pt")["input_ids"].to(model.device)
            logits = model(input_ids=torch.cat([p, a], dim=1), use_cache=False).logits[0, p.shape[1] - 1:-1].float()
            self.forward_passes += 1
            logp = torch.log_softmax(logits, dim=-1)
            tgt = a[0]
            for key in (it["skill"], "all"):
                s = by[key]
                s[0] += -logp[torch.arange(len(tgt), device=logp.device), tgt].sum().item()
                s[1] += len(tgt)
                s[2] += int(bool((logp.argmax(-1) == tgt).all()))
                s[3] += 1
        r = {k: {"tf_exact": round(v[2] / v[3], 3), "nll": round(v[0] / v[1], 3)} for k, v in sorted(by.items())}
        self._journal("canary", tag, r, len(items))
        return r

    # ---------------------------------------------------------------- notes about the weights
    def note(self, subject, text, evidence=None):
        """Record a finding about a part of the model (a layer, a module, a behaviour).

        Notes accumulate in lab/notes.jsonl and are rendered to lab/ATLAS.md, the running map
        of what is known about these weights. State the evidence: the measurement that
        supports the note, with numbers.
        """
        row = {"time": time.strftime("%Y-%m-%d %H:%M"), "subject": subject, "text": text,
               "evidence": evidence, "edits": list(self.stack)}
        with open(f"{self.dir}/notes.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")
        self._render_atlas()

    def notes(self, subject=None):
        path = f"{self.dir}/notes.jsonl"
        rows = [json.loads(line) for line in open(path)] if os.path.exists(path) else []
        return [r for r in rows if subject is None or r["subject"] == subject]

    def _render_atlas(self):
        by = collections.defaultdict(list)
        for r in self.notes():
            by[r["subject"]].append(r)
        lines = ["# Atlas of the Bonsai 2 9B weights", "",
                 "What has been learned about parts of the model, each with the measurement behind it.",
                 "Generated from `lab/notes.jsonl` by the weight lab; add entries with `lab.note(...)`.", ""]
        for subject in sorted(by):
            lines += [f"## {subject}", ""]
            for r in by[subject]:
                lines.append(f"- **{r['time']}** {r['text']}")
                if r["evidence"]:
                    lines.append(f"  - Evidence: {r['evidence']}")
                if r["edits"]:
                    lines.append(f"  - Edits active: {', '.join(r['edits'])}")
            lines.append("")
        with open(f"{self.dir}/ATLAS.md", "w") as f:
            f.write("\n".join(lines))


class Edit:
    """A named, reversible change to Bonsai's ternary weights.

    Build it with scale/delete/flip/set_scales/refit, then apply(). revert() restores the exact
    previous state. Only codes in {-1, 0, +1} and per-group scales ever change, so an applied
    edit can always be written back as a ternary file.
    """

    def __init__(self, lab, name):
        self.lab, self.name, self.ops, self.backup, self.applied = lab, name, [], {}, False

    def _mod(self, module):
        return self.lab.tern[module]

    # each op is (module, function mutating the module in place)
    def scale(self, module, factor, rows=slice(None), groups=slice(None)):
        """Multiply the scales of the chosen rows and input groups by `factor`."""
        self.ops.append((module, lambda m: m.scales.data[rows, groups].mul_(factor)))
        return self

    def set_scales(self, module, scales):
        self.ops.append((module, lambda m: m.scales.data.copy_(scales.to(m.scales))))
        return self

    def delete(self, module, mask):
        """Set to zero every weight where the boolean `mask` (rows, width) is true."""
        self.ops.append((module, lambda m: m.codes.masked_fill_(mask.to(m.codes.device), 0)))
        return self

    def flip(self, module, rows, cols, codes):
        """Set individual weights to given ternary values (-1, 0 or +1)."""
        self.ops.append((module, lambda m: m.codes.index_put_((rows.to(m.codes.device), cols.to(m.codes.device)),
                                                               codes.to(m.codes))))
        return self

    def refit(self, module, dense_target, change="scales"):
        """Move the layer toward a dense target matrix (original basis) while staying ternary.

        change="scales": keep every code, set each group's scale to the least-squares optimum.
        change="codes":  also re-choose the codes of each group (optimal ternary fit per group).
        """
        def op(m):
            target = ternary.fwht(dense_target.to(m.codes.device).float() * m.signs, m.block)   # into the rotated basis
            t = target.view(target.shape[0], -1, ternary.GROUP)
            if change == "codes":
                mag, order = t.abs().sort(dim=-1, descending=True)
                csum = mag.cumsum(-1)
                k = torch.arange(1, ternary.GROUP + 1, device=t.device)
                gain = csum ** 2 / k                               # error reduction for keeping the top k
                best = gain.argmax(-1, keepdim=True)
                keep = torch.zeros_like(t, dtype=torch.bool).scatter_(-1, order, k.view(1, 1, -1) <= (best + 1))
                m.codes.copy_((torch.sign(t) * keep).to(torch.int8).view_as(m.codes))
            c = m.codes.view(t.shape).float()
            m.scales.data.copy_(((c * t).sum(-1) / c.abs().sum(-1).clamp_min(1)).clamp_min(0))
        self.ops.append((module, op))
        return self

    def first_layer(self):
        """Index of the earliest layer this edit touches (number of layers = output head only)."""
        idx = []
        for module, _ in self.ops:
            m = re.search(r"layers\.(\d+)\.", module)
            idx.append(int(m.group(1)) if m else len(self.lab.B.model.language_model.layers))
        return min(idx)

    @torch.no_grad()
    def apply(self):
        assert not self.applied
        for module, op in self.ops:
            m = self._mod(module)
            if module not in self.backup:
                self.backup[module] = (m.codes.clone(), m.scales.data.clone())
            op(m)
            m.invalidate()
        self.applied = True
        self.lab.stack.append(self.name)
        return self.stats()

    @torch.no_grad()
    def revert(self):
        assert self.applied
        for module, (codes, scales) in self.backup.items():
            m = self._mod(module)
            m.codes.copy_(codes)
            m.scales.data.copy_(scales)
            m.invalidate()
        self.applied = False
        self.lab.stack.remove(self.name)

    @torch.no_grad()
    def stats(self):
        """How much changed, per module and in total."""
        rows, total_codes, total_scales = {}, 0, 0
        for module, (codes, scales) in self.backup.items():
            m = self._mod(module)
            dc, ds = int((m.codes != codes).sum()), int((m.scales.data != scales).sum())
            rows[module] = {"codes_changed": dc, "scales_changed": ds}
            total_codes, total_scales = total_codes + dc, total_scales + ds
        return {"edit": self.name, "codes_changed": total_codes, "scales_changed": total_scales, "modules": rows}

    @torch.no_grad()
    def save(self):
        """Store the edit compactly: for each touched module, the changed positions and new values."""
        assert self.applied
        out = {}
        for module, (codes, scales) in self.backup.items():
            m = self._mod(module)
            ci = (m.codes != codes).nonzero()
            si = (m.scales.data != scales).nonzero()
            out[module] = {"code_idx": ci.cpu(), "code_val": m.codes[ci[:, 0], ci[:, 1]].cpu(),
                           "scale_idx": si.cpu(), "scale_val": m.scales.data[si[:, 0], si[:, 1]].cpu()}
        digest = hashlib.sha1(json.dumps(self.stats(), sort_keys=True).encode()).hexdigest()[:8]
        path = f"{self.lab.dir}/edits/{self.name}_{digest}.pt"
        torch.save(out, path)
        return path
