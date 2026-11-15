// bonsai-assistant: with no arguments, the menu-bar app. With arguments, the same requests on
// saved screenshots, without capturing the screen or sending any event:
//
//   bonsai-assistant --models                                   what the server offers
//   bonsai-assistant --point shot.png "the Done button"         one pointing request
//   bonsai-assistant --step shot.png "turn on dark mode"        one next-step request
//   bonsai-assistant --samples ~/Bonsai-demo/samples            every request of hints.json, with hit or miss
//   bonsai-assistant --batch requests.txt --out steps.json      the app, carrying out a file of requests with nobody at the keyboard
//   bonsai-assistant --planner-prompt                            the planner's format v1 as the app sends it (no server needed)
//   bonsai-assistant --route "put Safari and Notes side by side"  what a request would become (nothing is done, no server needed)
//   bonsai-assistant --facts                                     the facts about this Mac that questions are answered from
//
// Options: --server URL (default LM Studio's), --model ID (default: the first Bonsai the server
// lists), --side 1280|896, --out DIR (write each screenshot with the point drawn on it),
// --one-message (screenshot and question in one message, as measured in the lab; slower),
// --tools (steps as a next_step tool call, for a model trained on steps).
import AppKit
import AssistantCore

let arguments = Array(CommandLine.arguments.dropFirst())

// --own-permissions (or BONSAI_OWN_PERMISSIONS=1): start again as a process that answers for
// itself. macOS decides Screen Recording and Accessibility by the program "responsible" for a
// process, which for something started from a shell is the program the shell runs in. Started
// this way the executable is its own responsible program, so the permissions are looked up
// under this file's path whatever started it. Uses a system call that is not a public one;
// if it is missing, the app starts as usual.
var disclaimedChild: pid_t = 0
if (arguments.contains("--own-permissions") || ProcessInfo.processInfo.environment["BONSAI_OWN_PERMISSIONS"] == "1"),
   ProcessInfo.processInfo.environment["BONSAI_ANSWERS_FOR_ITSELF"] == nil,
   let symbol = dlsym(UnsafeMutableRawPointer(bitPattern: -2), "responsibility_spawnattrs_setdisclaim"),
   let path = Bundle.main.executablePath {
    typealias Disclaim = @convention(c) (UnsafeMutablePointer<posix_spawnattr_t?>, Int32) -> Int32
    var attributes: posix_spawnattr_t?
    posix_spawnattr_init(&attributes)
    _ = unsafeBitCast(symbol, to: Disclaim.self)(&attributes, 1)
    var environment = ProcessInfo.processInfo.environment
    environment["BONSAI_ANSWERS_FOR_ITSELF"] = "1"
    let argv: [UnsafeMutablePointer<CChar>?] = CommandLine.arguments.map { strdup($0) } + [nil]
    let envp: [UnsafeMutablePointer<CChar>?] = environment.map { strdup("\($0.key)=\($0.value)") } + [nil]
    if posix_spawn(&disclaimedChild, path, nil, &attributes, argv, envp) == 0 {
        for number in [SIGINT, SIGTERM, SIGHUP] { signal(number) { kill(disclaimedChild, $0) } }     // pass them on
        var status: Int32 = 0
        while waitpid(disclaimedChild, &status, 0) < 0 && errno == EINTR {}
        exit((status & 0x7f) == 0 ? (status >> 8) & 0xff : 1)
    }
}

func option(_ name: String) -> String? {
    guard let i = arguments.firstIndex(of: name), i + 1 < arguments.count else { return nil }
    return arguments[i + 1]
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(2)
}

/// The planner's format v1 exactly as the app sends it, with no server: the system text (the
/// built-in one, or the file named for this run), the next_step tool, the sentence added when
/// the call is asked for as JSON, and a user message.
func printPlannerPrompt() -> Never {
    let replacement = Launch.plannerSystem
    if let problem = replacement.problem { fail(problem) }
    print("=== system (" + Launch.plannerSystemNote + ")")
    print(replacement.text ?? Planner.system)
    if let data = try? JSONSerialization.data(withJSONObject: Planner.tool, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]),
       let text = String(data: data, encoding: .utf8) {
        print("\n=== tool")
        print(text)
    }
    print("\n=== added to the system text when the call is asked for as JSON")
    print(Planner.asJSON)
    print("\n=== user (an example)")
    print(Planner.user(task: "Make a new event called Demo", apps: ["Finder", "Calendar", "Mail"], frontApp: "Calendar", window: "Calendar",
                       done: ["open_app Calendar"],
                       controls: [ListedControl(id: 1, role: "button", name: "Today"), ListedControl(id: 2, role: "text field", name: "Search", value: "demo"),
                                  ListedControl(id: 3, role: "radio", name: "Month", value: "selected"), ListedControl(id: 4, role: "menu", name: "File")]))
    exit(0)
}

