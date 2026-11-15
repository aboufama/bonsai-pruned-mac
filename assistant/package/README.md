# Bonsai assistant: run-anywhere package

The assistant app as one folder that runs from the copied files alone: Apple silicon, macOS 14
or later, no compiler, no LM Studio. Made by `assistant/package.sh` in the repository; `VERSION`
says which commit.

**Run in a virtual machine only.** The unattended batch path and the plain-server mode drive the
desktop, so they were not run on the laptop they were written on. They were first run, and are
used, in the macOS 26 virtual machine of [docs/REALMAC.md](../../docs/REALMAC.md). If something
is off, the log file says where.

## What is in the folder

| File | What |
|---|---|
| `bonsai-assistant` | The app (arm64, ad-hoc signed by the linker). It links only to macOS itself. |
| `swift-crypto_Crypto.bundle`, `swift-transformers_Hub.bundle` | Small resource folders of two libraries built into the app. Keep them **beside** the executable. |
| `run-batch.sh` | The batch command below, with the VM host's server as the default. |
| `requests-example.txt` | A file of requests to try. |
| `planner-system-candidate.txt` | A wording of the planner's system text under test (not the default). Use it with `BONSAI_PLANNER_SYSTEM_FILE`. |
| `voice-example-open-notes.wav`, `voice-example-dark-mode.wav`, `voice-example-silence.wav` | Three small sound files (the system voice saying "Open Notes" and "Turn on dark mode", and two seconds of silence) for trying the voice path with no microphone. |
| `demo/` | For rehearsing the demo video: `requests-demo.txt` (its spoken lines as a batch), `say-*.wav` (each line in the system voice, for `--mic-file` or `--voice-file`), `Presentation (stand-in).pdf` (replaced by the real deck), `recording-example.mp4` (a clip with a voice on it, for the captioning). |
| `VERSION` | Commit, build time, checksum of the executable. |

Not included: the speech model (about 150 MB). A batch never listens, so it is not needed.

## Putting it in place

Copy the folder anywhere, for example `~/bonsai-app/`. If the copy went through
something that marks files as downloaded, clear the mark once:

```sh
xattr -dr com.apple.quarantine ~/bonsai-app
```

## The batch command

```sh
BONSAI_SERVER=http://192.168.64.1:1234 BONSAI_PLAIN_SERVER=1 \
  ~/bonsai-app/bonsai-assistant --batch requests.txt --out steps.json --timeout 180 --log run.log
echo "exit code $?"
```

or the same thing: `run-batch.sh requests.txt steps.json`.

- `requests.txt`: one request per line; lines starting with `#` are skipped.
- Each request is carried out as if typed into the assistant. **It really clicks and types.**
- It must be started inside the logged-in user's window session (Terminal, `tart exec` through
  the guest agent, a LaunchAgent): it draws a pointer and reads the screen.
- It starts as a menu-bar app with no Dock icon, shows no log window, and quits by itself.

### What it writes

`steps.json` is rewritten after **every** request, so it is there whatever happens later:

```json
[
  {
    "request": "make a new note that says buy milk",
    "kind": "planned",
    "model": "…",
    "ending": "Done: The note is made. (4 steps)",
    "ok": true,
    "timed_out": false,
    "seconds": 21.4,
    "planner_system": "built in",
    "spoken": "The note is made.",
    "steps": [
      { "step": 1, "tool": "open_app", "line": "open_app Notes", "result": "ok",
        "plan_seconds": 1.1, "step_seconds": 3.0, "tokens": "…" }
    ]
  }
]
```

- `kind`: how the app took the request: `direct` (no model: apps, links, windows, dark mode,
  volume, folders, a calendar event), `planned` (the model, one `next_step` call per step),
  `spelled out` (a request that says its own clicks and typing), `answer` (a question answered
  in words), `point` (a question answered by pointing), `selected text`.
- `ok` is true when `ending` starts with `Done` or `Answered`. Otherwise `ending` starts with
  `Stopped`, `Not finished` or `Error` and says why.
- A request carried out in parts (see below) also has `parts`: each part's words and its own
  kind. Its `kind` stays one word: `direct` when every part is, else `planned` when any part
  is. Each step carries the number of its `part`; `step` starts at 1 again in each part.
- `result` of a step: `ok`, `nothing changed`, `not found on the screen`, or why it failed.
- `spoken`: what the app says aloud at the end when spoken replies are on: the planner's closing
  sentence, the answer to a question, or "Done.". A batch writes it here and plays no sound.

The log (`run.log`) is the readable account: what the model was sent in outline, what it wrote
word for word, the seconds and tokens of each request.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | every request ended well |
| 1 | at least one request stopped, failed or ran out of time (the others still ran) |
| 2 | the requests file could not be read or holds no request, or the file named for the planner's system text could not be read |
| 3 | the server never became ready (it is tried for about 90 s) |
| 4 | a permission is missing; the message says which |

The reason is also printed to standard error.

## Settings

Each is a flag or an environment variable; a flag wins. Nothing has to be set up beforehand and
nothing is stored.

