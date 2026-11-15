# Benchmark check: where does the 0.01 go between the training state (select 0.810 / report
# 0.797 on the Spark) and the exported patch v2 (0.800 / 0.790 on every pod)?
#
# Runs inside the lab session and changes the weights IN PLACE, then puts back exactly what it
# found (checked by re-scoring). States scored on the two 159-screen sets (teacher-forced p_hit):
#   S0  the session as found
#   S1  the shipped artifact: original pack + patch v2            -> 0.800 means the export loses it,
#                                                                    0.810 means hardware/library arithmetic
#   S1b S1 with the other patch-embedding path (Conv3d <-> one matrix product, core._fast_patch_embed)
#   S2  the training state rebuilt from its files: original pack + patch v1 (multipliers of layers
#       20..31 and the head) + the lab's float32 multipliers where they were saved + checkpoint
#       qat010 best (layers 4..19: codes, float32 multipliers, bfloat16 small parts)
#   S3  S2 with every multiplier rounded to float16 (what a patch stores)
#   S4  S2 with only the small tensors that the patch kept (make_patch drops those that moved by
#       less than 4e-3 of their largest value)
# Nothing here trains. Output: lab/bench_patch_check.json and the lines printed below.
import json
import os
import time

import numpy as np
import torch
from safetensors import safe_open

from weightlab import core, state, ternary
_pack = ternary.pack

PC_PATCH2 = f"{lab.root}/export/patches/bonsai2-9b-point-v2.patch.safetensors"
PC_PATCH1 = f"{lab.root}/export/patches/bonsai2-9b-point-v1.patch.safetensors"
PC_CKPT = f"{lab.root}/lab/ckpt/qat010_codes_lr0.002_s3000_best.safetensors"
PC_TUNE = f"{lab.root}/lab/ckpt/tune_all_L4-31_head_lr3e-4_u400.pt"
pc_model = lab.B
pc_sel, pc_rep = lab.data("ssv2", mod=(8, 1)), lab.data("ssv2", mod=(8, 5))
pc_out = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "stack_found": list(lab.stack), "states": {}}
pc_params = dict(pc_model.named_parameters())
assert all(type(m).__name__ == "TernaryLinear" for m in lab.tern.values()), "a trainer has layers open; not touching the weights"


def pc_score(name, note=""):
    t = time.time()
    with torch.inference_mode():
        s, r = lab.digits(pc_model, pc_sel, tag=f"patch_check:{name}:select"), lab.digits(pc_model, pc_rep, tag=f"patch_check:{name}:report")
    pc_out["states"][name] = {"select": s["p_hit"], "report": r["p_hit"], "select_tens": s.get("p_ok_tens"), "note": note}
    print("%-4s select %.4f  report %.4f   %s   [%.0f s]" % (name, s["p_hit"], r["p_hit"], note, time.time() - t), flush=True)
    json.dump(pc_out, open(f"{lab.dir}/bench_patch_check.json", "w"), indent=1)
    return s["p_hit"], r["p_hit"]


# ---------------------------------------------------------------- the state as found, and the original
pc_cfg = json.load(open(f"{lab.paths['pack']}/config.json"))
pc_packfile = f"{lab.paths['pack']}/model.safetensors"
pc_header, pc_start = _pack.read_header(pc_packfile)
pc_packpath = {ternary.hf_module_name(rec["path"]): rec["path"] for rec in pc_cfg["modules"]}
pc_dense = core.Tensors(lab.paths["B"])
pc_small = [k for k, p in pc_params.items() if (k.startswith("model.language_model.") or k.startswith("lm_head"))
            and not k.endswith(".scales") and not k.endswith(".gate") and k in pc_dense.map and p.numel() <= 20_000_000]

pc_s0 = pc_score("S0", "the session as found")

t0 = time.time()
pc_snap = {"scales": {}, "codes": {}, "small": {}}
pc_codes_dirty = set()
with torch.no_grad():
    for name, m in lab.tern.items():
        codes, scales, _ = ternary.read_packed(pc_packfile, pc_header, pc_start, "language_model." + pc_packpath[name], m.codes.device)
        if not torch.equal(m.scales.data, scales.to(m.scales.dtype)):
            pc_snap["scales"][name] = m.scales.data.detach().cpu().clone()
        if not torch.equal(m.codes, codes):
            pc_snap["codes"][name] = m.codes.detach().cpu().clone()
            pc_codes_dirty.add(name)
        del codes, scales
    for k in pc_small:
        o = pc_dense.get(k).to(pc_params[k].device, pc_params[k].dtype)
        if not torch.equal(pc_params[k].data, o):
            pc_snap["small"][k] = pc_params[k].data.detach().cpu().clone()
        del o
