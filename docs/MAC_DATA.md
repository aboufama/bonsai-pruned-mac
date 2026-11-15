# macOS pointing data: survey and first download

Written 2026-11-14. Goal: data to train a small vision-language model to point at UI elements on
macOS screenshots (screenshot + instruction -> click point), and a separate held-out macOS test set.
ScreenSpot-v2 and ScreenSpot-Pro are reserved for testing and must never enter training.

Numbers marked "measured" were computed from the files themselves (annotation files, zip directories,
parquet files, the Hugging Face file tree). Everything else is taken from the dataset card or paper.

## Short version

- The largest public source of real macOS screens with a pointer target is **AgentNet** (OpenCUA):
  5,168 recorded macOS sessions, 97,435 screenshots, MIT licence. It has human click points and a
  generated sentence per step, but no element boxes. Its macOS frames are about 1,200 px wide, which is
  close to our 1,280 px input.
- Exact element boxes on macOS are scarce. The public sets with boxes are small (hundreds to a few
  thousand screenshots): ScaleCUA's macOS part, Screen2AX, OS-Atlas macOS, OmniACT / ShowUI-desktop.
- **OS-Atlas macOS and ScaleCUA macOS overlap ScreenSpot-v2.** Both were captured on the same Mac as
  the eight macOS "shop" images that ScreenSpot-v2 added. OS-Atlas holds one of those images pixel for
  pixel; ScaleCUA holds the same screen twice. On 2026-11-14 it was decided to leave those eight cases
  out of all ScreenSpot-v2 scoring, so both sets are now training data. WaveUI and GroundUI-18K contain
  ScreenSpot rows outright and stay unused.
- Screen2AX-Tree and the Screen2AX-Task benchmark cover the same apps. On 2026-11-14 it was decided to
  split them by app: two thirds of the app keys train (Screen2AX-Tree), one third tests (Screen2AX-Task).
- Box training data on the Spark now: 43,442 cases on 2,276 real macOS images from four sources (OS-Atlas
  counts crops of a screen as separate images).
  The next section lists every set with its loader name.

## Sets on the Spark now

State after the decisions of 2026-11-14. The loader name is `mac:<folder>:<split>`; folders are under
`~/bonsai/data/mac/`.

| Loader name | Use | Cases | Screenshots | Apps | Target | Instruction text | Condition |
|---|---|---|---|---|---|---|---|
| `mac:showui_desktop_mac:train` | Train only | 1,037 | 61 | 20 | Box | Short human labels from OmniACT, median 2 words | None |
| `mac:screen2ax_tree:train` | Train only | 27,019 | 719 | 64 app keys | Box | Synthetic wording from accessibility label and role, median 4 words | Never together with `cases_full_DO_NOT_USE_WITH_TREE.jsonl` |
| `mac:os_atlas_mac:train` | Train only | 13,988 | 1,095 | Not labelled | Box | Raw accessibility names, median 1 word | ScreenSpot-v2 exclusion list in force |
| `mac:scalecua_mac:train` | Train only | 1,398 | 401 | 12 apps and 3 hand-annotated sets | Box; 1,385 also a click point | LLM-written descriptions, median 19 words | ScreenSpot-v2 exclusion list in force |
| `mac:screen2ax_task:test` | Test only | 2,106 | 134 | 27 app keys, 75 windows | Box | Short human commands, median 3 words | None |
| `mac:agentnet:train` and `mac:agentnet:test` | On hold for training: points only, pointer visible | 60,082 and 504 | One per case | 262 app names | Click point | Generated step sentences, median 18 words | Not decided |

**ScreenSpot-v2 scoring.** From 2026-11-14 on, every ScreenSpot-v2 score excludes the eight cases listed
in `~/bonsai/ssv2/excluded_overlap.json`: `desktop_0308`, `desktop_0309`, `desktop_0312`, `desktop_0319`,
`desktop_0322`, `desktop_0327`, `desktop_0330`, `desktop_0332` (ids are `<split>_<index>` in
`screenspot_<split>_v2.json`). That leaves 1,264 of 1,272 cases, 326 of 334 on desktop. Scores computed
before that date include them. The file gives the image and the reason for each case. `os_atlas_mac` and
`scalecua_mac` must not be trained on if those cases are ever scored again.