| Flag | Environment variable | Default | What |
|---|---|---|---|
| `--server URL` | `BONSAI_SERVER` | `http://localhost:1234/v1` | The model server. `/v1` is added if left out. |
| `--plain-server` | `BONSAI_PLAIN_SERVER=1` | off | Any OpenAI-compatible server. Nothing is started or loaded through LM Studio, `lms` is never called, the model is the one the server lists, and it is taken to have vision. |
| `--model ID` | `BONSAI_MODEL` | the server's | Only needed if the server lists several. |
| `--batch FILE` | `BONSAI_BATCH` | none | The file of requests. Turns on unattended running. |
| `--out FILE` | `BONSAI_OUT` | `~/Library/Logs/BonsaiAssistant/batch.json` | The steps file. |
| `--log FILE` | `BONSAI_LOG` | `~/Library/Logs/BonsaiAssistant/assistant.log` | The log; lines are added to it. |
| `--timeout SECONDS` | `BONSAI_REQUEST_TIMEOUT` | 180 | Time allowed for one request; then it is stopped and marked `timed_out`. |
| `--side 1280` or `896` | `BONSAI_IMAGE_SIDE` | 1280 | Longer side of the screenshot that is sent. |
| `--unattended` | `BONSAI_UNATTENDED=1` | on in a batch | Never ask a person anything. |
| `--skip-permission-check` | `BONSAI_SKIP_PERMISSION_CHECK=1` | off | Go on even if macOS reports a permission as missing. |
| `--own-permissions` | `BONSAI_OWN_PERMISSIONS=1` | off | See "Permissions". |
| `--planner-system FILE` | `BONSAI_PLANNER_SYSTEM_FILE` | the built-in text | A text file whose contents replace the planner's system text for this run. See below. |
| `--second-look` | `BONSAI_SECOND_LOOK=1` | off | A closer second look for things found on a screenshot. See below. |
| `--speak` | `BONSAI_SPEAK=1` | off | Spoken replies for this run (the system voice). Never in a batch. |
| `--pointer-url URL` | `BONSAI_POINTER_URL` | none | A helper that only points. See "A helper that only points". |
| `--presentation FILE-or-LINK` | `BONSAI_PRESENTATION` | the deck in `~/Bonsai-demo/demo` or `demo/` beside the program | What "bring up the presentation" shows. |
| `--mic-file FILE` | `BONSAI_MIC_FILE` | none | A sound file read in place of the microphone whenever the app listens. See "Speaking". |
| `--voice-file FILE` | `BONSAI_VOICE_FILE` | none | A batch run whose first request is what the sound file says. Turns on unattended running, with or without `--batch`. |
| `--own-models DIR` | `BONSAI_OWN_MODELS` | `~/Bonsai-demo/models/argmax` | The folder the speech model is kept in. |
| `--plan-everything` | `BONSAI_PLAN_EVERYTHING=1` | off | Whatever is not a question goes to the planner, also what the app would do directly or what spells its own steps out. For measuring the planner on whole tasks. |

Unattended means: no permission question is raised, no log window, no speech, the Keychain is
not touched (no API token is sent), steps never wait for Return, results are not left on screen,
and the screen is not read ahead in the background.

## Trying another wording of the planner's system text

```sh
BONSAI_PLANNER_SYSTEM_FILE=~/bonsai-app/planner-system-candidate.txt \
BONSAI_SERVER=http://192.168.64.1:1234 BONSAI_PLAIN_SERVER=1 \
  ./bonsai-assistant --batch requests.txt --out steps-candidate.json
```

- The file's contents take the place of the built-in system text, word for word. Spaces and
  line ends before and after the text are dropped; everything inside is kept.
- Nothing else changes: the same `next_step` tool, the same user message, and the same sentence
  added to the system text when the step has to be asked for as JSON.
- Without the variable the built-in text is used, as before.
- A batch whose file cannot be read, or is empty, ends at once with exit code 2 rather than
  quietly measuring the built-in text.
- Every request in the steps file says which text it ran with: `"planner_system": "built in"`
  or `"file /path, N characters"`. The log's first lines say it too.
- `BONSAI_PLANNER_SYSTEM_FILE=file ./bonsai-assistant --planner-prompt` prints exactly what
  would be sent, with no server.

## What the app does around the planner

These were added after the first package; all show in the steps file.

- **Return is not pressed twice in a row.** If the model asks for `key return` right after a
  step that already pressed Return (a `type` ending in Return, or `key return`), the key is not
  pressed. The step's `result` is `not pressed: the step before already pressed Return`, and
  the planner sees that in "Done so far". If its next answer is Return again, the request ends
  with `Stopped: the model kept asking for Return after it had been pressed`.
- **Requests that are one shortcut are pressed directly**, with no model (`kind` is `direct`):
  close this tab or window, new tab, new window, reload, go back or forward, undo, redo, select
  all, copy, paste, save, print, minimize this window, hide this app, zoom in or out, full
  screen. Only the whole phrase counts ("close the Mail window" still goes to the model).
  `--plan-everything` sends these to the planner too.
