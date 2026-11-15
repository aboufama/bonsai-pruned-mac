# Experiment 022, trial T1: vision transplant.
#
# Bonsai's vision tower and merger are full precision and have UI-Venus-2-9B's architecture.
#   a) reverse sanity check: the parent's tower (and merger) in Bonsai; should change nothing if
#      Bonsai ships the parent's vision weights
#   b) UI-Venus's vision tower in Bonsai, the ternary language model untouched
#   c) UI-Venus's tower and merger
#   d) the better of b/c by select, then 400 gentle updates of layers 0..31 (lane 3's recipe)
#   e) control: the same 400 updates from the baseline with Bonsai's own vision weights, so that
#      (d) can be read against it
# The baseline is restored and re-checked after every setting.
exec(open(f"{lab.root}/experiments/022_extreme_common.py").read())
assert x22_base_score is not None, "run 022_extreme_t0_baseline_bias.py first"
ONLY = globals().get("ONLY22", None)                 # e.g. {"a", "b"} to run part of the trial

vis_names = [n for n, _ in lab.B.named_parameters() if n.startswith("model.visual.")]
is_merger = lambda n: ".merger." in n


@torch.no_grad()
def compare(source):
    """Per part of the vision side: relative distance of Bonsai's tensors from the source's."""
    src, params, parts = Tensors(lab.paths[source]), dict(lab.B.named_parameters()), {}
    for n in vis_names:
        a, b = params[n].data.float(), src.get(n).to(params[n].device).float()
        part = "merger" if is_merger(n) else ("blocks" if ".blocks." in n else "embed")
        p = parts.setdefault(part, [0.0, 0.0, 0, 0, 0.0])
        p[0] += (a - b).pow(2).sum().item(); p[1] += b.pow(2).sum().item()
        p[2] += int(torch.equal(params[n].data, src.get(n).to(params[n].device, params[n].dtype))); p[3] += 1
        p[4] = max(p[4], (a - b).abs().max().item())
    return {k: {"rel_dist": (v[0] / max(v[1], 1e-30)) ** 0.5, "identical_tensors": v[2], "tensors": v[3], "max_abs": v[4]} for k, v in parts.items()}


@torch.no_grad()
def transplant(source, merger):
    src, params, n_bytes = Tensors(lab.paths[source]), dict(lab.B.named_parameters()), 0
    for n in vis_names:
        if is_merger(n) and not merger:
            continue
        p = params[n]
        t = src.get(n)
        assert t.shape == p.shape, (n, tuple(t.shape), tuple(p.shape))
        p.data.copy_(t.to(p.device, p.dtype))
        n_bytes += p.numel() * 2
    lab.stack.append(f"vision:{source}:{'tower+merger' if merger else 'tower'}")
    return n_bytes / 1e6


if "t1_cmp" not in globals():
    t1_cmp = {"Bonsai vs parent": compare("P"), "Bonsai vs UI-Venus": compare("V")}
    for k, v in t1_cmp.items():
        print(k + ": " + "   ".join("%s rel. distance %.4g, max abs %.3g, %d/%d tensors bit-identical" % (
            part, r["rel_dist"], r["max_abs"], r["identical_tensors"], r["tensors"]) for part, r in v.items()), flush=True)
    x22_notes.append({"T1_compare": t1_cmp}); x22_save()

res = globals().get("t1_res", {})
t1_res = res
for key, source, merger in (("a", "P", True), ("b", "V", False), ("c", "V", True)):
    if key in res or (ONLY and key not in ONLY):
        continue
    t = time.time()
    mb = transplant(source, merger)
    label = {"a": "parent's tower + merger (sanity)", "b": "UI-Venus tower", "c": "UI-Venus tower + merger"}[key]
    res[key] = x22_measure("T1", label, t)
    res[key]["mb"] = mb
    x22_back_to_baseline("after T1 " + key)

if "b" in res and "c" in res and "d" not in res and (not ONLY or "d" in ONLY):
    pick = "c" if res["c"]["select"] >= res["b"]["select"] else "b"
    t = time.time()
    transplant("V", pick == "c")
    x22_tune(400, 100, tag="T1d")
    res["d"] = x22_measure("T1", "%s, then 400 gentle updates L0-31" % ("UI-Venus tower + merger" if pick == "c" else "UI-Venus tower"), t)
    if res["d"]["select"] > x22_base_score[0]:
        t1_ckpt = {"snap": x22_snapshot(), "row": res["d"], "pick": pick}        # kept in memory for a later export
    x22_back_to_baseline("after T1 d")

if "e" not in res and (not ONLY or "e" in ONLY):
    t = time.time()
    x22_tune(400, 100, tag="T1e")
    res["e"] = x22_measure("T1", "control: 400 gentle updates L0-31, own vision", t)
    t1_ctrl = {"snap": x22_snapshot(), "row": res["e"]}
    x22_back_to_baseline("after T1 e")
print("T1 done", flush=True)
