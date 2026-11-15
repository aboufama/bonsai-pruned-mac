# Setup: machines and folder layout

State as of 2026-11-14, when the work ran on one training machine and one Mac. Later runs also used rented single-GPU machines (RTX PRO 6000, 96 GB; called "pods" or "lanes" in the code and documents) with the same layout under `/workspace/bonsai`; `tools/pod_bootstrap.sh` prepares one.

## Machines

### DGX Spark (evaluation, analysis, training)

- Ubuntu 24.04, aarch64, NVIDIA GB10, 121 GB memory shared between CPU and GPU, CUDA 13.0. Everything runs in user space: no `sudo`, no Docker.
- Everything lives under `~/bonsai` (`$BONSAI_ROOT` where a script takes one):

| Path | Contents |
|---|---|
| `llama.cpp/build/bin/` | PrismML's llama.cpp fork built with CUDA (`llama-server`, `llama-bench`, `llama-cli`). Needs `export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH` |
| `models/` | Bonsai 2 GGUFs: `Ternary-Bonsai-2-{2B,4B,9B,27B}-{PTQ1_0,PQ2_0}.gguf` and `-mmproj-BF16.gguf` vision files |
| `refs/` | Reference GGUFs: `Qwen3.5-9B-Q8_0.gguf`, `UI-Venus-2-9B-Q8_0.gguf`, each with an `-mmproj-BF16.gguf` |
| `hf/` | PyTorch-side checkpoints: `Ternary-Bonsai-2-9B-mlx-2bit` (the pack), `Bonsai-2-9B-dense` (converted), `Qwen3.5-9B`, `UI-Venus-2-9B` |
| `venv/` | Python 3.12 with torch 2.14.1+cu130, transformers 5.23.0, safetensors, Pillow, Playwright with headless Chromium |
| `sspro/`, `ssv2/` | ScreenSpot-Pro and ScreenSpot-v2 |
| `eval/` | One `.jsonl` of per-sample results per run |
| `logs/` | Logs of every script |
| `weights/` | Copy of this repo's `weights/` |
| `bench/`, `benchdata/` | Seeded benchmark generators and their output |
| `*.py`, `*.sh` | The scripts in this repo's `spark/` |

None of the model files or datasets are in this repository; the scripts in `spark/` fetch them from their public sources.

### 13-inch M4 MacBook, 16 GB (trying models, cross-checks, the assistant)

- LM Studio 0.4.28 with all four Bonsai sizes as GGUF `Q2_0`, plus the 9B MLX pack. Local server on port 1234.
- `~/Bonsai-demo`: PrismML's demo repo, their llama.cpp fork built with Metal, the weight files LM Studio links to, and `.venv-vlm` (MLX, `mlx-vlm` 0.7.8).
- Keep weights, clones and builds out of any folder that syncs to a cloud drive.

## Common tasks

### Grounding evaluation

```bash
cd ~/bonsai
./run_ground.sh "9B qwen9b venus9b" --dataset ssv2 --limit 150
./run_ground.sh "9B" --dataset sspro --max-side 1280 --limit 40
```

Names: `2B 4B 9B 27B` are Bonsai (`PTQ1_0`), `qwen9b` and `venus9b` are the references. Results append to `eval/<dataset>_<name>[_side<px>][_n<limit>].jsonl` and are resumable. The script starts and stops its own server on port 8112.

### Speed test

```bash
~/bonsai/run_all.sh PTQ1_0     # llama-bench per model, then all four served at once under load
```

### Convert the Bonsai pack to a dense PyTorch checkpoint

```bash
cd ~/bonsai/weights
../venv/bin/python convert_to_hf.py ../hf/Ternary-Bonsai-2-9B-mlx-2bit ../hf/Qwen3.5-9B ../hf/Bonsai-2-9B-dense
../venv/bin/python hf_point.py ../hf/Bonsai-2-9B-dense ../eval/sspro_9B_n40.jsonl --n 10 --dtype float32
```

### Downloads

The Hugging Face hub client stalled on the Spark when unauthenticated. `fetch_curl.sh <repo> <dest> <file-regex>` downloads with plain resumable `curl` instead and is reliable.

## Ports in use by convention

| Port | Use |
|---|---|
| 8101-8104 | `run_all.sh` speed test |
| 8111, 8112 | grounding evaluation |
| 8121 | tool-call benchmark |
| 8122 | pointing benchmark |

## Things that went wrong once and how to avoid them

- A model folder placed in a cloud-synced folder on the Mac started uploading. Keep large files in the home directory.
- Loading models in a hidden browser tab throttles downloads to a crawl.
- `pkill -f <pattern>` over SSH kills its own shell if the pattern appears in the command line. Use a bracket, as in `pkill -f "[f]etch_hf.py"`.
- A `grep -i error` on a build log stopped a queued job on a harmless warning. Wait on an explicit done-marker instead.
- Prebuilt llama.cpp binaries need macOS quarantine removal. Building from source avoids it.

## Memory on the Spark: one pool

The Spark's 121 GB is one pool for CPU and GPU. On 2026-11-14 this project filled it (the lab session at about 50 GB, an 18 GB teacher model being loaded, and three model servers running at the same time) and every process of the run was killed. Nothing on disk was lost.

Rules since then:

- Check free memory before starting a model server or loading a model. The scripts that start servers take a small check script through `$MEM_OK` (`bench/toolcall/serve_llama.sh`, `bench/pointing/run_baselines.sh`).
- The lab checks by itself (`weightlab.core.need_memory`) before loading a model or starting training, and a training run stops by itself if the machine drops below 14 GB available.
- One model server at a time, stopped as soon as the run ends; no other GPU work while the lab is training.
- A teacher model is loaded only as the block of layers that is needed (`weightlab.distill.teacher_block`), 7 GB instead of 18 GB.
