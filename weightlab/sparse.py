"""Skip the blank areas of a screenshot: drop image tokens before the language model reads them.

One image token covers a 32x32 px cell of the screenshot (a 2x2 group of 16 px patches). On the
target Mac nearly all the time of an answer goes into the language model reading about 1,000 of
them, and many cells are flat background. Removing the tokens of flat cells shortens the read in
proportion (ShowUI's UI-guided token selection, for GUI models). Zeroing the pixels does nothing:
the tokens have to leave the sequence.

What has to be passed (Qwen3.5, transformers 5.23, `modeling_qwen3_5.py`):

  * `inputs_embeds`: the token embeddings with the vision tower's features already written over
    the image placeholders, then indexed by the positions that remain. The vision tower still
    sees the whole image, so the features of the kept cells are exactly the usual ones.
  * `position_ids` with three rows (time, height, width), computed for the WHOLE sequence by
    `model.model.get_rope_index` and indexed the same way. An image token's rows are (start,
    start + row, start + column); text after the image continues at start + max(rows, columns),
    whatever the number of image tokens. So a kept token and all the text keep their positions.
    The fourth row some callers pass (text order; `generate` adds it) only reaches the mask
    builders, not the rotary embedding, and can be left out.
  * `attention_mask`: ones, of the reduced length.

What cannot be kept: 24 of the 32 layers are recurrent ("linear attention", a gated delta rule
behind a causal convolution over the previous 3 tokens). They have no positions; they see the
order of the sequence. For them a dropped token is simply absent: its neighbours close up and
its contribution to the running state is missing. Only the 8 full-attention layers get the
original geometry through the position ids. That part is the model's own design, not a choice.

Measured (experiment 021, docs/SKIP_BLANK.md): with nothing dropped the logits equal the normal
forward pass exactly, and the read gets shorter as expected, but on the current weights every rule
costs accuracy (the mildest, `win5` at threshold 1, about 0.05 p_hit for 10% of the image
tokens), because the model takes much of its sense of place from the order of the stream.

    prep = sparse.prepare(lab, model, sample)            # vision tower once; whole sequence
    keep = ~sparse.blank(prep.lo, prep.hi, thr=8)        # (rows, cols) of cells to keep
    logits, idx = sparse.logits(model, prep, keep)       # idx: which positions remained
    text = sparse.generate(lab, model, prep, keep)       # greedy answer on the reduced prompt
    with sparse.dropping(thr=8): tuner.train(...)        # TaskTuner / chat.score with dropping
"""
import collections
import contextlib
import re
import time

import torch
import torch.nn.functional as F

RULES = ("cell", "nbr", "win3", "win5", "bands")


class Prepared:
    """One sample, ready for the language model: the whole sequence, nothing dropped yet."""
    __slots__ = ("emb", "pos", "img_idx", "lo", "hi", "n_prompt", "tgt", "grid", "vision_seconds")


def cell_minmax(inputs, std=(0.5, 0.5, 0.5), merge=2, patch=16, tpatch=2):
    """Lowest and highest value of each colour channel inside each image token's cell, in 0..255
    units; two tensors of shape (rows, cols, 3). Read from `pixel_values`, so these are the
    pixels the model sees, after the lab's and the processor's resizing.

    `pixel_values` has one row per 16 px patch (3 channels x 2 frames x 16 x 16 values); the four
    patches of a token are consecutive rows, and tokens run row by row over the image."""
    grid = inputs["image_grid_thw"]
    assert grid.shape[0] == 1 and int(grid[0, 0]) == 1, "one still image per sample"
    gh, gw = int(grid[0, 1]) // merge, int(grid[0, 2]) // merge
    x = inputs["pixel_values"].float().view(gh * gw, merge * merge, 3, tpatch, patch, patch)
    scale = 255 * torch.tensor(std, device=x.device, dtype=x.dtype)
    lo = x.amin(dim=(1, 3, 4, 5)) * scale
    hi = x.amax(dim=(1, 3, 4, 5)) * scale
    return lo.view(gh, gw, 3), hi.view(gh, gw, 3)