pc_out["found_differs_from_original"] = {"multipliers": len(pc_snap["scales"]), "codes": len(pc_snap["codes"]), "small": len(pc_snap["small"])}
print("as found, differing from the original pack: multipliers of %d matrices, codes of %d, %d small tensors   [%.0f s]" % (
    len(pc_snap["scales"]), len(pc_snap["codes"]), len(pc_snap["small"]), time.time() - t0), flush=True)


@torch.no_grad()
def pc_to_original():
    """Every ternary matrix's multipliers, the codes of every matrix this cell or the session
    changed, and every small tensor of the language model: back to PrismML's values."""
    for name, m in lab.tern.items():
        need_codes = name in pc_codes_dirty
        if need_codes:
            codes, scales, _ = ternary.read_packed(pc_packfile, pc_header, pc_start, "language_model." + pc_packpath[name], m.codes.device)
            m.codes.copy_(codes)
        else:
            scales = torch.from_numpy(np.array(_pack.read_tensor(pc_packfile, pc_header, pc_start, "language_model." + pc_packpath[name] + ".scales"))).to(m.scales.device).float()
        if need_codes or not torch.equal(m.scales.data, scales):
            m.scales.data.copy_(scales)
            m.invalidate()
    for k in pc_small:
        pc_params[k].data.copy_(pc_dense.get(k).to(pc_params[k].device, pc_params[k].dtype))
    torch.cuda.empty_cache()


@torch.no_grad()
def pc_restore():
    pc_to_original()
    for name, v in pc_snap["scales"].items():
        lab.tern[name].scales.data.copy_(v.to(lab.tern[name].scales.device)); lab.tern[name].invalidate()
    for name, v in pc_snap["codes"].items():
        lab.tern[name].codes.copy_(v.to(lab.tern[name].codes.device)); lab.tern[name].invalidate()
    for k, v in pc_snap["small"].items():
        pc_params[k].data.copy_(v.to(pc_params[k].device))
    torch.cuda.empty_cache()


def pc_patch_codes(path):
    """Names of the matrices whose codes a patch replaces (so they can be put back)."""
    with safe_open(path, "pt") as f:
        ks = set(f.keys())
    names = {ternary.hf_module_name(k[len("language_model."):-len(".weight")]) for k in ks if k.endswith(".weight")}
    return {n for n in names if n in lab.tern}


@torch.no_grad()
def pc_load_ckpt(path, scales16=False, only_small=None):
    """A BlockTrainer/BlockDistiller checkpoint into the lab. only_small: a set of tensor names;
    other small tensors of the checkpoint are left as they are."""
    n = {"codes": 0, "multipliers": 0, "small": 0, "small_skipped": 0}
    with safe_open(path, "pt") as f:
        for k in f.keys():
            if k.endswith(".codes"):
                m = lab.tern[k[:-6]]
                c = f.get_tensor(k).to(m.codes.device)
                if not torch.equal(m.codes, c):
                    pc_codes_dirty.add(k[:-6]); m.codes.copy_(c); n["codes"] += 1
                s = f.get_tensor(k[:-6] + ".scales").float()
                if scales16:
                    s = s.half().float()
                m.scales.data.copy_(s.to(m.scales.device)); m.invalidate(); n["multipliers"] += 1
            elif not k.endswith(".scales"):
                if only_small is not None and k not in only_small:
                    n["small_skipped"] += 1
                    continue
                p = pc_params[k]
                p.data.copy_(f.get_tensor(k).float().to(p.device, p.dtype)); n["small"] += 1
    torch.cuda.empty_cache()
    return n