- **Places are opened by name, with no model** (`kind` is `direct`):
  - a pane of System Settings: "open Wi-Fi settings", "open the Sound pane in System Settings",
    "open System Settings > Displays", "go to Battery". Known panes: Wi-Fi, Bluetooth, Network,
    VPN, Notifications, Sound, Focus, Screen Time, General, Appearance, Accessibility, Control
    Center, Siri, Spotlight, Privacy & Security, Desktop & Dock, Displays, Wallpaper, Screen
    Saver, Battery, Lock Screen, Touch ID & Password, Users & Groups, Internet Accounts, Game
    Center, Keyboard, Mouse, Trackpad, Printers & Scanners, Software Update, Storage, Date &
    Time, Language & Region, Sharing, Time Machine, Login Items, About, Apple Account. They are
    opened with macOS's own `x-apple.systempreferences:` links; the identifiers were read from
    macOS 15.6 and compared with the same folder of the macOS 26.6 guest (also AirDrop &
    Handoff, Family, Transfer or Reset, Wallet & Apple Pay, Game Controllers). A link is never
    trusted: after it, the window's title is compared with the pane's names (macOS opens
    Settings even for a link it does not know, and then shows General). If it is not that
    pane, in this order: the pane is chosen by its name in the sidebar; if General came up,
    by its name in General's own list (Sharing, Time Machine, Storage, About are listed
    there); if the pane does not exist on this macOS (26.6 has no Screen Saver or VPN pane),
    the pane its settings are kept in is opened (Wallpaper, Network) and the step is reported
    as not done, `this macOS has no Screen Saver pane; Wallpaper, where its settings are kept,
    is open instead`, so the planner takes over from there; otherwise (Trackpad on a Mac
    without one) the step fails with `System Settings has no … pane that could be opened` and
    the planner takes over.
  - a pane wins over an app when the request says "settings": "open Bluetooth settings", "open
    Siri settings", "open Time Machine settings" and "open Sharing settings" are panes (they
    used to open Bluetooth File Exchange, Siri, Time Machine or Screen Sharing and press
    command-comma). Without "settings", an app of exactly that name still wins.
  - an app's own settings: "open Safari settings" opens the app and presses command-comma.
  - a folder: "go to the Downloads folder in Finder", "open documents", "open ~/Projects",
    "go to /Applications/Utilities" (Desktop, Documents, Downloads, Applications, Pictures,
    Movies, and Music or Home when "folder" is said; or any path).
  - a site by its name: "open YouTube", "go to the nytimes website" (about forty well-known
    names; "the X website" with one unknown word becomes www.X.com). An app of that name wins.
- **The Dock's plain settings are set directly**: "turn on Dock auto-hide", "stop hiding the
  Dock", "move the Dock to the left", "make the Dock bigger", "set the Dock size to 40%", "turn
  off Dock magnification". The Dock's preferences are written, the Dock is started again and
  the value is read back.
  Said another way they are direct too, as long as the request is an order about the Dock that
  names a side, a size, hiding or magnification: "Move the Dock back to the bottom of the
  screen", "Enlarge the Dock icons", "Stop the Dock from magnifying". Adding an app to the Dock
  or removing one is still planned.
- **Dark and light mode are direct however they are asked for**: any order to switch that names
  dark or light (or night) mode, appearance or theme: "Make my Mac use the dark appearance",
  "Set the appearance to Dark", "Take the Mac out of dark mode", "go back to light mode". A
  question ("is dark mode on?") is answered, "dark mode settings" is the pane, and a request
  to write or search something about it is planned.
- **A picture of the whole screen is command-shift-3**: "take a screenshot", "take a screenshot
  of the whole screen", "press the shortcut that takes a full screenshot". A picture of a
  window or a selection is planned.
- **A calendar event with no day or time** ("create a calendar event called Lunch with Sam",
  "make a new event: Budget meeting") is made for the next full hour today, instead of failing
  over to the planner. With a day or a time in the request it is as before.
- **More words join direct requests**: besides "then" and "and open …", a request is also cut
  before "and make / create / add / schedule / turn / set / put / take / mute", so "Open
  Calendar and make a new event: Budget meeting" and "open Notes and turn on dark mode" are
  direct as a whole. If any part is not direct, the whole request is planned as before.
- **A new folder with the place said first**: "On the Desktop, make a new folder named Trip
  Photos" is direct, like "make a new folder named Trip Photos on the Desktop".
- **A direct route checks its effect, and otherwise the planner takes over.** A new folder is
  looked for on disk; volume, mute and dark mode are read back; a window move is read back; a
  folder or a settings pane must actually be in front; for a calendar event the app answers
  Calendar's question (OK) and the step only counts when that question is gone. When a direct
  step does not have its effect, the whole request goes to the planner, whose "Done so far"
  starts with what was done and what failed. `kind` stays `direct`; the planner's steps follow
  in the same `steps` list.
- **An opened app is brought to the front and waited for.** After `open_app` the app is
  activated, raised through Accessibility if it is still behind, and the step returns only
  when it is frontmost (and has a window, if one comes). If it never comes forward the result
  is "… was opened but did not come to the front"; in front with no window is told to the
  planner as a note on the step.
- **A call that cannot be used is put right or explained.** `open_app`, `open_url`, `look` or
  `menu` that names nothing but gives a listed id becomes a click on that control; a path or
  keys written in `text` are moved; a click with an unknown id and a target in words uses the
  words. Otherwise "Done so far" gets a line such as `open_app (not carried out: open_app
  needs the app's name in app)`. Only three unusable answers in a row end the request.
