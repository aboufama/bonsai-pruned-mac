# The weight lab

A from-scratch toolkit for editing Bonsai's weights directly and seeing the effect within seconds. Code in `weightlab/`; it runs on the Spark. Built 2026-11-14.

## The idea

Bonsai 2 9B has two full-precision relatives with exactly the same architecture: its parent Qwen3.5-9B and the computer-use fine-tune UI-Venus-2-9B. Once Bonsai's ternary layers are folded into ordinary matrices ([WEIGHTS.md](WEIGHTS.md)), all three models live in the same coordinates. That allows three things most weight-editing work cannot do:

1. Compare Bonsai with a known-good model activation by activation and find where they part ways.
2. Put any piece of the good model into Bonsai and see what that fixes.
3. Aim a ternary layer at a dense target and re-fit it without leaving the ternary format.

## Pieces

| File | Role |
|---|---|
| `ternary.py` | `TernaryLinear`: a Bonsai layer as codes in {-1, 0, +1}, per-group scales and its rotation. Forward either through a cached dense fold (fast) or exactly as the runtimes do (for training). `attach_ternary` converts a loaded dense checkpoint; `export_pack` writes an MLX pack back. |
| `core.py` | `Lab`: loads the models, serves data, measures, swaps in the parent's weights, records notes and a journal. `Edit`: reversible ternary changes. |
| `fast.py` | `FastEval`: scores an edit by restarting from cached layer boundaries. |
| `kernel.py`, `client.py` | A persistent Python session with the lab loaded, driven over a local socket. |

## The session

Models stay in GPU memory between experiments, so an experiment costs seconds, not a reload.

```bash
# on the Spark, once
cd ~/bonsai && nohup ./venv/bin/python -m weightlab.kernel > lab/kernel.log 2>&1 &

# run code in it
./venv/bin/python weightlab/client.py exec "print(lab.stack)"
./venv/bin/python weightlab/client.py run experiment.py
./venv/bin/python weightlab/client.py status | interrupt | stop

# from another machine ($BONSAI_HOST is the ssh name of the GPU machine)
ssh "$BONSAI_HOST" '~/bonsai/venv/bin/python ~/bonsai/weightlab/client.py -' < experiment.py
```

Variables persist between requests. `lab` is preloaded. Every request and its output are saved under `~/bonsai/lab/cells/`, so the complete history of what was run against the weights can be replayed.

## Measuring

| Call | What it gives |
|---|---|
| `lab.data("ssv2", n=50, max_side=1280, offset=0)` | Evenly spaced samples with exact target boxes. A different `offset` gives a disjoint set. |
| `lab.score(model, samples)` | Generates real answers: accuracy, median distance, last-digit counts. Slow; use to confirm. |
| `lab.digits(model, samples)` | Teacher-forced: appends the correct answer and reads the probability the model gives to acceptable digits. One pass, no sampling. |
| `lab.hidden(model, samples, where)` | Residual-stream activations at the answer positions, the last prompt position, or averaged over the image. |
| `lab.diff(samples, "B", "P", where)` | Per layer, how far Bonsai's activations are from the parent's. |
| `with lab.swap(predicate):` | Inside the block Bonsai uses the parent's weights for the matching tensors. |

The teacher-forced numbers:

- `p_ok_hundreds`, `p_ok_tens`, `p_ok_units`: the probability, at each digit of each coordinate, of a digit that keeps the point inside the box, given that the more significant digits are right. Probabilities are taken over the ten digit tokens only, so they do not depend on habits such as a space after the comma.
- `p_hit`: the implied probability that every digit is acceptable. `miss_nll`: its negative log, averaged over samples. Lower is better; this is the default score for accepting an edit.

## Fast evaluation and the cache

An edit to layer L cannot change what layers 0 to L-1 compute. `lab.fast(samples)` runs each sample once and keeps the residual stream entering every second layer and leaving the last. `evaluate(first_layer)` restarts from the nearest boundary before the first edited layer.

