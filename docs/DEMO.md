# The assistant: running it on the laptop

A menu-bar app in Swift (`assistant/`): Clicky, remade to run on the Mac alone. You type (or say) a
request beside the mouse cursor. A Bonsai 2 model served by LM Studio on this Mac points at
things, answers questions about the screen, rewrites the text you selected, and carries tasks
out one step at a time; a set of everyday requests needs no model at all. Speech is turned into
text by Argmax's WhisperKit. Nothing leaves the machine.

## State, 15 Nov 09:53

The app was last used at 05:01 and is closed now. "Run" below means run in the app on this
laptop; everything else has only been built and passed the core checks (`run.sh --test`, 445).

| | State |
|---|---|
| Pointing through LM Studio on saved screenshots | **checked**: tuned 9B 16 of 18 known targets, stock 9B 6 of 18 |
| Starting LM Studio's server, loading the model, the status line, putting things back on quit | **checked** in the app's check mode |
| Hotkey, typing box, pointer, log window | **run** by hand, through several versions of the pointer |
| "Show me" (pointing at what was asked for) | **run** (three requests, 03:58 to 04:07) |
| Spelled-out clicks and typing ("type in the input bar "…"", "close the … window") | **run**: found, clicked, typed |
| The model planning from screenshots (older way) | **run** once: a message typed into another app and sent, 2 steps |
| The model planning from the list of controls | **run** twice in its first wording (a window minimised in 3 steps; one request ended after 1 step without doing it). The format now frozen (v1: one `next_step` tool call per step, with `open_app`, `open_url`, `menu`, numbered controls, `look`) is **not run** |
| The planner 9B (`bonsai-2-9b-planner`, the default from the next start) | linked into LM Studio at 06:08, checksum checked; **not loaded or run on this laptop**. Checked on llama.cpp when it was made (pointing 18 of 20, 10 of 10 well-formed `next_step` calls) and it is the model the virtual-machine runs use |
| Opening apps and sites, web search, email draft, without planning | not run |
| Answers in words, the selected text, windows, dark mode, volume, folders, calendar event | not run (built 05:30) |
| Step captions, the check mark at the end, the "offline" badge | not run (built 05:30) |
| Settings panes, folders and paths, sites by name, one-shortcut requests, centring a window | not run (built 06:20) |
| The second look for small targets (off by default) | not run (built 06:30) |
| Fixes from the virtual machine's first pilot (9 of 47 runs passed there on the first package): open requests no longer taken as a click, opened apps brought to the front, direct routes checking their effect, a deeper list of controls in System Settings, Dock settings, unusable calls put right, a budget for steps with no effect | not run (built 06:29 to 06:39); the new list of controls could not be tried here at all |
| Fixes from the pilot on a real macOS 26 in the virtual machine (26 of 50 passed there on build d757beb; every direct request passed, 11 of 33 planned ones): requests that say "then" carried out in parts; a `done` that says it is not done; Return and replacing text in one-line fields; typing that goes nowhere; app names; Dock, dark mode and a screenshot said any way; settings panes checked by the window's title | not run (built 08:20 to 08:32); the choosing of a pane in the sidebar of System Settings could not be tried here at all |
| The last package, from the twelve requests that still failed on a real macOS 26 (build 040b0a3 passed 38 of 50 there): each part of a request starts in its own app; a part that refers back is told the earlier parts; the button that commits (Done, Save) is pressed before `done`; files renamed and moved through the file system; a menu command chosen by its name; a sum in Calculator; a line break between two types into the same text area | not run (built 09:05) |
| Talking back: questions answered by the Mac itself or by the planner from a list of controls (a menu's items, the Dock's apps) | not run (built 08:32) |
| **Hold control-option-space and speak; tap it to type** (recording from key down, carried out on key up, "I did not catch that" under 0.3 s of voice, Esc cancels; the speech model loaded at start) | not run (built 09:15); the tap-or-hold decision and the measure of voice are checked in the core. It can be tried with a sound file in place of the microphone (`BONSAI_MIC_FILE`) |
| A helper that only points (`BONSAI_POINTER_URL`: Bonsai-Pruned 4B behind a small local server), with the language model as the fallback for every request | **checked against stand-in servers on this Mac, with no model** (built 09:22): a good reply is used and lands where the same grid answer would; a status 500, a point outside the picture and a helper that is not running each fall back to the language model with a log line; unset, nothing is sent. Not run with the real helper |
| For the demo video: a spoken name dropped, "bring up the presentation", "write down what you can help me with", "caption the video I just recorded" | not run (built 09:47). The drawing of subtitles on a video was tried here with no model: they show at their times and the copy keeps its sound. The reading of the recording by the speech model, the presentation and the note are for the rig |
| Pointing through Accessibility first: a thing the Mac can name is found by its name with no screenshot (one match: no model; several: one planning turn in text), and only otherwise is the screenshot read | not run (built 09:50); the matching of names is checked in the core |
| Speech to text (Argmax WhisperKit, `base.en`) | **checked on a sound file**, also with the network denied; the microphone path is not confirmed |
| Drag, double and right click, scroll, keys | not run |
| A file of requests with nobody at the keyboard, against a plain server | **run in the virtual machine on the Mac mini** (open an app in 1 step, 6.5 s; a new reminder in 5 steps, 20 s); see "Running it elsewhere" |
| Running with WiFi off | not tried; see "With the network off" |

