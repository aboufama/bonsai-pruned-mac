# Plan

Written 2026-11-14, at the start of the work. This is a research project, not a product. The stage table below shows the status on that date; what was done and measured afterwards is in [FINDINGS.md](FINDINGS.md), [docs/BENCHMARK.md](docs/BENCHMARK.md) and [docs/TASKENV.md](docs/TASKENV.md).

## Goal

A Bonsai 2 9B (about 2 GB, ternary) that is better at computer use than UI-Venus-2-9B, a full-precision fine-tune of the same parent model, and at least as good as the original Bonsai at tool calling. Then the same recipe for the 2B, 4B and 27B, and a general "pruned" Bonsai that scores better across the board.

The reference application is a Clicky-style assistant ([farzaa/clicky](https://github.com/farzaa/clicky)): press a hotkey, speak, and the model answers and points. It sends a screenshot shrunk to 1280 px on its long side and expects a short reply ending in a `[POINT:x,y:label]` tag. An agent mode acts through tool calls.

## What is wrong today

The ternary models kept coarse screen understanding and lost fine pointing precision. The 9B typically lands 5 to 15% of the screen away from the target, and its coordinate digits have collapsed (they end almost only in 6, 0, 8 and 2). Two independent runtimes (llama.cpp and MLX) give the same wrong answers, so the fault is in the weights. See [FINDINGS.md](FINDINGS.md).

Working hypothesis: PrismML's ternary training never exercised pixel-accurate pointing, so that skill was the first to go. Even the 27B lost it, which argues against a capacity limit. The first training run tests this.

## Approach

### Signals available

1. **Exact ground truth.** Pointing is verifiable: a click is inside the box or it is not. We render our own screens, so the right answer is known exactly.
2. **Same-architecture teachers.** Qwen3.5-9B (the parent) and UI-Venus-2-9B (its computer-use fine-tune) have the same shape as Bonsai, layer for layer. They can supervise Bonsai's internal activations, not just its final answer.
3. **Frontier models as teachers by example.** For natural instructions, Clicky-style spoken answers and multi-step tool-call traces, where no cheap ground truth exists. This is accepted for this research project.
4. **Direct weight work.** Because Bonsai has a full-precision twin, the two can be compared layer by layer on pointing tasks to find where position information is lost, and those places corrected directly ("weight-space programming" with a reference model).

### What may change in the model, least invasive first

1. Per-group scale values (one float per 128 weights, about 70M numbers in the 9B) and the full-precision parts: normalisation weights, the small non-ternary projections, and the vision-to-language connector. The file stays an ordinary Bonsai.
2. Which weights are zero. Zero is a legal ternary value, so a learned deletion mask keeps the model ternary and the file format unchanged.
3. Flipping ternary values (-1, 0, +1) with a straight-through estimator, if 1 and 2 are not enough.
4. Fallback: a small pointer head that picks the screen patch directly instead of writing digits.

### Benchmarks

Primary scores come from our own seeded benchmarks, which no model can have seen:

- **Pointing:** procedurally generated application screens rendered in a headless browser, with exact element boxes and instructions that match exactly one element. Scored at 1280 px, strict hit plus distance.
- **Tool calling:** procedurally generated tools and requests with exact expected calls, including selection among distractors, parallel calls, multi-step with simulated results, missing information and no-call cases.
- **Seeds:** a development seed, a sealed test seed, and fresh seeds on demand to detect overfitting. Train and test come from disjoint layout families, tool vocabularies and phrasings.
- **A private Mac set:** real macOS app windows with boxes from the accessibility system. Never used for training. Not built yet.

Public benchmarks (ScreenSpot-v2, ScreenSpot-Pro, later OSWorld-G and BFCL) stay as outside references and are never trained on.

A regression guard of general benchmarks runs on every candidate so that nothing else gets worse unnoticed.

## Stages

| Stage | Content | Status |
|---|---|---|
| 0 | Baselines on public sets; harness validated against published scores | Done for ScreenSpot-Pro; ScreenSpot-v2 running |
| 1 | Load Bonsai in PyTorch, prove it matches llama.cpp answers; build seeded benchmarks | In progress |
| 2 | Layer-by-layer comparison of Bonsai against Qwen3.5-9B on pointing prompts; locate the damage | Next |
| 3 | First corrections: scales, full-precision parts, connector; measure | Not started |
| 4 | Deletion masks and, if needed, ternary flips; teach from UI-Venus plus ground truth; add tool-call and Clicky-format data | Not started |
| 5 | Export back to the formats LM Studio and llama.cpp load; speed and memory unchanged | Not started |
| 6 | General "pruned" Bonsai with the parent as teacher on broad tasks; repeat for 2B, 4B, 27B | Not started |

## Success criteria

- Pointing at 1280 px on the sealed seed and on ScreenSpot-v2: at or above UI-Venus-2-9B.
- Tool calling: no regression against the original Bonsai 9B, ideally at or above Qwen3.5-9B.
- General benchmarks: within 1 point of the original Bonsai 9B.
- Size and speed: unchanged (about 2 GB; about 28 tok/s on a 13-inch M4 MacBook, about 109 tok/s on the Spark).

## Honest odds

- Recovering most of the parent's pointing ability: likely if the hypothesis holds.
- Beating UI-Venus on strict full-resolution ScreenSpot-Pro: a real stretch for a 2 GB ternary model.
- Beating it at 1280 px: more plausible. Bonsai is also about four times faster than a full-precision 9B on the same hardware, so it can afford a second, zoomed-in look in the same time.

## Compute

- DGX Spark (GB10, 121 GB): evaluation, analysis and first training runs.
- A rented 80 GB GPU would cut each training run from roughly a day to a couple of hours. Not arranged.