- **Steps with no effect are counted.** The very same step right after it changed nothing is
  not carried out again; after three scrolls in a row a fourth is not; once scrolling (or
  clicking) has changed nothing twice, no more of that kind until a step of another kind has
  had an effect. Each refusal is a line in "Done so far" (`… (not carried out: …)`) and a
  step in the steps file; three refusals in a row end the request with `Stopped: the model
  kept repeating steps that have no effect`.
- **A scroll with no place** goes to the middle of the largest scrolling area of the front
  window, not to wherever the mouse happens to be.
- **The list of controls** is read in one round trip per element, and a control with no name
  of its own takes the label beside it in its row (switches, pop-ups, sliders in System
  Settings) or the text inside it (rows of a sidebar). `bonsai-assistant --count-controls`
  prints how many controls of each kind it finds in the window in front, and how long it took,
  without printing any name.
- **The spelled-out parser** no longer takes a request that starts with open, launch or go to
  as one click, and without quotation marks only "type" is literal.
- **The planner's `open_app` and `open_url` are read the same way.** If the text of `open_app`
  is not an app on this Mac, or the text of `open_url` is words rather than an address, it is
  looked up as a settings pane ("Sound settings", "System Settings > Wi-Fi"), a folder
  ("downloads folder", "~/Projects") or a site ("youtube") before the step is reported as
  failed. Nothing in the format changes.
- **App names are read the way people say them.** "the Finder app", "Finder.app" and "my
  calendar app" are Finder and Calendar, in requests and in the planner's `open_app`. For the
  planner's `open_app` only, a name one letter off (two for a name of eight letters or more)
  is the nearest app. An `open_app` with no app takes the app the task speaks of, when it
  speaks of exactly one (by name outside quotation marks, or by a word that means one: remind,
  note, contact, event, email, terminal, calculate) and that app is not already in front.
- **Two more things the spelled-out parser leaves alone**: "move" with the Dock, a window or
  the pointer, or to a side of the screen (not a drag), and "press" with a shortcut or keys to
  work out (not a click). "move the file to the Trash" and "press the Send button" are as before.
- **A request that says one thing comes after another is carried out in parts.** It is cut
  only at "then", "and then", "after that", "afterwards" and ";" (never inside quotation
  marks), and only when the whole of it would otherwise go to the planner. Each part is a
  request of its own with its own "Done so far", so "Open python.org, then write a note saying
  …" opens the site directly and plans only the note. The next part starts when the one before
  ended with `Done` or `Answered`; otherwise the request ends with `Stopped at part 1 of 2 (…):
  …`. A part that refers back ("put the file inside it", "open that folder") starts with the
  earlier part's lines in its "Done so far". A whole request that is direct or spelled out is
  not cut. The ending of a request in parts is `Done, 2 parts: … | …`.
