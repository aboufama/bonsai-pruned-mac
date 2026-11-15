# Bonsai-Pruned: Ternary Bonsai 2 tuned for computer use on a Mac

By Andre Boufama. A hackathon entry, and the research notes behind it.

Created using Bonsai by Prism ML.

## What this is

PrismML's Ternary Bonsai 2 models are ternary versions of Qwen3.5: their large weight matrices hold only -1, 0 and +1, they take screenshots as input, and they fit in a few GB. As shipped they have lost most of one skill, pointing at the right spot on a screen. On ScreenSpot-v2 at 1280 px the 9B is right on 43.3% of cases and the 4B on 12.2%, where their full-precision parent Qwen3.5-9B is right on 91.7% ([docs/BENCHMARK.md](docs/BENCHMARK.md)).

This repository holds the code and the notes of an attempt to bring that skill back without leaving the ternary format, and a small Mac assistant that uses the result. You type or say a request; the assistant looks at the screen and either points at the thing, answers in words, or carries the request out one step at a time. Spoken requests are transcribed on the Mac by Argmax's WhisperKit.

It contains code, documents and result summaries, including the ideas that failed. It contains no model files.

## The hackathon requirement

The rules, as recorded in [docs/DEMO.md](docs/DEMO.md): the language models must be Bonsai 2 (2B, 4B or 9B), Argmax must be used, and everything must run on a Mac with WiFi off.

**Built on:** PrismML's Ternary Bonsai 2 4B and 9B. The retuning leaves their file format, size and speed as they were ([FINDINGS.md](FINDINGS.md), section 8); the pointing decoder is a small separate file.

**What was added:**

- **Retuned multipliers.** A Bonsai layer is a grid of -1, 0 and +1 with one multiplier for every group of 128 weights ([docs/WEIGHTS.md](docs/WEIGHTS.md)). The repair trains those multipliers and the small full-precision parts of the layers, and keeps the ternary values PrismML trained. The first patch changes no ternary value and moves each multiplier by 0.7% on average ([FINDINGS.md](FINDINGS.md), section 8). A later 9B patch, the one described in [docs/BENCHMARK.md](docs/BENCHMARK.md) under "Models and files", differs from the original in the multipliers of 176 matrices, in 27 small tensors and in the ternary values of 2 matrices.
- **A small pointing decoder.** Two layers, about 25 M parameters, full precision. It reads the 4B's state after layer 20 of its 32 layers and returns a point without writing any token, so the remaining layers do not run for pointing ([docs/TRIALS.md](docs/TRIALS.md), [docs/TASKENV.md](docs/TASKENV.md); code in `weightlab/head.py` and `taskenv/mlx_head.py`). The 9B was later given one as well, trained together with its multipliers ([docs/BENCHMARK.md](docs/BENCHMARK.md), "15 Nov, new models").
- **A planner.** The 9B was also trained to carry a task out from a list of the front window's controls instead of a screenshot: each turn it gets the request, the steps so far and the numbered controls, and answers with one `next_step` call ([docs/TASKENV.md](docs/TASKENV.md), "Planner mode"; `weightlab/planner.py`, `taskenv/planmode.py`).
- **A training simulator.** `macsim/` draws whole Mac desktops with every element labelled and scores each pointing answer, saying what was hit instead when it missed ([docs/MACSIM.md](docs/MACSIM.md)). Nothing of the test environment is used in it except the window engine.
- **Tool-call and action training.** Training cases in which the model answers with a tool call, and with one `computer_use` action per step ([docs/ACTION_FORMAT.md](docs/ACTION_FORMAT.md), `weightlab/actions.py`).
- **A Swift assistant** (`assistant/`). A menu-bar app that asks a Bonsai 2 model served by LM Studio. It points, answers questions about the screen, rewrites selected text, does a set of everyday requests itself with no model, and hands the rest to the planner one step at a time. Spoken requests are transcribed on the Mac by Argmax's WhisperKit ([docs/DEMO.md](docs/DEMO.md)).
- **Local only.** The app's one network address is LM Studio on the same Mac (`http://localhost:1234`). [docs/DEMO.md](docs/DEMO.md) says how far this was checked: speech to text was run with the network denied to its process, and one thing was left to try with WiFi switched off, that LM Studio's server starts and loads the model. Requests that open a web page ("go to …", "search for …") hand the address to the browser, which needs the network like any page.

Training used screens drawn by this repository's generator and public macOS screenshot sets ([docs/BENCHMARK.md](docs/BENCHMARK.md), "Contamination"). Bonsai's full-precision relatives, Qwen3.5-9B and UI-Venus-2-9B, served as references and teachers, and some training requests were written by Claude Fable ([docs/TRIALS.md](docs/TRIALS.md)). The model the assistant runs is Bonsai 2.