func runCommandLine() async {
    guard let base = LMClient.url(from: option("--server") ?? Settings.shared.server) else { fail("bad --server") }
    let client = LMClient(base: base)
    let side = Int(option("--side") ?? "") ?? 1280
    var listed: [String] = []
    do { listed = try await client.models() } catch { fail("\(error)") }
    if arguments.contains("--models") {
        print(listed.joined(separator: "\n"))
        return
    }
    guard let model = option("--model") ?? listed.first(where: { $0.lowercased().contains("bonsai") }) ?? listed.first else {
        fail("the server lists no model")
    }
    let pipeline = Pipeline(client: client, model: model)
    pipeline.pointer = Launch.pointerURL.flatMap { PointerHelper($0) }
    pipeline.separateImage = !arguments.contains("--one-message")     // --one-message: the lab's layout, a full read per question
    pipeline.plainStepPrompt = arguments.contains("--tools")
    pipeline.plannerSystem = Launch.plannerSystem.text
    let outDir = option("--out")
    if let outDir { try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true) }
    print("server \(base.absoluteString) · model \(model) · image \(side) px · "
          + (pipeline.separateImage ? "screenshot in its own message" : "screenshot and question in one message"))

    /// One pointing request on a file. `box`: the target as fractions of the image, if known.
    func point(_ path: String, _ instruction: String, box: [Double]? = nil, tag: String) async -> Bool? {
        guard let full = ImageOps.load(path: path) else { fail("cannot read \(path)") }
        let sent = ImageOps.shrunk(full, longSide: side)
        guard let url = ImageOps.dataURL(sent) else { fail("cannot encode \(path)") }
        do {
            let out = try await pipeline.point(imageURL: url, instruction: instruction)
            var line = String(format: "%.2f s", out.chat.seconds) + " (\(out.chat.tokenNote)) · wrote \(out.chat.written.prefix(60))"
            var hit: Bool?
            if let g = out.answer.point {
                let px = Geometry.pixel(grid: g, imageWidth: full.width, imageHeight: full.height)
                line += String(format: " · pixel (%.0f, %.0f) of %d x %d", px.x, px.y, full.width, full.height)
                var rect: CGRect?
                if let box, box.count == 4 {
                    let fx = g.x / 1000, fy = g.y / 1000
                    hit = fx >= box[0] && fx <= box[2] && fy >= box[1] && fy <= box[3]
                    rect = CGRect(x: box[0] * Double(full.width), y: box[1] * Double(full.height),
                                  width: (box[2] - box[0]) * Double(full.width), height: (box[3] - box[1]) * Double(full.height))
                }
                if let outDir, let drawn = ImageOps.annotated(full, at: px, box: rect) {
                    _ = ImageOps.save(drawn, path: "\(outDir)/\(tag).png")
                }
            } else {
                if box != nil { hit = false }
            }
            if let note = out.note { line += " · note: \(note)" }
            print("  \(hit == nil ? "    " : hit! ? "HIT " : "MISS") \"\(instruction)\" · \(line)")
            return hit
        } catch {
            print("  ERROR \"\(instruction)\": \(error)")
            return box == nil ? nil : false
        }
    }

    if let i = arguments.firstIndex(of: "--plan-text"), i + 1 < arguments.count {
        // One planning turn on a user message read from a file (format v1), to try the planner without a screen.
        guard let user = try? String(contentsOfFile: arguments[i + 1], encoding: .utf8) else { fail("cannot read \(arguments[i + 1])") }
        for turn in 1...(Int(option("--turns") ?? "") ?? 1) {
            do {
                let out = try await pipeline.plan(user: user.trimmingCharacters(in: .newlines))
                print("  turn \(turn): \(String(format: "%.2f s", out.chat.seconds)) (\(out.chat.tokenNote)) · wrote \(out.chat.written.prefix(260))")
                if let note = out.note { print("  note: \(note)") }
                print("  step: " + (out.step.map { Planner.doneLine($0, control: nil) + " [\($0.action)]" } ?? "none could be read"))
            } catch {
                print("  ERROR: \(error)")
            }
        }
    } else if let i = arguments.firstIndex(of: "--read-ahead"), i + 1 < arguments.count {
        // Who reads a screenshot ahead: the pointer helper when it answers its health check, else the language model.
        guard let full = ImageOps.load(path: arguments[i + 1]), let url = ImageOps.dataURL(ImageOps.shrunk(full, longSide: side)) else { fail("cannot read \(arguments[i + 1])") }
        if let helper = pipeline.pointer {
            let health = await helper.health()
            pipeline.pointerSaid(health.ok)
            print("pointer helper at \(helper.base.absoluteString): " + (health.ok ? "answered" : "did not answer") + " (\(health.note))")
        }
        do {
            let done = try await pipeline.readAheadForPointing(imageURL: url)
            print(String(format: "read ahead by %@ in %.2f s", done.by, done.seconds) + (done.note.map { " · \($0)" } ?? ""))
        } catch { fail("\(error)") }
    } else if let i = arguments.firstIndex(of: "--point"), i + 2 < arguments.count {
        _ = await point(arguments[i + 1], arguments[i + 2], tag: "point")
    } else if let i = arguments.firstIndex(of: "--step"), i + 2 < arguments.count {
        guard let full = ImageOps.load(path: arguments[i + 1]), let url = ImageOps.dataURL(ImageOps.shrunk(full, longSide: side)) else {
            fail("cannot read \(arguments[i + 1])")
        }
        do {
            let out = try await pipeline.nextStep(imageURL: url, goal: arguments[i + 2], history: [])
            print("  \(String(format: "%.2f s", out.chat.seconds)) (\(out.chat.tokenNote)) · wrote \(out.chat.written)")
            if let note = out.note { print("  note: \(note)") }
            print("  step: " + (out.step.map { $0.historyLine + ($0.problem().map { "  [not usable: \($0)]" } ?? "") } ?? "none could be read"))
        } catch {
            print("  ERROR: \(error)")
        }
    } else if let dir = option("--samples") {
        let folder = (dir as NSString).expandingTildeInPath
        guard let data = FileManager.default.contents(atPath: folder + "/hints.json"),
              let hints = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { fail("no hints.json in \(folder)") }
        var hits = 0, scored = 0
        for name in hints.keys.sorted() {
            guard let entry = hints[name] as? [String: Any], let list = entry["hints"] as? [[String: Any]] else { continue }
            print("\(name)  (\(entry["note"] as? String ?? ""))")
            for (k, hint) in list.enumerated() {
                guard let q = hint["q"] as? String else { continue }
                let box = (hint["box"] as? [Any])?.compactMap { ($0 as? NSNumber)?.doubleValue }
                let tag = (name as NSString).deletingPathExtension + "-\(k + 1)"
                if let hit = await point(folder + "/" + name, q, box: box, tag: tag) {
                    scored += 1
                    if hit { hits += 1 }
                }
            }
        }
        print("\(hits) of \(scored) requests with a known target were hit")
    } else {
        fail("usage: bonsai-assistant [--models | --point IMAGE \"what\" | --step IMAGE \"request\" | --samples DIR] [--server URL] [--model ID] [--side N] [--out DIR]")
    }
}

