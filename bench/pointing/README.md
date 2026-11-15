# pointing: seeded GUI pointing data

A generator of GUI "pointing" (grounding) cases that cannot be in anyone's training set: every
screen is HTML/CSS built from a random seed, rendered in headless Chromium, and every target's
box is read from the page. The same code gives a fresh benchmark (`dev`, `test`) and unlimited
training data (`train`), and the three splits share no layout family, colour theme, icon glyph,
label or wording.

A case is a screenshot, an instruction and one box. A model is right when the point it gives
lies inside the box.

## Setup (on the Spark)

    bash fetch_assets.sh      # once: icons and web fonts into ./assets (about 12 MB)

Needs Python 3.12 with Playwright's Chromium and Pillow (`~/bonsai/venv`). Nothing is fetched at
generation time.

## Commands

    # render screens
    python generate.py --seed 20261114 --n-screens 52 --split dev --cases-per-screen 8 --out DIR
    python generate.py --seed 1 --n-screens 100000 --split train --out DIR --workers 12

    # score a model served by llama-server (OpenAI-compatible API)
    python evaluate.py --data DIR --base-url http://127.0.0.1:8122/v1 --label qwen35_9b --max-side 1280

    # look at labels
    python contact_sheet.py --data DIR --n 24 --out sheet.png
    python contact_sheet.py --data DIR --n 12 --out misses.png --results DIR/results_qwen35_9b.jsonl --only misses

    # prove the splits share nothing
    python check_disjoint.py --n 3000                 # builds 3000 screens per split, no browser
    python check_disjoint.py --data DIR_TRAIN DIR_TEST

`generate.py` writes `DIR/images/<screen>.png`, `DIR/cases.jsonl` and `DIR/screens.jsonl`.
Screen `i` depends only on `(seed, split, i)`, so output is identical whatever `--workers` is, and
`--start I` generates a later slice of the same set (files are then named `cases.<I>.jsonl`).
By default every element with a valid instruction becomes a case (about 100 per screen, a direct
and a functional one where both exist). For a benchmark use `--cases-per-screen 8`, which keeps a
sample balanced over text/icon and direct/functional with at most one case per element.

`evaluate.py` sends the Qwen3.5-family grounding prompt (image first, answer `[x,y]` normalised to
0-1000, temperature 0, 64 tokens, thinking off), writes `DIR/results_<label>.jsonl` and prints
accuracy overall and by tag. It resumes: cases already answered with the same `--max-side` are
skipped. Use a different `--label` for a different model or setting.

## Case format

One JSON object per line in `cases.jsonl`:

    id           "dev-20261114-000003-005"
    image        "images/dev-20261114-000003.png"
    width, height   screenshot pixels (viewport times device scale factor)
    instruction  "Show me the page 1 button below the table"
    bbox         [x1, y1, x2, y2] in screenshot pixels
    element      {role, label, ui_type, icon?, concept?, region?}
    tags         ui_type (text|icon), instruction_kind (direct|functional), archetype, theme (light|dark),
                 size (xs|s|m|l), window_size ("1920x1080"), overlay, chrome, dpr, disambiguation
    meta         seed, split, screen, archetype, variant, theme_family, accent, font, density, chrome,
                 os_bars, floating, overlay, dpr

`size` is the box area as a fraction of the screenshot: xs < 0.03 %, s < 0.1 %, m < 0.4 %, l above.
`screens.jsonl` has one line per screen with every labelled element and its box, whether or not it
got an instruction.

## What a screen is made of

15 application archetypes, 67 layout variants. A variant is a layout family; each belongs to one split.