Measured on 16 samples at 1280 px (2.1 GB of cache), with another job sharing the GPU:

| Restart from | Time |
|---|---|
| layer 0 (everything) | 10.3 s |
| layer 16 | 5.4 s |
| layer 24 | 3.1 s |
| layer 30 | 1.1 s |
| output head only | 0.56 s |

All five give the identical score, which checks the cache.

Evaluating a candidate also computes the cache for the state after that edit. If the edit is kept, `commit()` adopts it; if not, it is dropped. So the cache is always warm for the next candidate with no extra work.

Edits to the vision tower or the embeddings invalidate everything; call `warm()` again.

## Editing

```python
e = lab.edit("name")
e.scale(module, factor, rows, groups)      # multiply scales
e.set_scales(module, scales)
e.delete(module, mask)                     # set weights to zero
e.flip(module, rows, cols, codes)          # set individual weights to -1, 0 or +1
e.refit(module, dense_target, "scales")    # least-squares scales toward a dense target, codes kept
e.refit(module, dense_target, "codes")     # also re-choose the codes, optimal per group of 128
e.apply(); e.revert(); e.stats(); e.save()
```

Only codes and scales ever change, so an applied edit can always be written back as a ternary file. `revert()` restores the exact previous state.

`lab.try_edit(edit, [dev, held_out])` applies the edit, scores it on every `FastEval` given, keeps it only if the first improves, and reports the rest. Use a second, disjoint set as a held-out check so that accepted edits are not just fitting the first set.

## Training that stays ternary

`weightlab/distill.py` re-trains a block of Bonsai's layers to do what a teacher's layers do, without leaving the ternary format.

```python
from weightlab.distill import BlockDistiller
D = BlockDistiller(lab, 4, 19, teacher="V")          # "P" parent, "V" UI-Venus
train = lab.data("gen:benchdata/pointing/train_s101", n=3000)
D.save(range(4, 20), "lab/ckpt/orig_L4-19.safetensors")   # so the block can be restored
D.local_error(train[:12])                            # per layer, error against the teacher's output
D.train([4, 5, 6, 7], train, steps=400)              # four layers at once, each on its own target
D.restore("lab/ckpt/orig_L4-19.safetensors")
```

How it works:

- **Target.** Bonsai runs up to the first layer of the block. From that state the teacher's layers run, giving the state after every layer. Each Bonsai layer is trained to produce the teacher's output for that layer. No answer labels are needed, so any screenshot with any instruction is training material.
- **Ternary codes.** Each weight gets a real-valued latent, starting at its current code. The forward pass rounds the latent to -1, 0 or +1 (threshold 0.5); the backward pass treats the rounding as the identity (a straight-through estimator). A code changes when its latent crosses a threshold.
- **Multipliers.** Each group's multiplier is trained through a log-gain that starts at zero.
- **Small full-precision parts** of the layer (normalisation weights, the linear-attention gates and convolution) are trained at a low learning rate. They are full precision in the file format already.
- **Afterwards** `bake()` writes codes and multipliers back, and the layer is an ordinary Bonsai layer: same format, size and speed.
- `inputs="student"` feeds a layer what Bonsai's own trained layers below it produce instead of the teacher's state, and `chain=True` lets gradients flow through the whole group, so layers learn to absorb each other's errors.

Memory: about 3.5 GB per layer in training (latent, gradient, two optimiser moments), which is why layers are trained in groups.

### Three trainers, one format

| Module | What it trains | Signal | Use |
|---|---|---|---|
| `tune.py`, `TaskTuner` | Multipliers only (optionally codes, small parts, head) of chosen layers | The task: probability mass on answer digits that land in the box | Cheapest change; codes untouched |
| `distill.py`, `BlockDistiller` | One layer at a time (codes, multipliers, small parts) | The teacher's output for that layer | Diagnosing single layers; warm starts |
| `e2e.py`, `BlockTrainer` | All layers of a block as a chain | Teacher states as hints, plus the task through Bonsai's frozen top layers | The main repair run |

