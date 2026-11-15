# STATUS: written but never run. T2 was dropped on 15 Nov to save tokens; treat this file as untested.
# Experiment 022, trial T2: the teacher's change written into the multipliers. No data.
#
# D = W(UI-Venus) - W(parent) for every language-model matrix Bonsai stores in ternary form.
# A Bonsai matrix is  W = fwht(codes * multipliers) * signs  (ternary.py: folded_weight; fwht is
# the normalised Walsh-Hadamard transform over blocks of the input dimension, its own inverse, and
# signs is a +1/-1 vector over the inputs). So in the basis the file stores,
#     D_rot = fwht(D * signs),
# and since the transform is orthonormal, the multiplier change of a group (one output row, 128
# consecutive rotated inputs) that best reproduces D in the least-squares sense with the codes
# fixed is
#     d_mult = <codes, D_rot> / <codes, codes>      over that group (0 where the group is all zero).
# The share of D's energy this captures is  sum(<codes, D_rot>^2 / <codes, codes>) / |D|^2.
#
# alpha * d_mult is added for alpha in ALPHAS22, on top of the original Bonsai multipliers and,
# separately, on top of v3-gentle. Multipliers are rounded to float16, as the pack stores them.
# Any setting that is not worse on select than its starting point gets 400 gentle updates.
exec(open(f"{lab.root}/experiments/022_extreme_common.py").read())
assert x22_base_score is not None, "run 022_extreme_t0_baseline_bias.py first"
ALPHAS = globals().get("ALPHAS22", (0.25, 0.5, 1.0))
BASES = globals().get("BASES22", ("v3-gentle", "original"))


@torch.no_grad()
def delta_multipliers():
    """{matrix name: d_mult} for the codes now in the model, and the per-layer bookkeeping."""
    P, V = Tensors(lab.paths["P"]), Tensors(lab.paths["V"])
    out, layers, skipped = {}, {}, []
    for name, m in lab.tern.items():
        key = name + ".weight"
        if key not in P.map or key not in V.map:
            skipped.append(name)
            continue
        dev = m.codes.device
        wp = P.get(key).to(dev).float()
        d = V.get(key).to(dev).float() - wp
        d_rot = fwht(d * m.signs, m.block)
        c = m.codes.float()
        rows = c.shape[0]
        num = (c * d_rot).view(rows, -1, GROUP).sum(-1)
        den = (c * c).view(rows, -1, GROUP).sum(-1)
        dm = torch.where(den > 0, num / den.clamp_min(1.0), torch.zeros_like(num))
        out[name] = dm
        layer = name.split("layers.")[1].split(".")[0] if "layers." in name else name
        s = layers.setdefault(layer, {"d": 0.0, "captured": 0.0, "parent": 0.0, "rel_change": [], "matrices": 0})
        s["d"] += d.pow(2).sum().item()
        s["captured"] += (num.pow(2) / den.clamp_min(1.0)).sum().item()
        s["parent"] += wp.pow(2).sum().item()
        s["rel_change"].append((dm.abs().mean() / m.scales.data.abs().mean()).item())
        s["matrices"] += 1
        del wp, d, d_rot, c, num, den
    torch.cuda.empty_cache()
    table = {k: {"captured_share": v["captured"] / max(v["d"], 1e-30), "d_over_parent": (v["d"] / max(v["parent"], 1e-30)) ** 0.5,
                 "mean_rel_multiplier_change": sum(v["rel_change"]) / len(v["rel_change"]), "matrices": v["matrices"]} for k, v in layers.items()}
    total = {"captured_share": sum(v["captured"] for v in layers.values()) / sum(v["d"] for v in layers.values()),
             "d_over_parent": (sum(v["d"] for v in layers.values()) / sum(v["parent"] for v in layers.values())) ** 0.5}
    return out, table, total, skipped


@torch.no_grad()
def add_delta(start, dm, alpha):
    """Multipliers = start + alpha * d_mult, rounded to float16. Returns the share of multipliers
    whose stored value actually changed."""
    changed = total = 0
    for name, m in lab.tern.items():
        if name not in dm:
            continue
        old = start["scales"][name]
        new = (old + alpha * dm[name]).half().float()
        changed += int((new != old.half().float()).sum()); total += new.numel()
        m.scales.data.copy_(new)
        m.invalidate()
    return changed / total


@torch.no_grad()
def add_small_delta(alpha):
    """Extra: the language model's small full-precision parts (norm weights, the linear-attention
    layers' convolution and gates) are not ternary, so the teacher's change can be added to them
    as it is: p += alpha * (UI-Venus - parent), kept in bfloat16. Returns bookkeeping."""
    P, V = Tensors(lab.paths["P"]), Tensors(lab.paths["V"])
    n = changed = total = 0
    num = den = 0.0
    for name, p in lab.B.named_parameters():
        if (not name.startswith("model.language_model.") or name.endswith(X22_SKIP) or "embed_tokens" in name
                or name not in P.map or name not in V.map):
            continue
        d = V.get(name).to(p.device).float() - P.get(name).to(p.device).float()
        if d.shape != p.shape:
            continue
        new = (p.data.float() + alpha * d).to(p.dtype)
        changed += int((new != p.data).sum()); total += p.numel(); n += 1
        num += d.pow(2).sum().item(); den += p.data.float().pow(2).sum().item()
        p.data.copy_(new)
    return {"tensors": n, "elements_changed_share": changed / max(total, 1), "d_over_value": (num / max(den, 1e-30)) ** 0.5}


