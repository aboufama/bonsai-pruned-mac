#!/usr/bin/env python
"""Write an edited Ternary Bonsai 2 model as a GGUF file for PrismML's llama.cpp fork.

    export_gguf.py --base BASE.gguf --patch PATCH.safetensors --out NEW.gguf
    export_gguf.py --base BASE.gguf --check-pack PACK_DIR        prove BASE.gguf holds exactly that MLX pack

The patch is a .safetensors file whose tensors carry the names and shapes of the MLX pack
(see docs/WEIGHTS.md): `<module>.scales` and `<module>.biases` to change multipliers, `<module>.weight`
to change the ternary codes, and optionally the small full-precision language-model tensors.
The base GGUF is copied and only the bytes the patch changes are rewritten, so everything else,
metadata and tokenizer included, stays byte-identical. The result is then compared with the base
and with the patch before it gets its final name.

What makes this a byte-level edit (established in docs/GGUF_EXPORT.md): the GGUF holds the same
matrices as the pack, in the same rotated basis, row for row and input for input, as blocks of
64 or 128 inputs that each carry one float16 multiplier and the 2-bit (or base-3) codes. The only
re-ordering is that the value-head rows of the linear-attention layers are stored "tiled" in the
GGUF and "grouped" in the pack.

Needs numpy only. Three block layouts are handled: Q2_0 (ggml type 42, 64 inputs per block),
PQ2_0 (142, 128 inputs) and PTQ1_0 (143, 128 inputs, 5 ternary digits per byte).
"""
import argparse
import mmap
import os
import re
import shutil
import struct
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack  # noqa: E402

F32, F16, Q2_0, PQ2_0, PTQ1_0 = 0, 1, 42, 142, 143
# ggml type -> (name, inputs per block, bytes per block, where the multiplier sits, where the codes sit)
PACKED = {
    Q2_0: ("Q2_0", 64, 18, slice(0, 2), slice(2, 18)),
    PQ2_0: ("PQ2_0", 128, 34, slice(0, 2), slice(2, 34)),
    PTQ1_0: ("PTQ1_0", 128, 28, slice(26, 28), slice(0, 26)),
}
DENSE = {F32: "<f4", F16: "<f2"}
CHUNK = 48 << 20          # bytes of one tensor handled at a time

# Packed modules of one layer: pack name -> (GGUF name, which rows are value heads of linear attention)
MODULES = {
    "mlp.gate_proj": ("ffn_gate", None),
    "mlp.up_proj": ("ffn_up", None),
    "mlp.down_proj": ("ffn_down", None),
    "self_attn.q_proj": ("attn_q", None),
    "self_attn.k_proj": ("attn_k", None),
    "self_attn.v_proj": ("attn_v", None),
    "self_attn.o_proj": ("attn_output", None),
    "linear_attn.in_proj_qkv": ("attn_qkv", "tail"),      # rows are [q, k, v]; only the v rows move
    "linear_attn.in_proj_z": ("attn_gate", "all"),
    "linear_attn.out_proj": ("ssm_out", None),            # its inputs stay grouped; the runtime permutes the activation
}
# Full-precision tensors of one layer: pack name -> (GGUF name, value-head rows, extra step)
SMALL = {
    "input_layernorm.weight": ("attn_norm.weight", None, None),
    "post_attention_layernorm.weight": ("post_attention_norm.weight", None, None),
    "self_attn.q_norm.weight": ("attn_q_norm.weight", None, None),
    "self_attn.k_norm.weight": ("attn_k_norm.weight", None, None),
    "linear_attn.norm.weight": ("ssm_norm.weight", None, None),
    "linear_attn.A_log": ("ssm_a", "heads", "minus_exp"),
    "linear_attn.dt_bias": ("ssm_dt.bias", "heads", None),
    "linear_attn.in_proj_a.weight": ("ssm_alpha.weight", "heads", None),
    "linear_attn.in_proj_b.weight": ("ssm_beta.weight", "heads", None),
    "linear_attn.conv1d.weight": ("ssm_conv1d.weight", "tail", "drop_last_axis"),
}


# ---------------------------------------------------------------- reading a GGUF file

