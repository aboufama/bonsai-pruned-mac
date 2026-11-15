# bench: the evaluation behind docs/BENCHMARK.md

Every number in [docs/BENCHMARK.md](../docs/BENCHMARK.md) comes from a per-case file written by `run.py` and is turned into a table by `report.py`. Nothing is typed in by hand except the published scores of other models (`published.json`, each with its source).

## Files

| File | Role |
|---|---|
| `run.py` | Runs one model on one or more jobs and writes one line per case, plus a `.meta.json` with the command, git commit, library versions, GPU, model files and the exact prompt. Resumes where it stopped. |
| `models.py` | The models (Bonsai pack with or without a patch, full-precision checkpoints, GGUF files behind `llama-server`), the prompt, the answer parser, image preparation, tool-call parsing. |
| `suites.py` | Loaders for the pointing sets and the hit rule (point inside box or polygon; a refusal is right only when the case has no target). |
| `tasks.py` | Tool calling (our set and BFCL v3), MMLU, ChartQA, the canary, cost. |
| `stats.py` | Bootstrap intervals, paired differences, McNemar's exact test. |
| `report.py` | Tables and `results/*.json` from the per-case files; rewrites the table blocks of `docs/BENCHMARK.md`. |
| `chain.sh` | Runs jobs one after another on a machine. |
| `published.json` | Scores other groups reported for their models, with the page each was read on. |
| `results/` | Summary JSON, one file per table. Per-case files are not in the repo; they are on the machine that ran them. |
| `canary/`, `pointing/`, `toolcall/` | The project's own seeded test sets and their generators (older than this folder). |

## What has to be on the machine

Under `$BONSAI_ROOT` (default `~/bonsai`; `/workspace/bonsai` on the pods):

| Path | Contents | Source |
|---|---|---|
| `hf/Ternary-Bonsai-2-9B-mlx-2bit`, `hf/Bonsai-2-9B-dense` | PrismML's pack and its dense conversion | `prism-ml/Ternary-Bonsai-2-9B-mlx-2bit`, `weights/convert_to_hf.py` |
| `export/patches/*.patch.safetensors` | The repair, as a patch on the pack | `weights/make_patch.py` |
| `hf/Qwen3.5-9B`, `hf/UI-Venus-2-9B` | Full-precision references | `Qwen/Qwen3.5-9B`, `inclusionAI/UI-Venus-2-9B` |
| `refs/Qwen3.5-4B-GGUF` | `Qwen3.5-4B-Q4_K_M.gguf`, `mmproj-BF16.gguf` | `unsloth/Qwen3.5-4B-GGUF` |
| `ssv2/` | ScreenSpot-v2 and `excluded_overlap.json` | `OS-Copilot/ScreenSpot-v2` |
| `sspro/` | ScreenSpot-Pro | `likaixin/ScreenSpot-Pro` |
| `pub/osworld-g-repo` | OSWorld-G | `github.com/xlang-ai/OSWorld-G` (commit `daa6bd8`) |
| `data/mac/screen2ax_task` | The reserved macOS set | see `docs/MAC_DATA.md` |
| `benchdata/pointing/dev_20261114` | Our generated screens | `bench/pointing/generate.py --seed 20261114 --split dev` |
| `benchdata/toolcall/dev_20261114` | Our tool-calling set | `bench/toolcall/generate.py --seed 20261114 --n 400 --split dev` |
| `pub/bfcl`, `pub/mmlu`, `pub/chartqa` | BFCL v3, MMLU test, ChartQA test | `gorilla-llm/Berkeley-Function-Calling-Leaderboard`, `cais/mmlu`, `HuggingFaceM4/ChartQA` |

Python 3.12, torch 2.9.1 (CUDA 12.8), transformers 5.23.0, pyarrow, Pillow; PrismML's llama.cpp fork (`prism` branch) built with CUDA for the GGUF models (`LLAMA_SERVER` names the binary).

## One command per table

Model names: `bonsai9b-new` (pack + patch), `bonsai9b-orig`, `qwen35-9b`, `venus2-9b`, `qwen35-4b-q4`, `bonsai4b-orig`, `bonsai4b-new`, `bonsai9b-new-gguf`, `bonsai9b-orig-gguf`. A job is `<set>[:<input>][:looks2][:n<limit>]`; `<input>` is `native` or `sNNNN` (long side at most NNNN px).

| Table in BENCHMARK.md | Command, per model `M` |
|---|---|
| ScreenSpot-v2 | `python3 bench/run.py --model M --jobs ssv2:s1280 ssv2:native` |
| ScreenSpot-Pro | `python3 bench/run.py --model M --jobs sspro:s1280 sspro:native` |
| OSWorld-G | `python3 bench/run.py --model M --jobs osworld_g_refined:native osworld_g_refined:s1280 osworld_g:native` |
| macOS app windows | `python3 bench/run.py --model M --jobs mac:s1280` |
| Our generated screens | `python3 bench/run.py --model M --jobs gen:s1280` |
| Tool calling | `python3 bench/run.py --model M --jobs toolcall bfcl:n400` |
| What remains of the original | `python3 bench/run.py --model M --jobs canary mmlu:n500 chartqa:n500` |
| Input size | `python3 bench/run.py --model M --jobs ssv2:s448 ssv2:s640 ssv2:s896 ssv2:s1280 ssv2:s1920` |
| Second look | `python3 bench/run.py --model M --jobs ssv2:s1280:looks2 sspro:s1280:looks2 gen:s1280:looks2 mac:s1280:looks2:n500` |
| Cost | `python3 bench/run.py --model M --jobs cost` (with nothing else on the GPU) |
| Shipped file in llama.cpp | `python3 bench/run.py --model bonsai9b-new-gguf --gguf <file.gguf> --jobs ssv2:s1280` |
| A different patch | add `--patch <file> --tag <name>`; results go to `benchruns/bonsai9b-new@<name>/` |
| All tables | `python3 bench/report.py --runs <benchruns> --new <run folder of the new model> --write` |

Output goes to `$BONSAI_ROOT/benchruns/<model>[@tag]/<job>.jsonl`. `report.py` needs numpy only.

## Rules the code keeps

- Greedy decoding, thinking off, one request at a time, no batching.
- The same prompt for every model of the family, verbatim from UI-Venus-2's reference evaluator (`models.PROMPTS`).
- A point counts when it lies inside the target box (or polygon). An answer that cannot be read as coordinates is a miss and is counted separately. `[-1,-1]` is a refusal: a miss when there is a target, a hit when there is none.
- Intervals are percentile bootstraps over cases (10,000 resamples, seed 20261114).