| archetype | kind | train | dev | test |
|---|---|---|---|---|
| settings | either | sidebar, tabs, mac_grid | cards | two_level |
| email | either | three_pane, stacked, wide_table | compose | rail_conversation |
| files | either | list_details, icon_grid, column_view | tree_dual | web_drive |
| ide | desktop | vscode, jetbrains, sublime | split_diff | notebook |
| sheet | either | ribbon, web_sheets | pivot_side | db_grid |
| kanban | either | columns, sprint_table | swimlanes | board_with_detail |
| chat | either | slack, messenger, discord | support_inbox | irc_compact |
| dashboard | either | kpi_grid, top_nav | report_builder | monitoring |
| music | either | spotify, itunes | album_grid | podcast |
| calendar | either | month, week | agenda | scheduler |
| shop (admin tables) | web | orders_table, products | customer_detail | inventory_dense |
| video (and audio) editor | desktop | premiere, simple_cut | davinci | audio_daw |
| design tool | either | figma, whiteboard | illustrator | photoshop |
| terminal with side panels | desktop | tabs_sessions, tmux_split, ssh_sftp | db_console | devops_logs |
| wizard (multi-step form) | either | stepper_top, sidebar_steps, installer | checkout | survey |

Variant names say which familiar layout a family resembles; no product is copied.

Around that: a macOS-like, Windows-like or GNOME-like title bar with window buttons and a menu bar,
or a browser frame for web apps; optionally the OS menu bar, dock or taskbar; sometimes a floating
window over a wallpaper. Viewports are 1280x800, 1366x768, 1440x900, 1512x982, 1536x864, 1680x1050,
1920x1080, 1920x1200 and 2560x1440, plus 1280x800, 1440x900, 1512x982 and 1728x1117 at device scale
factor 2. Font (ten sans families, six monospace), text size, density, corner radius, icon size and
stroke, button style and selection style vary per screen.

About 40 % of screens carry one overlay: an open menu-bar menu, a context menu, an open dropdown, a
tooltip, an overflow menu, an account popover or a modal dialog (ten dialog layouts, also split:
six train, two dev, two test). Whatever an overlay covers stops being a target.

## Ground truth

After rendering, a script in the page reads `getBoundingClientRect()` of every registered element
(`--check-boxes` compares a sample with Playwright's `bounding_box()`; the largest difference seen
is 0.000 px). A target is kept only if it is entirely inside the viewport and every clipping
ancestor, at least 8x8 CSS px, not truncated with an ellipsis, and on top at five points (centre
and four inset points, by `document.elementFromPoint`). The script also returns every visible text
run and icon glyph, which the instruction step uses to detect look-alikes.

## Instructions

- `direct` names what is visible: "the Export button", "the search field", "the trash can icon",
  "the close button on the main.py tab".
- `functional` says what the user wants without the label: "save my changes". A functional
  instruction is rejected if it contains the label or any content word of it.

An instruction is emitted only if exactly one element fits it. Rivals are any visible element or
free-standing text with the same label, any element of the same concept, and for icons any other
copy of the glyph. If there are rivals the instruction is qualified with the list entry the control
belongs to ("... for report.pdf") or its region ("... in the sidebar"), and dropped when neither
separates them. Two cases on a screen never share a sentence. Each split has its own sentence
frames, several of them spoken-style questions ("Where should I click to ...?").

## Splits

Decided in code, independent of the seed, and asserted when the package loads
(`vocab.check`, `theme.py`, `instruct.py`, `screen.load`):

| what | train | dev | test |
|---|---|---|---|
| layout variants | 37 | 15 | 15 |
| dialog layouts | 6 | 2 | 2 |
| theme families (light and dark in each split) | 10 | 4 | 4 |
| accent colours | 10 | 3 | 3 |
| sentence frames (direct + functional) | 25 | 12 | 13 |
| icon glyphs seen in 3000 screens | 267 | 183 | 160 |
| distinct text labels seen in 3000 screens | 6695 | 2238 | 2631 |

Vocabulary is a set of 1051 concepts (an action or destination), each with labels, icon glyphs and
intent wordings. A concept with three labels gives one to each split ("Delete" / "Remove" /
"Discard"), likewise its glyphs and intents; a one-label concept lives in a single split. Content
lists (people, file stems, projects, channels, subjects, ...) are dealt out by position, three
fifths to train and one fifth each to dev and test. A label has exactly one owner split; an element
whose text belongs to another split is still drawn but never becomes a target. Aliases of the same
Lucide drawing count as one glyph.

`check_disjoint.py` builds thousands of screens per split without a browser and compares what the
generator can actually emit; it reports nothing shared at 3000 screens per split.