class Gguf:
    """Metadata values of a GGUF file and where each tensor's bytes are."""

    _SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self._buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        self._pos = 0
        if self._buf[:4] != b"GGUF":
            raise ValueError(f"{path} is not a GGUF file")
        self._pos = 4
        version, n_tensors, n_kv = self._take("<I")[0], self._take("<Q")[0], self._take("<Q")[0]
        if version not in (2, 3):
            raise ValueError(f"GGUF version {version} is not supported")
        self.meta = {}
        for _ in range(n_kv):
            key = self._string()
            self.meta[key] = self._value(self._take("<I")[0])
        infos = []
        for _ in range(n_tensors):
            name = self._string()
            dims = [self._take("<Q")[0] for _ in range(self._take("<I")[0])]
            kind, offset = self._take("<I")[0], self._take("<Q")[0]
            infos.append((name, dims, kind, offset))
        align = int(self.meta.get("general.alignment", 32))
        self.data_start = (self._pos + align - 1) // align * align
        self.size = len(self._buf)
        self._buf.close()
        del self._buf
        self.tensors = {}
        for name, dims, kind, offset in infos:
            self.tensors[name] = {"name": name, "dims": dims, "type": kind, "start": self.data_start + offset,
                                  "nbytes": tensor_nbytes(dims, kind)}
        ends = sorted(t["start"] for t in self.tensors.values()) + [self.size]
        for t in self.tensors.values():           # a tensor must end where the next one starts (up to padding)
            if t["nbytes"] is not None:
                room = ends[ends.index(t["start"]) + 1] - t["start"]
                if not t["nbytes"] <= room < t["nbytes"] + align:
                    raise ValueError(f"{t['name']}: expected {t['nbytes']} bytes for its type, the file gives it {room}. "
                                     "A Q2_0 file with 128 inputs per block (the deprecated legacy layout) is not supported.")
        self.arch = self.meta.get("general.architecture", "")

    def _take(self, fmt):
        out = struct.unpack_from(fmt, self._buf, self._pos)
        self._pos += struct.calcsize(fmt)
        return out

    def _string(self):
        n = self._take("<Q")[0]
        s = self._buf[self._pos:self._pos + n]
        self._pos += n
        return s.decode("utf-8", "replace")

    def _value(self, kind):
        if kind in self._SCALAR:
            return self._take(self._SCALAR[kind])[0]
        if kind == 8:
            return self._string()
        if kind == 9:
            item, n = self._take("<I")[0], self._take("<Q")[0]
            if item in self._SCALAR:
                arr = np.frombuffer(self._buf, dtype=self._SCALAR[item], count=n, offset=self._pos).copy()
                self._pos += arr.nbytes
                return arr
            return [self._value(item) for _ in range(n)]
        raise ValueError(f"unknown GGUF value type {kind}")

    def heads(self):
        """(key heads, value heads per key head, rows of all value heads) of the linear-attention layers."""
        k = int(self.meta.get(f"{self.arch}.ssm.group_count", 0))
        v = int(self.meta.get(f"{self.arch}.ssm.time_step_rank", 0))
        inner = int(self.meta.get(f"{self.arch}.ssm.inner_size", 0))
        if not (k and v and inner) or v % k or inner % v:
            raise ValueError("the GGUF does not describe its linear-attention heads")
        return k, v // k, inner

    def signs(self, width):
        """The +1/-1 vector the runtime multiplies an input of this width by before the transform."""
        widths = [int(w) for w in self.meta.get("prism.hadamard.sign_widths", [])]
        values = np.asarray(self.meta.get("prism.hadamard.sign_values", []))
        if width not in widths:
            return None
        at = sum(widths[:widths.index(width)])
        return values[at:at + width]


def tensor_nbytes(dims, kind):
    n = int(np.prod(dims, dtype=np.int64)) if dims else 1
    if kind in PACKED:
        _, per, size, _, _ = PACKED[kind]
        return n // per * size if dims and dims[0] % per == 0 else None
    return n * np.dtype(DENSE[kind]).itemsize if kind in DENSE else None


# ---------------------------------------------------------------- names and row order

