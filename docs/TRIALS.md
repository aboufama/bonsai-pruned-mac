# Trials: what worked and what did not

State at 02:35 EST on 15 Nov 2026. This is the results table of a longer planning document; the planning itself (which machine runs what, in which order) is left out. "Select" and "report" are the two development eighths of ScreenSpot-v2 ([WEIGHTLAB.md](WEIGHTLAB.md)); the task benchmark is described in [TASKENV.md](TASKENV.md).

The target these trials were measured against: the 4B with its pointing decoder and assists should beat the full-precision 9B parent (91.8% generated on the report set at 1280 px; 92% of guided tasks in the task environment). The demo model is the 4B; the pointer gets plain instructions from a smarter step, so requests worded by intent matter less.

| | Trial | Evidence |
|---|---|---|
| Star | Small full-precision decoder on the 4B's layer-20 states ("keep the eyes, make the execution layers tiny") | 2 layers, 25 M parameters: 72.3% select / 69.6% report, above the 4B's written answers (67.1%); runs in MLX with identical verdicts |
| Star | That decoder trained together with the multipliers of layers 0..20 | 76.1% on select; canary and tool calls unchanged |
| Star | Fable-written requests | 4B trunk report 0.749 -> 0.787; Fable test direct 0.70 -> 0.76, intent 0.32 -> 0.44 |
| Star | Mixed-size training | 9B generated 73.4 -> 86.1% at 1280 px, 51.9 -> 77.2% at 896 |
| Star | Tuning at all, on the Mac mini task benchmark (guided) | 4B 3% -> 57% of tasks, 9B 8% -> 75%; parent 92%, UI-Venus 100% |
| Fell | Flipping ternary codes, by the usual method or chosen by evidence and checked | every variant lowered the score or raised held-out loss |
| Fell | Rank-16 side paths trained from scratch; UI-Venus's change written into multipliers; UI-Venus vision transplant (its tower is identical to Bonsai's) | no gain |
| Fell | Bonsai 2B; greyscale; skipping blank areas; decoders that plug in before layer 20; position signal in the decoder | weaker or no difference |
| Fell | The model checking its own action with yes or no | says no after 31% of good clicks; retries then break tasks |
| Open | Seg2Click (a Qwen3.5-4B specialist) as teacher and as a transplanted side path with its vision tower; 1.87 M-case GroundCUA data; finer-output decoder; position signal in the trunk (hurts at first score); snap and second look as separate aids; coarse-to-fine coordinates (behind at 1,500 steps, parked) | see [HF_SCOUT.md](HF_SCOUT.md), [EXTREME_TRIALS.md](EXTREME_TRIALS.md), [TASKENV.md](TASKENV.md) |

"Fable-written requests" are training requests written by Claude Fable for real Mac screenshots whose elements have exact boxes from accessibility data: natural requests (direct and by intent), requests for things that are not there, and first-step tasks.

## An earlier reading (00:50 EST)

Rising: mixed-size training (generated hits on the report set 73.4 -> 81.6% at 1280 px and 51.9 -> 75.9% at 896 px); tool calls by joint training (written correctly 28 -> 99% on the 9B, 37 -> 99% on the 4B); the 4B repair (lab score 0.14 -> 0.70 in half an hour). Fallen: skipping blank areas; training the head together with the trunk; opening all layers (noisy).

Write-ups of single trials: [SKIP_BLANK.md](SKIP_BLANK.md) (blank areas), [EXTREME_TRIALS.md](EXTREME_TRIALS.md) (vision transplant, coarse-to-fine coordinates, coordinate bias), [RESOLUTION_BY_EYE.md](RESOLUTION_BY_EYE.md) (input size).
