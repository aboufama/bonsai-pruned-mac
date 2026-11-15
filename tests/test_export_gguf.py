"""weights/export_gguf.py: block codecs, a whole export on small made-up files of each block layout,
and re-packing real pack modules into the bytes of the real base GGUF (skipped if the files are absent).

    ~/Bonsai-demo/.venv-vlm/bin/python tests/test_export_gguf.py
"""
import json
import os
import struct
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights"))
import export_gguf as E  # noqa: E402
import pack  # noqa: E402

rng = np.random.default_rng(20261114)


# ---- reference encoders, written from ggml-quants.c one value at a time (independent of the numpy codecs)

def ref_block(kind, codes, scale):
    d = np.float16(scale).tobytes()
    if kind in (E.Q2_0, E.PQ2_0):
        qs = bytearray(len(codes) // 4)
        for j, q in enumerate(codes):
            qs[j // 4] |= int(q) << (2 * (j % 4))
        return d + bytes(qs)
    out, x = bytearray(), [int(v) for v in codes]
    for start, width in ((0, 16), (80, 8)):                 # quantize_row_ptq1_0_ref: stages of 16 and 8 bytes
        for m in range(width):
            q = 0
            for n in range(5):
                q = q * 3 + x[start + m + n * width]
            out.append((q * 256 + 242) // 243)
    for h in range(2):
        q = 0
        for m in range(4):
            q = q * 3 + x[120 + h + m * 2]
        out.append((q * 3 * 256 + 242) // 243)
    return bytes(out) + d


def ref_tensor(kind, codes, scales):
    """Bytes of a packed tensor: codes (rows, inputs) in {0,1,2}, scales (rows, inputs/128)."""
    per = E.PACKED[kind][1]
    return b"".join(ref_block(kind, row[a:a + per], srow[a // 128])
                    for row, srow in zip(codes, scales) for a in range(0, codes.shape[1], per))


def tiled_rows(n_rows, n_value_rows, k, per_k):
    """GGUF row -> pack row, by explicit loops: value heads grouped by key head become tiled."""
    hd = n_value_rows // (k * per_k)
    order = list(range(n_rows - n_value_rows))
    for r in range(per_k):
        for key in range(k):
            order += [n_rows - n_value_rows + (key * per_k + r) * hd + d for d in range(hd)]
    return np.array(order)


# ---- 1. codecs

for kind in (E.Q2_0, E.PQ2_0, E.PTQ1_0):
    name, per, size, s_at, c_at = E.PACKED[kind]
    codes = rng.integers(0, 3, size=(5, 512), dtype=np.uint8)
    scales = (rng.random((5, 4)) * 0.05 + 0.001).astype(np.float16)
    view = np.zeros((5, 512 // per, size), dtype=np.uint8)
    E.write_scales(view, kind, scales)
    E.write_codes(view, kind, E.pack_codes(codes))
    assert view.tobytes() == ref_tensor(kind, codes, scales), name
    assert np.array_equal(E.read_codes(view, kind, 0, 5), E.pack_codes(codes)), name
    assert np.array_equal(E.read_scales(view, kind, 0, 5), np.repeat(scales, 128 // per, axis=1)), name
    print(f"{name}: writer equals the reference encoder, reader inverts it")

# one PTQ1_0 block produced by the fork's own quantize_row_ptq1_0_ref (commit 6447906) for these codes and scale 0.0125
c = ((np.arange(128) * 7 + (np.arange(128) // 5) ** 2) % 3).astype(np.uint8)
want = bytes.fromhex("3192b622663194bb3194bb3090b010314569af2fa2af296c465c6622")
assert E.ptq1_encode(c[None])[0].tobytes() + np.float16(0.0125).tobytes() == want
assert np.array_equal(E.ptq1_decode(np.frombuffer(want[:26], dtype=np.uint8)[None])[0], c)
print("PTQ1_0: equals a block written by the fork's C quantizer")

try:
    E.write_codes(np.zeros((1, 2, 18), dtype=np.uint8), E.Q2_0, np.full((1, 8), 3, dtype=np.uint32))
    raise SystemExit("a code of value 3 was accepted")
except ValueError:
    pass


# ---- 2. a whole export on made-up files

def gguf_file(path, meta, tensors):
    """Minimal GGUF v3 writer. meta: [(key, type id, value)]; tensors: [(name, dims, type id, bytes)]."""
    def s(text):
        raw = text.encode()
        return struct.pack("<Q", len(raw)) + raw
    out = b"GGUF" + struct.pack("<IQQ", 3, len(tensors), len(meta))
    for key, kind, value in meta:
        out += s(key) + struct.pack("<I", kind)
        if kind == 8:
            out += s(value)
        elif kind == 4:
            out += struct.pack("<I", value)
        else:                                              # array of int32
            out += struct.pack("<IQ", 5, len(value)) + np.asarray(value, dtype="<i4").tobytes()
    at, data = 0, b""
    for name, dims, kind, raw in tensors:
        out += s(name) + struct.pack("<I", len(dims)) + b"".join(struct.pack("<Q", d) for d in dims) + struct.pack("<IQ", kind, at)
        data += raw + b"\0" * (-len(raw) % 32)
        at = len(data)
    out += b"\0" * (-len(out) % 32)
    with open(path, "wb") as f:
        f.write(out + data)


def safetensors_file(path, tensors):
    header, data = {}, b""
    for name, arr in tensors.items():
        raw = np.ascontiguousarray(arr).tobytes()
        header[name] = {"dtype": {"float16": "F16", "float32": "F32", "uint32": "U32"}[str(arr.dtype)],
                        "shape": list(arr.shape), "data_offsets": [len(data), len(data) + len(raw)]}
        data += raw
    head = json.dumps(header).encode()
    with open(path, "wb") as f:
        f.write(struct.pack("<Q", len(head)) + head + data)


K, PER_K, HD = 2, 2, 8                      # 2 key heads, 2 value heads per key head, 8 rows per head
INNER, WIDTH = K * PER_K * HD, 256
SIGNS = np.where(rng.random(WIDTH) > 0.5, 1, -1)
PACK_NAMES = {"output.weight": "language_model.lm_head", "blk.0.ffn_gate.weight": "language_model.model.layers.0.mlp.gate_proj",
              "blk.0.attn_qkv.weight": "language_model.model.layers.0.linear_attn.in_proj_qkv",
              "blk.0.attn_gate.weight": "language_model.model.layers.0.linear_attn.in_proj_z",
              "blk.0.ssm_out.weight": "language_model.model.layers.0.linear_attn.out_proj"}
ROWS = {"output.weight": 12, "blk.0.ffn_gate.weight": 9, "blk.0.attn_qkv.weight": 2 * K * HD + INNER,
        "blk.0.attn_gate.weight": INNER, "blk.0.ssm_out.weight": 7}
VALUE_ROWS = {"blk.0.attn_qkv.weight": INNER, "blk.0.attn_gate.weight": INNER}


def order_of(target):
    n = VALUE_ROWS.get(target, 0)
    return tiled_rows(ROWS[target], n, K, PER_K) if n else np.arange(ROWS[target])


with tempfile.TemporaryDirectory() as tmp:
    for kind in (E.Q2_0, E.PQ2_0, E.PTQ1_0):
        name = E.PACKED[kind][0]
        # the "pack": codes and multipliers of each module, in the pack's row order
        model = {t: (rng.integers(0, 3, size=(r, WIDTH), dtype=np.uint8), (rng.random((r, WIDTH // 128)) * 0.05 + 0.001).astype(np.float16))
                 for t, r in ROWS.items()}
        a_log = rng.standard_normal(K * PER_K).astype(np.float32)
        norm = rng.standard_normal(WIDTH).astype(np.float32)
        other = rng.integers(0, 256, size=77, dtype=np.uint8).tobytes()
        heads = tiled_rows(K * PER_K, K * PER_K, K, PER_K)
        tensors = [(t, [WIDTH, r], kind, ref_tensor(kind, model[t][0][order_of(t)], model[t][1][order_of(t)])) for t, r in ROWS.items()]
        tensors.insert(2, ("blk.0.attn_norm.weight", [WIDTH], E.F32, norm.tobytes()))
        tensors.insert(4, ("blk.0.ssm_a", [K * PER_K], E.F32, (-np.exp(a_log))[heads].tobytes()))
        tensors.append(("some.other.tensor", [77], 24, other))            # a type the tool knows nothing about
        meta = [("general.architecture", 8, "qwen35"), ("qwen35.ssm.group_count", 4, K), ("qwen35.ssm.time_step_rank", 4, K * PER_K),
                ("qwen35.ssm.inner_size", 4, INNER), ("prism.hadamard.sign_widths", 9, [WIDTH]), ("prism.hadamard.sign_values", 9, SIGNS)]
        base, out, patch = (os.path.join(tmp, f"{name}.{x}") for x in ("base.gguf", "new.gguf", "patch.safetensors"))
        gguf_file(base, meta, tensors)

        # the edit: new multipliers for three modules, new codes for two of them, two full-precision tensors
        new = {t: [codes.copy(), scales.copy()] for t, (codes, scales) in model.items()}
        edit = {}
        for t in ("output.weight", "blk.0.attn_qkv.weight", "blk.0.attn_gate.weight"):
            new[t][1] = (new[t][1].astype(np.float32) * (1 + 0.02 * rng.standard_normal(new[t][1].shape))).astype(np.float16)
            edit[PACK_NAMES[t] + ".scales"] = new[t][1]
            edit[PACK_NAMES[t] + ".biases"] = -new[t][1]
        for t in ("blk.0.attn_qkv.weight", "blk.0.ssm_out.weight"):
            new[t][0] = rng.integers(0, 3, size=new[t][0].shape, dtype=np.uint8)
            edit[PACK_NAMES[t] + ".weight"] = E.pack_codes(new[t][0])
        edit[PACK_NAMES["output.weight"] + ".signs"] = SIGNS.astype(np.float32)
        new_a_log, new_norm = a_log + 0.1, norm * 1.5
        edit["language_model.model.layers.0.linear_attn.A_log"] = new_a_log
        edit["language_model.model.layers.0.input_layernorm.weight"] = new_norm
        safetensors_file(patch, edit)
        report = E.export(base, patch, out, log=lambda *_: None)
        assert (report["rewritten"], report["scales"], report["codes"], report["dense"]) == (6, 3, 2, 2), report

        # the new file must be the reference encoding of the edited model, and nothing else may have moved
        expect = [(t, d, k, ref_tensor(kind, new[t][0][order_of(t)], new[t][1][order_of(t)]) if t in new else raw) for t, d, k, raw in tensors]
        expect[2] = (*expect[2][:3], new_norm.tobytes())
        expect[4] = (*expect[4][:3], (-np.exp(new_a_log))[heads].tobytes())
        gguf_file(base + ".expected", meta, expect)
        assert open(out, "rb").read() == open(base + ".expected", "rb").read(), name

        # what the GGUF cannot hold is refused, and no file is left behind
        for bad, why in (({"language_model.lm_head.scales": new["output.weight"][1], "language_model.lm_head.biases": new["output.weight"][1]}, "offset"),
                         ({"language_model.lm_head.signs": -SIGNS.astype(np.float32)}, "signs"),
                         ({"language_model.lm_head.weight": np.full((12, WIDTH // 16), 0xFFFFFFFF, dtype=np.uint32)}, "code 3"),
                         ({"vision_tower.merger.norm.weight": norm}, "no place"),
                         ({"language_model.lm_head.scales": new["output.weight"][1][:5]}, "shape")):
            safetensors_file(patch, bad)
            try:
                E.export(base, patch, out + ".bad", log=lambda *_: None)
                raise SystemExit(f"{name}: accepted a patch with a bad {why}")
            except ValueError:
                assert not os.path.exists(out + ".bad") and not os.path.exists(out + ".bad.partial")
        print(f"{name}: export of multipliers, codes and full-precision tensors is byte-exact; bad patches are refused")


# ---- 3. the real files: pack modules re-packed from nothing must be the bytes of the base GGUF

HOME = os.environ.get("BONSAI_HOME", os.path.expanduser("~/Bonsai-demo"))
GGUF = os.path.join(HOME, "models", "bonsai2-gguf", "9B", "Ternary-Bonsai-2-9B-Q2_0.gguf")
PACK = os.path.join(HOME, "models", "Ternary-Bonsai-2-9B-mlx-2bit", "model.safetensors")
if os.path.isfile(GGUF) and os.path.isfile(PACK):
    g = E.Gguf(GGUF)
    header, start = pack.read_header(PACK)
    mm = np.memmap(GGUF, dtype=np.uint8, mode="r")
    for module in ("language_model.model.layers.3.self_attn.k_proj",        # attention projection
                   "language_model.model.layers.5.linear_attn.in_proj_qkv",  # attention projection with re-ordered value heads
                   "language_model.model.layers.5.mlp.down_proj",            # MLP projection, 12288 inputs
                   "language_model.lm_head"):                                # output head
        target, _, rows, _ = E.resolve(module + ".scales")
        t = g.tensors[target]
        order = E.row_order(t["dims"][1], rows, g.heads())
        scales = pack.read_tensor(PACK, header, start, module + ".scales")
        words = pack.read_tensor(PACK, header, start, module + ".weight")
        have = E.blocks(mm, t)
        again = np.zeros(have.shape, dtype=np.uint8)
        E.write_scales(again, t["type"], scales, order)
        E.write_codes(again, t["type"], words, order)
        assert np.array_equal(again, have), module
        # and an independent decode of the file: multiplier bytes and 2-bit fields picked apart here
        n = min(have.shape[0], 512)
        idx = np.arange(n) if order is None else order[:n]
        d = np.ascontiguousarray(have[:n, :, :2]).view(np.float16).reshape(n, -1)
        q = ((np.ascontiguousarray(have[:n, :, 2:])[..., None] >> np.array([0, 2, 4, 6], dtype=np.uint8)) & 3).reshape(n, -1)
        assert np.array_equal(d, np.repeat(np.asarray(scales)[idx], 2, axis=1))
        assert np.array_equal(q, pack.unpack_codes(np.asarray(words)[idx]))
        print(f"{module} -> {target}: {have.shape[0]} rows x {have.shape[1]} blocks re-packed to the same {have.size:,} bytes")
else:
    print("real files not found, skipped the re-packing test against the base GGUF")
print("ok")
