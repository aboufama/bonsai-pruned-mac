# Experiment 024, design G (15 Nov 01:45): code flips chosen by evidence and checked.
# The codes sweep (010 with the codes open) showed that per-weight normalised updates of the latents turn
# the noise of single screenshots into flips, and each flip is a jump of a whole multiplier: 0.1% of the
# codes flipped cost 0.19 on select. Here the latents are never updated. One round:
#   1. accumulate dL/dW (the quantity lean_update receives) over ACC packs, summed, nothing applied;
#   2. for every code of the block the candidate is one step towards lower loss (down if the gradient is
#      positive, up if negative, where the code is not already at -1 / +1); predicted change of the loss
#      = -|gradient| x multiplier; take the SHARE of codes with the most negative prediction;
#   3. apply them and measure the training loss on HELD packs before and after; keep the flips only if
#      the loss fell, otherwise undo them and halve the share.
# Multipliers and small parts do not move. Scored every EVERY rounds (select and report at 1280 and 896,
# teacher-forced), a checkpoint at every score; at the end generated answers and the canary.
# Settings: LO24, HI24, ROUNDS24, EVERY24, ACC24, HELD24, SHARE24, TAG24, SIZES24.
import json
import random
import time

import torch
import weightlab.hot as hot, importlib
importlib.reload(hot); hot.reload(globals())
from weightlab.e2e import BlockTrainer, point_loss, answer_targets
from weightlab.ternary import GROUP

LO, HI = globals().get("LO24", 4), globals().get("HI24", 19)
ROUNDS, EVERY = globals().get("ROUNDS24", 20), globals().get("EVERY24", 5)
ACC, HELD = globals().get("ACC24", 256), globals().get("HELD24", 128)
SHARE = globals().get("SHARE24", 5e-5)
TAG = globals().get("TAG24", "flips")
SIZES = globals().get("SIZES24", (1280, 896))

rs = random.Random(24)
pool = [[dict(it, max_side=side) for it in pack] for pack in packs for side in [rs.choice(SIZES)]]
rs.shuffle(pool)
held, pool = pool[:HELD], pool[HELD:]
sets = {side: (lab.data("ssv2", mod=(8, 1), max_side=side), lab.data("ssv2", mod=(8, 5), max_side=side)) for side in (1280, 896)}

E = BlockTrainer(lab, LO, HI, teacher=None)
ck = f"{lab.dir}/ckpt"
start_path = E.D.save(range(LO, HI + 1), f"{ck}/flips024_{TAG}_start.safetensors")
E.open(lr_codes=0.0, codes=True, scales=False, fp=False)
total = sum(m.codes.numel() for m in E.mods)
for m in E.mods:                                     # the layer hands its dL/dW here instead of updating latents
    m._gacc = None
    def _acc(G, m=m):
        m._gacc = G.float() if m._gacc is None else m._gacc.add_(G)
    m.lean_update = _acc


@torch.no_grad()
def held_loss():
    tot, n = 0.0, 0
    for pack in held:
        try:
            _, answers = E.forward(pack, use_hints=False)
        except Exception:
            continue
        for one, (lg, tgt) in zip(pack, answers):
            tot += point_loss(lg, answer_targets(one, tgt)).item(); n += 1
    return tot / max(1, n)


def score_line(label):
    t, row = time.time(), {}
    for side, (a, b) in sets.items():
        row[side] = {"select": E.score(a), "report": E.score(b)}
    print("%-10s " % label + "   ".join("%d px select %.3f report %.3f" % (s, r["select"]["p_hit"], r["report"]["p_hit"]) for s, r in row.items())
          + "   codes flipped %.4f%%   [%.0f s]" % (100 * E.flips(), time.time() - t), flush=True)
    return row


out = {"tag": TAG, "layers": [LO, HI], "share": SHARE, "acc": ACC, "held": HELD, "codes": total, "rounds": [], "scores": {}}
print("design G: %d codes in layers %d..%d; %d packs per round, %d held out; starting share %.4f%% (%d codes)" % (
    total, LO, HI, ACC, HELD, 100 * SHARE, int(total * SHARE)), flush=True)
