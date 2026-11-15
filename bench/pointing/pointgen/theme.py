"""Colour themes, fonts and style knobs. Theme families and accent colours are split-disjoint."""
from .splits import SPLITS, assert_disjoint

# name, mode, content bg, panel bg, bar bg, text, border
FAMILIES = {
    "train": [
        ("paper", "light", "#ffffff", "#f6f6f7", "#ededee", "#1f2328", "#d9dadd"),
        ("cool", "light", "#ffffff", "#f3f5f8", "#e9edf2", "#1b2430", "#d5dbe3"),
        ("warm", "light", "#fffdfa", "#f7f4ef", "#eeeae3", "#2b2620", "#ddd6ca"),
        ("aqua", "light", "#ffffff", "#f0f0f0", "#e8e6e6", "#262626", "#d1d1d1"),
        ("fluent", "light", "#fbfbfb", "#f3f3f3", "#eaeaea", "#1a1a1a", "#dedede"),
        ("vsdark", "dark", "#1e1e1e", "#252526", "#333333", "#d4d4d4", "#3c3c3c"),
        ("slate", "dark", "#0f172a", "#1e293b", "#172033", "#e2e8f0", "#334155"),
        ("ghdark", "dark", "#0d1117", "#161b22", "#21262d", "#e6edf3", "#30363d"),
        ("zinc", "dark", "#18181b", "#202023", "#27272a", "#e4e4e7", "#3f3f46"),
        ("mocha", "dark", "#1c1917", "#262220", "#2e2a27", "#e7e5e4", "#44403c"),
    ],
    "dev": [
        ("periwinkle", "light", "#fcfcff", "#f1f3fb", "#e6e9f6", "#1d2140", "#d3d8ee"),
        ("solar", "light", "#fdf6e3", "#f5eed9", "#eee8d5", "#3b4a50", "#ddd6bf"),
        ("nord", "dark", "#2e3440", "#3b4252", "#434c5e", "#e5e9f0", "#4c566a"),
        ("dracula", "dark", "#282a36", "#21222c", "#343746", "#f8f8f2", "#44475a"),
    ],
    "test": [
        ("mint", "light", "#fbfdfc", "#eff5f2", "#e3ece8", "#17251f", "#cfdcd5"),
        ("lilac", "light", "#fdfcff", "#f4f1f9", "#eae6f2", "#241f31", "#d9d3e6"),
        ("gruvbox", "dark", "#282828", "#32302f", "#3c3836", "#ebdbb2", "#504945"),
        ("tokyo", "dark", "#1a1b26", "#16161e", "#24283b", "#c0caf5", "#3b4261"),
    ],
}
ACCENTS = {
    "train": ["#2563eb", "#16a34a", "#ea580c", "#dc2626", "#0d9488", "#db2777", "#d97706", "#0284c7", "#7c3aed", "#0969da"],
    "dev": ["#4f46e5", "#059669", "#e11d48"],
    "test": ["#0891b2", "#9333ea", "#65a30d"],
}
assert_disjoint({s: {f[0] for f in FAMILIES[s]} for s in SPLITS}, "theme family")
assert_disjoint({s: {c for f in FAMILIES[s] for c in f[2:5]} for s in SPLITS}, "theme background colour")
assert_disjoint({s: set(ACCENTS[s]) for s in SPLITS}, "accent colour")

SANS = ["Inter", "Roboto", "Open Sans", "IBM Plex Sans", "Source Sans 3", "Ubuntu", "Cantarell",
        "Liberation Sans", "DejaVu Sans", "Nimbus Sans"]
