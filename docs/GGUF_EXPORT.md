# Exporting an edited Bonsai 2 model to GGUF

Worked out and verified on 2026-11-14 on a 13-inch M4 MacBook, against `Ternary-Bonsai-2-9B-Q2_0.gguf`, the `Ternary-Bonsai-2-9B-mlx-2bit` pack and PrismML's llama.cpp fork at commit `6447906` (Metal build). Tool: `weights/export_gguf.py`. Tests: `tests/test_export_gguf.py`.

## Result in one paragraph

The GGUF holds exactly the pack's language model: the same ternary matrices in the same rotated basis, row for row and input for input, with the same float16 multipliers. An edit made on the pack is therefore a byte-level edit of the GGUF. The tool copies the base GGUF and overwrites only the multiplier fields (and the code fields, when the patch changes codes) of the affected blocks. For `bonsai2-9b-point-v1` that is 93,354,160 bytes in 176 tensors; the other 2.46 GB are untouched. Served by the fork's `llama-server`, the new file gives the same four answers as the patched model in MLX.

## Run it

```bash
PY=~/Bonsai-demo/.venv-vlm/bin/python          # needs numpy only
M=~/Bonsai-demo/models

# export (about 1 to 2 minutes; checks itself before the file gets its name)
$PY weights/export_gguf.py \
    --base  $M/bonsai2-gguf/9B/Ternary-Bonsai-2-9B-Q2_0.gguf \
    --patch $M/patches/bonsai2-9b-point-v1.patch.safetensors \
    --out   $M/bonsai2-gguf/Ternary-Bonsai-2-9B-point-v1-Q2_0.gguf

# prove that a base GGUF holds exactly a given pack (20 s)
$PY weights/export_gguf.py --base $M/bonsai2-gguf/9B/Ternary-Bonsai-2-9B-Q2_0.gguf \
    --check-pack $M/Ternary-Bonsai-2-9B-mlx-2bit

# tests (3 s; the last part needs the 9B GGUF and pack and is skipped without them)
$PY tests/test_export_gguf.py
```

The patch is a `.safetensors` file whose tensors have the names and shapes of the pack: `<module>.scales` with `<module>.biases` to change multipliers, `<module>.weight` to change codes, and optionally the small full-precision tensors listed below. The output is written as `<out>.partial`, compared with the base and with the patch, and renamed only if every check passes. An existing `--out` is not replaced without `--force`.

The file written on this Mac: `~/Bonsai-demo/models/bonsai2-gguf/Ternary-Bonsai-2-9B-point-v1-Q2_0.gguf`, 2,556,640,128 bytes, sha256 `f8eb2f74a432dbae89aeb70fb5feb82a3a1434bf957b42e29eb6d85e0a0cc7e0`.

## The correspondence

### Names

| Pack (`language_model.` + ...) | GGUF tensor | Rows |
|---|---|---|
| `lm_head` | `output.weight` | same order |
| `model.embed_tokens` | `token_embd.weight` | same order |
| `model.layers.N.mlp.gate_proj`, `up_proj`, `down_proj` | `blk.N.ffn_gate.weight`, `ffn_up`, `ffn_down` | same order |
| `model.layers.N.self_attn.q_proj`, `k_proj`, `v_proj`, `o_proj` | `blk.N.attn_q.weight`, `attn_k`, `attn_v`, `attn_output` | same order |
| `model.layers.N.linear_attn.in_proj_qkv` | `blk.N.attn_qkv.weight` | q and k rows same; the value rows re-ordered (below) |
| `model.layers.N.linear_attn.in_proj_z` | `blk.N.attn_gate.weight` | all rows re-ordered (below) |
| `model.layers.N.linear_attn.out_proj` | `blk.N.ssm_out.weight` | same order, and its inputs keep the pack's order too |

A module's four pack tensors map as follows: `.weight` (codes) and `.scales` go into the blocks of the GGUF tensor; `.biases` is implied (always minus the multiplier); `.signs` is not stored per tensor in the GGUF but once per input width, in the metadata arrays `prism.hadamard.sign_widths` and `prism.hadamard.sign_values` (9B: one vector for width 4096 and one for 12288). All 202 pack sign vectors equal the vector of their width.

### Layout of a packed tensor

