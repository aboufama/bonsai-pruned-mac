# Icon set: small icon-only controls

A generated training set that practises one thing on purpose: pointing at small controls that
show an icon and no text. It exists because the models miss small targets most; on real Mac app
windows, which are full of toolbar icons, they score about half of what they score elsewhere.

Made by `bench/pointing/generate_icons.py` (mode `pointgen/iconscreens.py`, vocabulary
`pointgen/icon_vocab.txt`), a second mode of the screen generator. It is not one of the generator's
archetypes, so the existing benchmark and training sets render exactly as before.

## Where it is (on the Spark)

| Set | Path under `~/bonsai` | Screens | Cases | Seed | Use |
|---|---|---|---|---|---|
| training | `benchdata/pointing/icons_train_s1` | 20,000 | 160,000 | 1 | train |
| scoring | `benchdata/pointing/icons_dev_s1` | 300 | 2,400 | 2 | score only, never train on it |

Both use the generator's **train** split, so both stay clear of the benchmark's dev and test
splits. `icons_dev_s1` therefore shows the same icons and wordings as the training set on screens
the model has not seen; it measures whether the set was learned, not whether unseen icons are
recognised. For that, generate with `--split dev` (icons, themes, wordings and layouts no training
set contains). The training set is 5.0 GB, generated in 13.5 minutes (24.7 screens/s, 8 processes,
CPU only).

## Loading

    lab.data("gen:benchdata/pointing/icons_train_s1")
    lab.data("gen:benchdata/pointing/icons_dev_s1")

Same on-disk format as the other generated sets (`images/`, `cases.jsonl`, `screens.jsonl`), read
by the `gen:` loader in `weightlab/core.py` unchanged. Every case has `ui_type` `icon` and group
`icondense`. Case ids start with `icons-`, so they cannot collide with other generated sets. Extra
tags per case: `icon_set`, `surface`, `state`, `disambiguation`, `w1280` and `h1280` (the target's
width and height on a 1280 px wide screenshot).

## What a screen is

A desktop with a Mac-style window, laid out 1280 CSS px wide and rendered at nine image sizes from
1280x800 to 3024x1964, half light and half dark themes. Icon-only controls sit on these surfaces:

| Surface | Share of cases | What it holds |
|---|---|---|
| window toolbar (and a second, smaller bar) | 28.0 % | 6 to 16 icon buttons, grouped, plain, bordered, filled or segmented |
| sidebar (icon rail, or rows of icon plus a grey placeholder bar) | 22.9 % | 5 to 12 icons |
| menu-bar strip | 17.5 % | 5 to 9 small status icons |
| Dock-like row | 14.2 % | 7 to 13 application icons |
| inspector tab strip | 6.8 % | 4 to 7 icons |
| bottom bar | 5.5 % | 3 to 6 small icons |
| tab bar | 5.1 % | 4 to 8 icon-only tabs |

No target has a text label; captions next to sidebar icons are grey bars. 5.6 % of targets are
drawn disabled and 7.2 % highlighted. Each screen gives 8 requests, one per icon. A request is only
written when exactly one icon on the screen fits it: icons that mean the same thing never share a
screen, and a wording that two visible icons could claim is not used.

About 43 % of screens repeat one or two icons on two surfaces, and requests for those name the
place ("... in the sidebar"): 10.7 % of cases need the position. Requests for an icon that is not
on the screen are **not** included: the generator has no mark for absent targets and the `gen:`
loader needs a box.

## Icons and where the requests come from

Only real icons are used; none was drawn for this set.

| Source | Icons in the training set | Cases | Share | Used on |
|---|---|---|---|---|
| Apple system symbols | 454 | 80,908 | 50.6 % | Mac-style toolbars, sidebars, tab bars; every menu-bar strip |
| Apple application icons | 44 | 22,730 | 14.2 % | the Dock-like row |
| Lucide | 109 | 14,315 | 8.9 % | web-app style windows |
| Material Symbols | 149 | 14,177 | 8.9 % | web-app style windows |
| Heroicons | 105 | 14,076 | 8.8 % | web-app style windows |
| Tabler Icons | 157 | 13,794 | 8.6 % | web-app style windows |

Half of the windows use system symbols and half use one of the four web sets.