try:
    # ------------------------------------------------------------ S1: the shipped artifact
    pc_codes_dirty |= pc_patch_codes(PC_PATCH2)
    pc_to_original()
    print("S1: patch applied to the original pack:", state.apply_patch(lab, PC_PATCH2), flush=True)
    pc_s1 = pc_score("S1", "original pack + patch v2 (the shipped artifact), this machine's own patch-embedding path")

    pc_pe = pc_model.model.visual.patch_embed
    pc_fast = "forward" in vars(pc_pe)
    pc_out["patch_embed_as_found"] = "one matrix product (core._fast_patch_embed)" if pc_fast else "Conv3d"
    try:
        if pc_fast:
            pc_saved_forward = pc_pe.forward
            del pc_pe.forward
            pc_score("S1b", "S1 with the Conv3d patch embedding")
            pc_pe.forward = pc_saved_forward
        else:
            def pc_forward(hidden_states, pe=pc_pe):          # core._fast_patch_embed, inlined (this session may predate it)
                w = pe.proj.weight
                x = hidden_states.reshape(-1, w[0].numel()).to(w.dtype)
                return torch.nn.functional.linear(x, w.reshape(w.shape[0], -1), pe.proj.bias)
            pc_pe.forward = pc_forward
            pc_score("S1b", "S1 with the patch embedding as one matrix product (what the pods use)")
            del pc_pe.forward
    except Exception as e:                      # the other path may not exist in this session's code
        print("S1b skipped:", repr(e)[:200], flush=True)
        if not pc_fast and "forward" in vars(pc_pe):
            del pc_pe.forward

    # ------------------------------------------------------------ S2..S4: the training state from its files
    try:
        with safe_open(PC_PATCH2, "pt") as f:
            pc_kept = set()
            for k in f.keys():
                if k.endswith((".scales", ".biases")):
                    continue
                base, leaf = k[len("language_model."):].rsplit(".", 1)
                name = ternary.hf_module_name(base)
                if not (name in lab.tern and leaf == "weight"):
                    pc_kept.add(name + "." + leaf)
        with safe_open(PC_CKPT, "pt") as f:
            pc_ckpt_small = {k for k in f.keys() if not k.endswith((".codes", ".scales"))}
        pc_out["small_tensors"] = {"in_checkpoint": len(pc_ckpt_small), "kept_by_patch": len(pc_kept & pc_ckpt_small),
                                   "dropped_by_patch": sorted(pc_ckpt_small - pc_kept)[:60]}
        print("small tensors: %d in the checkpoint, %d kept by the patch, %d dropped" % (
            len(pc_ckpt_small), len(pc_kept & pc_ckpt_small), len(pc_ckpt_small - pc_kept)), flush=True)

        def pc_training_state(scales16=False, only_small=None):
            pc_codes_dirty.update(pc_patch_codes(PC_PATCH1))
            pc_to_original()
            state.apply_patch(lab, PC_PATCH1)                           # float16 multipliers, layers 4..31 and head
            used = "patch v1"
            if os.path.exists(PC_TUNE) and not scales16:                # the lab's own float32 multipliers, if readable
                try:
                    snap = torch.load(PC_TUNE, map_location="cpu")
                    got = 0
                    if isinstance(snap, dict):
                        for k, v in snap.items():
                            name = k[:-7] if k.endswith(".scales") else k
                            if name in lab.tern and torch.is_tensor(v) and v.shape == lab.tern[name].scales.shape:
                                lab.tern[name].scales.data.copy_(v.float().to(lab.tern[name].scales.device)); lab.tern[name].invalidate(); got += 1
                    used += f" + float32 multipliers of {got} matrices from {os.path.basename(PC_TUNE)}"
                except Exception as e:
                    used += f" (float32 multipliers not readable: {repr(e)[:80]})"
            n = pc_load_ckpt(PC_CKPT, scales16=scales16, only_small=only_small)
            return used + f" + checkpoint {n}"

        note = pc_training_state()
        pc_s2 = pc_score("S2", "training state rebuilt: " + note)
        note = pc_training_state(scales16=True)
        pc_score("S3", "S2 with float16 multipliers: " + note)
        note = pc_training_state(only_small=pc_kept)
        pc_score("S4", "S2 with only the small tensors the patch kept: " + note)
    except Exception as e:
        import traceback
        traceback.print_exc()
        pc_out["s2_error"] = repr(e)[:300]
finally:
    pc_restore()
    pc_end = pc_score("S0'", "after putting everything back; must equal S0")
    pc_out["restored_exactly"] = bool(abs(pc_end[0] - pc_s0[0]) < 1e-6 and abs(pc_end[1] - pc_s0[1]) < 1e-6)
    print("RESTORED EXACTLY" if pc_out["restored_exactly"] else
          "codes, multipliers and small tensors were copied back; the score differs from S0 by %.5f / %.5f "
          "(a re-folded layer can differ from its cached fold in the last bit)" % (pc_end[0] - pc_s0[0], pc_end[1] - pc_s0[1]), flush=True)
    json.dump(pc_out, open(f"{lab.dir}/bench_patch_check.json", "w"), indent=1)
    del pc_snap
    torch.cuda.empty_cache()
print("PATCH_CHECK_DONE", flush=True)