- **A `done` that says it is not done is not taken as done.** When the sentence says more is
  needed, asks the user something or gives up ("Now I need to…", "I'm sorry", "could you
  clarify", "is not available", "I don't see"), nothing is recorded and the planner is asked
  once more on the screen as it then is. If it says so again, the request ends with `Not
  finished: <sentence>` (`ok` false, the step's `result` is `not finished`) and the sentence is
  shown as it is, with no check mark.

- **Whether a step changed anything is told more exactly.** The comparison now also takes the
  full length and the end of every field's text (the list shows only 40 characters, so typing
  into a long text, a Terminal window for one, used to count as no change) and which element
  has the keyboard (so a click that only puts the cursor in a field counts as a change).
- **Typing replaces what a one-line field holds.** Before typing into a text field, search
  field or combo box that already has text, everything in it is selected, so "Groceries" typed
  into a field holding "New Folder" gives "Groceries". Not for a text area, and not when the
  step before was typing too with no control named.
- **Return before `done` when the typed text is still in a one-line field.** When `done` comes
  directly after a `type` with no Return, that typing changed something, and the keyboard is
  in a one-line field that is not empty and not part of a web page, Return is pressed first.
  The `done` step in the steps file then has `before: key return (…)`. A field in a web page
  is left alone, so nothing is ever submitted to a site this way.
- **Typing that goes nowhere is given somewhere to go.** When a `type` with no id changes
  nothing: if the front window has exactly one text area, it is clicked and the text is typed
  again; otherwise, in Notes, Reminders, TextEdit, Contacts, Calendar and Stickies, command-N
  is pressed (once in a request) and the text is typed again. "Done so far" then has the extra
  line in the usual style (`click "…"` or `key cmd+n`) before the `type` line, and the step in
  the steps file has `before: …`. If it still changes nothing the line ends `(nothing
  changed)` as before.

## The pointer always shows what is done

Accessibility decides where a thing is; the pointer goes there and does it. No step that acts
on the screen is carried out with the pointer parked.

- **Clicks** (by the planner's number, by name, by the pointing model) fly the pointer to the
  control and click there with a real click.
- **Opening an app** flies to its Dock icon and clicks it, when it is in the Dock. The app is
  then brought to the front whatever the click did.
- **A window's own buttons** (close, minimize, full screen) are clicked in the window's corner.
- **A menu command** (`menu File > New Window`, or a request that names one): the pointer
  goes to the menu's title and clicks it, the menu opens on the screen, the pointer goes to
  the item and clicks it. If the menu or the item cannot be placed, the menu is closed again
  and the item is chosen through Accessibility as before. Two-level paths only.
- **Typing** with no control named: the pointer goes to the field that has the keyboard first.
- **A file on the Desktop** (the presentation, a video) is double-clicked on its icon when the
  icon is not covered; **dark mode** is chosen by clicking Dark or Light in System Settings
  (the first row of choices), read back, with the system's own switch as the fallback.
- **A step with no place of its own** (the volume, a Dock setting, a new folder, a key, a
  link) still gets a flight, to where its result shows: the Dock, the controls at the right of
  the menu bar, the new folder's icon, else the title bar of the window in front.
- **Steps file:** every step has `flew` (true when the pointer flew for it), and then
  `flight_from` and `flight_to` as `[x, y]` in the screen points clicks use.
- A flight to a target takes 0.55 to 1.0 s by distance; a flight back to the cursor 0.35 to 0.9 s.

## Pointing: Accessibility first

For every request that points at or presses one thing ("where is…", "show me…", a `look`
step, a click or a drag named in words), in this order:

1. **By name, no model, no screenshot.** The names the Mac itself gives are searched: the
   front window's controls (an open menu's items first), the menus of the menu bar, the Dock's
   icons. Words for the kind of thing, its place and the asking ("the", "button", "in the
   toolbar", "where is") are left out of the comparison. One control whose name is exactly the
   remaining words, or failing that one whose name holds them all: its centre is used at once.
2. **Several could be meant** (two of the same name, or names that only share a word): one
   planning turn in text over just those, as `Controls`, picks one. No screenshot. If it
   chooses none, the next step is taken.
3. **No name fits**: the pointer reads the screenshot (the helper if it is up, else the
   language model), and the answer still snaps to the control under it.

The log line of each pointing says which was used, and the step in the steps file has
`found_by`: `accessibility`, `planner over accessibility` or `pointer`. "Find Controls by
Name First" in the leaf menu switches steps 1 and 2 off. The planner's format is unchanged.

## For the demo video

- **A spoken name is dropped**: "Clicky, bring up the presentation", "hey Bonsai, open Notes".
- **"Bring up the presentation"** (also "show my slides", "start the slideshow", "go back to
  the presentation"), `kind` direct, tool `present`: the app in front is hidden; the deck is
  opened in its own app (a link: in the browser); its window is made to fill the screen. The
  deck is `--presentation` (a file or a link), else the newest file named like presentation,
  slides or deck in `~/Bonsai-demo/demo`, else in `demo/` beside the program (Keynote,
  PowerPoint, PDF, web page, picture, in that order). The user's own folders are not searched.
  In Keynote the slideshow is started in a window (`Play > Play Slideshow in Window`, else
  `Play > In Window` then `Play > Play Slideshow`); in Preview the sidebar is hidden and the
  page fitted. The Keynote part has not been tried: Keynote is on neither Mac.
- **"Write down what you can help me with"** (also "write some things you can help me do",
  "make a note of what you can do", "write a note about <something>"), tool `write_note`:
  the model writes four short lines as a language model (the same every time: nothing is
  random), and the app opens Notes, makes a new note and types a title and the lines a word
  at a time. If the model writes nothing usable, four lines of the app's own are typed and the
  step's note says so. A note whose words are given ("a note that says …") is unchanged.
- **"Caption the video I just recorded"** (also "put subtitles on my last recording"), tool
  `caption_video`, no language model: the newest `.mov`/`.mp4` in Movies, on the Desktop or in
  Downloads has its sound read by Argmax WhisperKit with the time of each stretch; the words
  become subtitles of at most 42 characters; they are drawn on a copy written to
  `~/Movies/<name> (captioned).mov` with a `.srt` beside it; the copy is opened in QuickTime
  Player and played. The recording itself is not changed. Photo Booth's own library cannot be
  read without Full Disk Access, so a clip recorded there has to be dragged out first.
  Without the app: `bonsai-assistant --caption-video VIDEO [OUT]` does the whole of it and
  prints the subtitles; `--burn-captions VIDEO OUT` draws three made-up lines with no speech
  model (tried on this Mac: the lines show at their times and the copy keeps its sound).

## From the demo-beats check on build c483346

- **A site named with a browser** ("open apple.com in Safari", "go to example.com/docs in
  Chrome", "open YouTube in Brave") opens exactly that address in that browser. It used to
  become `www.applecom.com`.
- **An email draft is checked.** After the mail link is opened, a window of the mail app must
  show a message with the draft's subject. If the mail app shows its add-an-account sheet
  instead, the step fails with `Mail has no account set up, so no draft could be opened`, the
  user is told that, and the planner does not take over. A browser named in the request
  ("… in Safari"), or one just opened, takes the draft as Gmail's compose page; the step's
  note says which it was.
- **A question about a menu is answered from the menu itself**, with no model: its enabled
  items in order, eight at most, then how many more. `how` is `the menu itself`.

## A helper that only points

Optional, and off unless named. With `BONSAI_POINTER_URL=http://127.0.0.1:1235` (or
`--pointer-url`), whenever the app would ask the language model where something is on a
screenshot (a pointing request, a `look` step, a click or a drag named in words, a spelled-out
click), it first asks a small local server that only points (Bonsai-Pruned 4B with its
pointing decoder; `assistant/tools/pointer_server.py`). Planning, answering questions and
rewriting stay with the language model. Unset, nothing changes.

- At start: `GET /health` once, 1 s allowed. The log says whether the helper answered. If it
  did not, it is still tried on each pointing request (it may come up later).
- For each pointing: `POST /point` with `{"image_b64": …, "request": …, "looks": 1}`: the very
  picture the language model would have been sent (PNG, base64) and the same words for the
  target. With `--second-look`, `"looks": 2`, and the app's own second look is left out (it is
  only for the language model).
- The reply `{"x", "y", "seconds", "read_seconds", "cached"}` gives x and y as fractions of the
  picture's width and height. They are put on the 0 to 1000 grid the language model answers
  on and go to the screen the same way, including the snap to a named control.
- **Any failure falls back to the language model for that request**, with one log line saying
  why: no connection, a status other than 200, a reply after 30 s, x or y missing or outside
  0 to 1. After a failure that took more than 5 s the helper is left alone for a minute, so a
  helper that hangs does not cost 30 s on every step. The helper is never required.
- Steps file: every step that had something pointed at has `pointer`: `bonsai-pruned-4b` or
  `language model`.
- **Reading ahead.** While the helper is answering (its health check at start, or its last
  call), the screen is not read ahead through the language model: the screenshot goes to the
  helper instead, `POST /read` with `{"image_b64": …}`, which returns `{"read_seconds",
  "cached"}` and keeps the read, so a later `/point` costs only its decoder. If `/read` fails
  (no such path, a bad status, a late reply), the language model reads the screen ahead as
  before and the log says why, and it goes on doing so until the helper answers a call again.
  With the helper unset or silent, reading ahead is exactly as it was.
  `bonsai-assistant --read-ahead IMAGE` shows who reads, with no screen.

## Speaking: hold the key

**Hold control-option-space and speak; tap it to type.**

- Key down: recording starts at once and the pointer comes out with "Listening…". What is
  running stops, as it always did when this key was pressed.
- Key up after 0.35 s or more: recording stops, Argmax WhisperKit (`base.en`) turns it into
  text on this Mac, the sentence shows in the caption, and it is carried out as a request
  (the same as Return in the typing box). No further key.
- Key up sooner than 0.35 s: a tap. The recording is dropped and the typing box opens, as
  before. With the typing box open, the key closes it, as before.
- Less than 0.3 s of voice in the recording: it is not read at all (a speech model makes
  words out of silence), the caption says "I did not catch that", nothing is done.
- Esc while the key is held, or while the recording is being read: cancelled.
- **A meter of the microphone** stands beside "Listening…" while the app listens (the held key
  and control-option-V): seven small bars, filled by how loud the last tenth of a second was,
  quick to rise and slower to fall; all empty in silence. After a second and a half with
  nothing the words change to "I can't hear anything" and go back when sound arrives. With a
  sound file in the microphone's place the meter follows the file at its own pace. The steps
  file has `peak_level` (0 to 1) for a spoken request.
- **A short command is read twice if need be.** When a clip under three seconds comes back as
  nothing ("Open Notes" is 0.84 s), it is read once more with silence before and after it (to
  at least 1.5 s, half each side); the log says when that was done.
- **The pointer keeps company with the cursor as its own thing.** While the mouse moves it
  stays where it is; when the mouse has been still for about 0.3 s, or is more than about
  250 pt away, it takes one flight to its place beside the cursor (0.35 to 0.9 s by distance,
  the same curve as a flight to a target) and only then looks again. Moves under about 60 pt
  are not followed.
- Should the key's release ever go unreported (the app hears it through a Carbon hot key
  event), the hold still ends: once the system itself says the space key has been up for a
  second, or after 30 s. The log then says so.
- control-option-B (type) and control-option-V (speak without holding; it stops by itself
  when you stop talking) are as they were.

The speech model is loaded in the background when the app starts, so the first hold does not
wait for it; the log says `Speech model ready: WhisperKit base.en loaded in … s from … (from
disk; nothing was fetched)`. It is read from `~/Bonsai-demo/models/argmax` (or `--own-models
DIR`): copy that whole folder as it is (142 MB, 44 files). Inside it the model is
`models/argmaxinc/whisperkit-coreml/openai_whisper-base.en/` (three `.mlmodelc` folders) and
the tokenizer is `models/openai/whisper-base.en/`; both must be there, at those places. When
the folder holds the model nothing is ever fetched. With nobody at the keyboard (a batch, `--unattended`)
a missing model is an error, never a download.

### Trying it without a microphone

- **`BONSAI_MIC_FILE=FILE` (or `--mic-file FILE`)**: wherever the app would listen, this sound
  file is what it hears, for the held key and for control-option-V alike. No microphone is
  opened and no microphone permission is asked for. Hold the real hotkey for half a second or
  more and let go: the file is read and carried out. The log has `VOICE (held)  "…"` with the
  seconds of sound, the seconds of voice and the seconds the reading took, and says the sound
  came from the file. Run the app this way with `--out FILE` (and no `--batch`) and each
  request is added to that file as it ends, in the shape a batch writes, with `heard`,
  `heard_seconds`, `sound_seconds` and `voiced_seconds`.
- **`--voice-file FILE`**: a batch run with no key at all. The file is read by the same call,
  and its words are the first request (requests of a `--batch` file, if one is given too,
  follow). That request's entry in the steps file has `heard` (the text), `heard_seconds` (how
  long the reading took), `sound_seconds` (how long the sound is) and `voiced_seconds`. If
  nothing is heard, the steps file gets one entry with `ending: Stopped: nothing was heard in
  FILE` and the exit code is 1; a file that cannot be read as sound gives exit code 2.
- `bonsai-assistant --transcribe FILE` prints what a file is heard as and nothing else.

Sound files of any usual kind are taken (wav, m4a, aiff, mp3) and are resampled as needed.
With `voice-example-silence.wav` the answer must be "I did not catch that".

## The last package (from the twelve requests that still failed on build 040b0a3)

- **The one app a planned request speaks of is opened before the planner is asked** (by name
  outside quotation marks, or by a word that means one: remind, note, contact, event, email,
  calculate; a file called `notes.txt` is not Notes). So a later part of a request no longer
  carries on in the app of the part before. The step is in the steps file as `step: 0`, `by:
  the app, before planning`, and the planner's "Done so far" starts with `open_app <app>`.
- **A part that refers back is given the earlier parts.** It refers back when it says another,
  one more, also, again, it, them, there, the same, or speaks of no app and no place of its
  own. Its `Task` is then `<part> (earlier in the same request: "<earlier parts>")`, and its
  "Done so far" keeps the earlier lines.
- **Two things made with one verb are two parts**: "Add a reminder called Water plants and a
  calendar event called Coffee with Maya" becomes "Add a reminder …" and "Add a calendar event
  …" (the event is then direct).
- **The button that commits is pressed before `done`.** When `done` comes directly after
  typing that changed something: the front window's default button, else a button titled
  Done, Save, Add or Create (Contacts' Done), is pressed. Never a button of a web page or of a
  toolbar. The `done` step then has `committed: …`. This comes after the Return rule.
- **Two types in a row into the same text area get a line break between them** (a note's
  title, then its text), when the second starts with a capital letter or a digit.
- **Renaming and moving a named file in a named folder are direct**, through the file system,
  checked on disk, never over something that is there: "Rename the file notes.txt on the
  Desktop to final-notes.txt", "Move the file notes.txt on the Desktop into the Invoices
  folder", and after a part that made a folder, "put the file budget.csv inside it". "Move the
  file notes.txt on the Desktop to the Trash", "Delete notes.txt from the Desktop" and "Throw
  away notes.txt that is on my Desktop" put the file in the Trash the system's own way (it
  can be put back). If the
  file or the folder is not found the planner takes over. A file and a folder are never
  dragged by the spelled-out parser.
- **`open_app Finder` with no Finder window open opens one**, and an `open_app` that brought
  its app to the front is no longer marked `(nothing changed)` (asked for twice in a row it
  still is).
- **One command of the menu bar asked for by its name is chosen directly**: "Show the status
  bar in Finder", "In Finder, choose View > Show Path Bar". The request must be short and the
  command's title at least two words that are most of what is asked. It counts as done when
  the item's title is gone from its menu afterwards (Show became Hide) or its tick changed;
  otherwise the planner goes on, told `menu <path>`. `kind` stays `planned`.
- **A sum with Calculator named is direct**: "Open Calculator and compute 25 * 4" opens
  Calculator, presses Escape, the keys of the sum and =, and checks that the window shows the
  result (100); if it does not, the planner takes over.
- **"Enable Dark Mode in settings" is the switch**, and "Put the Dock on the left side and make
  it hide automatically" sets both (each read back).

## Talking back

A question is answered in words in the box beside the pointer, with no check mark and no
"Done" (`kind` is `answer`, `ending` starts with `Answered:`, the one step has `tool: answer`
and `how`). With `--speak` the same sentence is spoken. "Where is…", "show me…", "point at…"
and "how do I…" are still answered by pointing.

1. **What the Mac knows for certain it says itself**, with no model (`how: the Mac itself`):
   whether Wi-Fi is on, whether it is online, the battery, the time, the date, whether dark
   mode is on, the volume.
2. **Any other question goes to the planner in its own format** (`how: the planner`): the
   question as `Task`, `Done so far: nothing`, and as `Controls` the front window's list; or,
   for a question about a menu ("what can I do in the File menu?"), that menu's enabled items
   as `menu item`s, read through Accessibility without opening the menu ("this menu": the menu
   that is open, else the menus of the menu bar); or, for a question about the Dock, the apps
   kept in it as `button`s. Nothing else in the prompt changes.
   - `done` with a sentence: the sentence is the answer. Plain words with no call are too.
   - `look`, or an empty `done`: the answer is read from a screenshot (as for a question about
     a picture, a chart or an error, which goes there straight away).
   - any other action: it is **not carried out**, nothing is said, and the question is
     answered by pointing.

## The second look

Off unless `--second-look` or `BONSAI_SECOND_LOOK=1` is given. It applies to steps that find
their target on a screenshot: `look`, a click or a drag that names its target in words.

- The first answer is taken as usual. If the click then lands on a control whose own name fits
  the words (the log says "the control named …"), nothing more is asked.
- Otherwise a square is cut from the full-resolution capture around the first answer, half the
  screen's longer side on each side and kept inside the screen. It is sent with the same
  request at the usual size (longer side 1280, or 896), and its answer is mapped back to the
  screen and takes the first answer's place. If it gives no point, the first answer stays.
- It costs a second read of an image for each such step. The log shows both answers and how far
  apart they are.

## The server

Without `--plain-server` the app expects LM Studio and, if nothing answers on this Mac, tries to
start it. With it, the app only talks to the address given. It uses two calls:

- `GET /v1/models`: the first id listed is the model (unless `--model`).
- `POST /v1/chat/completions`: not streamed, `temperature` 0, images as base64 PNG data URLs.
  Planning sends the `next_step` tool in `tools`. If the server refuses tools, or the model
  writes no call, the same step is asked for as JSON in the text. `bonsai-assistant
  --planner-prompt` prints the exact system text, tool and user message, with no server.
- A planning reply may be up to 384 new tokens (a step that types a long text needs the room).
  A reply cut off at that limit cannot be read as a step, so it is asked for once more with
  room for 1152; the log says when that happened.
- Thinking is switched off with `chat_template_kwargs: {"enable_thinking": false}` and
  `reasoning_effort: "none"`; if the server refuses these fields they are left out from then on.

For llama.cpp's `llama-server`: start it with `--jinja` (so that `tools` is honoured), a context
of 8192 or more, and the vision file (`--mmproj`).

A request for something the list of controls does not hold (`look`), pointing, and questions
about a picture send a screenshot; everything else is text only.

## Permissions

The app needs two, and checks both at the start of a batch (exit code 4 if one is missing):

| Permission | TCC service | For |
|---|---|---|
| Screen Recording | `kTCCServiceScreenCapture` | the screenshot |
| Accessibility | `kTCCServiceAccessibility` (granting `kTCCServicePostEvent` as well does no harm) | reading the names of controls, clicking, typing, moving windows |

Not needed: Microphone (a batch never listens), Automation, Calendar, Reminders, Contacts. Only
the requests "make a new folder … on the desktop / in documents / in downloads" and "open my …
folder" touch those folders (`kTCCServiceSystemPolicyDesktopFolder`, `…DocumentsFolder`,
`…DownloadsFolder`).