out["scores"][0] = score_line("before")
share, kept_total, pos = SHARE, 0, 0
for rnd in range(1, ROUNDS + 1):
    t0 = time.time()
    for m in E.mods:
        m._gacc = None
    batch = pool[pos:pos + ACC]; pos += ACC
    E.train(batch, len(batch), task=1.0, hint=0.0, report_every=0)                               # gradients only: nothing is applied
    k = max(1, int(total * share))
    cands = []                                                               # (prediction, module index, flat index)
    for i, m in enumerate(E.mods):
        g = m._gacc
        if g is None:
            continue
        codes = m.hard_codes()
        allowed = ((g > 0) & (codes > -1)) | ((g < 0) & (codes < 1))
        pred = -(g.abs() * m.live_scales().float().repeat_interleave(GROUP, dim=1)) * allowed
        v, idx = torch.topk(-pred.flatten(), min(k, pred.numel()))
        cands.append((-v, torch.full_like(idx, i), idx))
        del pred, allowed
    v = torch.cat([c[0] for c in cands]); mi = torch.cat([c[1] for c in cands]); fi = torch.cat([c[2] for c in cands])
    top = torch.topk(-v, k).indices
    before = held_loss()
    undo = []
    for i, m in enumerate(E.mods):
        sel = fi[top][mi[top] == i]
        if sel.numel() and m._gacc is not None:
            lat = m.latent.data.view(-1)
            old = lat[sel].clone()
            lat[sel] = old - torch.sign(m._gacc.view(-1)[sel])
            m._hard = None
            undo.append((m, sel, old))
    after = held_loss()
    keep = after < before
    if not keep:
        for m, sel, old in undo:
            m.latent.data.view(-1)[sel] = old
            m._hard = None
    kept_total += k if keep else 0
    out["rounds"].append({"round": rnd, "share": share, "flips": k, "held_before": before, "held_after": after, "kept": bool(keep),
                          "predicted": float(v[top].sum()) / len(batch)})
    print("round %2d: %6d flips tried (share %.4f%%)   held-out loss %.4f -> %.4f   %s   kept so far %d   [%.0f s]" % (
        rnd, k, 100 * share, before, after, "KEPT" if keep else "undone, share halved", kept_total, time.time() - t0), flush=True)
    if not keep:
        share /= 2
    for m in E.mods:
        m._gacc = None
    if rnd % EVERY == 0 or rnd == ROUNDS:
        out["scores"][rnd] = score_line("round %d" % rnd)
        E.checkpoint(f"{ck}/flips024_{TAG}_r{rnd}.safetensors")
        json.dump(out, open(f"{lab.dir}/exp024_{TAG}.json", "w"), indent=1)
for m in E.mods:
    m.__dict__.pop("lean_update", None); m._gacc = None
closed = E.close()
print("closed: %.4f%% of the block's codes differ from the start (%d codes)" % (100 * closed["codes_changed_share"], closed["codes_changed"]))
a, b = fS.evaluate(LO), fR.evaluate(LO)
fS.discard(); fR.discard()
print("final, block closed: select %.3f   report %.3f" % (a["p_hit"], b["p_hit"]), flush=True)
out["generated"] = {}
for side, (_, bset) in sets.items():
    g = lab.score(lab.B, bset, tag=f"024:{TAG}:generated:{side}")
    out["generated"][side] = g["acc"]
    print("generated answers, report set at %4d px: %5.1f%% of %d on target" % (side, 100 * g["acc"], len(bset)), flush=True)
out["canary"] = lab.canary(lab.B, tag=f"024:{TAG}")
print("canary:", out["canary"]["all"])
E.D.save(range(LO, HI + 1), f"{ck}/flips024_{TAG}_final.safetensors")
json.dump(out, open(f"{lab.dir}/exp024_{TAG}.json", "w"), indent=1)
