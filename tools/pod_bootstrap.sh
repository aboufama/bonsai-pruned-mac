#!/bin/bash
# Turns a fresh RunPod pod into a lab machine. Run as root on the pod, after the code and the
# data bundle have been copied to /workspace/bonsai. Safe to run again.
set -e
cd /workspace/bonsai
export BONSAI_SIZE=${BONSAI_SIZE:-9B}
ln -sfn /workspace/bonsai /root/bonsai
mkdir -p hf logs lab/ckpt queue venv/bin export/patches
ln -sfn "$(command -v python3)" venv/bin/python
[ -f logs/pip.done ] || { pip install -q --break-system-packages numpy "transformers==5.23.0" "accelerate==1.15.0" "safetensors>=0.8" "flash-linear-attention==0.6.0" einops pillow "huggingface_hub>=1.0" && pip install -q --break-system-packages "torchvision==0.24.1" --index-url https://download.pytorch.org/whl/cu128 && touch logs/pip.done; }
python3 - <<'PY'
from huggingface_hub import snapshot_download
import os
size = os.environ.get("BONSAI_SIZE", "9B")
snapshot_download(f"prism-ml/Ternary-Bonsai-2-{size}-mlx-2bit", local_dir=f"hf/Ternary-Bonsai-2-{size}-mlx-2bit", token=False)
snapshot_download(f"Qwen/Qwen3.5-{size}", local_dir=f"hf/Qwen3.5-{size}", allow_patterns=["*.json", "*.jinja", "*.txt"], token=False)
PY
S=${BONSAI_SIZE:-9B}
[ -f hf/Bonsai-2-$S-dense/config.json ] || (cd weights && python3 convert_to_hf.py ../hf/Ternary-Bonsai-2-$S-mlx-2bit ../hf/Qwen3.5-$S ../hf/Bonsai-2-$S-dense)
# activity sampler, lab session, backlog filler
pgrep -f "[s]ample_activity.sh" > /dev/null || (nohup bash tools/sample_activity.sh /workspace/bonsai/logs/activity.csv > /dev/null 2>&1 &)
mkdir -p /workspace/logs && ln -sfn /workspace/bonsai/logs/activity.csv /workspace/logs/activity.csv
if ! [ -S lab/kernel.sock ] || ! kill -0 "$(cat lab/kernel.pid 2>/dev/null)" 2>/dev/null; then
  rm -f lab/kernel.sock; (nohup python3 -m weightlab.kernel > lab/kernel.log 2>&1 &); sleep 8
fi
pgrep -f "[t]ools/filler.sh" > /dev/null || (nohup bash tools/filler.sh /workspace/bonsai > logs/filler.log 2>&1 &)
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python3 -c "import torch, transformers; print('torch', torch.__version__, 'transformers', transformers.__version__, 'cuda', torch.cuda.is_available())"
echo BOOTSTRAP_OK
