"""Score weight edits quickly by caching the model's state at layer boundaries.

An edit to layer L cannot change what layers 0..L-1 compute. `FastEval.warm()` runs every
sample once and keeps the residual stream entering every `every`-th layer (and the one
leaving the last layer). `evaluate(first_layer)` then restarts each sample from the nearest
cached boundary at or before the first edited layer, so:

  an edit to the output head       costs one small matrix product per sample
  an edit to layer 24              re-runs layers 24..31 only
  an edit to the vision tower or   needs warm() again
  the embeddings

Evaluating a candidate also produces the cache for the state after that edit; `commit()` keeps
it (the edit was kept), otherwise it is dropped. So the cache is always warm for the next
candidate without any extra work.

The score is teacher-forced: the correct answer "[x,y]" is appended and the probabilities the
model gives to acceptable digits are read off. No sampling, one pass, and far more sensitive
than hit or miss. Confirm anything promising with `Lab.score`, which generates real answers.
"""
import collections
import time

import torch


class FastEval:
    def __init__(self, lab, which, samples, every=2, keep=None):
        """keep: store only these layer boundaries (e.g. {0, 4}) instead of every `every`-th.
        A large sample set then costs 9 MB per sample and boundary."""
        self.lab, self.which, self.samples, self.every = lab, which, samples, every
        self.keep = set(keep) if keep is not None else None
        self.model = lab.load(which)
        self.text = self.model.model.language_model
        self.layers = list(self.text.layers)
        self.types = list(self.model.config.text_config.layer_types)
        self.n_layers = len(self.layers)
        self.cache, self.pending, self.baseline = [], None, None

    def _stored(self, i):
        keep = getattr(self, "keep", None)          # objects made before `keep` existed
        return i in keep if keep is not None else i % self.every == 0

    @torch.inference_mode()
    def warm(self):
        """One full forward per sample; stores everything later evaluations reuse."""
        started = time.time()
        self.cache = []
        nll, ok = [], collections.defaultdict(list)
        for it in self.samples:
            answer = self.lab.answer_text(it)
            inputs, n_prompt = self.lab._inputs(self.model, it, answer)
            entry = {"hidden": {}, "kw": {}, "n_prompt": n_prompt, "tgt": inputs["input_ids"][0, n_prompt:].clone()}
            hooks = []

            def pre(i):
                def hook(module, args, kwargs):
                    if self._stored(i):
                        entry["hidden"][i] = args[0].detach().clone()
                    if self.types[i] not in entry["kw"]:
                        entry["kw"][self.types[i]] = dict(kwargs)
                return hook

            for i, layer in enumerate(self.layers):
                hooks.append(layer.register_forward_pre_hook(pre(i), with_kwargs=True))
            hooks.append(self.text.norm.register_forward_pre_hook(
                lambda module, args: entry.__setitem__("final", args[0].detach().clone())))
            try:
                logits = self.model(**inputs, use_cache=False).logits[0].float()
            finally:
                for h in hooks:
                    h.remove()
            self.lab.forward_passes += 1
            self.lab._digit_stats(torch.log_softmax(logits[n_prompt - 1:-1], dim=-1), entry["tgt"], it, nll, ok)
            self.cache.append(entry)
        self.baseline = self.lab._digit_summary(nll, ok)
        self.pending = None
        gb = sum(t.numel() * t.element_size() for e in self.cache for t in list(e["hidden"].values()) + [e["final"]]) / 1e9
        print(f"warm: {len(self.samples)} samples in {time.time() - started:.1f}s, cache {gb:.1f} GB, "
              f"baseline {_fmt(self.baseline)}")
        return self.baseline

    @torch.inference_mode()
    def evaluate(self, first_layer=0, tag=""):
        """Score the current weights, assuming nothing before `first_layer` changed since the
        cache was last warmed or committed. `first_layer` = number of layers means head only."""
        assert self.cache, "call warm() first"
        started = time.time()
        nll, ok, pending = [], collections.defaultdict(list), []
        for it, c in zip(self.samples, self.cache):
            new = {}
            if first_layer >= self.n_layers:
                h = c["final"]
            else:
                start = max(k for k in c["hidden"] if k <= first_layer)
                h = c["hidden"][start]
                for i in range(start, self.n_layers):
                    if i > start and self._stored(i):
                        new[i] = h
                    h = self.layers[i](h, **c["kw"][self.types[i]])
            answer_states = self.text.norm(h)[0, c["n_prompt"] - 1:-1]
            logits = self.model.lm_head(answer_states).float()
            self.lab._digit_stats(torch.log_softmax(logits, dim=-1), c["tgt"], it, nll, ok)
            pending.append((new, h))
        self.pending = pending
        r = self.lab._digit_summary(nll, ok)
        r["seconds"] = round(time.time() - started, 2)
        self.lab._journal("fast", tag, r, len(self.samples))
        return r

    def drop(self, ids):
        """Remove samples by id (for example cases found to overlap training data). Returns how
        many were removed; the stored baseline is no longer valid afterwards."""
        keep = [k for k, it in enumerate(self.samples) if it["id"] not in ids]
        removed = len(self.samples) - len(keep)
        self.samples = [self.samples[k] for k in keep]
        self.cache = [self.cache[k] for k in keep]
        self.pending = None
        return removed

    def commit(self, result=None):
        """Keep the state computed by the last evaluate() as the new cache (the edit stays)."""
        assert self.pending is not None
        for c, (new, final) in zip(self.cache, self.pending):
            c["hidden"].update(new)
            c["final"] = final
        self.pending = None
        if result is not None:
            self.baseline = {k: v for k, v in result.items() if k != "seconds"}

    def discard(self):
        self.pending = None


def _fmt(r):
    return " ".join(f"{k}={v:.3f}" for k, v in r.items() if isinstance(v, float))