- GGUF dimensions are `[inputs, rows]`. The data is stored row after row; inside a row the inputs are in order and cut into consecutive blocks.
- **Basis.** The numbers are the rotated-basis matrix `W_q`, as in the pack. The runtime computes `y = W_q · H(signs · x)` (`build_hadamard_input` in `src/llama-graph.cpp`), with `H` the normalised Walsh-Hadamard transform over blocks of `prism.hadamard.block_size` inputs (4096 for the 9B). For the embedding table it applies the inverse after the lookup. Nothing is folded back to the original basis.
- **Codes.** A 2-bit field holds the pack's code unchanged: ternary value + 1, so 0 is minus the multiplier, 1 is zero, 2 is plus the multiplier. The value 3 never occurs. No sign flip anywhere; every multiplier in the pack is positive.
- **Multipliers.** The block's float16 `d` is the pack's float16 scale, bit for bit.

| Type | ggml id | Inputs per block | Block bytes | Multiplier at | Codes |
|---|---|---|---|---|---|
| `Q2_0` | 42 | 64 | 18 | bytes 0..1 | bytes 2..17, 4 codes per byte, lowest bits first |
| `PQ2_0` | 142 | 128 | 34 | bytes 0..1 | bytes 2..33, same packing |
| `PTQ1_0` | 143 | 128 | 28 | bytes 26..27 | bytes 0..25, 5 base-3 digits per byte (see `ptq1_encode`) |

- **A 128-input group and a block.** The 9B file on this Mac is `Q2_0`, so one pack group of 128 inputs is two consecutive blocks that carry the same multiplier: group `g` of a row is blocks `2g` and `2g+1`. In `PQ2_0` and `PTQ1_0` a group is one block.
- For `Q2_0` and `PQ2_0` the code bytes of a row are the bytes of the pack's little-endian uint32 words as they are (16 codes per word, lowest bits first, is the same as 4 codes per byte, lowest bits first). Re-packing codes is a byte copy.

### The one re-ordering: value heads of linear attention

The linear-attention layers have 16 key heads and 32 value heads of 128 rows each (2 value heads per key head). The pack keeps the value heads grouped by key head (`gdn_activation_layout: grouped`); the GGUF keeps them tiled so the runtime can broadcast:

```
pack order:  k0v0, k0v1, k1v0, k1v1, ..., k15v0, k15v1
GGUF order:  k0v0, k1v0, ..., k15v0, k0v1, k1v1, ..., k15v1

GGUF value row (r·16 + k)·128 + d   =   pack value row (k·2 + r)·128 + d        r = 0..1, k = 0..15, d = 0..127
```

This applies to the last 4096 rows of `attn_qkv` and to all rows of `attn_gate`. `ssm_out` reads the value heads as inputs, in the rotated basis where they cannot be permuted, so its inputs stay grouped and the runtime permutes the activation instead (`prism.hadamard.gdn_v_grouped = true`). The tool reads the head counts from the GGUF (`qwen35.ssm.group_count`, `ssm.time_step_rank`, `ssm.inner_size`); with one value head per key head (the 2B) there is no re-ordering.

### Small full-precision tensors (all float32 in the 9B file)

| Pack | GGUF | Relation |
|---|---|---|
| `model.norm.weight` | `output_norm.weight` | equal |
| `layers.N.input_layernorm.weight`, `post_attention_layernorm.weight` | `blk.N.attn_norm.weight`, `post_attention_norm.weight` | equal (both already hold the transformers value plus 1) |
| `layers.N.self_attn.q_norm.weight`, `k_norm.weight` | `blk.N.attn_q_norm.weight`, `attn_k_norm.weight` | equal |
| `layers.N.linear_attn.norm.weight` | `blk.N.ssm_norm.weight` | equal |
| `layers.N.linear_attn.A_log` | `blk.N.ssm_a` | `-exp(A_log)`, value heads tiled |
| `layers.N.linear_attn.dt_bias` | `blk.N.ssm_dt.bias` | value heads tiled |
| `layers.N.linear_attn.in_proj_a.weight`, `in_proj_b.weight` | `blk.N.ssm_alpha.weight`, `ssm_beta.weight` | rows (value heads) tiled |
| `layers.N.linear_attn.conv1d.weight` (C, 4, 1) | `blk.N.ssm_conv1d.weight` (C, 4) | last axis dropped, the 4096 value channels tiled |