**Which program macOS asks about.** Not necessarily this executable. macOS looks permissions up
under the program *responsible* for the process: the one at the start of the chain that launched it.

| Started from | macOS attributes the permissions to |
|---|---|
| Terminal | Terminal (`com.apple.Terminal`) |
| `tart exec` | the guest agent (`tart-guest-agent`) |
| an SSH session | `/usr/libexec/sshd-keygen-wrapper` (as far as I know; not checked here) |
| a LaunchAgent that runs the executable directly | the executable itself, by its full path |
| anything, with `--own-permissions` | the executable itself, by its full path |

`--own-permissions` makes the app start itself again as a process that answers for itself, so a
grant written for the executable's path (client type 1) applies whatever launched it. It relies
on a system call that is not public (`responsibility_spawnattrs_setdisclaim`); where that call
is missing the app starts as usual. It has not been run yet.

Because macOS identifies an ad-hoc signed executable by its path and its code hash, a grant made
through System Settings has to be made again after the executable is replaced. Rows written
straight into the TCC database by path, with no code requirement, keep working.

**The monthly reminder.** macOS 15 and later ask again from time to time whether a program may go
on recording the screen. A grant that has just been made is not asked about for some weeks, so a
fresh guest should not meet this; if a "continue to allow" alert does appear, it has to be
answered once (I have not checked how to pre-answer it).