```python
from weightlab.e2e import BlockTrainer
E = BlockTrainer(lab, 4, 19, teacher="V")
E.open(lr_codes=1e-2)                      # layers 4..19 go into training form
E.train(train, 150, total_steps=600)       # can be called repeatedly
E.score(dev)                               # digit score with the block still open
E.close()                                  # back to ordinary ternary layers
```

What makes a training step affordable:

- **One product instead of twelve stages.** The rotation is done as a single product with the 4096 x 4096 sign matrix (`ternary.rotate`). The staged transform cost about 25,000 small GPU operations per step under autograd.
- **No weight-sized tensors in the graph.** `_RotatedProduct` saves only the layer input and forms the gradients for codes and multipliers directly.
- **Big products in bfloat16**, sums and optimiser state for the small parameters in float32.
- **Codes update themselves.** With `lean`, each ternary matrix applies Adam to its own latents during the backward pass, with both moments in bfloat16: 8 bytes per weight instead of 16, and no stored gradient. The test `tests/test_ternary_grad.py` checks this against `torch.optim.Adam`.

- **Several questions per screenshot.** A training step can ask up to five things about the same screenshot as one conversation (`lab._inputs_multi`). The screenshot's roughly 1,000 tokens are processed once, so this gives several times the supervised answers for about a third more compute. Every answer is still preceded by exactly the tokens it sees in single-question use, which is how the model is scored.

Measured on the Spark with the GPU to ourselves: about 2 s per step for multipliers of 16 layers, 2.8 s with the codes of 16 layers open.

Rules learnt the hard way (FINDINGS.md, section 8):

- Start every continuation gently: a warm-up and a learning rate well below the first run's. Adam's first updates are full-sized whatever the gradient.
- Judge a run at the end of its schedule, or by checkpoints scored on real screens, never by one mid-run number.
- Compare runs on the 159-screen "select" set (`lab.data("ssv2", mod=(8, 1))`), quote the "report" set (`mod=(8, 5)`). Sets of 32 move by 0.05 between equivalent runs.
- Do not pull Bonsai's internal states toward a teacher's. It points in its own representation.

`weightlab/hot.py` reloads edited lab code inside the running session without reloading the models.

`lab.data("gen:<dir>")` reads any output of `bench/pointing/generate.py`; `lab.data("mac:agentnet:train")` and `lab.data("mac:screen2ax_task:test")` read the Mac sets (see [MAC_DATA.md](MAC_DATA.md)). Screenshots are decoded on demand. Train only on the generator's train split; ScreenSpot stays untouched as a test.

## Notes and journal

- `lab.note(subject, text, evidence)` records a finding about a layer, a module or a behaviour. Notes accumulate in `~/bonsai/lab/notes.jsonl` and render to `~/bonsai/lab/ATLAS.md`, the running map of what is known about these weights. A note should always carry its evidence.
- Every score is appended to `~/bonsai/lab/journal.jsonl` together with the stack of edits active at that moment, so any number can be traced to the exact state of the weights.

## Export

- **MLX pack:** `ternary.export_pack(lab.tern, src_pack, out_dir)` writes the current codes and multipliers as an ordinary pack; a patch holding only the changed tensors is a few hundred MB and can be applied to the original pack in memory (see `playground/server.py`).
- **GGUF for the llama.cpp fork:** `weights/export_gguf.py --base <base.gguf> --patch <patch.safetensors> --out <new.gguf>` rewrites only the patched scale fields (and codes, and small full-precision tensors, when a patch has them). Verified bit for bit against the pack and by behaviour: the exported file gives the same four answers as the patched MLX model. Details and limits in [GGUF_EXPORT.md](GGUF_EXPORT.md). `weights/export_mmproj.py` builds the vision file from the pack.

## Not built yet

- Export of edited full-precision parts (normalisation weights, the small projections, the vision connector). Ternary layers export already.
- Background evaluation of a batch of candidate edits while the next ones are being written.
- Activation patching (running Bonsai with one layer's output replaced by the parent's on the same input).
