"""Read PrismML's packed Bonsai 2 weights (MLX "schema 2" pack) without MLX.

A packed linear layer stores, for a weight matrix of shape (rows, width):
  weight  uint32 (rows, width/16)   2-bit codes, 16 per word, lowest bits first
  scales  float16 (rows, width/128) one scale per group of 128 inputs
  biases  float16 (rows, width/128) affine offset per group (equals -scale: ternary)
  signs   float32 (width,)          +1/-1 vector of the input rotation

The layer computes  y = W_q . H(signs * x)  where W_q[r, c] = code * scale + bias, i.e.
(code - 1) * scale with code in {0, 1, 2}, and H is the normalised Walsh-Hadamard
transform applied to consecutive blocks of `block` inputs.

Because H is symmetric, the same layer is an ordinary dense layer in the original basis:
  W_dense = H(W_q) * signs        (H applied along each row, block by block)
`fold` returns that matrix. The embedding table uses the identical formula per row.
"""
import json
import struct

import numpy as np

GROUP = 128
CODES_PER_WORD = 16


def read_header(path):
    """Return (header dict, byte offset of the data section) of a .safetensors file."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    header.pop("__metadata__", None)
    return header, 8 + n


def read_tensor(path, header, data_start, name, rows=None):
    """Memory-map one tensor (optionally only its first `rows` rows) as a numpy array."""
    info = header[name]
    dtype = {"F16": np.float16, "F32": np.float32, "U32": np.uint32, "BF16": np.uint16}[info["dtype"]]
    begin, end = info["data_offsets"]
    arr = np.memmap(path, dtype=dtype, mode="r", offset=data_start + begin,
                    shape=tuple(info["shape"]))
    assert arr.nbytes == end - begin, name
    return arr if rows is None else arr[:rows]


def unpack_codes(words):
    """uint32 (rows, width/16) -> uint8 codes (rows, width) in {0, 1, 2, 3}."""
    words = np.ascontiguousarray(words).astype(np.uint32)
    shifts = (2 * np.arange(CODES_PER_WORD, dtype=np.uint32))[None, None, :]
    codes = (words[:, :, None] >> shifts) & np.uint32(3)
    return codes.reshape(words.shape[0], -1).astype(np.uint8)


def dequantize(words, scales, biases):
    """Packed codes + per-group scales/biases -> float32 weights in the rotated basis."""
    codes = unpack_codes(words).astype(np.float32)
    s = np.repeat(scales.astype(np.float32), GROUP, axis=1)
    b = np.repeat(biases.astype(np.float32), GROUP, axis=1)
    return codes * s + b


def fwht(x, block):
    """Normalised Walsh-Hadamard transform (natural/Sylvester order) over blocks of the last axis."""
    shape = x.shape
    y = x.astype(np.float32).reshape(-1, block).copy()
    h = 1
    while h < block:
        y = y.reshape(-1, block // (2 * h), 2, h)
        a, b = y[:, :, 0, :].copy(), y[:, :, 1, :].copy()
        y[:, :, 0, :], y[:, :, 1, :] = a + b, a - b
        y = y.reshape(-1, block)
        h *= 2
    return (y / np.sqrt(block)).reshape(shape)


def fold(w_rotated, signs, block):
    """Rotated-basis weights -> dense weights in the model's original basis."""
    return fwht(w_rotated, block) * signs.astype(np.float32)[None, :]
