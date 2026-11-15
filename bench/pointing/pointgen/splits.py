"""How vocabulary is divided between the train, dev and test splits.

Every string that can become a target label, every icon glyph, every instruction wording and
every layout variant belongs to exactly one split. The assignment is a pure function of the
definitions in the code (their order and a hash of their text), never of the random seed.
"""
import hashlib
import re

SPLITS = ("train", "dev", "test")
# Position pattern used for plain lists: three fifths train, one fifth dev, one fifth test.
PATTERN = ("train", "train", "train", "dev", "test")


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def norm(text):
    """Comparison key for labels: case, surrounding punctuation and spacing do not count."""
    text = re.sub(r"\s+", " ", str(text).strip().lower())
    return text.strip(" .…:*›»>")


def weighted_split(key):
    return PATTERN[stable_hash(key) % 5]


# label key -> split, filled while modules are imported (concept labels, pools declared at import,
# claim()). vocab.finalize() freezes it: afterwards nothing can take ownership of a label, so the
# split a label belongs to never depends on which screens a process happened to build first.
LABEL_SPLIT = {}
FROZEN = False


def owner(label, default):
    """The split that owns a label; the first claim wins and later claims follow it."""
    if FROZEN:
        return LABEL_SPLIT.get(norm(label), default)
    return LABEL_SPLIT.setdefault(norm(label), default)


def claim(labels):
    """Give fixed strings (labels written directly in layout code) to one split each, by hash."""
    for label in labels:
        owner(label, weighted_split("label:" + norm(label)))


def free_owner(label):
    """Owner of a label that no vocabulary list declares (e.g. a dropdown option): its declared
    owner if it has one, otherwise a split chosen by hashing the text."""
    return LABEL_SPLIT.get(norm(label)) or weighted_split("label:" + norm(label))


_GENERIC_WORDS = set("""january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday saturday sunday
mon tue wed thu fri sat sun cell row column header page in the mini calendar week day am pm ln col line char""".split())


def is_generic(label):
    """Numbers, dates, spreadsheet cell/row/column references and page numbers are not vocabulary
    and are exempt from the split rule: fewer than three letters remain once those words go."""
    words = re.findall(r"[a-z]+", str(label).lower())
    return sum(len(w) for w in words if len(w) > 1 and w not in _GENERIC_WORDS) < 3


_POOLS = {}
_POOL_SIZE = {}


def pool(name, items, split):
    """The slice of a content list that a split may show as target labels.

    Items are dealt out by position (train, train, train, dev, test, ...) unless the label
    is already owned by a split through an earlier definition.
    """
    if name in _POOLS:
        assert _POOL_SIZE[name] == len(items), f"pool {name!r} used with two different lists"
    else:
        _POOL_SIZE[name] = len(items)
        by = {s: [] for s in SPLITS}
        for i, item in enumerate(items):
            label = item[0] if isinstance(item, (tuple, list)) else item
            by[owner(label, PATTERN[i % 5])].append(item)
        _POOLS[name] = by
    return _POOLS[name][split]


def assert_disjoint(named_sets, what):
    """named_sets: {split: set}. Raises if two splits share an element."""
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            both = named_sets[a] & named_sets[b]
            assert not both, f"{what} shared by {a} and {b}: {sorted(both)[:8]}"