## The demo video

About a minute and a half, recorded as one screen recording with sound. You talk to the audience
freely; only what you say while holding control-option-space reaches the assistant.

| Time | To the camera | Holding the key | On screen |
|---|---|---|---|
| 0:00 | "This is my Mac. One key and my voice, that's the whole demo." | | Photo Booth, your face |
| 0:08 | | "Clicky, bring up the presentation." | "Listening…", what it heard, Photo Booth hides, the slides fill the screen |
| 0:14 | Read the slide | | The slide |
| 0:24 | "Slides are easy. Let's ask it." | "Write down what you can help me with." | Notes opens; a title and four lines type themselves |
| 0:42 | "Let's hold it to that." | "Turn on dark mode." | The whole screen flips |
| 0:50 | | "Put Safari and Notes side by side." | Two windows snap into halves |
| 0:58 | | "Caption the video I just recorded." | Four captions of what it is doing, then your recording plays with your words as subtitles |
| 1:15 | "One more thing." | "Is Wi-Fi on?" | The answer, in words |
| 1:22 | "Everything you saw ran on this Mac." | "Open Photo Booth." | Your face again |

Before recording:

1. **The slides.** Put the deck (a PDF is the safest) in `~/Bonsai-demo/demo/`, named with
   "presentation", "slides" or "deck" in its name; or start the app with
   `BONSAI_PRESENTATION=<file or link>`. A PDF opens in Preview and fills the screen.
2. **The recording to caption.** It must be in Movies, on the Desktop or in Downloads: the
   newest `.mov` or `.mp4` there is taken. Photo Booth keeps its clips where the app cannot
   read them, so record ten seconds with QuickTime Player (File > New Movie Recording, save to
   Movies), or drag the clip out of Photo Booth onto the Desktop.
3. **Permissions** for the app you start it from (Terminal): Screen Recording, Accessibility,
   Microphone.
4. **A dry run of every line**, in order, before the take. None of these lines has been run
   on this laptop. Start with `assistant/run.sh`, wait for the log line "Speech model ready",
   then hold the key for the first line.
5. **Wi-Fi.** For the "one more thing" to say Wi-Fi is off, turn it off before the take. The
   whole script works without it when the slides are a file.

What each line is: the presentation, the note, dark mode, side by side, the captioning and
Photo Booth are done directly, with no planning by the model; the note's four lines are
written by the model; the captions are made by Argmax WhisperKit; the Wi-Fi answer comes from
the Mac itself. If a line fails in the dry run, drop it: each stands alone.

## What the hackathon asks, and where this stands