Not partitioned, on purpose: numbers, dates, spreadsheet cell/row/column references, page numbers
and cursor positions (they are coordinates, not vocabulary); the three window-chrome styles and the
window buttons, tab close crosses, checkmarks and chevrons they draw; fonts; viewport sizes; the
kinds of overlay (menu, tooltip, ...); free text that is never a target (message bodies, code, logs).
Dropdown options are owned by hashing their text.

## Speed and determinism

On the Spark (20 cores, shared with other jobs), `--workers 12`: 1200 train screens in 50 s =
24 screens/s, 125 850 cases (105 per screen), about 290 kB of PNG per screen. 100 000 screens
take about 70 minutes and about 29 GB. Each worker is a Python process plus a Chromium (roughly
0.7 GB together); do not start more workers than the machine has spare memory for.

Same seed, generated twice with different worker counts, compared by SHA-256 of every file:
1200 train screens (12 and 7 workers) and 300 test screens (10 and 2 workers) were identical,
images and JSONL. Two things were needed for that and are easy to break:

- every screen renders in a fresh browser context, and Chromium runs with partial raster off
  (`render.py`). With a reused page, or with partial raster, about 2 % of PNGs differed between
  runs by one or a few grey levels in a handful of anti-aliased pixels;
- the measuring script loads all weights of the page's fonts and waits until no font is pending,
  again after overlays are inserted. Without that, an overlay could be measured in the fallback
  font and screenshotted in the real one (boxes off by a few pixels).

## Validation

Set: `generate.py --seed 20261114 --n-screens 52 --split dev --cases-per-screen 8` = 413 cases.
Models served by llama-server, screenshots shrunk to 1280 px on the long side (`--max-side 1280`),
14 November 2026. `run_baselines.sh` reproduces both runs (one server at a time, `-np 4`).

| | Qwen3.5-9B (Q8_0) | Ternary Bonsai 2 9B (PTQ1_0) |
|---|---|---|
| **all 413 cases** | **53.8 %** | **7.3 %** |
| text / direct (n=117) | 84.6 % | 18.8 % |
| text / functional (n=102) | 56.9 % | 3.9 % |
| icon / direct (n=96) | 43.8 % | 0.0 % |
| icon / functional (n=98) | 23.5 % | 4.1 % |
| direct (n=213) | 66.2 % | 10.3 % |
| functional (n=200) | 40.5 % | 4.0 % |
| text (n=219) | 71.7 % | 11.9 % |
| icon (n=194) | 33.5 % | 2.1 % |
| size l (n=49) | 75.5 % | 18.4 % |
| size m (n=126) | 73.8 % | 11.1 % |
| size s (n=149) | 43.6 % | 4.0 % |
| size xs (n=89) | 30.3 % | 1.1 % |
| dark theme (n=232) | 53.0 % | 6.5 % |
| light theme (n=181) | 54.7 % | 8.3 % |
| refused or unparseable | 27 | 9 |

For scale: a uniformly random point hits 0.2 % of these cases and the screen centre hits none.
Per-archetype, per-window-size and per-overlay figures are printed by `evaluate.py`; with 22 to
32 cases per archetype they are noisy (Qwen: files 82 %, chat 78 %, wizard 75 % at the top; ide
31 %, design 38 %, calendar 44 % at the bottom; 1728x1117 at scale factor 2, the most shrunk
size, 30 %).

