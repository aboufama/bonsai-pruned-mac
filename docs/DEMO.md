# The assistant: running it on the laptop

A menu-bar app in Swift (`assistant/`): Clicky, remade to run on the Mac alone. You type or say a
request; it captures the main display, asks a Bonsai 2 model served by LM Studio, and either points
at the thing ("show me") or carries the request out one step at a time ("do it"). Speech is turned
into text by Argmax's WhisperKit. Nothing leaves the machine.

## State, 15 Nov

| | State |
|---|---|
| Pointing through LM Studio on saved screenshots | **checked**: tuned 9B 16 of 18 known targets, stock 9B 6 of 18 |
| Starting LM Studio's server, loading the model, the status line, putting things back on quit | **checked** by starting the app in a check mode |
| App start, hotkey registration, overlay, pointer, drag line, label, input bar, log window | **started without a crash**; nobody has looked at them or typed into them yet |
| Speech to text (Argmax WhisperKit, `base.en`) | **checked on a sound file**: right text, 0.08 s; the microphone path is unrun |
| Screen capture, system events (click, drag, type, keys, scroll), Return/Esc while another app is in front | written, compiled, **never run** |
| Running with WiFi off | not tried (WiFi was left alone); read from the code and the files: see "With the network off" below |

## What the hackathon asks, and where this stands

| Rule (kickoff slides) | Here |
|---|---|
| Language models must be Bonsai 2 (2B, 4B or 9B) | the 9B, as shipped or with our pointing patch written into its GGUF |
| Must use Argmax "to some capacity" | spoken requests go through Argmax's open-source Swift SDK (WhisperKit). The answer is spoken with the system voice, not Argmax's TTSKit: its model is a 1 GB download and the laptop has about 2.3 GB free |
| Must run on a Mac with WiFi off | nothing in the app needs the network once the files are on disk (they are); not yet tried with WiFi off |
| Submit before noon: names, one sentence, a GitHub link, a video under 2 minutes | this repository |
| Accessibility / computer-use track is judged by LM Studio | the model is served by LM Studio |

## The one command

```bash
assistant/run.sh          # from the top of this repository
```

It builds only when a source file changed, then starts the app: a leaf appears in the menu bar and
the log window opens. Quit in the leaf menu, or Ctrl-C in Terminal, ends it and puts LM Studio back
as it was.

## What to do once

1. **Permissions for Terminal** (System Settings > Privacy & Security). The app asks for each:
   - **Screen & System Audio Recording**: needed for everything. After allowing it, quit and start again.
   - **Accessibility**: needed only for "do it".
   - **Microphone**: asked at the first spoken request.

   The permissions belong to the program the command was typed in: Terminal, or Claude if it is
   started from the Claude app's terminal panel.
   Use the same one every time. The app shows nothing in that terminal: it is the leaf in the menu bar.
2. **The hotkeys:** control-option-space opens the bar to type (control-option-B does the same, in
   case the first is taken). Control-option-V starts a spoken request and ends it.
3. **Only if LM Studio's server is set to require a token:** leaf menu > "API token…". It is stored
   in the macOS Keychain, read when a request is sent and sent as the bearer token; it is never in
   the settings, the log or the code. With no token stored, none is sent.