## Headline results

| Measure | Bonsai 2 as shipped | This work | Qwen3.5-9B, full precision | Source |
|---|---|---|---|---|
| Pointing, ScreenSpot-v2 at 1280 px (all 1,272 cases), 9B | 43.3% | with the pointing decoder: 85.5% with one look, 86.4% with a second look (a second pair: 85.0% and 87.7%) | 91.7% | [docs/BENCHMARK.md](docs/BENCHMARK.md), "15 Nov, new models" |
| The same, 4B | 12.2% | with the pointing decoder: 82.4% with one look, 85.2% with a second look | | [docs/BENCHMARK.md](docs/BENCHMARK.md), "15 Nov, new models" |
| Pointing, macOS app windows at 1280 px (2,106 cases), 9B | 13.2% | with the pointing decoder: 46.8% with one look, 57.5% with a second look | 63.8% | [docs/BENCHMARK.md](docs/BENCHMARK.md), "15 Nov, new models" |
| Long tasks where the model chooses every step from a list of controls (simulator; 120 episodes on tasks never trained on, three seeds), 9B | 1 of 120 | 27 of 120, and 34 of 120 inside the assistant's rules; 3 of 120 before the planner was trained on simulator rows | 9 of 120 | [docs/TASKENV.md](docs/TASKENV.md), "Planner mode" |
| Guided multi-step tasks (75 tasks), 4B with the pointing decoder at 1600 px, on a Mac mini in MLX | 3% (written answers, 1280 px) | 53 of 75 (71%); 55 of 75 with the click snapped to an element and a second look when nothing changed | | [docs/TASKENV.md](docs/TASKENV.md) |
| The assistant on real macOS apps (50 tasks, one run each) | | 9 of 50 with the first app package, 43 of 50 with the app of 15 Nov, 10:00 | | [docs/REALMAC.md](docs/REALMAC.md) |

- **Pointing.** The tuned models are well above the shipped ones and still behind the full-precision parent in every pointing row that has one.
- **Long tasks.** The trained planner is ahead of the parent on the long-task set (27 against 9 of 120). That set is a simulator, the parent was never trained on this format while the planner was trained on other tasks of the same simulator, and the intervals are wide: 17% to 44% on new tasks in known apps and 12% to 29% on apps never trained on, against 4% to 22% and 3% to 14% for the parent. 93 of 120 episodes still fail.
- **A second look** means the area around the first answer is enlarged and the question is asked again. It costs a second read of the screen.
- **On real macOS apps** most of the gain from 9 to 43 came from changes to the app, not to the model, and the fixes were written from the failures of those same 50 tasks ([docs/REALMAC.md](docs/REALMAC.md), "Limits").
- "This work" is not one checkpoint: each row uses the checkpoint its source document names. The intervals, the other reference models, the earlier checkpoints and the runs that were not done are in those documents.
- In guided tasks each step is given in words and the model only points. Choosing every step is the harder test.
- Speed on a Mac mini (M6, 16 GB) in MLX: one pointing answer at 1280 px takes 2.46 s with the 9B and 1.43 s with the 4B. With the decoder, a further request about a screenshot that has already been read costs 76 ms ([docs/TASKENV.md](docs/TASKENV.md)). On the laptop through LM Studio, the first question about a screenshot takes about 11 s with the 9B and each further one about 1.1 s ([docs/DEMO.md](docs/DEMO.md)).

## Running the assistant

```bash
assistant/run.sh            # builds when a source file changed, then starts the menu-bar app
assistant/run.sh --test     # the checks of the core
assistant/package.sh        # one folder that runs on another Mac, also unattended from a file of requests
```

What it needs, how to use it, and what was and was not checked: [docs/DEMO.md](docs/DEMO.md). In short:

- macOS 14 or later with the Swift command-line tools, and LM Studio with a Bonsai 2 model and its vision file.
- The first build fetches the Swift packages pinned in `assistant/Package.resolved` (Argmax's open-source SDK and what it depends on). The first spoken request downloads the WhisperKit `base.en` model, about 150 MB, unless it is already under `~/Bonsai-demo/models/argmax`. After that the app is written to fetch nothing.
- The tuned model files are not in this repository. With PrismML's models as shipped the app runs, and points as the shipped models do. A tuned GGUF is made from PrismML's file and a patch with `weights/export_gguf.py` ([docs/GGUF_EXPORT.md](docs/GGUF_EXPORT.md)).

## Repository layout

| Path | What it is |
|---|---|
| `assistant/` | The Swift menu-bar assistant |
| `weightlab/` | The weight lab: Bonsai's ternary layers in PyTorch, the trainers, the pointing decoder, tool-call and action training ([docs/WEIGHTLAB.md](docs/WEIGHTLAB.md)) |
| `weights/` | Reader for PrismML's packed format, conversion to a dense checkpoint, patches, export to GGUF |
| `experiments/` | The numbered experiments, as scripts run inside the lab session; `experiments/lanes/` holds the job files of the parallel GPU machines |
| `bench/` | The evaluation behind [docs/BENCHMARK.md](docs/BENCHMARK.md), with result summaries in `bench/results/`, the generator of test screens (`bench/pointing/`), the tool-call test set (`bench/toolcall/`) and a 50-question regression check (`bench/canary/`) |
| `taskenv/` | The task environment: ten Mac-style apps as web pages, 97 tasks, checkers, results, and the planner mode with its training rows ([docs/TASKENV.md](docs/TASKENV.md)) |
| `macsim/` | The training simulator: Mac desktops with every element labelled, pointing cases, a scorer ([docs/MACSIM.md](docs/MACSIM.md)) |
| `realmac/` | The 50 task templates and checkers of the test on real macOS apps ([docs/REALMAC.md](docs/REALMAC.md)); the runner is not included |
| `playground/` | A local web page that compares the shipped and the tuned 9B on one screenshot |
| `spark/` | The scripts of the first baseline measurements on the training machine |
| `tools/`, `tests/` | Small utilities and tests |
| `FINDINGS.md`, `PLAN.md` | The first day's measurements and the plan written at the start |
| `docs/` | See below |

| Document | What it holds |
|---|---|
| [docs/BENCHMARK.md](docs/BENCHMARK.md) | Pointing benchmarks: every model, method, statistics, limits |
| [docs/TASKENV.md](docs/TASKENV.md) | Multi-step tasks: results, the planner mode, what is measured, limits |
| [docs/REALMAC.md](docs/REALMAC.md) | The assistant on real macOS apps in a virtual machine: method, results by round, limits |
| [docs/MACSIM.md](docs/MACSIM.md) | The training simulator and its scorer |
| [docs/DEMO.md](docs/DEMO.md) | The assistant: running it, speed, what is checked and what is not |
| [docs/WEIGHTS.md](docs/WEIGHTS.md), [docs/WEIGHTLAB.md](docs/WEIGHTLAB.md), [docs/GGUF_EXPORT.md](docs/GGUF_EXPORT.md) | The weight format, the lab, the export to llama.cpp's format |
| [docs/ACTION_FORMAT.md](docs/ACTION_FORMAT.md), [docs/MAC_DATA.md](docs/MAC_DATA.md), [docs/ICON_SET.md](docs/ICON_SET.md) | The action schema and the training data |
| [docs/TRIALS.md](docs/TRIALS.md), [docs/EXTREME_TRIALS.md](docs/EXTREME_TRIALS.md), [docs/SKIP_BLANK.md](docs/SKIP_BLANK.md), [docs/RESOLUTION_BY_EYE.md](docs/RESOLUTION_BY_EYE.md) | What worked and what did not, with single write-ups |
| [docs/RL.md](docs/RL.md), [docs/HF_SCOUT.md](docs/HF_SCOUT.md), [docs/RESEARCH_DECISION_MODELS.md](docs/RESEARCH_DECISION_MODELS.md), [docs/REFERENCES.md](docs/REFERENCES.md) | Design notes, reading notes and sources |
| [docs/SETUP.md](docs/SETUP.md) | Machines and folder layout |
| `docs/visual/layer-anatomy.html` | An illustrated walk through one model layer |

Words used throughout: "the Spark" is an NVIDIA DGX Spark, the first training machine; a "pod" or "lane" is a rented single-GPU machine; "the Mac mini" is the Mac the task benchmark and the virtual machine ran on.

Not included: some operations scripts (copying files between machines, managing the rented machines, the runner of the real-Mac test) and the project's working logs. Where a script or a document names one of them, it is not in this repository.

## Model files

No model weights, patch files, datasets or build products are in this repository. The Bonsai 2 weights are PrismML's and come under PrismML's terms; get them from PrismML (links in [docs/REFERENCES.md](docs/REFERENCES.md)). The reference models and the public data sets named in the documents belong to their authors and come under their terms. The sample screens in `bench/pointing/samples/` and `playground/samples/` were drawn by this repository's generator with open-source icons.
