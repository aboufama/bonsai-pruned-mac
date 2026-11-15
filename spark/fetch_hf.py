"""Full-precision reference checkpoints (same architecture as Bonsai 2 9B) for layer-wise comparison and teaching."""
import os

from huggingface_hub import snapshot_download

ROOT = os.path.expanduser(os.environ.get("BONSAI_ROOT", "~/bonsai"))
for repo in ("Qwen/Qwen3.5-9B", "inclusionAI/UI-Venus-2-9B"):
    p = snapshot_download(repo, local_dir=f"{ROOT}/hf/{repo.split(chr(47))[1]}", allow_patterns=["*.json", "*.safetensors", "*.jinja", "*.txt", "*.model"])
    print("OK", repo, p, flush=True)
print("HF_DONE")