LM Studio needs nothing by hand. On start the app starts its server if it does not answer
(`lms server start`), loads the chosen model after unloading any other loaded language model
(16 GB: one at a time; context 8,192 tokens), and says how it went in one line (first line of the
leaf menu, the leaf's tooltip, the log). On quit it unloads what it loaded, loads again what it
had unloaded, and stops the server if it started it; "Keep the model loaded on quit" skips that.
LM Studio has no SDK for Swift (TypeScript and Python only), so this is its REST API
(`/api/v1/models`, `/models/load`, `/models/unload`, `/v1/chat/completions`) plus `lms` for the server.

For the demo, close what else is open: with the model loaded and many other programs running,
free memory fell to 21% and macOS added 2 GB of swap.

## Using it

Return carries the request out. A question is answered by pointing instead.

| Type in the bar (control-option-space), then **Return** | What happens |
|---|---|
| `click the search field` · `press on the calendar icon` · `double-click the Notes icon` · `right click the desktop` | The model finds the thing, the pointer flies to it, the click is made. |
| `type "hey" into the message box` | A click on the place, then the typing. |
| `drag the report to the Trash` | The model finds both ends; the drag is made. |
| `scroll down in the sidebar` · `press cmd+t` · `press enter` | Done directly. |
| `click the search field, then type "apple" and press enter, then click the first result` | Parts joined with "then", "and", ";" or full stops run one after another; each new screen is read again. |
| `turn on dark mode` (anything that is not spelled out as steps) | The model plans one step at a time, up to 12, until it says done. Weaker: neither 9B was taught this. |
| `where is the search field?` · `show me the settings` | Show me: pointer, label, the model's sentence, spoken. Nothing is clicked. |

- **Command-Return** only points, whatever the request (a safe preview).
- **control-option-V**, say it, **control-option-V** again: the same, spoken (with shift: only point).
- Steps run without asking; **Esc** stops everything at once. To approve each step with Return
  instead, untick "Run steps without asking" in the leaf menu.
- The first action needs **Accessibility** allowed for Terminal; until then the app stops and says so.

Leaf menu: the status line, model, image size (1280 or 896 px), server address, API token, keep
the model loaded on quit, read the screen as soon as the bar opens (on), keep the screen read in
the background (off), lab prompt layout (off), answer in a sentence, speak the answer, run steps
without asking (on), plain step prompt (for a model trained on `next_step`), log, permissions.

The **log window** is how to judge the model: what was asked, what the model wrote word for word,
the point on the 0 to 1000 grid and on the screen, the action, the seconds and tokens of each
request, and how much of the wait the read-ahead saved. Also in `~/Library/Logs/BonsaiAssistant/assistant.log`.

## Speed, and what was done about it

Measured on this laptop (M4, 16 GB) through LM Studio, tuned 9B, saved screenshots:

| | 1280 px | 896 px |
|---|---|---|
| First question about a screenshot (the model reads it) | about 11 s (10 to 14) | about 5.6 s (5 to 7) |
| Each further question about the same screenshot | about 1.1 s | about 1.05 s |
| Known targets hit, of 18 | 16 | 14 |

Reading the screenshot is the whole cost; the answer itself is 11 tokens. So:

- **The screenshot goes in its own message**, the question in the next. Only then can the server
  keep its read for another question (these models can only go back to the start of a message).
  With screenshot and question in one message, the layout the lab measured with, every question
  pays the full read: 12 to 22 s each here, 15 of 18 hit. That layout is the "lab prompt layout" switch.
- **The screen is read as soon as the bar opens** (or listening starts), while the request is
  being typed or spoken. If the screen still shows the same thing when the request is sent, the
  wait is what is left of the read plus about a second.
- **"Keep the screen read in the background"** reads the screen whenever it has changed and
  settled, so a request is answered in about a second at any time. It keeps the Mac working; off
  by default, worth switching on for a demo. Not run yet.
- In "do it" the step and the pointing request share one read; each new screen after an action
  costs a new read.
- Thinking is switched off with `reasoning_effort: "none"`; without it the model thinks first and
  an answer takes about 27 s.

## With the network off

What the running app talks to, read from its code and the files on disk:

| Part | Network? |
|---|---|
| The model | One address only, the server in the settings: `http://localhost:1234/v1`, LM Studio on this Mac. It is the app's only network call (`LMClient.swift`). |
| Starting LM Studio's server | `lms server start`, a local program. Whether LM Studio itself wants the network when started without it was not tried. |
| Speech to text | Argmax's open-source SDK; no account, key or licence check. The model (`~/Bonsai-demo/models/argmax/.../openai_whisper-base.en`) and its tokenizer (`.../models/openai/whisper-base.en`) are on disk and the app names both folders with downloading switched off. One fault was found and fixed here: without the tokenizer folder named, the SDK looked under `~/Documents/huggingface` and fetched the tokenizer from the network. |
| Speaking, screen capture, events, Keychain | macOS itself. |
| `run.sh` | Starts the program as it is when no source file is newer; otherwise it builds from the packages already fetched (`--force-resolved-versions`). Building with the network off was not tried, so do not edit the sources right before going offline. |

Speech was then checked with the network denied to that one process (a sandbox, WiFi untouched):
it loaded from disk and read the test sentence correctly (9.8 s to load cold, 0.62 s to read).

**The one thing to check with WiFi off before the demo:** that LM Studio's server starts and loads
the model. Everything else has been run or read.

## Models in LM Studio

The model is a setting: the leaf menu lists what LM Studio has, and choosing one unloads the
previous model and loads the new one. Until one is chosen there, the app picks for itself each
time it checks the server: a tuned Bonsai before one as shipped, the 4B before the 9B, and only
models LM Studio lists with vision. So a tuned 4B becomes the default the moment it is in LM
Studio with its vision file, with no change to the code.

| Name in the app | What | Vision |
|---|---|---|
| `bonsai-2-9b-pointer` (default until a tuned 4B is there) | the tuned 9B pointer, `Bonsai-2-9B-point-v3-mixed896-Q2_0.gguf` | yes |
| `ternary-bonsai-2-9b` | PrismML's 9B as shipped, for comparison | yes |
| `ternary-bonsai-2-4b`, `-2b` | as shipped | **no vision file yet**: answers about the screen are guesses. A tuned 4B needs the 4B's own vision file (`weights/export_mmproj.py` on the 4B pack, about 0.7 GB) beside it under a name starting `mmproj-` |
| `ternary-bonsai-2-9b-mlx` | PrismML's MLX pack through LM Studio's MLX engine | listed with vision; not tried |

The vision file for both 9B models is `~/Bonsai-demo/models/bonsai2-gguf/9B/Ternary-Bonsai-2-9B-mmproj-F16.gguf`
(0.92 GB, built from the MLX pack's own vision tower with `weights/export_mmproj.py`). LM Studio
finds it through a link beside each model whose name starts with `mmproj-`.

## A demo that stays on what was checked

Requests of the kind that hit in the check: a named button or key ("the Automate button", "the
divide key"), a field ("the search field"), a photo by what it shows, a named command ("create a
new file", "open the settings"). The two misses were tiny targets: a single day in a small
calendar and a 12-pixel "+" in a corner. Avoid those on stage.

1. Switch on "Keep the screen read in the background" and wait for one read (about 11 s).
2. With an app in front, control-option-V, say "where is the search field?", control-option-V. Pointer and spoken sentence.
3. Type a second question about the same screen: about a second.
4. "Do it": something of one or two steps (a button, then typing). Each new screen costs a read.
5. Show the log: every number above is there, and nothing went over the network.

## Checking the model without the screen

```bash
assistant/run.sh --samples ~/Bonsai-demo/samples --out ~/Bonsai-demo/build/assistant-samples
```

prints HIT or MISS and the seconds for every request of `hints.json` and writes each screenshot
with the point (red ring) and the target (blue box) drawn on it. The server must be up with a model
loaded, for example while the app runs. Also `--point IMAGE "what"`, `--step IMAGE "request"`,
`--transcribe SOUND`, `--models`, and `--model ID`, `--side 896`, `--one-message`, `--tools`.
`run.sh --test` runs the core's 95 checks.

## Not built, or weak

- Speaking the answer with Argmax's TTSKit (system voice instead; see the table above).
- Snapping to the nearest accessibility element; a yes/no check after an action.
- Steps: neither 9B was taught `next_step`. Asked for as JSON the tuned model gave sensible first
  steps on two screenshots ("click New File...", "click Search bar at the top left"); whole tasks
  are untested.
- The 4B has no vision file, so it cannot be compared yet.

## If something goes wrong

- The status line never says "ready": the log says at which point (server start, list, load). Open
  LM Studio once, start the server in its Developer tab, then "Check the server again" in the
  model menu.
- The pointer is wrong everywhere: the model has no vision file (the status line says so), or the
  display is scaled in a way the log's "pixels per point" line will show.
- The input bar does not take typing, or Return / Esc do not reach the app while another app is
  in front: these are the unrun parts.
- Fallback for showing pointing alone: the playground (`playground/server.py`, port 8791).