**Local network.** From macOS 15, a program that talks to another machine on the local network
(`192.168.64.1` is one) can bring up macOS's question about finding devices on the local
network. Apple's note TN3179 says tools started from Terminal, over SSH or by launchd are let
through without it. If the question does appear in the guest (it might with
`--own-permissions`), forward a port in the guest and point the app at `http://localhost:1234`
instead; connections to the machine itself are never asked about.

## What it expects in the home folder

Nothing has to exist. What it reads and writes:

| Path | |
|---|---|
| `~/Library/Logs/BonsaiAssistant/` | written: the log and the steps file, unless `--log` and `--out` say elsewhere |
| `~/Library/Caches/BonsaiAssistant/event.ics` | written only by a request for a calendar event, then opened in Calendar |
| `~/Library/Preferences/com.apple.dock.plist` | read: the apps in the Dock come first in the list of apps given to the planner |
| `/Applications`, `/System/Applications`, their `Utilities`, `~/Applications` | read: the names of the apps on this Mac |
| `~/Library/Preferences/bonsai-assistant.plist` | written only when a setting is changed in the app's menu; a batch does not |
| `~/.lmstudio/bin/lms` | used only without `--plain-server` |
| `~/Bonsai-demo/models/argmax/` | the speech model; used only for spoken requests, never in a batch |

## Other things it can do without touching the screen

```sh
bonsai-assistant --help
bonsai-assistant --route "put Safari and Notes side by side"     # what a request would become; nothing is done
bonsai-assistant --planner-prompt                                # the planner's format, word for word
bonsai-assistant --facts                                         # the facts about this Mac that questions are answered from
BONSAI_SERVER=http://192.168.64.1:1234 bonsai-assistant --models # what the server lists
```