Requests are 66 % names or looks ("the gear icon", "the three dots") and 34 % actions ("open
settings"). They come from two places:

- `pointgen/icon_vocab.txt`: 270 drawings in 223 meanings, written by hand, each with 3 to 6
  phrasings (about 720 names and looks, 500 actions). Each line names the matching drawing in
  Lucide, Heroicons, Tabler, Material Symbols and the system symbols, so one meaning has the same
  wording whichever set draws it.
- System symbols without a line there (about two thirds of them) are asked for by Apple's own name
  for the symbol and by the search words of Apple's symbol catalogue, as "the ... icon" or "the ...
  button". These are names only, never actions, and some of Apple's search words are loose (a
  gauge symbol found under "low"), so a small part of these requests reads oddly.
- Application icons are asked for by the application's display name: "open Mail", "the Calendar
  app", "Notes in the Dock".

Three example requests from the training set:

- "Can you click the microphone slash icon?" (system symbol, menu bar, 27x30 px box in a 1728 px image)
- "Can you align the text right?" (Tabler, toolbar)
- "The filter lines icon in the tab bar" (Lucide; the same icon is also elsewhere on the screen)

## Target sizes

Shorter side of the target box, scaled to a 1280 px wide screenshot (training set; the scoring set
matches within 2 points):

| px | 14-17 | 18-21 | 22-25 | 26-29 | 30-33 | 34-36 |
|---|---|---|---|---|---|---|
| share | 2.7 % | 26.3 % | 24.7 % | 19.7 % | 17.4 % | 9.3 % |

Minimum 16, median 25, maximum 36. In the image's own pixels the boxes are larger by the image
width divided by 1280 (up to 2.4 times).

## Splits

Lucide glyphs keep the split the generator already gave them, so no Lucide glyph of the dev or test
split is drawn. Every other icon is dealt to train, dev or test (three, one, one in five) by a hash
of its name. Themes, accent colours and phrasing templates are the generator's split-disjoint ones;
the three layouts used here are train-only. Checked with
`generate_icons.py --check DIR --against benchdata/pointing/dev_20261114 benchdata/pointing/test_sample`:
no icon, request, theme, accent or layout is shared, for both sets. `check_disjoint.py` still passes.

## Checks made

One contact sheet of 12 screens with boxes was read: boxes sit on the icons, icons are legible, no
text gives the answer away. After it, two wrong pairings of a system symbol with a meaning were
removed and the loose search words were limited to symbols without a hand-written line. All 160,000
boxes lie inside their image (three that stuck out by one pixel were clamped), every image file
exists and has the recorded size, ids are unique, every screen has 8 cases.

## Regenerating

On the Spark, in `~/bonsai/bench/pointing`, after `fetch_assets.sh`:

    ../../venv/bin/python generate_icons.py --seed 1 --n-screens 20000 --split train --workers 8 \
        --out ~/bonsai/benchdata/pointing/icons_train_s1
    ../../venv/bin/python generate_icons.py --seed 2 --n-screens 300 --split train --workers 8 \
        --out ~/bonsai/benchdata/pointing/icons_dev_s1
    ../../venv/bin/python generate_icons.py --describe

Output depends only on seed, split and screen index. Without `assets/apple/` the mode still runs
and uses the four web sets only.

## Licences and sources

- Lucide (`lucide-static` 1.73.0): ISC licence; some icons derive from Feather (MIT). Text in
  `assets/icons/LICENSE.lucide`.
- Heroicons 2.2.0: MIT. Tabler Icons 3.52.0: MIT. Material Symbols (`@material-symbols/svg-400`
  0.49.0): Apache-2.0. Each licence text is in `assets/iconsets/<set>/LICENSE`. All are fetched as
  npm tarballs by `bench/pointing/fetch_assets.sh`.
- Apple system symbols and application icons were rendered on a Mac (macOS 27) by the system's own
  AppKit calls, with names and search words read from the system's symbol catalogue. They are
  Apple's property, used here for training only. The pictures and their index live only on the
  Spark under `bench/pointing/assets/apple/` (ignored by git) and must not be committed, published
  or shown in this repository's documents. Symbols that Apple restricts to one of its own products
  were left out.