The tool writes these too when a patch contains them.

## What the tool refuses

- An offset (`.biases`) that is not minus the multiplier, a code of value 3, non-finite multipliers: the block formats cannot hold them, or the model would stop being ternary.
- `.signs` that differ from the GGUF's sign vector. Signs are shared by all tensors of a width.
- Patch tensors with no place in the language-model GGUF (the vision tower), unless `--ignore-unmapped` is given.
- Shapes that do not fit, a `Q2_0` file in the deprecated layout of 128 inputs per block, an output path that exists.

## What was verified

| Check | How | Result |
|---|---|---|
| Base GGUF equals the pack | `--check-pack`: every packed module decoded from the GGUF and compared with the pack | 202 of 202 modules: multipliers and codes equal bit for bit, both halves of every 128 group carry the pack's multiplier; 202 sign vectors equal; 223 of 225 small tensors equal bit for bit, 2 (`ssm_a`) differ in the last bit of `exp()` |
| Same, independent code | gguf-py's reader for offsets, bit fields picked apart by hand, on an attention projection (`layers.3.self_attn.k_proj`), linear-attention projections (`layers.5.linear_attn.in_proj_qkv`, `in_proj_z`, `out_proj`), MLP projections (`layers.5.mlp.gate_proj`, `down_proj`) and the head (`lm_head`) | every block multiplier and every code equal: `k_proj` 65,536 and 4,194,304; `in_proj_qkv` 524,288 and 33,554,432; `down_proj` 786,432 and 50,331,648; `lm_head` 15,892,480 and 1,017,118,720. `in_proj_qkv` and `in_proj_z` match only with the re-ordering above |
| Code re-packing | In the test: four pack modules written into empty buffers | the same bytes as the base GGUF (1.2 MB, 9.4 MB, 14.2 MB and 286 MB) |
| Whole pack exported onto the base | `--patch <pack>/model.safetensors --ignore-unmapped`: all 202 code and multiplier sets and all 225 small tensors rewritten | output differs from the base in 2 bytes, the two `ssm_a` last bits |
| Block codecs against the fork | A C harness linked to the fork's `libggml-base.a` (`quantize_row_*_ref`, `dequantize_row_*`) on random ternary rows, for `Q2_0`, `PQ2_0` and `PTQ1_0` | writer bytes equal the C quantizer's bytes; the C dequantizer returns the weights from the writer's bytes |
| Other layouts end to end | In the test: made-up GGUF files of each of the three types, edited and compared with a reference encoding written one value at a time | byte-exact for all three |
| The new file against the base | The tool's own check, and separately gguf-py's reader plus numpy | same size; metadata and tensor table (11,039,616 bytes) identical; 251 unpatched tensors identical; 93,354,160 bytes differ, all in multiplier fields of the 176 patched tensors; codes of those tensors identical to the base |
| The new file against the patch | Decode all 176 tensors | every multiplier equals the patch bit for bit (44,729,051 of 55,197,696 group multipliers differ from the base) |
| Reproducible | Second export with the final tool | same sha256 |

### Behaviour

`llama-server` of the fork, one model at a time, `-ngl 99 -fa on -c 8192 -np 1 --jinja --image-max-tokens 4096 --temp 0`, thinking off, the vision file described below. Screenshots from `playground/samples/` shrunk to a long side of 1280 px (LANCZOS, PNG), the prompt `PROMPT` of `playground/server.py`, image first then text in one user message, `temperature 0`, `max_tokens 24`. A 1280 x 800 screenshot is 1,000 image tokens, so the cap does not shrink it.

| Screenshot and instruction | Base GGUF | New GGUF | MLX original / patched |
|---|---|---|---|
| `dev-20261114-000000.png`, Put the cursor on the email with the subject "Re: Candidate debrief" | [269, 226] | [273, 246] | [269, 226] / [273, 246] |
| `dev-20261114-000010.png`, Point at the "Save changes" button | [450, 563] | [545, 522] | [450, 563] / [545, 522] |
| `dev-20261114-000012.png`, Point at the tab that says Billing queue | [106, 106] | [68, 116] | [102, 102] / [68, 116] |
| `dev-20261114-000013.png`, Can you find the "Town hall" event? | [206, 856] | [206, 836] | [206, 856] / [206, 836] |