What the strong model's 191 misses are: 42 land within 12 px of the box (in the sent image),
typically on the neighbouring row, icon or menu title; 122 land elsewhere (78 of them on another
labelled element); 27 are refusals (`[-1,-1]`), 21 of them on icon / functional cases. Its
points sit a little above box centres (median 1.1 px in the sent image), which costs it dense
rows and menu bars. All 18 text / direct misses were checked by eye against the boxes: the
boxes are right. Three misses on this set come from one convention worth knowing: the box of a
captioned form field is the input itself, so pointing at its caption ("To", "Cc", "Contact
phone") is a miss.

Other checks made on the same data: every box of the dev set and of a 45-screen test set was
compared with the pixels under it (7234 boxes; the only flat ones are four empty "Cc" inputs),
and several contact sheets were read case by case.

## Icon-only screens

`generate_icons.py` is a second generation mode (it is not an archetype, so it changes nothing about
what `generate.py` renders): icon-dense, Mac-style screens whose only targets are icon-only controls
in toolbars, sidebars, a menu-bar strip, tab bars and a Dock-like row, 8 requests per screen. Icons
are real ones from Lucide, Heroicons, Tabler, Material Symbols and, when `assets/apple/` is present,
Apple system symbols and application icons rendered on a Mac. Requests come from
`pointgen/icon_vocab.txt`. The output format is that of `generate.py`. See `docs/ICON_SET.md`.

    ./generate_icons.py --seed 1 --n-screens 20000 --split train --out DIR
    ./generate_icons.py --describe
    ./generate_icons.py --check DIR --against OTHER_DIR

## Licences of fetched assets

- Icons: Lucide (`lucide-static` 1.73.0), ISC licence; some icons derive from Feather (MIT).
  Licence text is copied to `assets/icons/LICENSE.lucide`.
- More icon sets for the icon-only screens: Heroicons 2.2.0 (MIT), Tabler Icons 3.52.0 (MIT),
  Material Symbols `@material-symbols/svg-400` 0.49.0 (Apache-2.0); each licence text is copied to
  `assets/iconsets/<set>/LICENSE`.
- Fonts: Inter, Roboto, Open Sans, IBM Plex Sans, Source Sans 3, JetBrains Mono, Fira Code from the
  `@fontsource` packages (5.3.x), all SIL Open Font License 1.1 (`assets/fonts/LICENSE.*`). The
  other fonts (Ubuntu, Cantarell, DejaVu, Liberation, Nimbus Sans, Noto Sans Mono) are the Spark's
  system fonts, named explicitly in the CSS.

## Layout of the code

    generate.py, evaluate.py, contact_sheet.py, check_disjoint.py
    run_baselines.sh (Spark: both baselines, one server at a time), fetch_assets.sh
    pointgen/splits.py      who owns a label; pools; the exemption rule
    pointgen/vocab.py       concepts and how labels, glyphs and intents are dealt to splits
    pointgen/icons.py       Lucide loading, alias collapsing, icon "looks"
    pointgen/theme.py       theme families, accents, fonts, density
    pointgen/css.py         the one stylesheet
    pointgen/ui.py          screen context: target registration and components
    pointgen/chrome.py      title bars, menu bars, browser frame, OS bars
    pointgen/overlays.py    menus, tooltips, popovers, dialogs
    pointgen/screen.py      plans a screen from (seed, split, index)
    pointgen/render.py      Chromium rendering and the in-page measuring script
    pointgen/instruct.py    instruction wording and the uniqueness rules
    pointgen/archetypes/    one module per archetype (layouts plus its vocabulary)
    generate_icons.py, pointgen/iconscreens.py, pointgen/icon_vocab.txt   the icon-only screens
    samples/                two contact sheets and four raw screenshots

## Known limits

- Images are placeholders: album art, photos, video frames and design canvases are gradients and
  simple shapes, and there are no real app icons in docks and taskbars.
- Free text repeats: message bodies, code and log lines come from small shared lists.
- dev and test get a fifth of each content list, so some of their side lists are short and a few
  tall windows have empty space at the bottom.
- With three synonyms per concept, each split shows some less usual wording ("Modify" for an Edit
  menu, "Look up" for search, "Ahead one" for next), and icon-only controls are named after
  those labels ("the step back button" for undo). The dev wording for search, "type in what I'm
  trying to locate", is weak: the strong model missed it 8 times out of 11.
- Functional instructions are unique by construction among elements of the same concept, not
  among different concepts with overlapping meaning (a Reload button and an "Apply layout"
  button; a Month view tab and a mini month calendar). A few per cent of functional cases are
  arguable for that reason.
- Everything is rendered by one browser engine with one text rasteriser; there is no real OS
  widget rendering, no blur or transparency effects, no hover or pressed states beyond a few.
- Icon meaning is judged by the concept the generator attached; a glyph that is a weak picture of
  its concept (a droplet for "sample colour") makes a hard but honest case.