if arguments.contains("--help") || arguments.contains("-h") {
    print("""
    bonsai-assistant                       the menu-bar app (LM Studio on this Mac by default)
    bonsai-assistant --batch FILE          the app carrying out a file of requests, one per line, with nobody at the keyboard

    Options of the app (each also as an environment variable):
      --server URL             BONSAI_SERVER             the model server (default http://localhost:1234/v1)
      --plain-server           BONSAI_PLAIN_SERVER=1     any OpenAI-compatible server: no LM Studio, the model it lists, taken to see
      --model ID               BONSAI_MODEL              the model to ask for (default: the server's)
      --out FILE               BONSAI_OUT                where a batch writes its steps (default ~/Library/Logs/BonsaiAssistant/batch.json)
      --timeout SECONDS        BONSAI_REQUEST_TIMEOUT    time allowed for one request of a batch (default 180)
      --log FILE               BONSAI_LOG                the log (default ~/Library/Logs/BonsaiAssistant/assistant.log)
      --side 1280|896          BONSAI_IMAGE_SIDE         longer side of the screenshot that is sent
      --unattended             BONSAI_UNATTENDED=1       never ask a person anything (always so in a batch)
      --skip-permission-check  BONSAI_SKIP_PERMISSION_CHECK=1   a batch goes on even if macOS says a permission is missing
      --own-permissions        BONSAI_OWN_PERMISSIONS=1  macOS looks the permissions up under this executable, not the program that started it
      --planner-system FILE    BONSAI_PLANNER_SYSTEM_FILE   a text file whose contents replace the planner's system text for this run
      --plan-everything        BONSAI_PLAN_EVERYTHING=1  whatever is not a question is planned by the model; nothing is done directly
      --second-look            BONSAI_SECOND_LOOK=1      a closer second look when something looked for is not a named control (a second read)
      --speak                  BONSAI_SPEAK=1            spoken replies for this run (never in a batch)

    A batch ends with: 0 every request ended well · 1 some did not · 2 no requests · 3 server not ready · 4 a permission is missing

    Without the screen: --route "request" · --planner-prompt · --facts · --models · --point IMAGE "what" · --samples DIR
    """)
    exit(0)
} else if let i = arguments.firstIndex(of: "--preview-bar"), i + 1 < arguments.count {
    // A picture of the input bar and the menu's header drawn to a file (no window is shown; the
    // glass itself cannot be drawn this way, so it stands on a plain dark ground).
    _ = NSApplication.shared
    let field = NSTextField(), face = NSTextField(labelWithString: Faces.typing(""))
    let bar = InputBar.content(face: face, field: field)
    bar.appearance = NSAppearance(named: .darkAqua)
    let header = MenuHeader()
    header.set("Ready · bonsai-2-9b-pointer", .ready)
    header.appearance = NSAppearance(named: .darkAqua)
    let canvas = NSView(frame: CGRect(x: 0, y: 0, width: 720, height: 240))
    canvas.wantsLayer = true
    canvas.layer?.backgroundColor = NSColor(calibratedWhite: 0.2, alpha: 1).cgColor
    bar.setFrameOrigin(CGPoint(x: 40, y: 110))
    header.setFrameOrigin(CGPoint(x: 40, y: 30))
    canvas.addSubview(bar)
    canvas.addSubview(header)
    guard let rep = canvas.bitmapImageRepForCachingDisplay(in: canvas.bounds) else { exit(1) }
    canvas.cacheDisplay(in: canvas.bounds, to: rep)
    guard let data = rep.representation(using: .png, properties: [:]) else { exit(1) }
    exit((try? data.write(to: URL(fileURLWithPath: arguments[i + 1]))) != nil ? 0 : 1)
} else if arguments.contains("--planner-prompt") {
    printPlannerPrompt()
} else if let i = arguments.firstIndex(of: "--route"), i + 1 < arguments.count {
    // What a request would become, without doing any of it. A request that says one thing
    // comes after another is shown part by part.
    func described(_ request: String) -> String {
        switch Router.route(request, app: Apps.resolve) {
        case .point: return "point at it (a screenshot and the pointing prompt)"
        case .answer(let screen):
            if Talk.fact(request) != nil { return "answer in words, from the Mac itself (no model)" }
            if screen { return "answer in words, from the screenshot" }
            let list = Talk.menu(request) != nil ? "the menu's items" : Talk.asksDock(request) ? "the Dock's apps" : "the front window's controls"
            return "answer in words: asked of the planner with \(list) as its list; from the screenshot if it asks to look; by pointing if it sets off to act"
        case .text(let skill):
            return "the selected text: \(skill.caption)" + (skill.instruction.isEmpty ? " (no model)" : skill.replaces ? " (the result replaces the selection)" : " (the result is shown)")
        case .direct(let steps):
            return "done directly, without planning: " + steps.map { $0.action == Recipes.draftEmail ? "Drafting an email (the model writes it; never sent)" : Captions.step($0, control: nil) }
                .joined(separator: "; ")
        case .scripted(let steps): return "as spelled out: " + steps.map(\.historyLine).joined(separator: "; ")
        case .plan: return "planned by the model, one step at a time"
        }
    }
    let asked = Router.addressed(arguments[i + 1])                         // "Clicky, …": the name is not part of the request
    let parts = Router.parts(asked, app: Apps.resolve)
    if parts.count > 1 {
        print("in \(parts.count) parts, one after another:")
        for (n, part) in parts.enumerated() {
            print("  \(n + 1). \"\(part)\": \(described(part))" + (n > 0 && Router.refersBack(part, apps: Apps.list) ? " (told what the parts before it did)" : ""))
        }
    } else {
        print(described(asked))
    }
    exit(0)
} else if arguments.contains("--count-controls") {
    // A check of the control lister on whatever window is in front: how many controls of each
    // kind it finds and how long it takes. Only counts are printed, never a name or a text.
    let start = Date()
    let list = Access.screenList()
    var kinds: [String: Int] = [:]
    for control in list.controls { kinds[control.role, default: 0] += 1 }
    let valued = list.controls.filter { !$0.value.isEmpty }.count
    print("\(list.controls.count) controls in \(String(format: "%.2f", Date().timeIntervalSince(start))) s: "
          + kinds.sorted { $0.key < $1.key }.map { "\($0.key) \($0.value)" }.joined(separator: ", ") + " · \(valued) with a value · window title \(list.window.isEmpty ? "empty" : "present")")
    print(Access.readingCheck())
    exit(0)
} else if arguments.contains("--facts") {
    // The few facts about this Mac that questions are answered from. Nothing is changed.
    _ = NSApplication.shared
    print(Mac.facts())
    exit(0)
} else if let i = arguments.firstIndex(of: "--preview"), i + 1 < arguments.count {
    // A picture of the pointer drawn to a file, without touching the display.
    _ = NSApplication.shared
    exit(Overlay.preview(to: arguments[i + 1]) ? 0 : 1)
} else if let i = arguments.firstIndex(of: "--burn-captions"), i + 2 < arguments.count {
    // The drawing of subtitles on a video, with no speech model: three made-up lines are put on
    // a copy of VIDEO written to OUT.   bonsai-assistant --burn-captions VIDEO OUT
    Task {
        let lines = Subtitles.lines([Subtitle(start: 0.3, end: 2.3, text: "This line is a check of the subtitles."),
                                     Subtitle(start: 2.6, end: 6.0, text: "A longer stretch of speech is cut into lines that are short enough to read at a glance.")])
        if let samples = try? await Media.samples(of: URL(fileURLWithPath: arguments[i + 1])) {
            print(String(format: "its sound: %.1f s, %.1f s of it voice", Double(samples.count) / 16000, PushToTalk.voicedSeconds(samples)))
        } else {
            print("it has no sound that could be read")
        }
        let start = Date()
        if let failure = await Media.burn(lines, into: URL(fileURLWithPath: arguments[i + 1]), to: URL(fileURLWithPath: arguments[i + 2])) { fail(failure) }
        print(String(format: "%d subtitles drawn on a copy in %.1f s: %@", lines.count, Date().timeIntervalSince(start), arguments[i + 2]))
        exit(0)
    }
    dispatchMain()
} else if let i = arguments.firstIndex(of: "--caption-video"), i + 1 < arguments.count {
    // The whole of it on one file, with no app: the sound is read by the speech model, the
    // subtitles are written beside OUT as .srt and drawn on a copy.   bonsai-assistant --caption-video VIDEO [OUT]
    Task {
        do {
            let movie = URL(fileURLWithPath: arguments[i + 1])
            let out = i + 2 < arguments.count && !arguments[i + 2].hasPrefix("--") ? URL(fileURLWithPath: arguments[i + 2]) : Media.captionedURL(for: movie)
            let samples = try await Media.samples(of: movie)
            print(String(format: "%.1f s of sound, %.1f s of it voice", Double(samples.count) / 16000, PushToTalk.voicedSeconds(samples)))
            let start = Date()
            let lines = Subtitles.lines(try await Voice().captions(samples))
            print(String(format: "read in %.1f s: %d subtitles", Date().timeIntervalSince(start), lines.count))
            print(Subtitles.srt(lines))
            try? Subtitles.srt(lines).write(to: out.deletingPathExtension().appendingPathExtension("srt"), atomically: true, encoding: .utf8)
            if let failure = await Media.burn(lines, into: movie, to: out) { fail(failure) }
            print("the captioned copy: \(out.path)")
            exit(0)
        } catch {
            fail("\(error)")
        }
    }
    dispatchMain()
} else if let i = arguments.firstIndex(of: "--transcribe"), i + 1 < arguments.count {
    // The speech model on a sound file: bonsai-assistant --transcribe request.wav   (no microphone needed)
    Task {
        do {
            let voice = Voice()
            let loadStart = Date()
            try await voice.prepare()
            print(String(format: "WhisperKit %@ loaded in %.1f s from %@", Voice.modelName, Date().timeIntervalSince(loadStart), Voice.localModel() ?? "?"))
            let heard = try await voice.transcribe(file: arguments[i + 1])
            print(String(format: "%.2f s · heard: %@", heard.seconds, heard.text))
            exit(0)
        } catch {
            fail("\(error)")
        }
    }
    dispatchMain()
} else if !arguments.contains(where: { ["--models", "--point", "--step", "--samples", "--plan-text", "--read-ahead"].contains($0) }) {
    // The app: with no arguments, or with only its own options (--batch FILE, --out FILE,
    // --timeout S, --server URL, --plain-server, --model ID, --log FILE, --unattended, --smoke).
    let app = NSApplication.shared
    let controller = AppController()
    app.delegate = controller
    app.setActivationPolicy(.accessory)                 // a menu-bar app: no Dock icon, never steals the front
    app.run()
} else {
    Task {
        await runCommandLine()
        exit(0)
    }
    dispatchMain()
}
