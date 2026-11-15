"""A "System 1" pointing head: three numbers straight from the model's internal state.

Writing "[512, 87]" costs about ten tokens of generation and forces the position through decimal
digits. This head skips both. After the screenshot has been read (those states can be cached) and
the instruction has been fed, it takes

    q     the model's state at the last position of the prompt, after some layer
    keys  the model's states at the image positions (one per 32 x 32 px cell), after some layer

and returns, in one small computation with no token generation,

    x, y   a point on the 0..1000 scale
    click  a logit: should anything be clicked at all (is the thing asked for on the screen)

PointHead ("pointer" kind): score every image cell against the query, take the probability-
weighted average of the cell centres (so the answer is not limited to cell centres), then add a
small learned offset. About 2.4 million parameters.

RegressHead ("regress" kind): the literal version of the idea, an MLP from q alone to (x, y,
click), with no look at the image cells. Trained alongside as the control.

The backbone is frozen while a head trains, so one forward pass per screenshot trains any number
of heads at once; `HeadBench` does that for a list of (query layer, key layer) choices, including
early layers. If a head that reads layer 20 is as good as one that reads layer 32, the last 12
layers need not run for pointing at all.
"""
import math
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F


class PointHead(nn.Module):
    def __init__(self, d=4096, r=256):
        super().__init__()
        self.qn, self.kn = nn.LayerNorm(d), nn.LayerNorm(d)
        self.A, self.B = nn.Linear(d, r), nn.Linear(d, r)
        self.temp = nn.Parameter(torch.tensor(math.log(8.0)))
        self.off = nn.Sequential(nn.Linear(2 * r, 256), nn.GELU(), nn.Linear(256, 2))
        self.click = nn.Sequential(nn.Linear(r, 128), nn.GELU(), nn.Linear(128, 1))
        nn.init.zeros_(self.off[-1].weight); nn.init.zeros_(self.off[-1].bias)

    def forward(self, q, keys, centres, cell):
        """q (Q, d), keys (N, d), centres (N, 2) and cell (2,) on the 0..1000 scale.
        Returns cell scores (Q, N), points (Q, 2), click logits (Q,)."""
        qa = self.A(self.qn(q))
        kb = self.B(self.kn(keys))
        s = (qa @ kb.t()) * self.temp.exp() / math.sqrt(qa.shape[-1])
        p = torch.softmax(s, dim=-1)
        offset = torch.tanh(self.off(torch.cat([qa, p @ kb], dim=-1))) * cell * 1.5
        return s, p @ centres + offset, self.click(qa).squeeze(-1)