MONO = ["JetBrains Mono", "Fira Code", "Ubuntu Mono", "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono"]
# fonts that suit each window chrome (first entries are the most typical)
CHROME_FONTS = {
    "mac": ["Inter", "Inter", "Nimbus Sans", "Source Sans 3", "IBM Plex Sans"],
    "win": ["Open Sans", "Open Sans", "Liberation Sans", "Roboto", "Source Sans 3", "IBM Plex Sans"],
    "gnome": ["Cantarell", "Ubuntu", "Inter", "DejaVu Sans"],
    "web": ["Inter", "Roboto", "Open Sans", "IBM Plex Sans", "Source Sans 3", "Liberation Sans", "Ubuntu"],
}


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, t):
    """Colour a moved a fraction t of the way to colour b."""
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


def luminance(h):
    r, g, b = [x / 255 for x in _rgb(h)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def pick_theme(rng, split):
    fam = rng.choice(FAMILIES[split])
    accent = rng.choice(ACCENTS[split])
    return {"family": fam[0], "mode": fam[1], "accent": accent, "vars": palette(fam, accent, rng)}


def palette(fam, accent, rng):
    _, mode, bg, bg1, bg2, fg, bd = fam
    dark = mode == "dark"
    ac = mix(accent, "#ffffff", 0.22) if dark else accent
    v = {
        "--bg": bg, "--bg1": bg1, "--bg2": bg2,
        "--bg3": mix(bg, fg, 0.08 if dark else 0.055),
        "--bg4": mix(bg, fg, 0.14 if dark else 0.10),
        "--bd": bd, "--bd2": mix(bd, fg, 0.18),
        "--fg": fg, "--fg1": mix(fg, bg, 0.32), "--fg2": mix(fg, bg, 0.52),
        "--ac": ac, "--acf": "#ffffff" if luminance(ac) < 0.55 else "#111111",
        "--acs": mix(bg, ac, 0.20 if dark else 0.12), "--acs2": mix(bg, ac, 0.34 if dark else 0.22),
        "--inp": mix(bg, "#000000", 0.18) if dark else "#ffffff",
        "--pop": mix(bg1, fg, 0.04) if dark else "#ffffff",
        "--ok": "#3fb950" if dark else "#1a7f37", "--warn": "#d29922" if dark else "#9a6700",
        "--err": "#f85149" if dark else "#cf222e",
        "--sh": "rgba(0,0,0,.55)" if dark else "rgba(15,23,42,.18)",
        "--code-k": "#c586c0" if dark else "#af00db", "--code-s": "#ce9178" if dark else "#a31515",
        "--code-c": "#6a9955" if dark else "#6e7781", "--code-f": "#dcdcaa" if dark else "#795e26",
        "--code-n": "#b5cea8" if dark else "#098658", "--code-t": "#4ec9b0" if dark else "#267f99",
    }
    return v


def pick_style(rng, chrome):
    """Shape and density knobs shared by every component on a screen."""
    density = rng.choices(["compact", "cozy", "comfy"], [5, 4, 2])[0]
    fs, rh, ch = {"compact": (12, 22, 22), "cozy": (13, 26, 26), "comfy": (14, 32, 30)}[density]
    if rng.random() < 0.25:
        fs -= 1 if density != "compact" else 0
    radius = rng.choice([0, 2, 3, 4, 6, 8] if chrome != "win" else [0, 2, 4, 4])
    isz = rng.choice([14, 15, 16, 16, 18]) if density != "comfy" else rng.choice([16, 18, 20])
    return {
        "density": density,
        "font": rng.choice(CHROME_FONTS[chrome]),
        "mono": rng.choice(MONO),
        "btn": rng.choice(["outline", "outline", "soft", "flat"]),
        "navsel": rng.choice(["soft", "soft", "solid", "bar"]),
        "vars": {
            "--fs": f"{fs}px", "--rh": f"{rh}px", "--ch": f"{ch}px", "--cp": f"{rng.choice([8, 10, 12])}px",
            "--r": f"{radius}px", "--r2": f"{min(12, radius * 2)}px",
            "--is": f"{isz}px", "--isw": str(rng.choice([1.5, 1.75, 2, 2])), "--ibs": f"{ch + rng.choice([0, 2, 4])}px",
        },
    }