**Screen2AX split.** An app key is reserved for testing when `int(sha1(app_key), 16) % 3 == 0`; that is
27 keys. `screen2ax_task/cases.jsonl` holds the 2,106 benchmark cases of those keys; the full 5,775-case
benchmark is kept beside it as `cases_full_DO_NOT_USE_WITH_TREE.jsonl`. `screen2ax_tree` holds the
accessibility-tree elements of the other 64 keys. After the move no app key and no screenshot is on both
sides (closest train/test thumbnail difference 3.8 of 255, where the same picture gives under 1.5). Every
case in both folders carries `meta.app_key`, so cases can be capped per app: `org_eclipse` alone is
10,986 of the 27,019 training cases, and `com_apple` is 671 of the 2,106 test cases.

## Comparison

| Source | What it contains | macOS part | Annotation | Instruction text | Image size | Size on disk | Licence | Gated | Overlap with ScreenSpot-v2 / -Pro |
|---|---|---|---|---|---|---|---|---|---|
| [AgentNet](https://huggingface.co/datasets/xlangai/AgentNet) ([paper](https://arxiv.org/abs/2508.09123)) | Human computer-use recordings made with a recorder on annotators' own computers: 22,532 tasks in the metadata file (12,364 Windows, 5,168 macOS, 5,000 Ubuntu), one screenshot + description + pyautogui code per step (measured) | 5,168 sessions, 97,435 screenshots, 76,538 steps with exactly one pointer target, 263 application names (measured) | Human click points, normalised 0-1. No boxes | One sentence per step written by an LLM from the recording, median 18 words | Video keyframes. macOS: mostly 1188-1212 px wide (1212x758, 1192x772), some 1280x720, few 2560x1440 and larger (measured) | Repo 199.6 GB. Windows+macOS screenshots: one 124.3 GB split zip, 349,169 PNG. macOS screenshots: 35.9 GB (measured) | MIT | No | None stated. Our check found no shared screenshot |
| [ScaleCUA-Data](https://huggingface.co/datasets/OpenGVLab/ScaleCUA-Data) ([paper](https://arxiv.org/abs/2509.15221)) | Grounding and trajectory data for six platforms | Grounding: 4,302 box rows (1,434 distinct elements, three descriptions each) and 5,485 point rows on 438 screenshots, of which 20 hand-made screenshots carry 3,051 and 3,907 rows. Trajectories: 23,022 step rows, 382 trajectories, about 2,100 screenshots (measured from the annotation files) | Boxes on a 0-1000 grid and click points. Card: labelled by a model (Claude 3.7), then checked by people | Several LLM paraphrases per element or step | 2880x1800 for every macOS row (measured) | Repo about 1.07 TB. macOS image archives about 10.1 GB | None on the dataset repo; two requests for one are open and unanswered. Project repository: Apache-2.0. Paper: data released "to advance future research" | No | **Yes, ScreenSpot-v2 (measured).** Same Mac as OS-Atlas macOS; two App Store screenshots are the same picture as `pc_pl3ry1.png` |
| [Screen2AX-Task](https://huggingface.co/datasets/macpaw-research/Screen2AX-Task), with [Tree](https://huggingface.co/datasets/macpaw-research/Screen2AX-Tree) and [Element](https://huggingface.co/datasets/macpaw-research/Screen2AX-Element) ([paper](https://arxiv.org/abs/2507.16704)) | macOS-only application-window screenshots from MacPaw. Task is a benchmark: target box + command + visual description. Tree has full accessibility trees | Task: 5,933 rows on 435 screenshots, 215 app windows (measured). Tree: 1,127 screenshots from 112 apps. Element: 986 screenshots. Task and Element screenshots are all taken from Tree (measured) | Task: human-drawn boxes in pixels (paper) | Short commands, median 3 words ("open help") | Window captures, JPEG, typically 2,000-2,900 px wide (measured) | Task 0.71 GB, Tree 0.62 GB, Element 0.12 GB | Apache-2.0 | No | Paper evaluates on ScreenSpot's macOS subset separately. Our check found no shared screenshot |
| [OS-Atlas data](https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data), `desktop_domain` ([paper](https://arxiv.org/abs/2410.23218)) | Accessibility-tree grounding corpus: Windows, Linux, macOS desktop plus web and mobile | 1,312 image files (full screens and crops of them) with 18,399 element boxes (measured). Paper: 1,339 screenshots, 13,326 elements | Accessibility-tree boxes, normalised 0-1 | Raw accessibility names. 72 % are static text; many are numbers, values or icon glyphs | 2880x1800 full screens, 1440x900 crops (measured) | macOS zip 5.5 GB (desktop 80 GB, repo 816 GB) | Apache-2.0 | No | **Yes, ScreenSpot-v2 (measured).** One image is pixel-identical to ScreenSpot-v2 `pc_pl3ry1.png`; same Mac and same screens as ScreenSpot-v2's macOS "shop" images. The card does not mention it |
| [ShowUI-desktop](https://huggingface.co/datasets/showlab/ShowUI-desktop) / [OmniACT](https://huggingface.co/datasets/Writer/omniact) ([paper](https://arxiv.org/abs/2402.17553)) | OmniACT: 9,802 tasks on desktop and web screens with human-drawn boxes. ShowUI-desktop: 7,496 rows = 1,874 OmniACT desktop elements, each with its label and three GPT-4o rewrites | ShowUI-desktop: 61 of its 101 screenshots are macOS (20 app folders, 1,060 elements); the other 40 are Windows and Ubuntu (measured). OmniACT paper: 22 macOS apps, 4,258 macOS tasks | Human-drawn boxes; ShowUI-desktop stores them normalised with the centre point | OmniACT: task sentence + pyautogui script. ShowUI-desktop: raw label plus GPT-4o rewrites by appearance, position and function | macOS: 2880x1800 and 3360x2100 (measured) | 1.0 GB and 0.8 GB | OmniACT: MIT. ShowUI-desktop: none stated on the card; ShowUI code repository is Apache-2.0 | No | None stated; our check found no shared screenshot. OmniACT screens are also part of GroundUI-18K and WaveUI |
| [UGround-V1-Data](https://huggingface.co/datasets/osunlp/UGround-V1-Data) | Synthetic web grounding (Web-Hybrid, Web-Direct) | None, web pages only | Points and boxes on a 0-999 grid | Generated referring expressions | Rendered web pages | 424 GB | CC BY-NC-SA 4.0 | Yes: form and terms, auto-approved. Not requested | None stated |
| [macOSWorld](https://github.com/showlab/macosworld) ([paper](https://arxiv.org/abs/2506.04135)) | Interactive benchmark: 202 tasks, 30 apps, 5 languages, run against a macOS machine on AWS or a VMware image | All macOS, but no annotated screenshots are shipped | Task success checks only | Task sentences | Live screen | VM images only (340 GB for the VMware variant) | See repository | No | Not a training source. Usable later as an end-to-end test |
| [GUI-360](https://huggingface.co/datasets/vyokky/GUI-360) | 1.2 M agent steps in Word, Excel, PowerPoint | None, Windows only | Accessibility boxes | Agent thoughts | Windows full screens | 721 GB | MIT | No | Not relevant |
| Aguvis [stage 1](https://huggingface.co/datasets/xlangai/aguvis-stage1) / [stage 2](https://huggingface.co/datasets/xlangai/aguvis-stage2) | Stage 1: grounding mix (SeeClick web, GUIEnv, Rico sets, WebUI, OmniACT). Stage 2: mobile and web trajectories | Only the OmniACT part | Boxes and points | Templated | Mixed | 180 GB and 168 GB | Apache-2.0 | No | None stated |
| [JEDI](https://huggingface.co/datasets/xlangai/Jedi) ([paper](https://arxiv.org/abs/2505.13227)) | 4 M synthetic examples (icons, components, layouts, refusals) plus relabelled Aguvis and OS-Atlas desktop data | Mac app icons on plain backgrounds; the OS-Atlas desktop relabelling (images come from OS-Atlas) | Boxes and points in Qwen2.5-VL resized coordinates | Generated | Synthetic renders | 177 GB | Apache-2.0 | No | Inherits the OS-Atlas macOS overlap for that subset |
| [Click-100k](https://huggingface.co/datasets/mlfoundations/Click-100k) | 101,314 filtered rows unified from ShowUI, AutoGUI, PC-Agent-E, WaveUI, OS-Atlas, UGround, PixMo, SeeClick, UI-Vision, JEDI and tutorial-video frames | Small. In a 1,400-row sample 2.4 % were OmniACT / ShowUI-desktop images; OS is not labelled | Boxes in pixels | Prompt with a short description | Mixed | 29.9 GB | None stated | No | Risk. Includes WaveUI (which carries ScreenSpot rows), the UI-Vision benchmark and OS-Atlas; the card does not say these were filtered |
| [WaveUI](https://huggingface.co/datasets/agentsea/wave-ui) | 79,412 rows from WebUI, Roboflow and GroundUI-18K with relabelled names and descriptions | 1,770 desktop rows of 63,530 in train (OmniACT, ScreenSpot, AgentStudio) (measured) | Boxes | LLM-written name, description, purpose | Mixed | 37 GB | Per source: MIT, WebUI custom, AGPL-3.0 | No | **Yes.** 1,001 train rows have `source = screenspot` (measured). [GroundUI-18K](https://huggingface.co/datasets/agent-studio/GroundUI-18K) says on its card that it is a test set |
| Related, checked briefly | [agentnet-clicks](https://huggingface.co/datasets/mlfoundations-cua-dev/agentnet-clicks): AgentNet clicks with a small fixed box drawn around each click (24 px in the card's example), Windows and Ubuntu included, 61.8 GB. [AgentNetBench](https://huggingface.co/datasets/xlangai/AgentNetBench): 100 held-out tasks. [MMBench-GUI](https://huggingface.co/datasets/OpenGVLab/MMBench-GUI): benchmark with a macOS folder. [GroundCUA](https://huggingface.co/datasets/ServiceNow/GroundCUA) and [UI-Vision](https://huggingface.co/datasets/ServiceNow/ui-vision): desktop apps, OS not labelled. [DeskVision](https://huggingface.co/datasets/caca9527/DeskVision): annotations only, images by URL | AgentNetBench: 39 macOS tasks (paper). MMBench-GUI: macOS is one of six platforms | Varies | Varies | Varies | 0.4-62 GB | MIT, Apache-2.0 or none stated | No | AgentNetBench, MMBench-GUI and UI-Vision are test sets. DeskVision's OS-Atlas captions inherit the OS-Atlas overlap |

## The ScreenSpot-v2 overlap in OS-Atlas macOS

After converting OS-Atlas macOS we compared its screenshots with the ScreenSpot-v2 and ScreenSpot-Pro
images already on the Spark (read only): a 256-bit difference hash, then a thumbnail difference for the
close pairs, then looking at the closest pairs.

- `20240905_140515_screenshot.png` in OS-Atlas is identical, pixel for pixel at 2880x1800, to
  ScreenSpot-v2 `pc_pl3ry1.png` (App Store, Updates page), which carries the test case
  "update all available apps".
- ScreenSpot-v2 desktop has 28 images with `data_source = shop`; eight of them are 2880x1800 macOS
  screens. Their nearest OS-Atlas screenshots show the same Mac: same wallpaper, same desktop files,
  same dock, and in at least three more cases the same screen on another day (System Settings >
  Battery, Music > Radio, the desktop itself).
- No other ScreenSpot-v2 desktop image and no ScreenSpot-Pro image matched an OS-Atlas macOS image.

The OS-Atlas paper says ScreenSpot entries were removed from its instruction-grounding data; the desktop
data was collected separately and this overlap is not mentioned on the card. Anything built from the
OS-Atlas desktop images (the JEDI relabelling, the OS-Atlas share of Click-100k, the DeskVision captions)
carries the same problem for its macOS part.

## Choice

1. **AgentNet, macOS sessions** for training. It is by far the most real macOS data, covers 263
   application names on many different Macs, and is MIT licensed. The cost is precision: click points
   instead of boxes, and generated instructions.
2. **ScaleCUA-Data, macOS part** looked like the next training source: Retina MacBook screenshots at
   2880x1800 with boxes and points. The second pass found that it shares its Mac and some screens with
   ScreenSpot-v2, like OS-Atlas, so it is usable only if the eight affected ScreenSpot-v2 cases are
   left out of scoring.
3. **Screen2AX** for exact boxes. Screen2AX-Task is a benchmark with human boxes, so it is used here as
   the held-out macOS test set rather than for training. Screen2AX-Tree can give box training data only
   if part of the Task apps are released from the test set, because Tree and Task cover the same apps.
4. **ShowUI-desktop (OmniACT) macOS screenshots**: small, but human boxes and no overlap found.

OS-Atlas macOS has exact boxes and is usable under the same condition. The user accepted that condition
on 2026-11-14: the eight ScreenSpot-v2 cases are no longer scored.

## What is on the Spark

Everything is under `~/bonsai/data/mac/`. Scripts used are in `~/bonsai/data/mac/scripts/`.

**AgentNet macOS** (MIT). The Windows and macOS screenshots sit in one 124 GB split zip in random order.
We read the zip directory from the last segment, selected the macOS pointer steps, and fetched only those
76,538 files by HTTP byte range with curl (28.2 GB), checking each file's CRC32 against the zip directory.

- Raw: `~/bonsai/data/mac/raw/agentnet/` (`agentnet_win_mac_18k.jsonl`, `meta_data_merged.jsonl`,
  `win_mac_images/images.zip`, `images/` with 76,538 PNG, `mac_steps.jsonl`, `cd_index.tsv`).
- Converted: `~/bonsai/data/mac/agentnet/cases.jsonl`, `images/` (60,586 PNG at original size, hard
  links to the raw files), `stats.json`, `check/`.
- 60,586 cases on 60,586 screenshots; every case has a point and no box. 262 application names.
  Actions: 57,695 click, 1,902 double click, 921 right click, 66 triple click, 2 other.
- Resolution (long side): 54,609 cases at 1280 px or less, 4,456 at 1281-1920, 1,314 at 1921-2560,
  207 above. Most common sizes: 1212x758 (20,880), 1192x772 (19,198), 1188x772 (4,785),
  1192x770 (4,446), 1280x720 (3,023).
- Rules: a step is used when its code has exactly one coordinate call and that call is a click,
  double click, right click, triple click or pointer move. Dropped: 8,503 steps the dataset flags as
  incorrect (the click often misses the described element), 5,320 pointer moves followed by a scroll,
  133 points on the screen edge, 1 with no text. The instruction is the step's `action` sentence; the
  point is the normalised coordinate times the stored image size.

**Screen2AX-Task** (Apache-2.0), test only. The numbers below describe the full benchmark; since the app
split of 2026-11-14 `cases.jsonl` holds 2,106 of these cases on 134 screenshots.

- Raw: `~/bonsai/data/mac/raw/screen2ax_task/` (three parquet files, 0.71 GB).
- Converted: `~/bonsai/data/mac/screen2ax_task/cases.jsonl`, `images/` (424 JPEG, original bytes),
  `stats.json`, `check/`.
- 5,775 cases on 424 screenshots from 207 app windows; every case has a box and no point; all
  `split = test`. `meta.small = true` marks one case per screenshot (424 cases) for a quick run.
  `app` is the bundle-style name taken from the source file name.
- Dropped: 152 rows whose declared image size differs from the stored image (other aspect ratio, so the
  box cannot be mapped) and 6 rows with a box outside the image.
- Screenshots are 195 different window sizes; long side above 1920 px for 3,740 cases.

**OS-Atlas macOS** (Apache-2.0), train only — `mac:os_atlas_mac:train`.

- Raw: `~/bonsai/data/mac/raw/os_atlas/` (zip, annotation JSON, 1,312 PNG).
- Converted: `~/bonsai/data/mac/os_atlas_mac/`, 13,988 box cases on 1,095 images: 7,251 on 2880x1800
  full screens and 6,737 on 1440x900 crops of them. The instruction is the raw accessibility name;
  there are no app labels. Seven cases on one truncated PNG were dropped.
- It was first held back because of the ScreenSpot-v2 overlap described above and was released for
  training on 2026-11-14 together with the ScreenSpot-v2 exclusion list.

All downloads were verified after the out-of-memory event on the Spark on 2026-11-14: every whole file
matches the size and SHA-256 published by Hugging Face, and all 76,538 AgentNet screenshots match the
size and CRC32 in the zip directory.

## How the split was made

AgentNet is split by recording session. A session is one `task_id`, one continuous screen recording.

- A session is a test session when `int(sha1(task_id).hexdigest(), 16) % 50 == 0`. That gives 88 of the
  5,120 sessions that have at least one usable step.
- From a test session only clean steps are taken: click, double click or right click, not flagged
  redundant. At most six per session, evenly spaced through the session. The other 596 steps of test
  sessions are discarded, not moved to train.
- Train screenshots that look almost the same as a test screenshot are dropped: 256-bit difference hash,
  32 bits or fewer apart. This removed 1,399 train cases, mostly the same start screen recorded again by
  the same annotator.
- Result: train 60,082 cases from 5,012 sessions, test 504 cases from 88 sessions (3 to 6 each, 32
  application names). No session is on both sides.

Screens from the same application, and from the same annotator's Mac, still occur on both sides; that is
what a session split means. Screen2AX-Task is entirely test. Since 2026-11-14 it is cut down to the apps reserved for testing, and
Screen2AX-Tree supplies training data from the other apps.

## Checks

- Annotated samples: `~/bonsai/data/mac/agentnet/check/` and `~/bonsai/data/mac/screen2ax_task/check/`;
  four AgentNet samples and two Screen2AX samples were also kept under `docs/mac_data_samples/`, which is
  ignored by git and not in this repository (the screenshots show third parties' data).
- AgentNet: 14 samples viewed. In 12 the point sits on the element the sentence names. One sits on the
  border between two menu rows with the neighbouring row highlighted. One was a click on the screen
  edge with a made-up description, which led to the edge filter.
- Screen2AX-Task: 3 samples viewed, all boxes tight on the named control.
- OS-Atlas: 6 samples viewed. Boxes are exact on full screens and on crops; one box lay on an element
  that is not visible on screen.
- Against ScreenSpot-v2 and ScreenSpot-Pro (2,336 images): no AgentNet or Screen2AX screenshot matches.
  The only close pairs were unrelated, nearly blank windows. The comparison works on whole images, so a
  benchmark image that is a crop of a training screenshot would not be found.

## Problems seen

AgentNet
- Screenshots are video keyframes: slightly soft, some with black bars, some caught in the middle of a
  menu animation.
- The mouse pointer is visible and is often on or near the target, because the frame is taken just
  before the click. A model can learn to follow the pointer. On our Mac the pointer will not be there.
- Click points are where a person clicked, not element centres, and can lie near an element's edge.
  There are no boxes, so scoring the 504 test cases needs a distance tolerance.
- Instructions are generated, long (median 18 words) and include the reason for the click.
- `app` is the session's application list, not the app in that screenshot. It is empty for 25 % of
  cases (web-only sessions), and Finder appears as "file explorer".
- Screenshots come from annotators' own computers and show names, e-mail addresses and documents. Keep
  the data private.

Screen2AX-Task
- App windows only, no menu bar or dock, larger than our input size, JPEG.
- Commands are very short and sometimes generic ("open help").

OS-Atlas macOS
- Labels are raw accessibility names, some elements are not visible, one PNG in the zip is truncated,
  and the ScreenSpot-v2 overlap described above.

## Second pass: box data for training

Done on 2026-11-14 after the first pass, because the training loss needs a box per target. Same case
schema and folder layout as `agentnet`; everything converted here has `split = train`. The loader name
is `mac:<folder>:<split>`.

**ShowUI-desktop, macOS screenshots** (boxes and labels from OmniACT, MIT) — `mac:showui_desktop_mac:train`

- Converted: `~/bonsai/data/mac/showui_desktop_mac/`. Raw: `~/bonsai/data/mac/raw/showui_desktop/`.
- 1,037 cases on 61 screenshots from 20 apps; 533 cases at 2880x1800, 504 at 3360x2100. Every case
  has a box and no point. Median box 176 x 66 px.
- macOS screenshots are the ones stored at 2880x1800 or 3360x2100. The 40 screenshots at about
  1920x1080 are Windows and Ubuntu (checked by eye on one screenshot per app folder) and are left out.
- One case per element. The instruction is the label a person gave the box in OmniACT, underscores
  turned into spaces ("week", "search stock", "more options last kingdom"); median 2 words. The three
  GPT-4o rewrites are kept in `meta.alt_instructions` and are not checked.
- Dropped: 23 elements whose label is used for two boxes on the same screenshot.
- Overlap check: no screenshot matches ScreenSpot-v2, ScreenSpot-Pro or Screen2AX-Task.
- 10 samples viewed: all 10 boxes sit on the element the label names. In 3 of the 10 a GPT-4o rewrite
  describes a neighbouring element (the station logo instead of its "..." button, the photo instead of
  its heart button), which is why the rewrites are not used as the instruction.
- Licence: the screenshots and boxes come from OmniACT (MIT). The ShowUI-desktop card states no
  licence; the ShowUI code repository is Apache-2.0.

**Screen2AX-Tree and Screen2AX-Element** (Apache-2.0) — `mac:screen2ax_tree:train`, 27,019 cases after the app split

- Converted: `~/bonsai/data/mac/screen2ax_tree/`. Raw: `~/bonsai/data/mac/raw/screen2ax_tree/` and
  `raw/screen2ax_element/`.
- First result, under the rule "no app and no screenshot that appears in Screen2AX-Task": **1
  screenshot, 24 cases** (the HelloAI chat window). Of the 1,127 Tree screenshots, 522 are the same picture as a
  Task screenshot, 586 more belong to an app that appears in Task, and 18 have no file name.
- How apps were matched. Tree rows carry no file name. Each Tree screenshot was matched by picture to
  the Element and Task rows (same pixel size, thumbnail difference under 1.5 of 255); all 435 Task and
  all 986 Element screenshots are found in Tree. The file name of the matching row gives bundle id +
  window title + timestamp. The app key is the first two tokens of that name (`com_moneywiz`,
  `org_zotero`), or the first token alone when it is not a common reverse-DNS prefix (`jabref`, `md`).
  That is coarser than one app on purpose, because bundle id and window title are joined by underscores.
- Screen2AX-Element has boxes and roles but no labels, so it yields no cases by itself. It was used to
  recover the file names.
- The instruction is synthetic wording built from the accessibility label and role, recorded as
  `meta.synthetic_instruction = true`: "the Prompts button", 'the text "GPT-4o"', "the close button".
- Skipped: containers (groups, rows, cells), empty labels, labels over 80 characters, developer
  identifiers used as labels, an instruction that occurs twice on one screenshot, zero-size boxes,
  boxes not inside the image (43 % of labelled elements: scrolled-out rows), boxes with uniform
  pixels, elements under a sheet or menu.
- Overlap check: no screenshot matches ScreenSpot-v2 or ScreenSpot-Pro.
- Because that rule leaves nothing, the user chose on 2026-11-14 to split Screen2AX by app instead.
  One third of the app keys is reserved for testing (`sha1(key) % 3 == 0`, 27 keys) and the rest of
  Tree trains: 27,019 box cases on 719 screenshots from 64 app keys. The test set is the 2,106
  Screen2AX-Task cases of the reserved keys, on 134 screenshots. This is what is installed now; the
  24-case version is kept in `raw/screen2ax_tree/strict_24_cases_superseded/`.
- 12 samples viewed (2 from the strict set, 10 from the alternative): all 12 boxes sit on the named
  element. Label problems seen: one developer identifier ("shareUnread", now filtered), one map pin
  (now filtered), one radio button whose frame spans the whole row, one button dimmed behind a dialog.

**ScaleCUA-Data, macOS box rows** — `mac:scalecua_mac:train`, 1,398 cases

- Licence found: the dataset repository has no licence file or tag, and two requests asking for one
  (June and July 2026) are unanswered. The project repository that publishes the data, models and code
  says "This project is licensed under the Apache 2.0 License"; the models are tagged Apache-2.0; the
  paper says "We release data, models, and code to advance future research". We took that as
  permission for research use. Use beyond research is not established.
- Fetched: the two macOS grounding archives (1.56 GB and 2.71 GB) and the four macOS grounding
  annotation files; only the 438 referenced screenshots were unpacked. Raw:
  `~/bonsai/data/mac/raw/scalecua/`.
- Converted: 1,433 cases on 436 screenshots, all 2880x1800, all with a box; 1,419 also carry the
  click point of the matching click instruction. The 4,302 box rows are 1,434 elements with three
  descriptions each: the shortest is the instruction, the others are in `meta.alt_instructions`, and
  the click instructions for the same element are in `meta.action_instructions`. 416 screenshots from
  the automatic pipeline have one element each (12 apps); 20 hand-annotated desktop screenshots have
  1,017 elements.
- **Overlap check: positive.** Two App Store screenshots are the same picture as ScreenSpot-v2
  `pc_pl3ry1.png`. The screenshots show the same Mac as ScreenSpot-v2's eight macOS "shop" images and
  as OS-Atlas macOS: same wallpaper, dock and desktop files. The hand-annotated set labels the icons of
  the very dock that `pc_u77zz1.png` ("open the map app") asks about, and the Music Radio page of
  `pc_f6eng1.png` also occurs. No match with ScreenSpot-Pro or Screen2AX-Task.
- Because of that the conversion was first held back. Since the decision of 2026-11-14 it is installed
  at `~/bonsai/data/mac/scalecua_mac/`: 1,398 cases on 401 screenshots (381 from the automatic
  pipeline, 1,017 hand-annotated).
- 10 samples viewed: 9 boxes sit on the described element (menu items, dock and menu-bar icons, a
  browser tab, a dialog button, a checkbox). One box from the automatic pipeline is misplaced: the
  description names the "Food" category in a Pages popover and the box lies over the shapes next to it.
  The archive's own accessibility list for that screenshot has two elements called "Food", and the
  published box belongs to the other one. So the 35 automatic cases whose accessibility label is shared
  by another element of the same screenshot were dropped; that is the difference between 1,433 and
  1,398. Other misplaced boxes may remain.
- The archives also contain what the published rows were made from: accessibility element lists with
  pixel boxes for 636 screenshots (16,543 elements) and hand-made element lists for 24 screenshots
  (1,263 elements). They could be converted with synthetic wording like Screen2AX-Tree; they are not
  converted yet.

**The eight ScreenSpot-v2 cases behind both overlaps**

`pc_b5q1tt.png`, `pc_drcjo3.png`, `pc_f6eng1.png`, `pc_odcu20.png`, `pc_pl3ry1.png`, `pc_u77zz1.png`,
`pc_vcud9k.png`, `pc_zuyj00.png`: the 2880x1800 images with `data_source = shop` in
`screenspot_desktop_v2.json`, one case each. They are left out of all ScreenSpot-v2 scoring from
2026-11-14 on; ids and reasons are in `~/bonsai/ssv2/excluded_overlap.json`. That is what makes ScaleCUA
macOS and OS-Atlas macOS usable for training. We compared every ScreenSpot-v2 image, all three splits,
with both sets again before installing them: apart from these eight, the closest pairs are unrelated
light pages, so no further case was added.

## What to fetch next

1. Convert the accessibility element lists inside the ScaleCUA archives already on the Spark (about
   17,800 more boxes on 660 screenshots of full macOS desktops at 2880x1800).
2. Cap or reweight `org_eclipse` in `mac:screen2ax_tree:train` using `meta.app_key`.
3. The other ScaleCUA macOS archives (trajectories, about 5.8 GB) add click points only, on the same Mac.
4. AgentNetBench (0.43 GB): 39 held-out macOS tasks. Check its task ids against the training sessions.
5. MMBench-GUI (2.2 GB): its macOS grounding cases as a second box-annotated test set.
6. The 4,019 AgentNet macOS drag steps, if drag start points are wanted (their screenshots are in the
   same zip).
