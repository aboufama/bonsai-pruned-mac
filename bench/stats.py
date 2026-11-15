"""Intervals and paired tests for the benchmark tables.

Accuracy is the share of cases answered correctly. Its 95% interval is the 2.5th to 97.5th
percentile of the accuracy over 10,000 resamples of the cases drawn with replacement (a
percentile bootstrap, seed fixed so the numbers repeat). Where a set asks several questions
about one screenshot, `clusters` resamples screenshots instead of cases, which is wider and is
reported next to the case interval.

Two models are compared on the cases both answered: the difference in accuracy with a paired
bootstrap interval (the same resampled cases for both), and McNemar's exact test on the cases
where exactly one of them is right.
"""
import math

import numpy as np

N_BOOT = 10000
SEED = 20261114


def _resample_means(values, n_boot, seed, clusters=None):
    """values: array (cases, k). Returns (n_boot, k) resampled means."""
    v = np.asarray(values, dtype=np.float64)
    if v.ndim == 1:
        v = v[:, None]
    rng = np.random.default_rng(seed)
    n = v.shape[0]
    if clusters is None:
        out = np.empty((n_boot, v.shape[1]))
        for start in range(0, n_boot, 500):                      # in blocks, to keep memory small
            idx = rng.integers(0, n, size=(min(500, n_boot - start), n))
            out[start:start + idx.shape[0]] = v[idx].mean(axis=1)
        return out
    names, inv = np.unique(np.asarray(clusters), return_inverse=True)
    sums = np.zeros((len(names), v.shape[1]))
    np.add.at(sums, inv, v)
    sizes = np.bincount(inv, minlength=len(names)).astype(np.float64)
    out = np.empty((n_boot, v.shape[1]))
    for start in range(0, n_boot, 500):
        idx = rng.integers(0, len(names), size=(min(500, n_boot - start), len(names)))
        out[start:start + idx.shape[0]] = sums[idx].sum(axis=1) / sizes[idx].sum(axis=1, keepdims=True)
    return out


def accuracy(hits, clusters=None, n_boot=N_BOOT, seed=SEED):
    """{"n", "hits", "acc", "lo", "hi"} in percent; with clusters also "lo_cluster", "hi_cluster", "clusters"."""
    h = np.asarray(hits, dtype=np.float64)
    if len(h) == 0:
        return {"n": 0, "hits": 0, "acc": None, "lo": None, "hi": None}
    m = _resample_means(h, n_boot, seed)[:, 0]
    out = {"n": int(len(h)), "hits": int(h.sum()), "acc": round(100 * h.mean(), 2),
           "lo": round(100 * float(np.percentile(m, 2.5)), 2), "hi": round(100 * float(np.percentile(m, 97.5)), 2)}
    if clusters is not None:
        mc = _resample_means(h, n_boot, seed, clusters)[:, 0]
        out.update(lo_cluster=round(100 * float(np.percentile(mc, 2.5)), 2), hi_cluster=round(100 * float(np.percentile(mc, 97.5)), 2),
                   clusters=int(len(set(clusters))))
    return out


def mcnemar_exact(only_a, only_b):
    """Two-sided exact p-value: under no difference, each discordant case favours either model
    with probability one half."""
    n, k = only_a + only_b, min(only_a, only_b)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def paired(hits_a, hits_b, clusters=None, n_boot=N_BOOT, seed=SEED):
    """A minus B on the same cases, in percentage points."""
    a, b = np.asarray(hits_a, dtype=np.float64), np.asarray(hits_b, dtype=np.float64)
    assert a.shape == b.shape
    if len(a) == 0:
        return {"n": 0}
    d = _resample_means(a - b, n_boot, seed, clusters)[:, 0]
    only_a, only_b = int(((a == 1) & (b == 0)).sum()), int(((a == 0) & (b == 1)).sum())
    return {"n": int(len(a)), "acc_a": round(100 * a.mean(), 2), "acc_b": round(100 * b.mean(), 2),
            "diff": round(100 * (a.mean() - b.mean()), 2), "lo": round(100 * float(np.percentile(d, 2.5)), 2),
            "hi": round(100 * float(np.percentile(d, 97.5)), 2), "only_a": only_a, "only_b": only_b,
            "both": int(((a == 1) & (b == 1)).sum()), "neither": int(((a == 0) & (b == 0)).sum()),
            "p_mcnemar": mcnemar_exact(only_a, only_b)}


def fmt_p(p):
    return "<0.0001" if p < 1e-4 else f"{p:.4f}" if p < 0.01 else f"{p:.3f}" if p < 0.1 else f"{p:.2f}"
