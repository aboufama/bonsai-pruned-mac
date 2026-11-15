# Training with verifiable rewards

The gradient-based track, alongside direct editing ([WEIGHTLAB.md](WEIGHTLAB.md)). Decided 2026-11-14. Not yet wired or run.

## Why rewards work here

Pointing and tool calling are checkable by a program: a click is inside the box or not; a tool call matches the expected call or not. That gives a reward with no human or model judge, which is the setting reinforcement learning with verifiable rewards is built for. It also handles what supervised targets handle badly: any point inside the box is correct, and a multi-step task has many correct paths.

## Framework: TRL's `GRPOTrainer`

Chosen after checking what exists.

| Option | Verdict |
|---|---|
| **TRL `GRPOTrainer`** (Hugging Face, v1.18) | Chosen. Accepts an already-built model object, so our ternary modules work unchanged. Takes plain Python reward functions that receive dataset columns by name. Supports vision-language models through an `image` column. Runs in one process on one GPU with `model.generate`. |
| verl (used by the Deletion Tuning code) | Built for distributed rollouts with vLLM and Ray on x86. Our model cannot be served by vLLM in ternary form, and the Spark is one aarch64 machine. |
| prime-rl, ART, others | Ship their own trainers or async stacks; nothing we need that TRL lacks at this scale. |

Qwen3.5 is not on TRL's list of tested vision-language models, so the first run is also a compatibility test.

From Deletion Tuning's code (MIT) we take the mask design, not the training stack: one logit per weight, a sigmoid sharpened linearly over training into a hard keep-or-delete decision, logits initialised from pruning scores.

## What is trainable

`weightlab/ternary.py` already has the module this needs. In "rotated" mode a `TernaryLinear` computes exactly what the runtimes compute, and gradients reach:

1. `scales`: about 62 million numbers in the 9B.
2. `gate`: optional deletion logits on chosen modules. On every `gate_proj` that is about 1.6 billion logits; on all ternary layers it would be 7.9 billion, which is too much memory with optimiser state.
3. The full-precision parts, including the vision connector.

The ternary codes themselves stay fixed in this track unless a straight-through estimator is added later.

## Rewards

- **Pointing:** 1 if the point is inside the box; otherwise a small shaped reward that falls with distance, so early training has a gradient. Malformed answers get 0.
- **Tool calling:** 1 for an exact match after type-aware normalisation, using the same checker as the benchmark; partial credit only where the benchmark defines it.
- **Clicky format:** the pointing reward applied to the `[POINT:x,y:label]` tag, plus a format check.

Rewards come from the same code that scores the benchmarks, so training and evaluation cannot drift apart.

## Data

Training data comes only from the `train` split of our seeded generators, which is disjoint from `dev` and `test` by layout family, tool vocabulary and phrasing. Public benchmarks are never trained on.

## Relation to supervised training

For pointing we also have exact labels, and supervised learning on them is far more sample-efficient than policy gradients. The plan is to use both in one trainer: a supervised term on the digit distribution (with all in-box digits counted as correct) and the reward term on sampled answers. Teachers add a third signal: UI-Venus's activations and output distribution on the same inputs.

## Order of work

1. Smoke test: `GRPOTrainer` with the Bonsai 9B object, scales trainable, a few hundred pointing samples, to confirm the plumbing and measure speed.
2. Add deletion gates on the modules the lab identifies as damaged.
3. Add the supervised and teacher terms.
4. Scale the data once the seeded generators deliver.
