"""Lucide icons, inlined as SVG. Aliases (same drawing under two names) collapse to one glyph."""
import glob
import hashlib
import os
import re

from .splits import SPLITS, stable_hash

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")

_INNER = {}   # canonical name -> svg inner markup
_CANON = {}   # any name -> canonical name
ICON_SPLIT = {}  # canonical name -> split, explicit assignments made by vocab.finalize()

# What an icon looks like, for instructions such as "the gear icon". Only unmistakable shapes.
LOOKS = {
    "trash": "trash can", "trash-2": "trash can", "settings": "gear", "cog": "cog wheel",
    "search": "magnifying glass", "bell": "bell", "star": "star", "heart": "heart",
    "house": "house", "paperclip": "paperclip", "printer": "printer", "pencil": "pencil",
    "pen": "pen", "plus": "plus", "funnel": "funnel", "lock": "padlock", "eye": "eye",
    "mail": "envelope", "save": "floppy disk", "scissors": "scissors", "calendar": "calendar",
    "clock": "clock", "camera": "camera", "mic": "microphone", "smile": "smiley face",
    "globe": "globe", "bookmark": "bookmark", "flag": "flag", "tag": "tag", "pin": "pin",
    "link": "chain link", "cloud": "cloud", "sun": "sun", "moon": "moon", "zap": "lightning bolt",
    "circle-help": "question mark", "ellipsis": "three dots", "ellipsis-vertical": "three vertical dots",
    "menu": "three lines", "download": "download arrow", "upload": "upload arrow",
    "play": "play triangle", "pause": "pause", "phone": "phone", "video": "video camera",
    "key": "key", "bug": "bug", "wand": "magic wand", "pipette": "eyedropper", "eraser": "eraser",
    "hand": "hand", "crop": "crop", "shuffle": "shuffle", "magnet": "magnet", "brush": "brush",
    "paint-bucket": "paint bucket", "mouse-pointer-2": "arrow cursor", "type": "letter T",
    "bold": "bold B", "italic": "slanted I", "underline": "underlined U", "info": "letter i",
    "folder": "folder", "image": "picture", "refresh-cw": "circular arrows", "x": "X",
    "send": "paper plane", "shopping-cart": "shopping cart", "thumbs-up": "thumbs up",
    "git-branch": "branch", "terminal": "terminal prompt", "undo": "curved back arrow",
    "undo-2": "curved back arrow", "redo": "curved forward arrow", "redo-2": "curved forward arrow",
    "layers": "stacked layers", "music": "music note", "headphones": "headphones",
    "archive": "archive box", "inbox": "inbox tray", "copy": "two overlapping squares",
    "share-2": "three connected dots", "power": "power symbol", "rocket": "rocket",
    "sparkles": "sparkles", "shield": "shield", "wifi": "wifi", "bluetooth": "bluetooth",
    "square": "square", "circle": "circle", "hexagon": "hexagon", "triangle": "triangle",
    "ruler": "ruler", "compass": "compass", "book-open": "open book", "gift": "gift box",
    "lightbulb": "light bulb", "thumbs-down": "thumbs down", "anchor": "anchor",
    "user-plus": "person with a plus", "users": "two people", "at-sign": "at sign",
    "hash": "hash sign", "volume-2": "speaker", "volume-x": "crossed-out speaker",
}


def _load():
    by_hash = {}
    for path in sorted(glob.glob(os.path.join(ICON_DIR, "*.svg"))):
        name = os.path.basename(path)[:-4]
        with open(path, encoding="utf-8") as f:
            text = f.read()
        body = text[text.index("<svg"):]
        inner = body[body.index(">") + 1:body.rindex("</svg>")]
        inner = re.sub(r"\s+", " ", inner).replace(" />", "/>").replace("> <", "><").strip()
        digest = hashlib.md5(inner.encode()).hexdigest()
        by_hash.setdefault(digest, []).append(name)
        _INNER[name] = inner
    for names in by_hash.values():
        # prefer a name with a known look, then the shortest
        canon = sorted(names, key=lambda n: (n not in LOOKS, len(n), n))[0]
        for n in names:
            _CANON[n] = canon
    assert _INNER, f"no icons in {ICON_DIR}; run fetch_assets.sh"


def canon(name):
    if not _INNER:
        _load()
    if name not in _CANON:
        raise KeyError(f"unknown icon {name!r}")
    return _CANON[name]


def exists(name):
    if not _INNER:
        _load()
    return name in _CANON


def icon_split(name):
    """Split that may draw this glyph: explicit if a concept claimed it, else by hash."""
    c = canon(name)
    return ICON_SPLIT.get(c) or SPLITS[stable_hash("icon:" + c) % 3]


def svg(name, cls="", size=None, sw=None):
    """Inline SVG for an icon. `data-i` carries the canonical glyph name for the page scan."""
    c = canon(name)
    style = ""
    if size or sw:
        style = ' style="' + (f"width:{size}px;height:{size}px;" if size else "") + (f"stroke-width:{sw};" if sw else "") + '"'
    return f'<svg class="i{" " + cls if cls else ""}" data-i="{c}" viewBox="0 0 24 24"{style}>{_INNER[c]}</svg>'