Seven of the eight answers equal the MLX runtime's exactly; the eighth is 4 units away. The new file moves every answer the way the patch does in MLX.

### Speed on the M4 MacBook (16 GB, Metal, other apps open)

Same server settings, new GGUF; the base is the same within noise.

| | Prompt tokens read | Prompt speed | Time to the answer |
|---|---|---|---|
| One screenshot, 1280 x 800 | 1,094 | 104 tokens/s (the time includes about 3 s of image preparation and vision tower before the first token is read) | 10.9 s |
| One screenshot, 1280 x 720 | 967 | 106 tokens/s | 9.6 s |
| A different question about the same screenshot | 964 (nothing reused) | 99 tokens/s | 10.1 s |
| The identical request again, even after other screenshots | 4 (1,090 reused) | | 0.5 s |
| Answer | 11 tokens | 27.5 tokens/s | 0.36 s |

The server loads in 4 to 6 s with the files in the disk cache and uses 3.5 GB of memory.

**The image prefix is not reused for a new question in this prompt layout.** Qwen3.5 has recurrent (linear-attention) layers, so the server cannot roll its state back to an arbitrary token; it can only return to a checkpoint. It makes checkpoints at the start of a user message and near the end of the prompt, 4 tokens before it (`tools/server/server-context.cpp`). With image and instruction in one message no checkpoint lies between the image and the instruction, so for a different instruction the image is encoded and read again. Only an identical prompt is restored.

Putting the screenshot in its own user message, followed by a second user message with the instruction, places a checkpoint right after the image:

| Split into two user messages | Prompt tokens read | Time to the answer |
|---|---|---|
| First question about a screenshot | 972 to 1,099 | 10.1 to 12.3 s |
| Every further question about it | 82 (887 to 1,007 reused) | 1.0 to 1.3 s |

That is a different prompt from the one the models were measured with (five extra tokens between image and text). On the four cases above the new model gave the same four answers; the original model changed three of its four ([326, 226], [468, 563], [106, 106], [246, 856]). Use it only where a fast follow-up matters more than matching the measured prompt.

## The vision file

Images need a second GGUF, the vision tower ("mmproj"). PrismML publishes one per model, but none was on this Mac, so the checks above used one built from the pack's own vision tower:

```bash
$PY weights/export_mmproj.py --pack $M/Ternary-Bonsai-2-9B-mlx-2bit --out /some/dir/Ternary-Bonsai-2-9B-mmproj-F16.gguf
```

20 s, 0.92 GB, 334 tensors. It follows `conversion/qwen3vl.py` of the fork (matrices in the pack's float16, vectors and the position table in float32) and needs the fork's `gguf-py`. That it is right is shown by the table above: with it, the base GGUF reproduces the MLX answers. It has not been compared with PrismML's published file. The file made for the checks was deleted afterwards to save disk space; the vision tower is the same for the original and for every edited language model, so one file serves both.

Do not add `--image-min-tokens 1024`, which the server suggests at start-up: it would enlarge a 1280 px screenshot and move the answers away from the measured ones.

## Not covered

- **Edits to the vision tower.** They belong in the vision file; `export_mmproj.py` does not apply patches.
- **`PQ2_0` and `PTQ1_0` on real files.** No such file was readable here. The two layouts are verified against the fork's C codecs and on made-up files, including the row re-ordering, but not on a published file and not through the runtime.
- **Other sizes.** The 2B, 4B and 27B `Q2_0` files parse and expose the same structure, but were not compared with their packs (the packs are not on this Mac). The 2B and 4B have no separate `output.weight` (their head is the embedding table, `prism.hadamard.tied_output`), so a patch to `lm_head` has no place there. The 27B stores `ssm_alpha` and `ssm_beta` as bfloat16, which the tool does not write.
- **Metadata.** `general.name` is copied from the base, so the new file still calls itself `Ternary-Bonsai-2-9B`. Tell the files apart by name or hash.
- **A changed code through the runtime.** Code re-packing is proven at the byte level (it reproduces the base file), but no patch with changed codes exists yet to run.
- **LM Studio.** The new file was run with the fork's `llama-server` only.