def resolve(name):
    """Pack tensor name -> (GGUF tensor name, field, value-head rows, extra step), or None if it has no place.

    field is 'weight', 'scales', 'biases' or 'signs' for a packed module and 'dense' for a full-precision tensor.
    """
    if name.startswith("language_model."):
        name = name[len("language_model."):]
    for prefix, target in (("lm_head.", "output.weight"), ("model.embed_tokens.", "token_embd.weight")):
        if name.startswith(prefix) and name[len(prefix):] in ("weight", "scales", "biases", "signs"):
            return target, name[len(prefix):], None, None
    if name == "model.norm.weight":
        return "output_norm.weight", "dense", None, None
    m = re.fullmatch(r"model\.layers\.(\d+)\.(.+)", name)
    if not m:
        return None
    layer, rest = m.groups()
    if rest in SMALL:
        target, rows, step = SMALL[rest]
        return f"blk.{layer}.{target}", "dense", rows, step
    module, _, field = rest.rpartition(".")
    if module in MODULES and field in ("weight", "scales", "biases", "signs"):
        target, rows = MODULES[module]
        return f"blk.{layer}.{target}.weight", field, rows, None
    return None


def row_order(n_rows, rows, heads):
    """Row i of the GGUF tensor is row row_order(...)[i] of the pack tensor (None: same order).

    The pack keeps the value heads of linear attention grouped by key head, [k0v0, k0v1, k1v0, ...];
    the GGUF keeps them tiled, [k0v0, k1v0, ..., k0v1, k1v1, ...].
    """
    if rows is None:
        return None
    k, per_k, inner = heads
    if per_k == 1:
        return None
    n = k * per_k if rows == "heads" else inner
    if n > n_rows or (rows == "all" and n != n_rows) or (rows == "heads" and n != n_rows):
        raise ValueError(f"{n_rows} rows do not fit {n} value-head rows")
    tiled = np.arange(n).reshape(k, per_k, n // (k * per_k)).transpose(1, 0, 2).reshape(n)
    return np.concatenate([np.arange(n_rows - n), n_rows - n + tiled])


# ---------------------------------------------------------------- block codecs

_POW3 = np.array([81, 27, 9, 3, 1], dtype=np.uint16)


def ptq1_encode(codes):
    """uint8 codes in {0,1,2}, shape (..., 128) -> the 26 code bytes of a PTQ1_0 block (24 qs + 2 qh)."""
    lead = codes.shape[:-1]
    c = codes.astype(np.uint16)
    a = (c[..., :80].reshape(*lead, 5, 16) * _POW3[:, None]).sum(axis=-2)           # byte m holds inputs m + 16 n
    b = (c[..., 80:120].reshape(*lead, 5, 8) * _POW3[:, None]).sum(axis=-2)         # byte m holds inputs 80 + m + 8 n
    h = (c[..., 120:].reshape(*lead, 4, 2) * _POW3[:4, None]).sum(axis=-2)          # 4 digits, first one highest
    q = np.concatenate([a, b, h], axis=-1).astype(np.uint32)
    return ((q * 256 + 242) // 243).astype(np.uint8)


def ptq1_decode(q):
    """The 26 code bytes of PTQ1_0 blocks, shape (..., 26) -> uint8 codes (..., 128)."""
    lead = q.shape[:-1]
    out = np.empty((*lead, 128), dtype=np.uint8)
    for start, stop, at, digits in ((0, 16, 0, 5), (16, 24, 80, 5), (24, 26, 120, 4)):
        width = stop - start
        part = q[..., start:stop].astype(np.uint8)
        for n in range(digits):
            digit = (((part * np.uint8(3 ** n)).astype(np.uint16) * 3) >> 8).astype(np.uint8)   # uint8 product wraps
            out[..., at + n * width:at + (n + 1) * width] = digit
    return out


def pack_codes(codes):
    """uint8 codes (rows, width) -> uint32 words (rows, width/16), lowest bits first (inverse of pack.unpack_codes)."""
    c = codes.reshape(codes.shape[0], -1, pack.CODES_PER_WORD).astype(np.uint32)
    shifts = 2 * np.arange(pack.CODES_PER_WORD, dtype=np.uint32)
    return (c << shifts).sum(axis=-1, dtype=np.uint32)


def blocks(mm, t):
    """A (rows, blocks per row, bytes per block) view of a packed tensor's bytes."""
    _, per, size, _, _ = PACKED[t["type"]]
    n_in, n_rows = t["dims"]
    return mm[t["start"]:t["start"] + t["nbytes"]].reshape(n_rows, n_in // per, size)


def chunks(n_rows, row_bytes):
    step = max(1, CHUNK // max(1, row_bytes))
    return [(a, min(n_rows, a + step)) for a in range(0, n_rows, step)]


def take(arr, order, a, b):
    return np.ascontiguousarray(arr[a:b] if order is None else arr[order[a:b]])


def write_scales(view, kind, scales, order=None):
    """Put pack multipliers, float16 (rows, groups), into the blocks; a group may span several blocks."""
    _, per, size, where, _ = PACKED[kind]
    n_rows, n_blocks = view.shape[:2]
    repeat = n_blocks // scales.shape[1]
    if scales.shape[0] != n_rows or repeat * scales.shape[1] != n_blocks or repeat < 1:
        raise ValueError(f"multipliers of shape {scales.shape} do not fit {n_rows} rows of {n_blocks} blocks")
    for a, b in chunks(n_rows, n_blocks * size):
        s = take(scales, order, a, b).astype("<f2")
        if not np.isfinite(s).all():
            raise ValueError("a multiplier is not finite")
        view[a:b, :, where] = np.repeat(s, repeat, axis=1).view(np.uint8).reshape(b - a, n_blocks, 2)


def write_codes(view, kind, words, order=None):
    """Put pack codes, uint32 words (rows, inputs/16), into the blocks."""
    _, per, size, _, where = PACKED[kind]
    n_rows, n_blocks = view.shape[:2]
    if words.shape != (n_rows, n_blocks * per // pack.CODES_PER_WORD):
        raise ValueError(f"codes of shape {words.shape} do not fit {n_rows} rows of {n_blocks * per} inputs")
    for a, b in chunks(n_rows, n_blocks * size):
        w = take(words, order, a, b).astype("<u4")
        if (w & (w >> 1) & np.uint32(0x55555555)).any():
            raise ValueError("a code has the value 3; a ternary model only uses 0, 1 and 2")
        if kind == PTQ1_0:
            view[a:b, :, where] = ptq1_encode(pack.unpack_codes(w).reshape(b - a, n_blocks, per))
        else:       # 4 codes per byte, lowest bits first: the bytes of the little-endian words as they are
            view[a:b, :, where] = w.view(np.uint8).reshape(b - a, n_blocks, per // 4)


def read_scales(view, kind, a, b):
    """float16 (rows, blocks) multipliers of rows a..b."""
    where = PACKED[kind][3]
    return np.ascontiguousarray(view[a:b, :, where]).view("<f2").reshape(b - a, view.shape[1])


def read_codes(view, kind, a, b):
    """uint32 words (rows, inputs/16) of rows a..b, in the pack's packing."""
    _, per, _, _, where = PACKED[kind]
    raw = np.ascontiguousarray(view[a:b, :, where])
    if kind == PTQ1_0:
        return pack_codes(ptq1_decode(raw).reshape(b - a, -1))
    return raw.reshape(b - a, -1).view("<u4")


def dense_value(arr, t, rows, step, heads):
    """A full-precision pack tensor as the bytes the GGUF tensor holds."""
    a = np.asarray(arr, dtype=np.float32)
    if step == "minus_exp":
        a = -np.exp(a)
    elif step == "drop_last_axis":
        a = a.reshape(a.shape[:-1]) if a.shape[-1] == 1 else a
    order = row_order(a.shape[0], rows, heads) if rows else None
    if order is not None:
        a = a[order]
    if list(a.shape) != list(t["dims"])[::-1]:
        raise ValueError(f"{t['name']}: shape {list(a.shape)} does not fit {list(t['dims'])[::-1]}")
    if t["type"] not in DENSE:
        raise ValueError(f"{t['name']}: type {t['type']} is not a plain float tensor")
    return np.ascontiguousarray(a.astype(DENSE[t["type"]])).view(np.uint8).reshape(-1)


# ---------------------------------------------------------------- planning, writing, checking

def make_plan(g, header, ignore_unmapped=False):
    """Decide what each patch tensor changes. Returns ({GGUF tensor: {field: patch tensor name, ...}}, skipped names)."""
    plan, skipped = {}, []
    for name in sorted(header):
        hit = resolve(name)
        if hit is None or hit[0] not in g.tensors:
            skipped.append(name)
            continue
        target, field, rows, step = hit
        t = g.tensors[target]
        entry = plan.setdefault(target, {"rows": rows, "step": step})
        entry[field] = name
        packed = t["type"] in PACKED
        if (field == "dense") == packed:
            raise ValueError(f"{name}: {target} has ggml type {t['type']}, which this tensor cannot be written to")
    if skipped and not ignore_unmapped:
        raise ValueError(f"{len(skipped)} patch tensor(s) have no place in this GGUF (the vision tower lives in the "
                         f"separate mmproj file): {', '.join(skipped[:4])}{' ...' if len(skipped) > 4 else ''}. "
                         "Pass --ignore-unmapped to leave them out.")
    return plan, skipped


def check_plan(g, patch, header, start, plan):
    """Refuse, before anything is written, what the GGUF cannot hold: a wrong shape, an offset that is not
    minus the multiplier, or other signs."""
    for target, entry in plan.items():
        t = g.tensors[target]
        if t["type"] in PACKED:
            per = PACKED[t["type"]][1]
            n_in, n_rows = t["dims"]
            for field, fits in (("scales", lambda s: len(s) == 2 and s[0] == n_rows and s[1] and (n_in // per) % s[1] == 0),
                                ("weight", lambda s: s == [n_rows, n_in // pack.CODES_PER_WORD])):
                if field in entry and not fits(header[entry[field]]["shape"]):
                    raise ValueError(f"{entry[field]}: shape {header[entry[field]]['shape']} does not fit {target}, "
                                     f"{n_rows} rows of {n_in} inputs")
        if "biases" in entry:
            if "scales" not in entry:
                raise ValueError(f"{entry['biases']}: offsets without multipliers; the GGUF stores one multiplier and no offset")
            s = pack.read_tensor(patch, header, start, entry["scales"])
            b = pack.read_tensor(patch, header, start, entry["biases"])
            for a, z in chunks(s.shape[0], s.shape[1] * 4):
                if not (np.asarray(b[a:z]) == -np.asarray(s[a:z])).all():
                    raise ValueError(f"{entry['biases']} is not minus the multipliers; the GGUF cannot hold that")
        if "signs" in entry:
            want = np.asarray(pack.read_tensor(patch, header, start, entry["signs"]))
            have = g.signs(want.size)
            if have is None or not np.array_equal(want, have):
                raise ValueError(f"{entry['signs']} differs from the sign vector in the GGUF; changing signs is not supported")
        if "dense" in entry and t["nbytes"] is None:
            raise ValueError(f"{target}: unsupported tensor type {t['type']}")


def apply_plan(mm, g, patch, header, start, plan):
    heads = None
    for target, entry in plan.items():
        t = g.tensors[target]
        if "dense" in entry:
            heads = heads or (g.heads() if entry["rows"] else None)
            mm[t["start"]:t["start"] + t["nbytes"]] = dense_value(
                pack.read_tensor(patch, header, start, entry["dense"]), t, entry["rows"], entry["step"], heads)
            continue
        if "scales" not in entry and "weight" not in entry:
            continue
        heads = heads or (g.heads() if entry["rows"] else None)
        order = row_order(t["dims"][1], entry["rows"], heads)
        view = blocks(mm, t)
        if "scales" in entry:
            write_scales(view, t["type"], pack.read_tensor(patch, header, start, entry["scales"]), order)
        if "weight" in entry:
            write_codes(view, t["type"], pack.read_tensor(patch, header, start, entry["weight"]), order)


def count_diff(a, b):
    total = 0
    for at in range(0, a.size, CHUNK):
        total += int(np.count_nonzero(a[at:at + CHUNK] != b[at:at + CHUNK]))
    return total


def verify(base_path, new_path, g, patch, header, start, plan):
    """Compare the new file with the base and with the patch. Returns a report; raises if anything is off."""
    old = np.memmap(base_path, dtype=np.uint8, mode="r")
    new = np.memmap(new_path, dtype=np.uint8, mode="r")
    if old.size != new.size:
        raise AssertionError("the new file has a different size")
    report = {"tensors": len(g.tensors), "rewritten": 0, "scales": 0, "codes": 0, "dense": 0,
              "bytes_changed": 0, "bytes_changed_outside": 0}
    heads, at = None, 0
    for target in sorted(plan, key=lambda n: g.tensors[n]["start"]):
        entry, t = plan[target], g.tensors[target]
        if not ({"dense", "scales", "weight"} & set(entry)):
            continue
        report["bytes_changed_outside"] += count_diff(old[at:t["start"]], new[at:t["start"]])
        at = t["start"] + t["nbytes"]
        report["rewritten"] += 1
        report["bytes_changed"] += count_diff(old[t["start"]:at], new[t["start"]:at])
        heads = heads or (g.heads() if entry["rows"] else None)
        if "dense" in entry:
            want = dense_value(pack.read_tensor(patch, header, start, entry["dense"]), t, entry["rows"], entry["step"], heads)
            if not np.array_equal(new[t["start"]:at], want):
                raise AssertionError(f"{target}: does not hold the patch values")
            report["dense"] += 1
            continue
        kind = t["type"]
        _, per, size, s_at, c_at = PACKED[kind]
        order = row_order(t["dims"][1], entry["rows"], heads)
        v_old, v_new = blocks(old, t), blocks(new, t)
        scales = pack.read_tensor(patch, header, start, entry["scales"]) if "scales" in entry else None
        words = pack.read_tensor(patch, header, start, entry["weight"]) if "weight" in entry else None
        for a, b in chunks(t["dims"][1], v_new.shape[1] * size):
            if scales is not None:
                got = read_scales(v_new, kind, a, b).view(np.uint16)
                want = np.repeat(take(scales, order, a, b).astype("<f2"), got.shape[1] // scales.shape[1], axis=1)
                if not np.array_equal(got, want.view(np.uint16)):
                    raise AssertionError(f"{target}: multipliers differ from the patch")
            elif not np.array_equal(v_new[a:b, :, s_at], v_old[a:b, :, s_at]):
                raise AssertionError(f"{target}: multipliers changed although the patch has none")
            if words is not None:
                if not np.array_equal(read_codes(v_new, kind, a, b), take(words, order, a, b)):
                    raise AssertionError(f"{target}: codes differ from the patch")
            elif not np.array_equal(v_new[a:b, :, c_at], v_old[a:b, :, c_at]):
                raise AssertionError(f"{target}: codes changed although the patch has none")
        report["scales"] += scales is not None
        report["codes"] += words is not None
    report["bytes_changed_outside"] += count_diff(old[at:], new[at:])
    if report["bytes_changed_outside"]:
        raise AssertionError(f"{report['bytes_changed_outside']} bytes changed outside the patched tensors")
    return report


def export(base, patch, out, ignore_unmapped=False, force=False, log=print):
    if os.path.abspath(base) == os.path.abspath(out):
        raise ValueError("--out must not be the base file")
    if os.path.exists(out) and not force:
        raise ValueError(f"{out} exists; pass --force to replace it")
    t0 = time.time()
    g = Gguf(base)
    header, start = pack.read_header(patch)
    plan, skipped = make_plan(g, header, ignore_unmapped)
    check_plan(g, patch, header, start, plan)
    kinds = sorted({PACKED.get(g.tensors[n]["type"], ("plain",))[0] for n in plan})
    log(f"base   {base}  ({g.size / 1e9:.2f} GB, {len(g.tensors)} tensors)")
    log(f"patch  {patch}  ({len(header)} tensors -> {len(plan)} GGUF tensors of type {', '.join(kinds)}"
        f"{f'; {len(skipped)} left out' if skipped else ''})")
    free = shutil.disk_usage(os.path.dirname(os.path.abspath(out)) or ".").free
    if free < g.size + (256 << 20):
        raise OSError(f"not enough free disk space for a {g.size / 1e9:.2f} GB file ({free / 1e9:.2f} GB free)")
    tmp = out + ".partial"
    try:
        shutil.copyfile(base, tmp)
        mm = np.memmap(tmp, dtype=np.uint8, mode="r+")
        apply_plan(mm, g, patch, header, start, plan)
        mm.flush()
        del mm
        report = verify(base, tmp, g, patch, header, start, plan)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    log(f"wrote  {out}")
    log(f"check  {report['rewritten']} of {report['tensors']} tensors rewritten "
        f"({report['scales']} multipliers, {report['codes']} codes, {report['dense']} full-precision); "
        f"{report['bytes_changed']:,} bytes differ from the base, {report['bytes_changed_outside']} of them outside "
        f"those tensors; every rewritten value read back equal to the patch.  {time.time() - t0:.0f} s")
    return report


# ---------------------------------------------------------------- proving a GGUF holds a pack

def check_pack(base, pack_dir, log=print):
    """Compare every language-model tensor of an MLX pack with the GGUF. Returns the number of mismatches."""
    path = os.path.join(pack_dir, "model.safetensors") if os.path.isdir(pack_dir) else pack_dir
    g = Gguf(base)
    header, start = pack.read_header(path)
    mm = np.memmap(base, dtype=np.uint8, mode="r")
    plan, skipped = make_plan(g, header, ignore_unmapped=True)
    bad, counts, heads, seen = [], {"modules": 0, "signs": 0, "dense": 0, "dense_close": 0}, None, set()
    for target, entry in sorted(plan.items()):
        t = g.tensors[target]
        seen.add(target)
        heads = heads or (g.heads() if entry["rows"] else None)
        if "dense" in entry:
            want = dense_value(pack.read_tensor(path, header, start, entry["dense"]), t, entry["rows"], entry["step"], heads)
            have = mm[t["start"]:t["start"] + t["nbytes"]]
            if np.array_equal(have, want):
                counts["dense"] += 1
            elif entry["step"] == "minus_exp" and np.allclose(have.view(DENSE[t["type"]]), want.view(DENSE[t["type"]]), rtol=1e-6, atol=0):
                counts["dense_close"] += 1          # exp() of another library, last bit
            else:
                bad.append(target)
            continue
        if not {"scales", "biases", "weight"} <= set(entry):
            bad.append(target + " (incomplete in the pack)")
            continue
        kind = t["type"]
        size = PACKED[kind][2]
        order = row_order(t["dims"][1], entry["rows"], heads)
        view = blocks(mm, t)
        scales = pack.read_tensor(path, header, start, entry["scales"])
        biases = pack.read_tensor(path, header, start, entry["biases"])
        words = pack.read_tensor(path, header, start, entry["weight"])
        ok = True
        for a, b in chunks(t["dims"][1], view.shape[1] * size):
            s = take(scales, order, a, b)
            got = read_scales(view, kind, a, b)
            ok &= np.array_equal(got.view(np.uint16), np.repeat(s, got.shape[1] // s.shape[1], axis=1).view(np.uint16))
            ok &= np.array_equal(read_codes(view, kind, a, b), take(words, order, a, b))
            ok &= bool((take(biases, order, a, b) == -s).all())
        counts["modules"] += ok
        if not ok:
            bad.append(target)
        if "signs" in entry:
            want = np.asarray(pack.read_tensor(path, header, start, entry["signs"]))
            same = g.signs(want.size) is not None and np.array_equal(g.signs(want.size), want)
            counts["signs"] += same
            if not same:
                bad.append(target + " (signs)")
    missing = sorted(set(g.tensors) - seen)
    log(f"{counts['modules']} packed modules: multipliers and codes equal bit for bit, offsets equal minus the multipliers")
    log(f"{counts['signs']} sign vectors equal the GGUF's sign table")
    log(f"{counts['dense']} full-precision tensors equal bit for bit, {counts['dense_close']} equal to the last bit of exp()")
    log(f"{len(skipped)} pack tensors have no place in the GGUF (vision tower: {sum(n.startswith('vision_tower.') for n in skipped)})")
    log(f"GGUF tensors without a pack tensor: {missing or 'none'}")
    log(f"mismatches: {bad or 'none'}")
    return len(bad) + len(missing)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", required=True, help="the GGUF file of the unedited model")
    ap.add_argument("--patch", help="a .safetensors file with the edited pack tensors")
    ap.add_argument("--out", help="the GGUF file to write")
    ap.add_argument("--ignore-unmapped", action="store_true", help="leave out patch tensors that have no place in the GGUF")
    ap.add_argument("--force", action="store_true", help="replace --out if it exists")
    ap.add_argument("--check-pack", metavar="PACK", help="instead of exporting, compare the base GGUF with an MLX pack")
    args = ap.parse_args()
    if args.check_pack:
        sys.exit(1 if check_pack(args.base, args.check_pack) else 0)
    if not (args.patch and args.out):
        ap.error("--patch and --out are required")
    try:
        export(args.base, args.patch, args.out, args.ignore_unmapped, args.force)
    except (ValueError, OSError, AssertionError) as e:
        sys.exit(f"export_gguf: {e}")


if __name__ == "__main__":
    main()
