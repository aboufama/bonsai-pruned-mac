# The Bonsai 2 weight format, and loading it in PyTorch

Worked out on 2026-11-14 from the `prism-ml/Ternary-Bonsai-2-9B-mlx-2bit` pack and `mlx-vlm` 0.7.8's loader (`mlx_vlm/models/prism_hadamard_qwen35`). Verified numerically against MLX; see the end.

## What is in the pack

`model.safetensors` (3.46 GB for the 9B) holds 1,366 tensors:

- **202 packed modules** in the language model: every MLP projection (`up_proj`, `gate_proj`, `down_proj`, 32 layers), the attention projections of the 8 full-attention layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`), the three large projections of the 24 linear-attention layers (`in_proj_qkv`, `in_proj_z`, `out_proj`), plus `embed_tokens` and `lm_head`. The embedding and the output head are stored separately and are not identical.
- **Full-precision language-model parts** (float32): all normalisation weights, and in each linear-attention layer `A_log`, `dt_bias`, `conv1d.weight`, `in_proj_a.weight`, `in_proj_b.weight`.
- **The whole vision tower** (float16): 27 blocks of width 1152 and the merger that maps to the language model's width of 4096.

`config.json` lists the packed modules under `modules`, each with a `path` and a rotation `block` (4096 for every module in the 9B; 512 in the 2B and 4B).

## A packed module

For a weight matrix of shape (rows, width):

| Tensor | Type and shape | Meaning |
|---|---|---|
| `weight` | uint32, (rows, width/16) | 2-bit codes, 16 per word, lowest bits first |
| `scales` | float16, (rows, width/128) | one scale per group of 128 consecutive inputs |
| `biases` | float16, (rows, width/128) | affine offset; always equal to `-scales` |
| `signs` | float32, (width,) | a fixed vector of +1 and -1 |

The stored weight is `code * scale + bias = (code - 1) * scale`, with code in {0, 1, 2}: exactly ternary, about a third of each value. So about a third of all weights are already zero.

The layer does not apply that matrix to its input directly. It first rotates the input:

```
x' = H(signs * x)        normalised Walsh-Hadamard transform over consecutive blocks of `block` inputs
y  = W_q x'
```

The embedding table does the inverse on its output: look up the row, apply H, multiply by `signs`.

## Folding to an ordinary dense layer

H is symmetric and orthogonal, so the same layer is an ordinary linear layer in the model's original basis:

```
W_dense = H(W_q) * signs      (H applied along each row, block by block)
```

The embedding uses the identical formula per row. This is what `weights/convert_to_hf.py` writes: a standard `Qwen3_5ForConditionalGeneration` checkpoint (float16, about 18 GB) that loads with stock transformers and sits in the same basis as Qwen3.5-9B and UI-Venus-2-9B. That makes tensor-by-tensor and activation-by-activation comparison with the full-precision models direct.

The dense checkpoint is for analysis and comparison. Training must act on the packed form (codes, scales, full-precision parts) so the result can be written back as a ternary file.

## Name and layout differences from the transformers checkpoint

| Pack (MLX layout) | transformers |
|---|---|
| `language_model.model.X` | `model.language_model.X` |
| `language_model.lm_head.*` | `lm_head.weight` |
| `vision_tower.X` | `model.visual.X` |
| `conv1d.weight` (C, K, 1) | (C, 1, K) |
| `patch_embed.proj.weight` (O, T, H, W, C) | (O, C, T, H, W) |
| `input_layernorm`, `post_attention_layernorm`, final `norm`, `q_norm`, `k_norm` weights | pack value minus 1 (transformers computes `x * (1 + w)`) |
| `linear_attn.norm.weight` | unchanged |

The Qwen3.5-9B checkpoint also carries a small draft head (`mtp.*`) that the pack does not ship; the converted config sets `mtp_num_hidden_layers` to 0.

## Verification

On `layers.3.self_attn.k_proj` of the 9B pack, comparing `weights/pack.py` (numpy) with MLX:

| Check | Result |
|---|---|
| Codes take only the values 0, 1, 2 | yes (22,064 / 21,476 / 21,996 in the first 16 rows) |
| `biases == -scales` | yes |
| Dequantised weights vs `mx.dequantize` | max difference 0.0 |
| Walsh-Hadamard transform vs `mx.hadamard_transform` | max difference 0.0 |
| Folded dense layer vs the runtime's rotate-then-multiply | max difference 2.7e-7 on outputs of size about 0.5 |

The end-to-end check (the converted checkpoint giving the same pointing answers as llama.cpp) is recorded in [../FINDINGS.md](../FINDINGS.md) once run.

## Sizes of the trainable levers (9B)

- Scales: one per 128 weights, about 70 million numbers.
- Full-precision language-model parts: a few million.
- Vision tower and merger: about 0.9 GB in float16, entirely full precision.
- Ternary codes: about 9 billion.