class CrossHead(nn.Module):
    """Second design. The image cells' states do not depend on the question (the screenshot comes
    first), so one dot product has to do all the matching. Here the cells first read the question:
    two small layers in which every cell attends to the question's tokens and to the other cells.
    Then each cell gives a score and its own estimate of where the target centre lies relative to
    itself; the answer is the score-weighted average of those estimates over the 3 x 3 cells around
    the best one. Keys can mix several depths (0 = the vision features as they enter the model).
    About 3 million parameters."""

    def __init__(self, key_layers, d=4096, r=256, layers=2, click="attention"):
        """click: what the click-or-not logit reads.
        "attention"  (default; experiment 016 and every head saved so far) the mean of the projected
                     question tokens joined with the score-weighted cell states. In experiment 016
                     it never left 50% (it always answered "present").
        "query"      the repair: the model's state at the last prompt position, through its own
                     normalisation and projection, the input PointHead's click output has.
                     HeadBench kind "cross_qclick"."""
        super().__init__()
        self.key_layers = list(key_layers)
        self.click_input = click
        self.kn = nn.ModuleList(nn.LayerNorm(d) for _ in self.key_layers)
        self.kp = nn.ModuleList(nn.Linear(d, r) for _ in self.key_layers)
        self.qn, self.qp = nn.LayerNorm(d), nn.Linear(d, r)
        self.pos = nn.Sequential(nn.Linear(4, r), nn.GELU(), nn.Linear(r, r))
        self.blocks = nn.ModuleList(nn.TransformerDecoderLayer(r, 4, 4 * r, dropout=0.0, batch_first=True, norm_first=True)
                                    for _ in range(layers))
        self.out = nn.LayerNorm(r)
        self.score = nn.Linear(r, 1)
        self.offset = nn.Linear(r, 2)
        if click == "query":
            self.cn, self.cp = nn.LayerNorm(d), nn.Linear(d, r)
            self.click = nn.Sequential(nn.Linear(r, 128), nn.GELU(), nn.Linear(128, 1))
        else:
            self.click = nn.Sequential(nn.Linear(2 * r, 128), nn.GELU(), nn.Linear(128, 1))
        nn.init.zeros_(self.offset.weight); nn.init.zeros_(self.offset.bias)

    def forward(self, qtok, qmask, keys, centres, cell, grid):
        """qtok (Q, T, d) question-token states, qmask (Q, T) True where padded, keys {layer: (N, d)},
        centres (N, 2), cell (2,), grid (rows, cols). Returns scores (Q, N), points (Q, 2), click (Q,)."""
        k = sum(p(n(keys[l])) for l, n, p in zip(self.key_layers, self.kn, self.kp))
        c = centres / 1000
        k = k + self.pos(torch.cat([c, torch.sin(6.2832 * c)], dim=-1))
        x = k.unsqueeze(0).expand(qtok.shape[0], -1, -1)
        mem = self.qp(self.qn(qtok))
        for blk in self.blocks:
            x = blk(x, mem, memory_key_padding_mask=qmask)
        x = self.out(x)
        s = self.score(x).squeeze(-1)                                             # (Q, N)
        est = centres.unsqueeze(0) + torch.tanh(self.offset(x)) * cell * 2.0      # each cell's guess of the centre
        rows, cols = grid
        best = s.argmax(-1)
        br, bc = best // cols, best % cols
        idx = torch.arange(s.shape[1], device=s.device)
        near = ((idx[None] // cols - br[:, None]).abs() <= 1) & ((idx[None] % cols - bc[:, None]).abs() <= 1)
        w = torch.softmax(s.masked_fill(~near, float("-inf")), dim=-1)            # 3 x 3 cells around the best
        pt = (w.unsqueeze(-1) * est).sum(1)
        if self.click_input == "query":
            # The question tokens fill positions 0..n-1 of each row and the last of them is the
            # last prompt position (HeadBench.features), the state PointHead reads as q.
            last = ((~qmask).sum(1) - 1).clamp_min(0)                                 # (Q,)
            q = qtok[torch.arange(qtok.shape[0], device=qtok.device), last]           # (Q, d)
            return s, pt, self.click(self.cp(self.cn(q))).squeeze(-1), est
        qmean = (mem * (~qmask).unsqueeze(-1)).sum(1) / (~qmask).sum(1, keepdim=True).clamp_min(1)
        top = (torch.softmax(s, dim=-1).unsqueeze(-1) * x).sum(1)
        return s, pt, self.click(torch.cat([qmean, top], dim=-1)).squeeze(-1), est


def fourier_position(c, freqs=32):
    """(N, 2) positions in 0..1 -> (N, 4 * freqs): sine and cosine at `freqs` frequencies per axis
    (1, 2, 4, ... are too coarse a ladder for 32 steps; the frequencies run evenly from 1 to freqs cycles)."""
    f = torch.arange(1, freqs + 1, device=c.device, dtype=c.dtype) * 6.283185307
    a = c.unsqueeze(-1) * f                                                       # (N, 2, freqs)
    return torch.cat([torch.sin(a), torch.cos(a)], dim=-1).flatten(1)


class DecoderHead(nn.Module):
    """A larger pointing head (15 Nov): a small transformer decoder in which the REQUEST tokens attend to
    the image tokens (cross-attention) and to each other. The state at the last request position then
    scores every image cell (dot product with the cells' projected states), each cell gives its estimate
    of the target centre, and the same position gives the click logit. Image states of several layers
    are concatenated before the projection. Same outputs and loss as CrossHead.
    HeadBench kind "cross_dec:<width>:<layers>"."""

    def __init__(self, key_layers, d=4096, r=768, layers=2, fourier=False):
        super().__init__()
        self.key_layers = list(key_layers)
        self.kn = nn.ModuleList(nn.LayerNorm(d) for _ in self.key_layers)
        self.kp = nn.Linear(d * len(self.key_layers), r)
        # fourier=True (kind "cross_decp"): each image token's screen position (centre of its square, x and y in
        # 0..1, sine and cosine at 32 frequencies per axis = 128 numbers) through one linear layer that starts
        # at zero, added to the image-token states before anything else reads them
        self.fpos = nn.Linear(128, d) if fourier else None
        if fourier:
            nn.init.zeros_(self.fpos.weight); nn.init.zeros_(self.fpos.bias)
        self.qn, self.qp = nn.LayerNorm(d), nn.Linear(d, r)
        self.pos = nn.Sequential(nn.Linear(4, r), nn.GELU(), nn.Linear(r, r))
        self.blocks = nn.ModuleList(nn.TransformerDecoderLayer(r, 8, 4 * r, dropout=0.0, batch_first=True, norm_first=True)
                                    for _ in range(layers))
        self.out = nn.LayerNorm(r)
        self.qk, self.kk = nn.Linear(r, r), nn.Linear(r, r)
        self.offset = nn.Sequential(nn.Linear(r, r), nn.GELU(), nn.Linear(r, 2))
        self.click = nn.Sequential(nn.Linear(r, 128), nn.GELU(), nn.Linear(128, 1))
        nn.init.zeros_(self.offset[-1].weight); nn.init.zeros_(self.offset[-1].bias)

    def _encode(self, qtok, qmask, keys, centres):
        """(N, r) image-cell states with position, and (Q, r) the state at the last request position."""
        c = centres / 1000
        if self.fpos is not None:
            add = self.fpos(fourier_position(c))
            keys = {l: keys[l] + add for l in self.key_layers}
        k = self.kp(torch.cat([n(keys[l]) for l, n in zip(self.key_layers, self.kn)], dim=-1))     # (N, r)
        k = k + self.pos(torch.cat([c, torch.sin(6.2832 * c)], dim=-1))
        x = self.qp(self.qn(qtok))                                                # (Q, T, r) request tokens
        mem = k.unsqueeze(0).expand(x.shape[0], -1, -1)
        for blk in self.blocks:
            x = blk(x, mem, tgt_key_padding_mask=qmask)
        last = ((~qmask).sum(1) - 1).clamp_min(0)
        q = self.out(x[torch.arange(x.shape[0], device=x.device), last])          # (Q, r) last request position
        return k, q

    def forward(self, qtok, qmask, keys, centres, cell, grid):
        k, q = self._encode(qtok, qmask, keys, centres)
        s = (self.qk(q).unsqueeze(1) * self.kk(k).unsqueeze(0)).sum(-1) / k.shape[-1] ** 0.5       # (Q, N)
        est = centres.unsqueeze(0) + torch.tanh(self.offset(k.unsqueeze(0) + q.unsqueeze(1))) * cell * 2.0
        rows, cols = grid
        best = s.argmax(-1)
        br, bc = best // cols, best % cols
        idx = torch.arange(s.shape[1], device=s.device)
        near = ((idx[None] // cols - br[:, None]).abs() <= 1) & ((idx[None] % cols - bc[:, None]).abs() <= 1)
        w = torch.softmax(s.masked_fill(~near, float("-inf")), dim=-1)            # 3 x 3 cells around the best
        pt = (w.unsqueeze(-1) * est).sum(1)
        return s, pt, self.click(q).squeeze(-1), est


class MaskHead(DecoderHead):
    """D4 (15 Nov): the decoder with a finer-than-token output. Each image token gives up x up scores
    (pixel shuffle), so the output is a mask over the screenshot at the resolution of the original
    patches; the target is the box as a hard mask, the loss 0.5 BCE + 0.5 Dice (recipe of the Seg2Click
    paper, arXiv 2610.16234); the point is the centre of mass of the top region. HeadBench kind
    "cross_mask:<width>:<layers>"."""

    def __init__(self, key_layers, d=4096, r=768, layers=2, up=32):
        super().__init__(key_layers, d=d, r=r, layers=layers)
        self.up = up
        self.pix = nn.Sequential(nn.Linear(r, r), nn.GELU(), nn.Linear(r, up * up))

    def mask(self, qtok, qmask, keys, centres, cell, grid):
        k, q = self._encode(qtok, qmask, keys, centres)
        rows, cols = grid
        m = self.pix(k.unsqueeze(0) + q.unsqueeze(1))                              # (Q, N, up * up)
        m = m.view(q.shape[0], rows, cols, self.up, self.up).permute(0, 1, 3, 2, 4).reshape(q.shape[0], rows * self.up, cols * self.up)
        return m, self.click(q).squeeze(-1)

    @staticmethod
    def _axes(m):
        H, W = m.shape[-2:]
        ys = (torch.arange(H, device=m.device, dtype=torch.float32) + 0.5) / H * 1000
        xs = (torch.arange(W, device=m.device, dtype=torch.float32) + 0.5) / W * 1000
        return xs, ys

    def forward(self, qtok, qmask, keys, centres, cell, grid):
        m, click = self.mask(qtok, qmask, keys, centres, cell, grid)
        p = torch.sigmoid(m.float())
        w = p * (p >= 0.5 * p.amax(dim=(1, 2), keepdim=True))                      # the top region
        xs, ys = self._axes(m)
        tot = w.sum(dim=(1, 2)).clamp_min(1e-6)
        pt = torch.stack(((w.sum(1) * xs).sum(-1) / tot, (w.sum(2) * ys).sum(-1) / tot), dim=-1)
        return None, pt, click

    def mask_loss(self, feats, boxes, present):
        m, click = self.mask(*feats)
        loss = F.binary_cross_entropy_with_logits(click, present)
        pos = present > 0.5
        if pos.any():
            m, b = m[pos].float(), boxes[pos]
            xs, ys = self._axes(m)
            t = (((xs[None, None, :] >= b[:, 0, None, None]) & (xs[None, None, :] <= b[:, 2, None, None])
                  & (ys[None, :, None] >= b[:, 1, None, None]) & (ys[None, :, None] <= b[:, 3, None, None]))).float()
            p = torch.sigmoid(m)
            dice = 1 - (2 * (p * t).sum(dim=(1, 2)) + 1) / (p.sum(dim=(1, 2)) + t.sum(dim=(1, 2)) + 1)
            loss = loss + 0.5 * F.binary_cross_entropy_with_logits(m, t) + 0.5 * dice.mean()
        return loss


class RegressHead(nn.Module):
    def __init__(self, d=4096):
        super().__init__()
        self.net = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, 512), nn.GELU(), nn.Linear(512, 256), nn.GELU(), nn.Linear(256, 3))

    def forward(self, q, keys, centres, cell):
        o = self.net(q)
        return None, torch.sigmoid(o[:, :2]) * 1000, o[:, 2]


def cell_targets(boxes, centres, cell):
    """(Q, N): for each box, a distribution over image cells in proportion to the overlap of the
    cell with the box (a box smaller than a cell puts all its weight on the cells it touches)."""
    lo, hi = centres - cell / 2, centres + cell / 2                      # (N, 2)
    b = boxes[:, None, :]                                                # (Q, 1, 4)
    w = (torch.minimum(hi[None, :, 0], b[..., 2]) - torch.maximum(lo[None, :, 0], b[..., 0])).clamp_min(0)
    h = (torch.minimum(hi[None, :, 1], b[..., 3]) - torch.maximum(lo[None, :, 1], b[..., 1])).clamp_min(0)
    a = w * h
    empty = a.sum(-1, keepdim=True) <= 0                                 # box outside the image: nearest cell
    if empty.any():
        c = torch.stack(((boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2), dim=-1)
        near = F.one_hot(((centres[None] - c[:, None]) ** 2).sum(-1).argmin(-1), centres.shape[0]).float()
        a = torch.where(empty, near, a)
    return a / a.sum(-1, keepdim=True)


def gaussian_targets(boxes, centres, cell):
    """(Q, N): a Gaussian the size of the box (never narrower than half a cell) evaluated at the
    cell centres and normalised. Mass is concentrated on the box centre instead of spread evenly
    over every cell the box touches."""
    c = torch.stack(((boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2), dim=-1)      # (Q, 2)
    sig = torch.maximum((boxes[:, 2:] - boxes[:, :2]) / 4, cell / 2)                                # (Q, 2)
    z = ((centres[None] - c[:, None]) / sig[:, None]).pow(2).sum(-1)
    t = torch.exp(-0.5 * z)
    return t / t.sum(-1, keepdim=True).clamp_min(1e-9)


def point_terms(pt, b):
    """Bounded penalties on a predicted point: how far outside the box it is (grows like a log,
    so one far-off case cannot dominate), and a mild pull to the centre once inside."""
    outside = (b[:, :2] - pt).clamp_min(0) + (pt - b[:, 2:]).clamp_min(0)
    centre, half = (b[:, :2] + b[:, 2:]) / 2, (b[:, 2:] - b[:, :2]) / 2 + 2
    inside = ((pt - centre) / half).clamp(-1, 1).pow(2)
    return torch.log1p(outside / 5).sum(-1).mean() + 0.2 * inside.sum(-1).mean()


def head_loss(head, feats, boxes, present):
    """feats: what HeadBench.features returns for this head; boxes (Q, 4) on the 0..1000 scale;
    present (Q,) 1 if the target exists on this screen."""
    if hasattr(head, "mask_loss"):                   # heads with their own target (MaskHead)
        return head.mask_loss(feats, boxes, present)
    out = head(*feats)
    s, pt, click = out[0], out[1], out[2]
    centres, cell = feats[-3] if isinstance(head, (CrossHead, DecoderHead)) else feats[2], feats[-2] if isinstance(head, (CrossHead, DecoderHead)) else feats[3]
    loss = F.binary_cross_entropy_with_logits(click, present)
    pos = present > 0.5
    if pos.any():
        b = boxes[pos]
        loss = loss + point_terms(pt[pos], b)
        if s is not None:
            logp = torch.log_softmax(s[pos], dim=-1)
            loss = loss - (gaussian_targets(b, centres, cell) * logp).sum(-1).mean()
            inbox = ((centres[None, :, 0] >= b[:, None, 0] - cell[0] / 2) & (centres[None, :, 0] <= b[:, None, 2] + cell[0] / 2)
                     & (centres[None, :, 1] >= b[:, None, 1] - cell[1] / 2) & (centres[None, :, 1] <= b[:, None, 3] + cell[1] / 2))
            loss = loss + 0.5 * (logp.exp() * (~inbox)).sum(-1).mean()               # probability mass outside the box
        if len(out) > 3:                                                          # every nearby cell's own estimate of the centre
            c = torch.stack(((b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2), dim=-1)
            near = ((centres[None] - c[:, None]).abs() <= cell * 2.0).all(-1)        # cells within two cells of the centre
            err = ((out[3][pos] - c[:, None]) / cell).abs().sum(-1)
            loss = loss + (err * near).sum() / near.sum().clamp_min(1)
    return loss


class HeadBench:
    """Train and score several heads at once on a frozen model."""

    def __init__(self, lab, specs, seed=0, lr=1e-3):
        """specs: list of (name, kind, query layer, key layers). Layers count the state after that
        many layers (32 is the last; 0 is the input, i.e. the vision features for image cells).
        kind: "cross" (CrossHead), "pointer" (PointHead, one key layer), "regress" (RegressHead),
        "cross_qclick" (CrossHead whose click output reads the last prompt position)."""
        torch.manual_seed(seed)
        self.lab, self.model = lab, lab.B
        self.specs = [(n, k, ql, tuple(kl) if isinstance(kl, (list, tuple)) else (kl,)) for n, k, ql, kl in specs]
        dev = self.model.device
        d = self.model.config.text_config.hidden_size
        make = {"cross": lambda kl: CrossHead(kl, d=d), "cross_qclick": lambda kl: CrossHead(kl, d=d, click="query"),
                "pointer": lambda kl: PointHead(d=d), "regress": lambda kl: RegressHead(d=d)}
        def build(kind, kl):
            if kind.startswith("cross_mask"):             # "cross_mask:<width>:<layers>"
                _, r, layers = kind.split(":")
                return MaskHead(kl, d=d, r=int(r), layers=int(layers))
            if kind.startswith("cross_dec"):              # "cross_dec:<width>:<layers>"
                _, r, layers = kind.split(":")
                return DecoderHead(kl, d=d, r=int(r), layers=int(layers), fourier=kind.startswith("cross_decp"))
            return make[kind](kl)
        self.heads = {n: build(k, kl).to(dev).float() for n, k, _, kl in self.specs}
        self.params = {n: sum(p.numel() for p in h.parameters()) for n, h in self.heads.items()}
        # lr: one number, or {"pointer": 1e-3, "cross": 5e-4, ...} keyed by the first word of the kind
        self.lrs = {n: (lr[k.split("_")[0]] if isinstance(lr, dict) else lr) for n, k, _, _ in self.specs}
        self.opts = {n: torch.optim.AdamW(h.parameters(), lr=self.lrs[n], weight_decay=0.01) for n, h in self.heads.items()}
        self.layers = sorted({l for _, _, ql, kl in self.specs for l in (ql, *kl)})
        self.lr, self.steps, self.resumed_at = lr, 0, 0

    # ---- features ------------------------------------------------------------------------
    @torch.no_grad()
    def forward(self, inputs):
        out = self.model.model(**inputs, use_cache=False, output_hidden_states=True)
        hs = out.hidden_states
        img = (inputs["mm_token_type_ids"][0] == 1).nonzero().squeeze(-1)
        _, gh, gw = inputs["image_grid_thw"][0].tolist()
        rows, cols = gh // 2, gw // 2                                   # 2 x 2 patches are merged into one token
        assert rows * cols == img.numel(), (rows, cols, img.numel())
        dev = img.device
        ys, xs = torch.meshgrid(torch.arange(rows, device=dev), torch.arange(cols, device=dev), indexing="ij")
        centres = torch.stack(((xs.flatten() + 0.5) / cols * 1000, (ys.flatten() + 0.5) / rows * 1000), dim=-1).float()
        cell = torch.tensor([1000 / cols, 1000 / rows], device=dev)
        return {l: hs[l][0].float() for l in self.layers}, img, centres, cell, (rows, cols)

    def features(self, spec, states, img, centres, cell, grid, ranges):
        """Inputs of one head for the questions whose prompt tokens are `ranges` = [(first, last + 1)]."""
        _, kind, ql, kl = spec
        last = torch.tensor([b - 1 for _, b in ranges], device=img.device)
        if kind.startswith("cross"):
            T = min(96, max(b - a for a, b in ranges))
            qtok = torch.zeros(len(ranges), T, states[ql].shape[-1], device=img.device)
            mask = torch.ones(len(ranges), T, dtype=torch.bool, device=img.device)
            for i, (a, b) in enumerate(ranges):
                a = max(a, b - T)
                qtok[i, :b - a] = states[ql][a:b]; mask[i, :b - a] = False
            return (qtok, mask, {l: states[l][img] for l in kl}, centres, cell, grid)
        return (states[ql][last], states[kl[0]][img], centres, cell)

    def _ranges(self, img, spans):
        """Prompt-token range of each question: from the end of the image (first question) or of
        the previous answer (later ones) to the position that precedes its answer."""
        out, start = [], int(img[-1]) + 1
        for a, n in spans:
            out.append((start, a))
            start = a + n
        return out

    # ---- training ------------------------------------------------------------------------
    def train(self, packs, steps, negatives=0.2, seed=0, report_every=200, total=None, warmup=100):
        """One pack (several questions on one screenshot) per step. With probability `negatives`
        one extra question is added whose instruction belongs to a different screenshot; for it
        only the click output is trained (towards "nothing to click")."""
        rng = random.Random(seed + self.steps)
        total = total or steps
        order = list(range(len(packs)))
        rng.shuffle(order)
        hist = {n: [] for n in self.heads}
        t0 = time.time()
        for k in range(steps):
            items = list(packs[order[k % len(packs)]])
            present = [1.0] * len(items)
            if rng.random() < negatives:
                other = packs[rng.randrange(len(packs))][0]
                if other["path"] != items[0]["path"] and other["group"] != items[0]["group"]:
                    items.append(dict(items[0], id=items[0]["id"] + "-neg", instruction=other["instruction"],
                                      target=(-1, -1), box1000=[0.0, 0.0, 0.0, 0.0]))
                    present.append(0.0)
            try:
                inputs, spans = self.lab._inputs_multi(self.model, items)
                states, img, centres, cell, grid = self.forward(inputs)
            except Exception as e:
                print(f"  skipped a pack ({items[0]['id']}): {type(e).__name__}: {str(e)[:100]}", flush=True)
                continue
            ranges = self._ranges(img, spans)
            boxes = torch.tensor([it["box1000"] for it in items], device=centres.device, dtype=torch.float32)
            pres = torch.tensor(present, device=centres.device)
            # the warm-up counts from where this bench started or was continued (load)
            factor = min(1.0, (self.steps - self.resumed_at + 1) / warmup) * (0.05 + 0.95 * 0.5 * (1 + math.cos(math.pi * min(self.steps, total) / total)))
            for spec in self.specs:
                name = spec[0]
                opt = self.opts[name]
                for g in opt.param_groups:
                    g["lr"] = self.lrs[name] * factor
                opt.zero_grad(set_to_none=True)
                loss = head_loss(self.heads[name], self.features(spec, states, img, centres, cell, grid, ranges), boxes, pres)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.heads[name].parameters(), 1.0)
                opt.step()
                hist[name].append(loss.item())
            self.steps += 1
            self.lab.forward_passes += 1
            if report_every and (k + 1) % report_every == 0:
                print(f"  step {self.steps}  " + "  ".join(f"{n} {sum(h[-report_every:]) / len(h[-report_every:]):.2f}" for n, h in hist.items())
                      + f"  [{(time.time() - t0) / (k + 1):.2f}s/step]", flush=True)
        return {n: sum(h[-200:]) / max(1, len(h[-200:])) for n, h in hist.items()}

    # ---- scoring -------------------------------------------------------------------------
    @torch.no_grad()
    def score(self, samples, negatives=True, seed=1):
        """Each sample asked by itself (no earlier questions in the context), the way the head
        would be used. Returns per head: hit rate (point inside the box), median distance from
        the box centre, and, with negatives, how often `click` separates a real target from an
        instruction taken from another screen (accuracy at logit 0)."""
        rng = random.Random(seed)
        for h in self.heads.values():
            h.eval()
        res = {n: {"hits": 0, "dist": [], "click_ok": 0, "click_n": 0, "near20": 0} for n in self.heads}
        for it in samples:
            cases = [(it, 1.0)]
            if negatives:
                other = samples[rng.randrange(len(samples))]
                if other["group"] != it["group"] or other["path"] != it["path"]:
                    cases.append((dict(it, instruction=other["instruction"]), 0.0))
            for case, present in cases:
                inputs, n_prompt = self.lab._inputs(self.model, case)
                states, img, centres, cell, grid = self.forward(inputs)
                ranges = [(int(img[-1]) + 1, n_prompt)]
                for spec in self.specs:
                    out = self.heads[spec[0]](*self.features(spec, states, img, centres, cell, grid, ranges))
                    r = res[spec[0]]
                    r["click_ok"] += int((out[2].item() > 0) == (present > 0.5)); r["click_n"] += 1
                    if present > 0.5:
                        x, y = out[1][0].tolist()
                        b = it["box1000"]
                        r["hits"] += int(b[0] <= x <= b[2] and b[1] <= y <= b[3])
                        r["dist"].append(math.hypot(x - it["target"][0], y - it["target"][1]))
                        w, h = it["size"]                 # distance to the box edge in px at a 1280 px long side
                        px = 1280 / max(w, h) / 1000
                        r["near20"] += int(math.hypot(max(b[0] - x, 0, x - b[2]) * w * px, max(b[1] - y, 0, y - b[3]) * h * px) <= 20)
        for h in self.heads.values():
            h.train()
        out = {}
        for n, r in res.items():
            d = sorted(r["dist"])
            out[n] = {"hit": r["hits"] / len(samples), "median_dist": d[len(d) // 2], "click_acc": r["click_ok"] / max(1, r["click_n"]),
                      "within20": r["near20"] / len(samples)}
        return out

    def save(self, path):
        torch.save({"specs": self.specs, "steps": self.steps, "heads": {n: h.state_dict() for n, h in self.heads.items()}}, path)
        return path

    @torch.no_grad()
    def time_heads(self, sample, repeats=20):
        """Milliseconds per answer of each head alone, given the model's states for one screenshot and
        request (the trunk's own time for the request tokens is not included), and of the whole forward."""
        inputs, n_prompt = self.lab._inputs(self.model, sample)
        torch.cuda.synchronize(); t = time.time()
        states, img, centres, cell, grid = self.forward(inputs)
        torch.cuda.synchronize(); full = 1000 * (time.time() - t)
        ranges = [(int(img[-1]) + 1, n_prompt)]
        out = {"whole forward, image included": full}
        for spec in self.specs:
            f = self.features(spec, states, img, centres, cell, grid, ranges)
            self.heads[spec[0]](*f)
            torch.cuda.synchronize(); t = time.time()
            for _ in range(repeats):
                self.heads[spec[0]](*f)
            torch.cuda.synchronize(); out[spec[0]] = 1000 * (time.time() - t) / repeats
        return out

    def load(self, path):
        """Continue from a file written by save(): every head of this bench whose name is in the file
        gets its saved weights, the others keep their fresh start. The step count continues from the
        file; optimiser state is not saved, so the warm-up starts again here. Returns the names loaded."""
        ck = torch.load(path, map_location=self.model.device)
        rename = getattr(self, "load_as", None) or {}                # {head here: head in the file}, for a head that starts from another's weights
        got = [n for n in self.heads if rename.get(n, n) in ck["heads"]]
        for n in got:
            self.heads[n].load_state_dict(ck["heads"][rename.get(n, n)], strict=n not in rename)
        self.steps = self.resumed_at = int(ck["steps"])
        return got


class JointHeadTuner:
    """Train a pointing head together with the model's own multipliers.

    A frozen model was never asked to make its state easy to read a location from. Here the
    multipliers of the chosen layers (codes untouched, still ternary) learn with the head, from two
    signals on every training step:
        head    the head's point should land in the box (and its click output be right)
        digits  the written answer "[x, y]" should still land in the box (the lab's usual loss),
                so the model does not trade its ordinary pointing for the head's
    One full forward pass gives both: the head reads the state after `layer`, the digits come from
    the output head as always.
    """

    def __init__(self, lab, layers, kind="pointer", layer=20, key_layers=None, head=None):
        from .ternary import TernaryLinear
        self.lab, self.model = lab, lab.B
        self.layer, self.kind = layer, kind
        self.key_layers = tuple(key_layers) if key_layers else (layer,)
        dev = self.model.device
        d = self.model.config.text_config.hidden_size
        self.head = head or (CrossHead(self.key_layers, d=d) if kind == "cross" else PointHead(d=d)).to(dev).float()
        blocks = list(self.model.model.language_model.layers)
        self.mods = [m for i in sorted(layers) for m in blocks[i].modules() if isinstance(m, TernaryLinear)]
        self.spec = ("joint", kind, layer, self.key_layers)
        self.bench = HeadBench.__new__(HeadBench)                      # reuse its feature and scoring code
        self.bench.lab, self.bench.model = lab, self.model
        self.bench.specs, self.bench.heads = [self.spec], {"joint": self.head}
        self.bench.layers = sorted({layer, *self.key_layers})
        self.steps, self.hist = 0, []

    def _forward(self, inputs):
        out = self.model.model(**inputs, use_cache=False, output_hidden_states=True)
        hs = out.hidden_states
        img = (inputs["mm_token_type_ids"][0] == 1).nonzero().squeeze(-1)
        _, gh, gw = inputs["image_grid_thw"][0].tolist()
        rows, cols = gh // 2, gw // 2
        dev = img.device
        ys, xs = torch.meshgrid(torch.arange(rows, device=dev), torch.arange(cols, device=dev), indexing="ij")
        centres = torch.stack(((xs.flatten() + 0.5) / cols * 1000, (ys.flatten() + 0.5) / rows * 1000), dim=-1).float()
        cell = torch.tensor([1000 / cols, 1000 / rows], device=dev)
        states = {l: hs[l][0].float() for l in self.bench.layers}
        last = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]
        return states, img, centres, cell, (rows, cols), last

    def train(self, packs, steps, lr_scales=2e-4, lr_head=1e-3, digits=1.0, negatives=0.2, warmup=50, total=None,
              seed=0, report_every=100):
        from .tune import answer_targets, point_loss
        rng = random.Random(seed + self.steps)
        total = total or steps
        if not getattr(self, "open", False):
            gains = [p for m in self.mods for p in m.start_training(codes=False, scales=True, keep_hard=True, compute_dtype=torch.bfloat16)]
            self.gains = gains
            self.opt = torch.optim.Adam([{"params": gains, "lr": lr_scales}, {"params": list(self.head.parameters()), "lr": lr_head}],
                                        betas=(0.9, 0.99), eps=1e-6)
            self.base, self.open = [lr_scales, lr_head], True
        order = list(range(len(packs)))
        rng.shuffle(order)
        hist, t0 = [], time.time()
        for k in range(steps):
            items = list(packs[order[k % len(packs)]])
            present = [1.0] * len(items)
            if rng.random() < negatives:
                other = packs[rng.randrange(len(packs))][0]
                if other["path"] != items[0]["path"] and other["group"] != items[0]["group"]:
                    items.append(dict(items[0], id=items[0]["id"] + "-neg", instruction=other["instruction"],
                                      target=(-1, -1), box1000=[0.0, 0.0, 0.0, 0.0]))
                    present.append(0.0)
            factor = min(1.0, (self.steps + 1) / warmup) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(self.steps, total) / total)))
            for g, lr in zip(self.opt.param_groups, self.base):
                g["lr"] = lr * factor
            self.opt.zero_grad(set_to_none=True)
            try:
                inputs, spans = self.lab._inputs_multi(self.model, items)
                states, img, centres, cell, grid, last = self._forward(inputs)
                ranges = self.bench._ranges(img, spans)
                boxes = torch.tensor([it["box1000"] for it in items], device=centres.device, dtype=torch.float32)
                pres = torch.tensor(present, device=centres.device)
                lh = head_loss(self.head, self.bench.features(self.spec, states, img, centres, cell, grid, ranges), boxes, pres)
                ld = torch.zeros((), device=centres.device)
                if digits > 0:
                    real = [(it, sp) for it, sp, pr in zip(items, spans, present) if pr > 0.5]
                    idx = torch.cat([torch.arange(a - 1, a - 1 + n, device=centres.device) for _, (a, n) in real])
                    logits = self.model.lm_head(last[0, idx])
                    ids, off, per = inputs["input_ids"][0], 0, []
                    for it, (a, n) in real:
                        per.append(point_loss(logits[off:off + n], answer_targets(it, ids[a:a + n])))
                        off += n
                    ld = torch.stack(per).mean()
                (lh + digits * ld).backward()
            except torch.OutOfMemoryError:
                raise
            except Exception as e:
                print(f"  skipped a pack ({items[0]['id']}): {type(e).__name__}: {str(e)[:100]}", flush=True)
                for m in self.mods:
                    m.after_step()
                continue
            torch.nn.utils.clip_grad_norm_(self.gains, 1.0)
            torch.nn.utils.clip_grad_norm_(self.head.parameters(), 1.0)
            self.opt.step()
            for m in self.mods:
                m.after_step()
            self.steps += 1
            self.lab.forward_passes += 1
            hist.append((lh.item(), ld.item()))
            if report_every and (k + 1) % report_every == 0:
                r = hist[-report_every:]
                print(f"  step {self.steps}  head {sum(x[0] for x in r) / len(r):.2f}  digits {sum(x[1] for x in r) / len(r):.2f}"
                      f"  [{(time.time() - t0) / (k + 1):.2f}s/step]", flush=True)
        self.hist += hist
        return {"head": sum(x[0] for x in hist[-200:]) / max(1, len(hist[-200:])), "digits": sum(x[1] for x in hist[-200:]) / max(1, len(hist[-200:]))}

    def score(self, samples):
        """Hit rate of the head, each sample asked by itself (works while training is open)."""
        return self.bench.score(samples)["joint"]

    def close(self):
        """Write the trained multipliers back; the model is an ordinary Bonsai again."""
        for m in self.mods:
            m.bake()
        self.open = False
        torch.cuda.empty_cache()
        self.lab.stack.append(f"joint-head:{self.kind}:L{self.layer}:{self.steps}")