def blank(lo, hi, thr, rule="cell"):
    """Boolean (rows, cols): True where the cell may be dropped.

    cell   the cell's colour range (largest of the three channels' max - min) is below `thr`
    nbr    the cell and its 8 neighbours are all blank by the rule above, so the cells along
           the edge of any element stay (cells outside the image count as blank)
    win3   the 3x3 block of cells around it (96x96 px) is one flat colour: the range over the
           whole block is below `thr`. Stricter than `nbr`: also keeps both sides of a colour
           change that happens to fall exactly on a cell boundary. Only the inside of large flat
           regions goes; every cell that touches anything stays.
    win5   the same over the 5x5 block (160x160 px): a two-cell margin around everything.
           (`win7`, ... work too; `win` means `win3`.)
    bands  every cell of a row (or column) of the grid that is one flat colour from edge to edge
    """
    b = (hi - lo).amax(-1) < thr
    if rule == "cell":
        return b
    if rule == "nbr":
        return F.max_pool2d((~b).float()[None, None], 3, 1, 1)[0, 0] == 0
    if rule.startswith("win"):
        k = int(rule[3:] or 3)
        hk = F.max_pool2d(hi.permute(2, 0, 1)[None], k, 1, k // 2)[0]
        lk = -F.max_pool2d(-lo.permute(2, 0, 1)[None], k, 1, k // 2)[0]
        return (hk - lk).amax(0) < thr
    if rule == "bands":
        # whole rows and whole columns of one flat colour: what remains is still a full
        # rectangular grid read row by row, only with fewer rows and columns
        rows = (hi.amax(1) - lo.amin(1)).amax(-1) < thr
        cols = (hi.amax(0) - lo.amin(0)).amax(-1) < thr
        return rows[:, None] | cols[None, :]
    raise ValueError(rule)


def keep_mask(prep, thr, rule="cell"):
    """Cells to keep, (rows, cols). Never empty: a completely flat image keeps its first cell."""
    if not thr:
        return None
    keep = ~blank(prep.lo, prep.hi, thr, rule)
    if not keep.any():
        keep[0, 0] = True
    return keep


@torch.no_grad()
def prepare_inputs(model, inputs, n_prompt=None, std=(0.5, 0.5, 0.5)):
    """Run the vision tower and build what the language model needs for the whole sequence."""
    core = model.model
    ids = inputs["input_ids"]
    p = Prepared()
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    feats = core.get_image_features(inputs["pixel_values"], inputs["image_grid_thw"], return_dict=True).pooler_output
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    p.vision_seconds = time.perf_counter() - t0
    emb = core.get_input_embeddings()(ids)
    feats = torch.cat(list(feats), dim=0).to(emb.device, emb.dtype)
    is_img = ids == model.config.image_token_id
    assert int(is_img.sum()) == feats.shape[0]
    p.emb = emb.masked_scatter(is_img.unsqueeze(-1), feats)
    p.pos, _ = core.get_rope_index(ids, mm_token_type_ids=inputs["mm_token_type_ids"],
                                   image_grid_thw=inputs["image_grid_thw"],
                                   attention_mask=inputs.get("attention_mask"))
    p.img_idx = is_img[0].nonzero().flatten()
    p.lo, p.hi = cell_minmax(inputs, std)
    p.grid = tuple(p.lo.shape[:2])
    assert p.grid[0] * p.grid[1] == p.img_idx.numel()
    p.n_prompt = n_prompt
    p.tgt = ids[0, n_prompt:].clone() if n_prompt is not None else None
    return p


def prepare(lab, model, it, answer=True):
    """A lab sample (teacher-forced answer appended unless answer=False), prepared."""
    inputs, n_prompt = lab._inputs(model, it, lab.answer_text(it) if answer else None)
    std = tuple(getattr(lab.processor.image_processor, "image_std", None) or (0.5, 0.5, 0.5))
    return prepare_inputs(model, inputs, n_prompt, std)


def sequence(prep, keep=None, upto=None):
    """Positions of the whole sequence that remain when the image tokens of cells with
    keep == False are dropped. `upto` cuts the sequence (e.g. at the end of the prompt)."""
    n = prep.emb.shape[1] if upto is None else upto
    stay = torch.ones(n, dtype=torch.bool, device=prep.emb.device)
    if keep is not None:
        stay[prep.img_idx[~keep.flatten()]] = False
    return stay.nonzero().flatten()


def run(model, prep, keep=None, upto=None, hidden=False, positions="original"):
    """The language model on the reduced sequence. Returns (output, idx): idx[k] is the position
    in the whole sequence of the k-th remaining token.

    positions="original" passes every remaining token's own position (the point of this module);
    "sequential" passes none, so the model numbers the reduced sequence 0, 1, 2, ... on all
    three axes (a control that shows what the position ids are worth)."""
    idx = sequence(prep, keep, upto)
    kw = {"position_ids": prep.pos[:, :, idx]} if positions == "original" else {}
    out = model.model.language_model(
        inputs_embeds=prep.emb[:, idx],
        attention_mask=torch.ones(1, idx.numel(), dtype=torch.long, device=idx.device),
        use_cache=False, output_hidden_states=hidden, **kw)
    return out, idx


def logits(model, prep, keep=None, hidden=False):
    """Logits at every remaining position: (logits, idx) or (logits, idx, hidden_states)."""
    out, idx = run(model, prep, keep, hidden=hidden)
    lg = model.lm_head(out.last_hidden_state)
    return (lg, idx, out.hidden_states) if hidden else (lg, idx)


def answer_positions(prep, idx, start, n):
    """Where the n positions that predict answer tokens start..start+n-1 of the whole sequence
    sit in the reduced one. Every image token must come before the answer."""
    dropped = prep.emb.shape[1] - idx.numel()
    assert int(prep.img_idx.max()) < start - 1
    return torch.arange(start - 1 - dropped, start - 1 - dropped + n, device=idx.device)


def answer_logits(model, prep, keep=None, positions="original", timed=False):
    """Logits at the positions that predict the teacher-forced answer (output head on those
    only). With timed=True also returns the seconds the language model's body took."""
    if timed:
        torch.cuda.synchronize()
        t0 = time.perf_counter()
    out, idx = run(model, prep, keep, positions=positions)
    if timed:
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
    at = answer_positions(prep, idx, prep.n_prompt, prep.tgt.numel())
    lg = model.lm_head(out.last_hidden_state[0, at])
    return (lg, idx.numel(), dt) if timed else lg


@torch.inference_mode()
def score(lab, model, samples, preps, keeps, positions="original"):
    """Teacher-forced score with tokens dropped: the lab's p_hit and digit probabilities, the
    share of image tokens dropped (mean, least, most), the mean sequence length and the mean
    seconds per pass of the language model."""
    nll, ok, share, length, secs = [], collections.defaultdict(list), [], [], []
    for it, prep, keep in zip(samples, preps, keeps):
        lg, n, dt = answer_logits(model, prep, keep, positions, timed=True)
        lab.forward_passes += 1
        lab._digit_stats(torch.log_softmax(lg.float(), dim=-1), prep.tgt, it, nll, ok)
        share.append(0.0 if keep is None else 1 - keep.float().mean().item())
        length.append(n)
        secs.append(dt)
    r = lab._digit_summary(nll, ok)
    r.update(dropped=sum(share) / len(share), dropped_min=min(share), dropped_max=max(share),
             tokens=sum(length) / len(length), seconds=sum(secs) / len(secs), n=len(samples))
    r["per_sample"] = {"p": [float(torch.tensor(-v).exp()) for v in nll], "dropped": share, "seconds": secs}
    return r


@torch.inference_mode()
def generate(lab, model, prep, keep=None, max_new_tokens=16, timed=False):
    """Greedy answer from the reduced prompt, written out because `model.generate` rebuilds the
    position ids itself. Each new token gets the next position after the prompt on all three
    axes, as in the whole sequence. With keep=None this is `model.generate` (checked in 021)."""
    lm, embed = model.model.language_model, model.model.get_input_embeddings()
    idx = sequence(prep, keep, upto=prep.n_prompt)
    stop = set(lab._stop_ids())
    if timed:
        torch.cuda.synchronize()
        t0 = time.perf_counter()
    out = lm(inputs_embeds=prep.emb[:, idx], position_ids=prep.pos[:, :, idx], use_cache=True)
    if timed:
        torch.cuda.synchronize()
        first = time.perf_counter() - t0
    past = out.past_key_values
    p = prep.pos[:, :, prep.n_prompt - 1:prep.n_prompt]
    h, toks = out.last_hidden_state[:, -1], []
    for _ in range(max_new_tokens):
        nxt = model.lm_head(h).argmax(-1)
        if nxt.item() in stop:
            break
        toks.append(nxt.item())
        p = p + 1
        out = lm(inputs_embeds=embed(nxt)[:, None], position_ids=p, past_key_values=past, use_cache=True)
        past, h = out.past_key_values, out.last_hidden_state[:, -1]
    text = lab.processor.decode(toks, skip_special_tokens=True)
    if timed:
        torch.cuda.synchronize()
        return text, first, time.perf_counter() - t0
    return text


def hit(it, text):
    """Is the generated answer inside the target box (the test `Lab.score` applies)?"""
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", text)]
    b = it["box1000"]
    return len(nums) >= 2 and b[0] <= nums[0] <= b[2] and b[1] <= nums[1] <= b[3]


@contextlib.contextmanager
def dropping(thr, rule="cell", std=(0.5, 0.5, 0.5)):
    """Inside the block, `chat.answer_logits` drops blank image tokens. That function is what
    `TaskTuner.train` and `chat.score` read the answer through, so training and scoring both run
    on the reduced sequence without any change to them. Samples without an image pass through."""
    from . import chat
    original = chat.answer_logits

    def answer_logits(model, inputs, start, n):
        if inputs.get("pixel_values") is None or not thr:
            return original(model, inputs, start, n)
        prep = prepare_inputs(model, inputs, None, std)
        out, idx = run(model, prep, keep_mask(prep, thr, rule))
        return model.lm_head(out.last_hidden_state[0, answer_positions(prep, idx, start, n)])

    chat.answer_logits = answer_logits
    try:
        yield
    finally:
        chat.answer_logits = original
