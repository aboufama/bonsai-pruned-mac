# Test P1_control (see experiments/025_position_input.py): position input in the trunk of the 4B, the control without it.
# Needs a fresh 4B session: tools/restart_lane.sh <this file> 4B
import os

PATCH = f"{lab.root}/export/patches/bonsai2-4b-point-v3-mixed.patch.safetensors"
exec(open(f"{lab.root}/experiments/_prelude.py").read())
if lab.size != "4B" or lab.stack != [f"patch:{os.path.basename(PATCH)}"]:
    raise RuntimeError(f"this needs a fresh 4B session on the v3-mixed patch (size {lab.size}, stack {lab.stack})")
UPDATES25, EVERY25, MODULE25, TAG25 = 1500, 250, False, "position_control"
exec(open(f"{lab.root}/experiments/025_position_input.py").read())
