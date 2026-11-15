# STATUS: written but never run. T3 was dropped on 15 Nov to save tokens; treat this file as untested.
# Experiment 022, trial T3: open the vision tower.
#
# From v3-gentle, 1,500 steps of lane 3's recipe (block 4..19: multipliers and small parts, no
# codes, lr 1e-4 / 2e-5, warm-up 100, cosine to 0.2) with the vision tower's last 6 blocks and
# the merger trainable as well, at 1e-5. They are full precision, so nothing ternary changes; but
# the vision file a user downloads does. The task loss reaches the vision side through the frozen
# layers 0..3 (X22Trainer). While they train, the opened vision modules are held in float32 (an
# update of 1e-5 is below bfloat16's resolution for most weights); checkpoints store them rounded
# to bfloat16 and every score below is measured on the rounded values.
# Measured at steps 500, 1000, 1500, with Mac app windows and 896 px.
exec(open(f"{lab.root}/experiments/022_extreme_common.py").read())
assert x22_base_score is not None, "run 022_extreme_t0_baseline_bias.py first"
from safetensors.torch import save_file
from weightlab.tune import answer_targets, point_loss

LO, HI = 4, 19
STEPS, EVERY = globals().get("STEPS22", 1500), globals().get("EVERY22", 500)
LR_VIS, N_BLOCKS = globals().get("LR_VIS22", 1e-5), 6
ck = f"{lab.dir}/ckpt"
vis = lab.B.model.visual
depth = len(vis.blocks)
open_mods = list(vis.blocks)[depth - N_BLOCKS:] + [vis.merger]
vis_names = [n for n, _ in lab.B.named_parameters() if n.startswith("model.visual.merger.")
             or any(n.startswith(f"model.visual.blocks.{i}.") for i in range(depth - N_BLOCKS, depth))]
all_vis = [n for n, _ in lab.B.named_parameters() if n.startswith("model.visual.")]
params_by_name = dict(lab.B.named_parameters())


def vision_open():
    hooks = []
    for m in open_mods:
        m.float()
        hooks.append(m.register_forward_pre_hook(lambda mod, args, kwargs: (_cast(args, torch.float32), _cast(kwargs, torch.float32)), with_kwargs=True))
    hooks.append(vis.merger.register_forward_hook(lambda mod, args, out: out.to(torch.bfloat16)))
    params = [params_by_name[n] for n in vis_names]
    for p in params:
        p.requires_grad_(True)
    return params, hooks


def vision_close(params, hooks):
    for h in hooks:
        h.remove()
    for p in params:
        p.requires_grad_(False)
        p.grad = None
    for m in open_mods:
        m.to(torch.bfloat16)


def vision_save(path):
    save_file({n: params_by_name[n].data.to(torch.bfloat16).cpu() for n in vis_names}, path)


if "t3_res" not in globals():
    t = time.time()
    vparams, vhooks = vision_open()
    try:
        E = X22Trainer(lab, LO, HI, vision=vparams)
        E.open(lr_codes=2e-3, lr_scales=1e-4, lr_fp=2e-5, codes=False)
        E.opt.add_param_group({"params": vparams, "lr": LR_VIS})
        E.base["groups"].append(LR_VIS)
        # pre-flight: one backward pass without an update; the loss must reach the vision side
        pack = x22_packs[0]
        hints, answers = E.forward(pack, want_logits=True, use_hints=False)
        torch.stack([point_loss(lg, answer_targets(one, tgt)) for one, (lg, tgt) in zip(pack, answers)]).mean().backward()
        gn = {n: (params_by_name[n].grad.float().norm().item() if params_by_name[n].grad is not None else None)
              for n in (vis_names[0], vis_names[-1])}
        gains = [g.grad.float().norm().item() for g in E.opt.param_groups[0]["params"][:1] if g.grad is not None]
        print("pre-flight gradient norms:", gn, "| first multiplier gain of the block:", gains, flush=True)
        assert all(v is not None and v > 0 for v in gn.values()), "no gradient reaches the vision tower"
        E.opt.zero_grad(set_to_none=True)
        for m in E.mods:
            m.after_step()
        s0 = E.score(x22_sel)["p_hit"]
        print("T3: block %d..%d and %d vision tensors open (%.1f M parameters); select before any step %.3f" % (
            LO, HI, len(vparams), sum(p.numel() for p in vparams) / 1e6, s0), flush=True)
        marks = []
        for r in range(0, STEPS, EVERY):
            res = E.train(x22_packs, min(EVERY, STEPS - r), total_steps=STEPS, task=1.0, hint=0.0, warmup=100, final=0.2,
                          seed=10, report_every=100)
            x22_light_save(f"{ck}/x22_t3_lm_step{E.steps_done}.safetensors", range(LO, HI + 1), E)
            vision_save(f"{ck}/x22_t3_vision_step{E.steps_done}.safetensors")
            marks.append(E.steps_done)
            print("T3 step %4d: select %.3f (block open, vision in float32)  train loss %.2f / %.2f  [%.0f min]" % (
                E.steps_done, E.score(x22_sel)["p_hit"], res["first_question"], res["later_questions"], (time.time() - t) / 60), flush=True)
        E.close()
    finally:
        if getattr(globals().get("E"), "training", False):
            E.close()
        vision_close(vparams, vhooks)
    del E
    torch.cuda.empty_cache()
    train_minutes = (time.time() - t) / 60
    # how much of the vision file changed (bfloat16 values against the baseline's)
    changed = sum(params_by_name[n].numel() * 2 for n in all_vis if not torch.equal(params_by_name[n].data, x22_base["params"][n]))
    total = sum(params_by_name[n].numel() * 2 for n in all_vis)
    print("vision tensors changed: %.0f MB of %.0f MB (bfloat16)" % (changed / 1e6, total / 1e6), flush=True)
    t3_res = {"marks": marks, "train_minutes": train_minutes, "vision_mb_changed": changed / 1e6, "vision_mb_total": total / 1e6, "rows": {}}
    for k in marks:
        x22_light_restore(f"{ck}/x22_t3_lm_step{k}.safetensors")
        x22_light_restore(f"{ck}/x22_t3_vision_step{k}.safetensors")
        lab.stack[:] = [f"patch:{os.path.basename(X22_PATCH)}", f"022x:T3:open_vision:{k}"]
        row = x22_measure("T3", "block 4-19 + last 6 vision blocks + merger, step %d" % k, time.time() - 60 * train_minutes * k / STEPS, extra=True)
        t3_res["rows"][k] = row
    x22_notes.append({"T3": {k: v for k, v in t3_res.items() if k != "rows"}}); x22_save()
    x22_back_to_baseline("after T3")
print("T3 done", flush=True)
