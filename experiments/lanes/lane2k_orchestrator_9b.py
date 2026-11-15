# Lane 2: the 9B as orchestrator (15 Nov 02:55; experiment 027). 3,000 updates, scores
# every 500, step cases without thoughts, tool calls with no-call cases, a quarter plain pointing, long
# sides half 1280 half 896. A patch at every best: export/patches/bonsai2-9b-orch-v1-u<step>.
# Start state, as lane1c did it with v3-gentle: v3-tools, with v3-mixed896 (the best 9B pointer by
# generated answers) combined in as  mixed896 + (tools - v2)  on the multipliers if that does not cost
# plain pointing on select or the tool-call format; otherwise plain v3-tools.
# First a smoke run of 20 updates (nothing saved), since the step code had not run on a GPU before.
# Needs a fresh 9B session, data/mac/agentnet/step_pick.json with its screenshots (tools/step_images.py)
# and the v2, v3-mixed896 and v3-tools patch files.
import os

from safetensors import safe_open

_pd = f"{lab.root}/export/patches"
PATCH = f"{_pd}/bonsai2-9b-point-v3-tools.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 9B session started on the v3-tools patch (stack: {lab.stack})")
from weightlab import chat, ternary
from weightlab.tune import TaskTuner


def _scales(path):
    """Multipliers in a patch file, by the lab's module names."""
    with safe_open(path, "pt") as f:
        return {ternary.hf_module_name(k[len("language_model."):-len(".scales")]): f.get_tensor(k).float()
                for k in f.keys() if k.endswith(".scales")}


def _look(label):
    a, b = fS.evaluate(4), fR.evaluate(4)
    fS.discard(); fR.discard()
    pc = chat.score(lab, lab.B, [chat.point_call(it) for it in fS.samples[:60]])
    print("%-28s plain pointing select %.3f   report %.3f   pointing as a tool call: call written correctly %.0f%%" % (
        label, a["p_hit"], b["p_hit"], 100 * pc["format"]), flush=True)
    return a["p_hit"], pc["format"]


_gentle = f"{_pd}/bonsai2-9b-point-v3-mixed896.patch.safetensors"
_v2 = f"{_pd}/bonsai2-9b-point-v2.patch.safetensors"
_t = _look("v3-tools")
if os.path.exists(_gentle) and os.path.exists(_v2):
    # to go back to v3-tools: its multipliers, and every small tensor the v3-mixed896 patch will write
    _tt = TaskTuner(lab, list(range(4, 32)), scales=True, head=True)
    _keep = _tt.snapshot()
    _params = dict(lab.B.named_parameters())
    with safe_open(_gentle, "pt") as _f:
        _small = [ternary.hf_module_name(k[len("language_model."):].rsplit(".", 1)[0]) + "." + k.rsplit(".", 1)[1] for k in _f.keys()
                  if not k.endswith((".scales", ".biases")) and ternary.hf_module_name(k[len("language_model."):].rsplit(".", 1)[0]) not in lab.tern]
    _keep_small = {n: _params[n].data.clone() for n in _small}
    _tools, _base = _scales(PATCH), _scales(_v2)
    print("v3-mixed896 laid over the session:", state.apply_patch(lab, _gentle))
    for _n, _s in _tools.items():                        # gentle + (tools - v2)
        if _n in _base:
            _m = lab.tern[_n]
            _m.scales.data.add_((_s - _base[_n]).to(_m.scales.device, _m.scales.dtype)); _m.invalidate()
    _c = _look("v3-mixed896 + (tools - v2)")
    if _c[0] < _t[0] or _c[1] < _t[1] - 0.05:
        _tt.restore(_keep)
        for _n, _v in _keep_small.items():
            _params[_n].data.copy_(_v)
        _look("back to v3-tools")
        print("start state: v3-tools (the combination was worse)")
    else:
        lab.stack[:] = ["patch:bonsai2-9b-point-v3-mixed896 + (v3-tools - v2) multipliers"]
        print("start state: v3-mixed896 with the tool-calling change of the multipliers added")
    del _keep, _keep_small, _tools, _base
else:
    print("start state: v3-tools (the v2 or v3-mixed896 patch file is not on this machine)")

SMOKE27 = 20
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
UPDATES27, EVERY27, LR27, ACC27, TAG27, PATCHNAME27, THOUGHT27 = 3000, 500, 2e-4, 2, "orch_9b", "bonsai2-9b-orch-v1", False
exec(open(f"{lab.root}/experiments/027_orchestrator.py").read())
