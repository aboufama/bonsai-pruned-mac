# How small can a Mac screenshot get before the answer is no longer in it?

A test of the image, not of Bonsai. Claude (the assistant running this project) looked at real macOS
screenshots at five sizes, smallest first, and pointed at labelled targets without seeing the boxes.
If a far larger model cannot find a target at some size, the information is not in the image at that
size, and no amount of tuning a 9B model will recover it. The reverse does not hold: a size that is
enough for Claude may still be too small for Bonsai. That part is measured on the model itself
(`experiments/013_looks.py`, and the input-size sweep in `docs/BENCHMARK.md`).

14 Nov 2026.

## Result

Seven screenshots, 21 targets. Seven of the 21 have a box in the source data that does not match the
request (judged at the largest size), so the count that means something is the other 14.

| Long side of the screenshot | 320 px | 448 px | 640 px | 896 px | 1280 px |
|---|---|---|---|---|---|
| Found, of 14 correctly labelled targets | 10 | 11 | 14 | 14 | 14 |
| Found, of all 21 | 10 | 11 | 14 | 14 | 14 |

By how large the target was on the image shown (its smaller side), correctly labelled targets only:

| Smaller side of the target | under 6 px | 6 to 9 px | 9 to 14 px | 14 px and over |
|---|---|---|---|---|
| Found | 7 of 8 | 12 of 18 | 14 of 14 | 30 of 30 |

- **The threshold is 640 px on the long side** for a full Retina Mac screen (2880 x 1800 or
  3360 x 2100 scaled down). Below it, the misses are all of one kind: icons that have to be told
  apart from their neighbours by how they look, in the Dock and in the menu bar. At 448 px a Dock
  icon is 6 to 9 px across; at 640 px it is 9 to 13 px and can be recognised.
- Things found at every size, down to 320 px: text buttons, tabs, sliders and switches inside a
  window, and anything whose place is fixed (the Apple menu). At 320 px these were located from the
  layout rather than read; the 7 of 8 in the first column are of this kind.
- Nothing was gained above 640 px on these targets.
- Rule of thumb: a target that must be recognised by its look needs about 9 px on its smaller side.
  A 640 px screenshot has a quarter of the pixels of a 1280 px one, so about a quarter of the image
  tokens.

## Method

- Screenshots: three macOS desktops (ScaleCUA, hand-made set), one desktop with Control Center open
  and one full-screen web app (ShowUI desktop), two app windows (Screen2AX-Task). Three targets
  each: the image's smallest, median and largest labelled box by area, roughly.
- Each screenshot was scaled with Lanczos so its long side was 320, 448, 640, 896 or 1280 px.
- Order: all seven at 320, then 448, 640, 896. Answers were written down as fractions of width and
  height before any larger size was opened, and before the boxes were read. At 896 px two
  screenshots, and at 1280 px five, were not reopened because every target on them had been found
  with confidence at a smaller size; their earlier answers were carried over.
- A point counts when it is inside the box.

## The seven mislabelled targets

Kept here because they say something about the data: three of the seven come from Screen2AX-Task
and three from ScaleCUA, both of which are in the training mix.

| Request | What the box is actually on |
|---|---|
| VS Code icon in the Dock (two screenshots) | a minimised window at the right end of the Dock, not the app icon |
| Purple Podcasts icon in the menu bar | a different menu-bar icon; the purple Podcasts icon is in the Dock |
| one key cash | the "Explore One Key perks" link, not the OneKeyCash banner |
| navigate back | the chevron that collapses the sidebar |
| collapse side panel | the chevron that collapses the page header |
| select category | the arrow on a different row |

## Limits

Seven screenshots and 21 targets is a small sample, and three of the screenshots are nearly the same
desktop. The reader knew where things usually are on a Mac, which helps at small sizes in a way a
freshly tuned model may not match. Coordinates were estimated by eye, so a target counted as found
was also pointed at accurately enough to land inside its box.