| Rule (kickoff slides) | Here |
|---|---|
| Language models must be Bonsai 2 (2B, 4B or 9B) | the 9B with our tuning written into its GGUF: one file that plans steps and points |
| Must use Argmax "to some capacity" | spoken requests (control-option-V) go through Argmax's open-source Swift SDK, WhisperKit. Answers are spoken with the system voice, not Argmax's TTSKit (its model is a large download that was not made) |
| Must run on a Mac with WiFi off | nothing in the app needs the network once the files are on disk (they are); not yet tried with WiFi off. While the network is off the leaf says "offline" and a badge is shown |
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
   - **Screen & System Audio Recording**: needed for everything that looks at the screen. After allowing it, quit and start again.
   - **Accessibility**: needed to click, type, paste, move windows and read the names of controls.
   - **Microphone**: asked at the first spoken request.

   The permissions belong to the program the command was typed in: Terminal, or Claude if it is
   started from the Claude app's terminal panel.
   Use the same one every time. The app shows nothing in that terminal: it is the leaf in the menu bar.
2. **The hotkeys:** control-option-space to type (control-option-B does the same), control-option-V to speak.
3. **Only if LM Studio's server is set to require a token:** leaf menu > Advanced > "API Token…". It is stored
   in the macOS Keychain, read when a request is sent and sent as the bearer token; it is never in
   the settings, the log or the code. With no token stored, none is sent.

