# assistant: the Bonsai screen assistant (Swift, menu bar)

How to run it, what it does and what is not built yet: `docs/DEMO.md`.

    assistant/run.sh            build and start the app
    assistant/run.sh --test     the checks of the core

| Folder | What |
|---|---|
| `Sources/AssistantCore` | no screen needed: units (`Geometry.swift`), answers (`Parsing.swift`), prompts, key names, images, the server client, the three requests (`Pipeline.swift`) |
| `Sources/bonsai-assistant` | the app: `AppController.swift` (menu, show me, do it), `Overlay.swift` (pointer), `Windows.swift` (input bar, log), `System.swift` (settings, hotkeys, capture, events), `main.swift` (app or saved-screenshot mode) |
| `Sources/assistant-tests` | the core's checks as a plain program (the command-line tools have no XCTest) |

Builds with the Swift command-line tools alone, no Xcode. The first build fetches the packages pinned in
`Package.resolved` (Argmax's open-source SDK and what it depends on); later builds use those copies.
