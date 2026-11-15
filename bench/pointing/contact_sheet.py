#!/usr/bin/env python3
"""Draw target boxes and instructions on sampled screenshots, for checking labels by eye.

    contact_sheet.py --data DIR --n 24 --out FILE.png [--cols 4] [--tile 720] [--seed 0]
                     [--results DIR/results_<label>.jsonl --only misses|hits]

Each tile shows the whole screenshot with the target box outlined, a magnified crop around the
target in a corner, and the instruction underneath. With --results, the model's answer is drawn
as a cross and tiles can be restricted to misses or hits.
"""
import argparse
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont

BOX = (255, 0, 170)
PRED = (0, 190, 255)


def font(size, bold=False):
    for path in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
                 f"/System/Library/Fonts/Supplemental/Arial{' Bold' if bold else ''}.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def tile(case, data_dir, tw, pred=None):
    im = Image.open(os.path.join(data_dir, case["image"])).convert("RGB")
    W, H = im.size
    x1, y1, x2, y2 = case["bbox"]
    scale = tw / W
    th = round(H * scale)
    small = im.resize((tw, th), Image.LANCZOS)
    d = ImageDraw.Draw(small)
    d.rectangle([x1 * scale - 3, y1 * scale - 3, x2 * scale + 3, y2 * scale + 3], outline=BOX, width=2)
    # magnified crop, placed in the corner farthest from the target
    cw, ch = max(x2 - x1 + 160, 520), max(y2 - y1 + 110, 260)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    left = int(min(max(0, cx - cw / 2), max(0, W - cw)))
    top = int(min(max(0, cy - ch / 2), max(0, H - ch)))
    crop = im.crop((left, top, min(W, left + cw), min(H, top + ch)))
    cd = ImageDraw.Draw(crop)
    cd.rectangle([x1 - left - 2, y1 - top - 2, x2 - left + 2, y2 - top + 2], outline=BOX, width=2)
    if pred:
        px, py = pred[0] * W / 1000, pred[1] * H / 1000
        d.line([px * scale - 9, py * scale, px * scale + 9, py * scale], fill=PRED, width=3)
        d.line([px * scale, py * scale - 9, px * scale, py * scale + 9], fill=PRED, width=3)
        cd.line([px - left - 10, py - top, px - left + 10, py - top], fill=PRED, width=3)
        cd.line([px - left, py - top - 10, px - left, py - top + 10], fill=PRED, width=3)
    iw = int(tw * 0.42)
    ih = round(crop.height * iw / crop.width)
    if ih > th * 0.5:
        ih = int(th * 0.5)
        iw = round(crop.width * ih / crop.height)
    crop = crop.resize((iw, ih), Image.LANCZOS)
    ix = 6 if cx * scale > tw / 2 else tw - iw - 6
    iy = 6 if cy * scale > th / 2 else th - ih - 6
    small.paste(crop, (ix, iy))
    d.rectangle([ix - 2, iy - 2, ix + iw + 1, iy + ih + 1], outline=(255, 210, 0), width=2)
    # caption
    f1, f2 = font(15, True), font(12)
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    lines = wrap(probe, case["instruction"], f1, tw - 12)
    t = case["tags"]
    info = f'{case["id"]}  ·  {t["ui_type"]}/{t["instruction_kind"]}/{t["size"]}  ·  {case["element"]["role"]}: {case["element"]["label"]}'
    cap_h = 8 + 19 * len(lines) + 18
    out = Image.new("RGB", (tw, th + cap_h), (250, 250, 250))
    out.paste(small, (0, 0))
    od = ImageDraw.Draw(out)
    y = th + 4
    for line in lines:
        od.text((6, y), line, fill=(15, 15, 15), font=f1)
        y += 19
    od.text((6, y), info[:140], fill=(95, 95, 95), font=f2)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile", type=int, default=720)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--results", default=None)
    ap.add_argument("--only", choices=("misses", "hits"), default=None)
    ap.add_argument("--where", default=None, help="tag filter such as ui_type=icon or archetype=email")
    args = ap.parse_args()

    with open(os.path.join(args.data, "cases.jsonl"), encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
    preds = {}
    if args.results:
        with open(args.results, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                preds[r["id"]] = r
        cases = [c for c in cases if c["id"] in preds]
        if args.only:
            cases = [c for c in cases if preds[c["id"]]["hit"] == (args.only == "hits")]
    if args.where:
        k, v = args.where.split("=", 1)
        cases = [c for c in cases if str(c["tags"].get(k)) == v]
    rng = random.Random(args.seed)
    by_screen = {}
    for c in cases:
        by_screen.setdefault(c["image"], []).append(c)
    screens = sorted(by_screen)
    rng.shuffle(screens)
    picked = []
    while len(picked) < args.n and any(by_screen.values()):   # one case per screen first, then a second round
        for s in screens:
            if by_screen[s] and len(picked) < args.n:
                picked.append(by_screen[s].pop(rng.randrange(len(by_screen[s]))))
    tiles = [tile(c, args.data, args.tile, (preds.get(c["id"]) or {}).get("point")) for c in picked]
    if not tiles:
        raise SystemExit("no cases to show")
    cols = min(args.cols, len(tiles))
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    heights = [max(t.height for t in row) for row in rows]
    sheet = Image.new("RGB", (cols * (args.tile + 8) + 8, sum(heights) + 8 * (len(rows) + 1)), (40, 40, 44))
    y = 8
    for row, h in zip(rows, heights):
        for i, t in enumerate(row):
            sheet.paste(t, (8 + i * (args.tile + 8), y))
        y += h + 8
    sheet.save(args.out)
    print(f"{len(tiles)} cases -> {args.out} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