LM Studio needs nothing by hand. On start the app starts its server if it does not answer
(`lms server start`), loads the chosen model after unloading any other loaded language model
(16 GB: one at a time; context 8,192 tokens), and says how it went in one line (first line of the
leaf menu, the leaf's tooltip, the log). On quit it unloads what it loaded, loads again what it
had unloaded, and stops the server if it started it; "Keep Model Loaded on Quit" skips that.
LM Studio has no SDK for Swift (TypeScript and Python only), so this is its REST API
(`/api/v1/models`, `/models/load`, `/models/unload`, `/v1/chat/completions`) plus `lms` for the server.

For the demo, close what else is open: with the model loaded and many other programs running,
the laptop was several GB into swap.

## Using it

**Hold control-option-space and speak; tap it to type.**

Held, the pointer comes out with "Listening…" and the Mac records from the moment the key goes
down. Let go, and what you said is turned into text on this Mac (Argmax WhisperKit), shown in the
box, and carried out, with no further key. With less than about a third of a second of voice it
says "I did not catch that" and does nothing. Esc while holding, or while it reads, cancels.

**Tapped, then type it.** A small pointer (the Mac's arrow in 3D frosted glass,
smaller than the real one) grows out of the mouse cursor and waits beside it, with one small box
to its side to type in. While the box is empty the pointer drifts and sways a little; when you
start typing it comes to attention. Return does what you typed. While the model works the box
shows a text face and a word (`(._.) thinking.`, `(o_O) hmm..`) and the pointer makes small moves
in a fixed order: a hop, a slow turn about its long axis, a wiggle, a peek at its other side. Then
it darts to the target on a gentle arc with a caption of the step (`(^-^) 2 · Clicking Today`),
acts, ends with `\(^o^)/ ✓ done` and shrinks back into the cursor. An answer is written in the
same box. Esc stops everything at once. Faces are plain ASCII and never random.

Speaking without holding a key: control-option-V; it stops listening when you stop talking.

**Spoken replies are off** until "Speak Answers" is ticked in the leaf menu (or the app is started with `--speak`). With it on, answers,
the closing sentence of a task and a short "Done." are spoken with the Mac's own voice (offline).
"Read this to me" speaks either way.

## What to try

`run.sh --route "…"` prints which of these a request would become, without doing anything.

**1. Ask where something is: it points.** *(run)*

| Type | What happens |
|---|---|
| "where is the Share button?" · "show me the Trash" · "where is the View menu?" | When the Mac itself can name the thing (most buttons, fields, menus and Dock icons), the pointer goes straight to it: no screenshot, no model, well under a second. *(not run)* |
| "where is the search field?" · "show me the settings" · "how do I make a new note?" | Otherwise the screenshot is read: the pointer flies to it; with "Answer in a Sentence" ticked a sentence follows in the box. Nothing is clicked. About a second when the screen was read ahead, about 11 s otherwise. |

**2. Ask about the screen: it answers in words.** *(not run)*

| Type | What happens |
|---|---|
| "is Wi-Fi on?" · "am I online?" · "is dark mode on?" · "how much battery is left?" · "what time is it?" · "what's the volume?" | The Mac says it itself: no model, no screenshot, at once. |
| "what can I do in the File menu?" · "what's in this menu?" (with one open) | The menu's items are read through Accessibility and named in order, eight at most, then how many more. No model. |
| "what's on my Dock?" | The same, with the apps kept in the Dock as the list. |
| "which view am I in?" · "what does this window let me do?" | The same, with the front window's controls as the list. |
| "what am I looking at?" · "what does this chart say?" · "explain this error" | Answered from the screenshot. Also when the planner asks to look. |
| "and the one next to it?" (within five minutes) | For an answer from the screenshot, the last question and answer go along. |

The answer is shown in the box beside the pointer with no check mark, and spoken when "Speak
Answers" is on (off by default). A question never does anything: if the planner replies with a
step instead of an answer, the step is not carried out and the thing is pointed at instead.

**3. Select text, then ask for something to be done to it.** *(not run)*

| Type | What happens |
|---|---|
| "rewrite this more politely" · "make this shorter" · "fix the grammar" · "translate this to Spanish" | The selection is read (from the app, else by copying), the model rewrites it, and the result is pasted over the selection. The clipboard is put back as it was. With "Confirm Each Step" ticked it waits for Return before pasting. |
| "summarise this" · "explain this" | Two sentences in the box, nothing is changed. With nothing selected the question is asked of the screenshot instead. |
| "read this to me" | The selection is spoken with the Mac's voice. No model. |

**4. Everyday requests done directly: no model, instant.** *(not run)*

| Type | What happens |
|---|---|
| "open Mail" · "go to github.com" · "open YouTube" · "search for ternary networks" | Opened through the system. A site can be given by its address or, for well-known ones, its name. |
| "open Wi-Fi settings" · "open the Sound pane in System Settings" · "open System Settings and go to Displays" | System Settings opens at that pane (about forty panes by name), and the window is checked to be that pane; on a macOS that has no such pane the nearest one is opened and the planner takes over. "open Safari settings" opens the app's own settings. |
| "go to the Downloads folder" · "open documents" · "open ~/Projects" | The folder is shown in the Finder: a named one or any path. |
| "put Safari and Notes side by side" · "move this window to the left" · "maximize this window" · "center this window" | Both apps are opened and their windows placed in the two halves of the screen; or the front window is moved. |
| "turn on dark mode" · "toggle dark mode" · "make my Mac use the dark appearance" · "take the Mac out of dark mode" | Switched with the system's own switch, however it is asked for. |
| "take a screenshot" · "press the shortcut that takes a full screenshot" | Command-shift-3 is pressed: a picture of the whole screen. |
| "set the volume to 30" · "mute" · "turn the volume up" | Set on the sound output in use. |
| "rename the file notes.txt on the Desktop to final-notes.txt" · "move the file notes.txt on the Desktop into the Invoices folder" · "delete notes.txt from the Desktop" (to the Trash) | Done through the file system and checked on disk; never over something that is already there. If the file or the folder is not found, the model plans it. |
| "open Calculator and compute 25 * 4" | Calculator is opened, the keys of the sum and = are pressed, and the window is checked to show the result. |
| "show the status bar in Finder" · "in Finder, choose View > Show Path Bar" | The command is chosen from the menu bar by its name, and counts when its title flipped (Show to Hide) or its tick changed. |
| "make a new folder called Demo on the desktop" · "make a new folder named Taxes inside my Documents folder" | Made on disk (never over an existing one), checked, and shown in the Finder. |
| "add a meeting with Sam tomorrow at 3pm" · "make a new event: Budget meeting" (no time: the next full hour) | A one-hour event is written to a calendar file and opened in Calendar; the app answers Calendar's question about which calendar (OK: the default one) and checks that the question is gone. |
| "turn on Dock auto-hide" · "move the Dock back to the bottom of the screen" · "enlarge the Dock icons" · "turn off Dock magnification" | The Dock's setting is written, the Dock starts again (it flickers once) and the value is read back. |
| "draft an email to Sam about the demo" | The model writes a few lines and a draft is opened in the mail app (Gmail's compose page if a browser was just opened). Nothing is ever sent. |
| "close this tab" · "open a new tab" · "minimize this window" · "undo" · "select all" · "save" · "reload" · "zoom in" | One keyboard shortcut, pressed directly. Only the whole phrase counts. |
| "open Mail, then set the volume to 20" · "open Notes and turn on dark mode" · "open Calendar and make a new event: Budget meeting" | Parts joined with "then", "and", ";" run one after another. |

Each of these checks that it had its effect (the folder exists, the volume reads back, the app is
in front). If it did not, the request is handed to the planner, which is told what was tried.

**5. Clicks and typing you spell out.** *(run)*

| Type | What happens |
|---|---|
| "click the search field" · "double-click the Notes icon" · "right click the desktop" | The control is found (by its own name if it has one, else by the model on the screenshot), the pointer flies to it, the click is made. |
| "type in the search field "apple" and press enter" · "press command t" · "scroll down" | A click on the place, then the typing; keys and scrolling directly. |
| "drag the report to the Trash" | The model finds both ends; the drag is made. *(drag not run)* |

**6. Anything else: the model plans it, one step at a time.** *(first wording run twice; the frozen format not run)*

| Type | What happens |
|---|---|
| "make a new note that says buy milk" · "add a reminder to call Sam" · "start a new message to Sam in Mail" | Each turn the model gets the request, the apps on this Mac, the steps so far and the front window's controls as a numbered list, and answers with one `next_step` call: press or fill a control by its number, press keys, open an app or a link, choose a menu item by its path, scroll, drag, or look for something that is not listed (only that, and a click named in words, reads a screenshot). After each step the window is listed again; a step that changed nothing is repeated once and then reported to the model. Return is never pressed twice in a row, the very same step is not repeated right after it changed nothing, and scrolling or clicking that keeps changing nothing is stopped; each time the model is told. A call with a slip that is not in doubt is put right. Up to 15 steps. Its closing sentence is shown with the check mark (and spoken when replies are on). |

A request that says one thing comes after another ("open python.org, then write a note saying
…"; also "after that", "afterwards", ";") is carried out in parts: each part is a request of its
own, so the site is opened directly and only the note is planned. The next part starts when the
one before ended well.

Around the planner the app also does these, each shown in the log:

- A `done` whose sentence says more is needed or that it gave up is asked about once more; said
  again, the sentence is shown as it is, with no check mark.
- Typing into a one-line field that already holds text replaces the text.
- When `done` comes right after typing into a one-line field with no Return, Return is pressed
  first (an event's title, a new name). Never in a field of a web page.
- Typing that goes nowhere: the window's one text area is clicked, or in Notes, Reminders,
  TextEdit, Contacts, Calendar and Stickies command-N is pressed once, and the text is typed again.
- "the Finder app" is Finder; an `open_app` with no app takes the one app the request speaks of.

From its next start the app picks the planner 9B (`bonsai-2-9b-planner`), which was trained on
exactly this format and also points. It has not been loaded on this laptop yet; the same file
is what the virtual-machine runs use. `run.sh --planner-prompt` prints the format word for word.

Good to know:

- Command-Return instead of Return only points, whatever was typed. With **shift** added to the speaking hotkey the request only points.
- Trouble that needs a sentence (a missing permission, a server that does not answer) appears as one line at the top of the screen; everything else stays in the box.
- Steps run without asking. To approve each with Return, tick "Confirm Each Step" in the leaf menu.
- Requests that need no model (group 4 without the email, and "read this to me") do not wait for the model to be loaded.
- **Names of controls.** A step whose target is exactly the name of one control in the front
  window is done without reading the screen ("found by label" in the log). After the model
  points, the click goes to the control whose name fits the words, else to the pressable control
  under the point, else to the bare point. Both can be switched off in the leaf menu.
- **Second look** (leaf menu > Advanced, off by default; or `--second-look`). When the model has
  to find something on a screenshot and its answer is not a control the Mac can name, a square
  around that answer (half the screen's longer side) is looked at once more at the usual size
  and that answer is used. It finds more of the smallest targets and costs a second read.
- **Offline.** While the Mac is off the network the leaf in the menu bar reads "offline" and a
  small badge ("offline · everything runs on this Mac") sits in the top right corner whenever the
  assistant is out.

Leaf menu: a status line; Ask, Speak Instead, Stop; Model, Screenshot Size (1280 or 896 px), Read the
Screen Ahead (every 30 s, every minute, only when asked); Speak Answers, Answer in a Sentence,
Confirm Each Step, Find Controls by Name First; Advanced (server address, API token, snap clicks
to controls, second look for small targets, keep model loaded on quit, lab prompt layout, plan from screenshots (the older way), check permissions);
Show Log; Quit.

The **log window** is how to judge the model: what was asked, what the model wrote word for word,
the point on the 0 to 1000 grid and on the screen, the action, the seconds and tokens of each
request, and how much of the wait the read-ahead saved. Also in `~/Library/Logs/BonsaiAssistant/assistant.log`.
Selected text is never written there, only its length.

## Not run yet: what to look at first

In the order to try them, with what could go wrong:

1. **Group 4** (no model): "turn on dark mode", "set the volume to 30", "put Safari and Notes side
   by side", "make a new folder called Demo on the desktop", "add a meeting with Sam tomorrow at 3pm".
   - Dark mode uses a system switch that is not a public one; if this macOS lacks it, System Events is asked and macOS shows its own permission question once.
   - The first folder made on the Desktop may bring up macOS's question about access to the Desktop folder.
   - Side by side needs each app to have a window; an app with none is reported.
2. **Group 2**: "is Wi-Fi on?" (no model), "what can I do in the File menu?" (the planner), then "what am I looking at?" (the screenshot). Unknown: whether the planner answers a question with `done` and a sentence rather than setting off to do something, and how good the sentence is.
3. **Group 3**: select a sentence in Notes or TextEdit, "rewrite this more politely". Unknown: whether paste lands in every app (it presses command-V in the front app), and the quality of the rewrite.
4. **Captions, check mark, badge**: any task; turn WiFi off for the badge.
5. **The frozen planner format** on a short task ("make a new note that says buy milk"), and `open_app` / `menu` steps.
6. Drag, double and right click, scroll, the microphone.

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
- **The screen is read as soon as the app is ready, and looked at again every 30 s** (leaf menu:
  30 s, 60 s, or only when the bar opens). It is read again only when it shows something else, and
  also when the bar opens, when listening starts and after each request. A request about a screen
  that is already read is answered in about a second. Run on 15 Nov: the first read took 10.3 s.
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
| Speaking, screen capture, events, Keychain, the facts (Wi-Fi, volume, battery), windows, dark mode, folders, the calendar file | macOS itself. |
| "go to …", "search for …", an email draft after a browser was opened | These open a page in the browser, which needs the network like any page. Offline, the email draft opens in the mail app instead when no browser was opened first. |
| `run.sh` | Starts the program as it is when no source file is newer; otherwise it builds from the packages already fetched (`--force-resolved-versions`). Building with the network off was not tried, so do not edit the sources right before going offline. |

Speech was then checked with the network denied to that one process (a sandbox, WiFi untouched):
it loaded from disk and read the test sentence correctly (9.8 s to load cold, 0.62 s to read).

**The one thing to check with WiFi off before the demo:** that LM Studio's server starts and loads
the model. Everything else was run, or read from the code.

## Models in LM Studio

The model is a setting: the leaf menu lists what LM Studio has, and choosing one unloads the
previous model and loads the new one. Until one is chosen there, the app picks for itself each
time it checks the server: the planner before a model that only points, before one as shipped,
the 9B before the 4B, and only models LM Studio lists with vision.

| Name in the app | What | Vision |
|---|---|---|
| `bonsai-2-9b-planner` (the default) | the 9B that plans with `next_step` and points, `Bonsai-2-9B-orch-v1-u3000-Q2_0.gguf` | yes |
| `bonsai-2-9b-pointer` | the 9B that only points, `Bonsai-2-9B-point-v3-mixed896-Q2_0.gguf`; the numbers under "Speed" were measured with it | yes |
| `ternary-bonsai-2-9b` | PrismML's 9B as shipped, for comparison | yes |
| `ternary-bonsai-2-4b`, `-2b` | as shipped | no vision file: answers about the screen would be guesses |

The vision file for all three 9B models is `~/Bonsai-demo/models/bonsai2-gguf/9B/Ternary-Bonsai-2-9B-mmproj-F16.gguf`
(0.92 GB, built from the MLX pack's own vision tower with `weights/export_mmproj.py`). LM Studio
finds it through a link beside each model whose name starts with `mmproj-`.

## A demo that stays on what was checked

Requests of the kind that hit in the check: a named button or key ("the Automate button", "the
divide key"), a field ("the search field"), a photo by what it shows, a named command ("create a
new file", "open the settings"). The two misses were tiny targets: a single day in a small
calendar and a 12-pixel "+" in a corner. Avoid those on stage.

1. Start the app and wait for the log line "screen read ahead" (about 11 s after "ready").
2. With an app in front, control-option-space, "where is the search field?". The pointer flies there.
3. A second question about the same screen: about a second.
4. "Do it": something of one or two steps (a button, then typing). Each new screen costs a read.
5. Show the log: every number above is there, and nothing went over the network.

## Checking the model without the screen

```bash
assistant/run.sh --samples ~/Bonsai-demo/samples --out ~/Bonsai-demo/build/assistant-samples
```

prints HIT or MISS and the seconds for every request of `hints.json` and writes each screenshot
with the point (red ring) and the target (blue box) drawn on it. The server must be up with a model
loaded, for example while the app runs. Also `--point IMAGE "what"`, `--step IMAGE "request"`,
`--transcribe SOUND`, `--plan-text FILE` (one planning turn on a written situation), `--planner-prompt` (the planner's
fixed instructions), `--route "request"` (what a request would become; no server needed), `--facts` (the facts
about this Mac that questions are answered from), `--models`, and `--model ID`,
`--side 896`, `--one-message`, `--tools`. `--batch FILE --out LOG.json` starts the app, carries out every line of
FILE as if typed (it drives the desktop) and writes each request's steps, tools and timings as JSON.
`run.sh --test` runs the core's 210 checks. `run.sh --help` lists every option.

## Running it elsewhere, with nobody at the keyboard

`assistant/package.sh` puts the app and the few files it needs into one folder
(`~/bonsai-macvm/app-package/` by default) that runs on another Apple-silicon Mac with no
compiler and no LM Studio. Its `README.md` has the batch command, every setting, the permissions
and which program macOS attributes them to, and what it touches in the home folder. In short:

```sh
BONSAI_SERVER=http://192.168.64.1:1234 BONSAI_PLAIN_SERVER=1 ./bonsai-assistant --batch requests.txt --out steps.json --timeout 180
```

- `--plain-server`: any OpenAI-compatible server (llama.cpp's `llama-server`, started with
  `--jinja` and its vision file). Nothing goes through LM Studio; the model is the one the
  server lists and is taken to see. LM Studio stays the default on the laptop.
- A batch asks nothing of a person (no permission question, no log window, no Keychain), stops a
  request after its time limit, writes the steps after every request whether it worked or not,
  and ends with 0 (all well), 1 (some not), 2 (no requests), 3 (server not ready) or 4 (a
  permission is missing).
- `BONSAI_PLANNER_SYSTEM_FILE=file` replaces the planner's system text with the file's contents
  for that run (to try a wording without rebuilding); `BONSAI_PLAN_EVERYTHING=1` sends every
  request that is not a question to the planner. Each request in the steps file says which
  system text it ran with.
- It drives the desktop, so it is not for this laptop. It runs in the virtual machine on the Mac mini.

## Not built, or weak

- Speaking the answer with Argmax's TTSKit (system voice instead; see the table above).
- Reminders, and Do Not Disturb: no direct route without a new permission; they go to the planner.
- A yes/no check by the model after an action (the planner is only told when nothing changed).
- Planning with the planner 9B has not been run on this laptop yet (see the state table).
- The 4B has no vision file in LM Studio, so it cannot be used here yet.

## If something goes wrong

- The status line never says "ready": the log says at which point (server start, list, load). Open
  LM Studio once, start the server in its Developer tab, then "Check the server again" in the
  model menu.
- The pointer is wrong everywhere: the model has no vision file (the status line says so), or the
  display is scaled in a way the log's "pixels per point" line will show.
- A rewrite was not pasted: the front app did not take command-V where the selection was. Click
  into the text, select it again and repeat; with "Confirm Each Step" ticked it waits for Return
  before pasting.
- "select some text first": the app in front did not say what is selected and copying gave
  nothing; select the text again with that app's window in front.
- Windows do not move, or nothing is clicked: Accessibility is not allowed for the program the
  app was started from (leaf menu > Advanced > Check Permissions).