t2_res = globals().get("t2_res", {})
t2_keep = globals().get("t2_keep", {})
for base in BASES:
    start = x22_base if base == "v3-gentle" else x22_orig
    x22_restore(start)
    lab.stack[:] = [f"patch:{os.path.basename(X22_PATCH)}"] if base == "v3-gentle" else []
    if ("dm", base) not in t2_keep:
        t = time.time()
        dm, table, total, skipped = delta_multipliers()
        t2_keep[("dm", base)] = dm
        print("T2 projection with the codes of %s: %.2f%% of D's energy captured overall; |D|/|W parent| %.4f; no teacher tensor for %s  [%.0f s]" % (
            base, 100 * total["captured_share"], total["d_over_parent"], skipped or "none", time.time() - t), flush=True)
        print("  per layer, % of D captured: " + " ".join("%s:%.2f" % (k, 100 * v["captured_share"]) for k, v in table.items()), flush=True)
        print("  per layer, |D|/|W parent| x1000: " + " ".join("%s:%.1f" % (k, 1000 * v["d_over_parent"]) for k, v in table.items()), flush=True)
        print("  per layer, mean |d_mult|/mean multiplier x1000: " + " ".join("%s:%.2f" % (k, 1000 * v["mean_rel_multiplier_change"]) for k, v in table.items()), flush=True)
        x22_notes.append({"T2_projection": {"base": base, "total": total, "per_layer": table, "skipped": skipped}}); x22_save()
    dm = t2_keep[("dm", base)]
    if base == "original" and ("start", base) not in t2_res:
        t2_res[("start", base)] = x22_measure("T2", "original Bonsai (start point)", time.time())
    start_select = x22_base_score[0] if base == "v3-gentle" else t2_res[("start", base)]["select"]
    for alpha in ALPHAS:
        if (alpha, base) in t2_res:
            continue
        t = time.time()
        x22_restore(start)
        share = add_delta(start, dm, alpha)
        lab.stack.append(f"T2:delta:{alpha:g}")
        r = x22_measure("T2", "%s + %g x teacher change" % (base, alpha), t)
        r["multipliers_changed_share"], r["start_select"] = share, start_select
        print("     stored multipliers changed: %.1f%%   select against the start %+.4f" % (100 * share, r["select"] - start_select), flush=True)
        t2_res[(alpha, base)] = r
        x22_save()
        lab.stack.pop()
    if base == "v3-gentle":
        # extras beyond the planned settings: larger alphas if alpha 1 did no harm (the projection keeps only a
        # small share of D, so a larger step along it is the obvious next thing), and the small
        # full-precision parts moved by the teacher's change exactly
        if t2_res[(1.0, base)]["select"] >= start_select - 0.01:
            for alpha in (2.0, 4.0, 8.0):
                if (alpha, base) in t2_res:
                    continue
                t = time.time()
                x22_restore(start)
                share = add_delta(start, dm, alpha)
                lab.stack.append(f"T2:delta:{alpha:g}")
                r = x22_measure("T2", "%s + %g x teacher change (extra)" % (base, alpha), t)
                r["multipliers_changed_share"], r["start_select"] = share, start_select
                t2_res[(alpha, base)] = r
                lab.stack.pop()
                if r["select"] < start_select - 0.02:
                    break
        if ("small", base) not in t2_res:
            t = time.time()
            x22_restore(start)
            info = add_small_delta(1.0)
            lab.stack.append("T2:small_parts:1")
            r = x22_measure("T2", "%s + teacher change in the small full-precision parts (extra)" % base, t)
            r["small"] = info
            print("     small parts: %d tensors, |D|/|value| %.4f, %.1f%% of elements changed in bfloat16" % (
                info["tensors"], info["d_over_value"], 100 * info["elements_changed_share"]), flush=True)
            t2_res[("small", base)] = r
            lab.stack.pop()
            x22_save()
    # the best setting on select, if it is not worse than where it started: 400 gentle updates
    best = max([a for a in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0) if (a, base) in t2_res], key=lambda a: t2_res[(a, base)]["select"])
    if t2_res[(best, base)]["select"] >= start_select and ("tune", base) not in t2_res:
        t = time.time()
        x22_restore(start)
        add_delta(start, dm, best)
        lab.stack.append(f"T2:delta:{best:g}")
        x22_tune(400, 100, tag=f"T2_{base}_{best:g}")
        t2_res[("tune", base)] = x22_measure("T2", "%s + %g x teacher change, then 400 gentle updates L0-31" % (base, best), t)
        if base == "v3-gentle" and t2_res[("tune", base)]["select"] > x22_base_score[0]:
            t2_ckpt = {"snap": x22_snapshot(), "row": t2_res[("tune", base)]}
    else:
        print("T2 on %s: best alpha %g gives select %.4f against a start of %.4f; %s" % (
            base, best, t2_res[(best, base)]["select"], start_select,
            "already tuned" if ("tune", base) in t2_res else "worse than the start, no tune"), flush=True)
    x22_back_to_baseline(f"after T2 on {base}")
print("T2 done", flush=True)
