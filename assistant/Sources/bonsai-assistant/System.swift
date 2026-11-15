// The thin pieces that touch the machine: settings, global hotkeys, screen capture, system events.
import AppKit
import ApplicationServices
import AssistantCore
import Carbon.HIToolbox
import ScreenCaptureKit
import Security

// MARK: how this run was started

/// Options given on the command line or in the environment. They apply to this run only and
/// are never stored, so a run on another machine (a virtual machine, with nobody at the
/// keyboard) needs no settings file. A flag wins over its environment variable.
enum Launch {
    private static let arguments = Array(CommandLine.arguments.dropFirst())
    private static let environment = ProcessInfo.processInfo.environment

    private static func value(_ flag: String, _ variable: String) -> String? {
        if let i = arguments.firstIndex(of: flag), i + 1 < arguments.count { return arguments[i + 1] }
        let v = (environment[variable] ?? "").trimmingCharacters(in: .whitespaces)
        return v.isEmpty ? nil : v
    }

    private static func on(_ flag: String, _ variable: String) -> Bool {
        arguments.contains(flag) || ["1", "true", "yes", "on"].contains((environment[variable] ?? "").lowercased())
    }

    /// The server's address: --server URL, or BONSAI_SERVER.
    static let server = value("--server", "BONSAI_SERVER")
    /// A plain OpenAI-compatible server (llama.cpp's llama-server, …): nothing is started or
    /// loaded through LM Studio, the model is the one the server lists, and it is taken to see.
    static let plainServer = on("--plain-server", "BONSAI_PLAIN_SERVER")
    static let model = value("--model", "BONSAI_MODEL")
    /// A file of requests to carry out one after another, and where their steps are written.
    static let batch = value("--batch", "BONSAI_BATCH")
    static let out = value("--out", "BONSAI_OUT")
    /// The log file (default ~/Library/Logs/BonsaiAssistant/assistant.log).
    static let log = value("--log", "BONSAI_LOG")
    static let side = value("--side", "BONSAI_IMAGE_SIDE").flatMap { Int($0) }
    /// Seconds one request of a batch may take before it is stopped (default 180).
    static let timeout = value("--timeout", "BONSAI_REQUEST_TIMEOUT").flatMap { Double($0) }
    /// Nobody is at the keyboard: nothing is asked of a person (no permission question, no log
    /// window over the screen), steps never wait for Return, results are not left on screen.
    static let unattended = batch != nil || voiceFile != nil || on("--unattended", "BONSAI_UNATTENDED")
    /// A helper that only points (Bonsai-Pruned 4B behind a small local server), for example
    /// http://127.0.0.1:1235. Unset: the language model points, as always.
    static let pointerURL = value("--pointer-url", "BONSAI_POINTER_URL")
    /// Seconds between the requests of a batch (default 1.5), and whether each request is
    /// shown beside the pointer before it is carried out (for a run that is being filmed).
    static let pause = value("--pause", "BONSAI_BATCH_PAUSE").flatMap { Double($0) }
    static let showRequests = on("--show-requests", "BONSAI_SHOW_REQUESTS")
    /// What "bring up the presentation" shows: a file (a deck, a PDF) or a link.
    static let presentation = value("--presentation", "BONSAI_PRESENTATION")
    /// A sound file read in place of the microphone, wherever the app would listen (for trying
    /// the voice path with no microphone: the hotkey is held as usual, the file is what is heard).
    static let micFile = value("--mic-file", "BONSAI_MIC_FILE").map { ($0 as NSString).expandingTildeInPath }
    /// A sound file whose words are the request of a batch run (alone, or before a --batch file).
    static let voiceFile = value("--voice-file", "BONSAI_VOICE_FILE").map { ($0 as NSString).expandingTildeInPath }
    /// The folder the speech model is kept in (default ~/Bonsai-demo/models/argmax), so that
    /// it can be copied to another Mac rather than downloaded there.
    static let ownModels = value("--own-models", "BONSAI_OWN_MODELS").map { ($0 as NSString).expandingTildeInPath }
    /// A text file whose contents replace the planner's system text for this run.
    static let plannerSystemFile = value("--planner-system", "BONSAI_PLANNER_SYSTEM_FILE").map { ($0 as NSString).expandingTildeInPath }
    /// The replacement text, or why the named file cannot be used. Spaces and line ends around
    /// the text are dropped; everything inside it is kept as written.
    static let plannerSystem: (text: String?, problem: String?) = {
        guard let path = plannerSystemFile else { return (nil, nil) }
        guard let raw = try? String(contentsOfFile: path, encoding: .utf8) else { return (nil, "the planner system file \(path) could not be read") }
        let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        return text.isEmpty ? (nil, "the planner system file \(path) is empty") : (text, nil)
    }()
    /// In a few words, for the log and the steps file.
    static var plannerSystemNote: String {
        if let text = plannerSystem.text { return "file \(plannerSystemFile ?? ""), \(text.count) characters" }
        return plannerSystem.problem.map { "built in (\($0))" } ?? "built in"
    }
    /// Every request that is not a question goes to the planner, also those the app could do
    /// directly or that spell their steps out (for measuring the planner on whole tasks).
    static let planEverything = on("--plan-everything", "BONSAI_PLAN_EVERYTHING")
    /// A second, closer look for things found on a screenshot (see Settings.secondLook), for this run.
    static let secondLook = on("--second-look", "BONSAI_SECOND_LOOK")
    /// Spoken replies for this run, whatever the menu's switch says.
    static let speak = on("--speak", "BONSAI_SPEAK")
    /// Go on even when macOS says a permission is missing (in case it says so wrongly).
    static let skipPermissionCheck = on("--skip-permission-check", "BONSAI_SKIP_PERMISSION_CHECK")
}

// MARK: settings

final class Settings {
    static let shared = Settings()
    private let d = UserDefaults.standard

    var server: String {
        get { Launch.server ?? d.string(forKey: "server") ?? "http://localhost:1234/v1" }
        set { d.set(newValue, forKey: "server") }
    }
    /// The model taken from a plain server for this run; never stored.
    var runModel: String?
    var model: String {
        get { Launch.model ?? runModel ?? d.string(forKey: "model") ?? "" }
        set { d.set(newValue, forKey: "model") }
    }
    /// The model was picked in the menu (otherwise the app keeps choosing the best one it finds).
    var modelChosenByUser: Bool { get { flag("modelChosenByUser", default: false) } set { d.set(newValue, forKey: "modelChosenByUser") } }
    /// Longer side of the image that is sent, in pixels.
    var imageSide: Int {
        get { Launch.side ?? (d.integer(forKey: "imageSide") == 896 ? 896 : 1280) }
        set { d.set(newValue, forKey: "imageSide") }
    }
    private func flag(_ key: String, default value: Bool) -> Bool { (d.object(forKey: key) as? Bool) ?? value }

    /// Steps run one after another without asking (Esc stops). Off: each step waits for Return.
    var continuous: Bool { get { Launch.unattended || flag("continuous", default: true) } set { d.set(newValue, forKey: "continuous") } }
    var speak: Bool { get { !Launch.unattended && (Launch.speak || flag("speakAloud", default: false)) } set { d.set(newValue, forKey: "speakAloud") } }
    var sentence: Bool { get { flag("sentence", default: true) } set { d.set(newValue, forKey: "sentence") } }
    var plainStepPrompt: Bool { get { flag("plainStepPrompt", default: false) } set { d.set(newValue, forKey: "plainStepPrompt") } }
    /// Read the screen as soon as the bar opens, before the request is typed.
    var readAhead: Bool { get { !Launch.unattended && flag("readAhead", default: true) } set { d.set(newValue, forKey: "readAhead") } }
    /// A target named exactly like one control in the front window is found by that name, without reading the screen.
    var useLabels: Bool { get { flag("useLabels", default: true) } set { d.set(newValue, forKey: "useLabels") } }
    /// A click goes to the control at or beside the model's point (by name, else the one under it), not the bare point.
    var snap: Bool { get { flag("snap", default: true) } set { d.set(newValue, forKey: "snap") } }
    /// When something looked for on a screenshot is not a control the Mac can name, look once
    /// more at a square around the first answer (half the screen's longer side), sent at the
    /// usual size, and take that answer. Finds more of the smallest targets; costs a second read.
    var secondLook: Bool { get { Launch.secondLook || flag("secondLook", default: false) } set { d.set(newValue, forKey: "secondLook") } }
    /// Seconds between looks at the screen to keep its read current (0: only when the bar opens).
    var watchSeconds: Int {
        get { Launch.unattended ? 0 : (d.object(forKey: "watchSeconds") as? Int) ?? 30 }
        set { d.set(newValue, forKey: "watchSeconds") }
    }
    /// Screenshot and question in one message, as measured in the lab: every question pays the full read.
    var labLayout: Bool { get { flag("labLayout", default: false) } set { d.set(newValue, forKey: "labLayout") } }
    /// On quit: leave the model loaded and the server running instead of putting things back.
    var keepLoaded: Bool { get { flag("keepLoaded", default: false) } set { d.set(newValue, forKey: "keepLoaded") } }
}

// MARK: the API token (macOS Keychain; never in the settings, the log or the code)

enum Keychain {
    private static var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "BonsaiAssistant",
         kSecAttrAccount as String: "lm-studio-api-token"]
    }

    /// The stored token, read when a request is about to be sent; nil when none is stored.
    static func token() -> String? {
        var q = query
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    /// Whether a token is stored, without reading it.
    static var hasToken: Bool {
        var q = query
        q[kSecReturnAttributes as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        return SecItemCopyMatching(q as CFDictionary, nil) == errSecSuccess
    }

    /// Stores the token, or removes it when given nil or nothing.
    @discardableResult
    static func set(_ token: String?) -> Bool {
        SecItemDelete(query as CFDictionary)
        guard let token, !token.isEmpty, let data = token.data(using: .utf8) else { return true }
        var q = query
        q[kSecValueData as String] = data
        return SecItemAdd(q as CFDictionary, nil) == errSecSuccess
    }
}

// MARK: LM Studio's command-line tool (to start and stop its server)

enum StudioCLI {
    static let path = NSHomeDirectory() + "/.lmstudio/bin/lms"
    static var exists: Bool { FileManager.default.isExecutableFile(atPath: path) }

    /// Runs `lms` with the arguments and returns its exit code (-1: could not start, -2: took too long).
    /// Its output is dropped: a server it leaves running would keep a pipe open for ever.
    static func run(_ arguments: [String], timeout: TimeInterval = 45) async -> Int32 {
        await withCheckedContinuation { done in
            DispatchQueue.global(qos: .userInitiated).async {
                let process = Process()
                process.executableURL = URL(fileURLWithPath: path)
                process.arguments = arguments
                process.standardInput = FileHandle.nullDevice
                process.standardOutput = FileHandle.nullDevice
                process.standardError = FileHandle.nullDevice
                do { try process.run() } catch {
                    done.resume(returning: -1)
                    return
                }
                let deadline = Date().addingTimeInterval(timeout)
                while process.isRunning && Date() < deadline { usleep(100_000) }
                if process.isRunning {
                    process.terminate()
                    done.resume(returning: -2)
                } else {
                    done.resume(returning: process.terminationStatus)
                }
            }
        }
    }
}

// MARK: global hotkeys (Carbon: needs no permission)

final class HotKeys {
    static let shared = HotKeys()
    private var handlers: [UInt32: () -> Void] = [:]
    private var releases: [UInt32: () -> Void] = [:]           // for a key that is held: called when it is let go
    private var refs: [UInt32: EventHotKeyRef] = [:]
    private var installed = false

    private func install() {
        guard !installed else { return }
        installed = true
        var specs = [EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed)),
                     EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyReleased))]
        InstallEventHandler(GetEventDispatcherTarget(), { _, event, _ -> OSStatus in
            var id = EventHotKeyID()
            let status = GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil,
                                           MemoryLayout<EventHotKeyID>.size, nil, &id)
            if status == noErr {
                let n = id.id
                let letGo = GetEventKind(event) == UInt32(kEventHotKeyReleased)
                DispatchQueue.main.async { letGo ? HotKeys.shared.releases[n]?() : HotKeys.shared.handlers[n]?() }
            }
            return noErr
        }, 2, &specs, nil, nil)
    }

    @discardableResult
    func register(id: UInt32, keyCode: Int, modifiers: Int = 0, released: (() -> Void)? = nil, handler: @escaping () -> Void) -> Bool {
        install()
        unregister(id: id)
        releases[id] = released
        var ref: EventHotKeyRef?
        let hotKeyID = EventHotKeyID(signature: OSType(0x424E_5341), id: id)          // 'BNSA'
        let status = RegisterEventHotKey(UInt32(keyCode), UInt32(modifiers), hotKeyID, GetEventDispatcherTarget(), 0, &ref)
        guard status == noErr, let ref else { return false }
        refs[id] = ref
        handlers[id] = handler
        return true
    }

    func unregister(id: UInt32) {
        if let ref = refs.removeValue(forKey: id) { UnregisterEventHotKey(ref) }
        handlers[id] = nil
        releases[id] = nil
    }
}

// MARK: screen capture (ScreenCaptureKit; needs Screen Recording)

struct Shot {
    let full: CGImage          // the main display at full resolution
    let region: CGRect         // the display in points, Quartz global coordinates
    let scale: CGFloat         // pixels per point
    let seconds: Double
}

struct CaptureError: Error, CustomStringConvertible {
    let description: String
}

enum Capture {
    static func allowed() -> Bool { CGPreflightScreenCaptureAccess() }
    /// Brings up macOS's own question, unless nobody is there to answer it.
    static func ask() { if !Launch.unattended { _ = CGRequestScreenCaptureAccess() } }

    /// The main display (the one with the menu bar) without this app's own windows, so that
    /// the pointer, the input bar and the log never appear in what the model sees.
    static func mainDisplay() async throws -> Shot {
        let start = Date()
        let content: SCShareableContent
        do {
            content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        } catch {
            throw CaptureError(description: "The screen cannot be captured: Screen Recording is not allowed for the app this was started from "
                + "(Terminal, or Claude if started in its terminal panel). Allow it in System Settings > Privacy & Security > "
                + "Screen & System Audio Recording, then quit and start again. (\(error.localizedDescription))")
        }
        let mainID = CGMainDisplayID()
        guard let display = content.displays.first(where: { $0.displayID == mainID }) ?? content.displays.first else {
            throw CaptureError(description: "No display to capture")
        }
        let pid = ProcessInfo.processInfo.processIdentifier
        let own = content.applications.filter { $0.processID == pid }
        let filter = SCContentFilter(display: display, excludingApplications: own, exceptingWindows: [])
        let bounds = CGDisplayBounds(display.displayID)
        let config = SCStreamConfiguration()
        config.width = Int((bounds.width * CGFloat(filter.pointPixelScale)).rounded())
        config.height = Int((bounds.height * CGFloat(filter.pointPixelScale)).rounded())
        config.showsCursor = false
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        return Shot(full: image, region: bounds, scale: CGFloat(image.width) / bounds.width, seconds: Date().timeIntervalSince(start))
    }
}

// MARK: system events (needs Accessibility)

enum Events {
    /// Set to stop a long action (typing) part-way.
    static var cancelled = false

    static func allowed(prompt: Bool) -> Bool {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: prompt && !Launch.unattended] as CFDictionary
        return AXIsProcessTrustedWithOptions(options)
    }

    private static let source = CGEventSource(stateID: .hidSystemState)
    private static func post(_ event: CGEvent?) { event?.post(tap: .cghidEventTap) }
    private static func pause(_ ms: UInt32) { usleep(ms * 1000) }

    private static func mouse(_ type: CGEventType, _ p: CGPoint, _ button: CGMouseButton = .left, clicks: Int64 = 1) {
        let e = CGEvent(mouseEventSource: source, mouseType: type, mouseCursorPosition: p, mouseButton: button)
        e?.setIntegerValueField(.mouseEventClickState, value: clicks)
        e?.flags = []
        post(e)
    }

    static func move(to p: CGPoint) {
        mouse(.mouseMoved, p)
        pause(60)
    }

    static func click(at p: CGPoint, right: Bool = false, count: Int = 1) {
        move(to: p)
        for n in 1...max(1, count) {
            mouse(right ? .rightMouseDown : .leftMouseDown, p, right ? .right : .left, clicks: Int64(n))
            pause(40)
            mouse(right ? .rightMouseUp : .leftMouseUp, p, right ? .right : .left, clicks: Int64(n))
            pause(70)
        }
    }

    static func drag(from a: CGPoint, to b: CGPoint) {
        move(to: a)
        mouse(.leftMouseDown, a)
        pause(150)
        let n = 16
        for i in 1...n {
            let t = CGFloat(i) / CGFloat(n)
            mouse(.leftMouseDragged, CGPoint(x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t))
            pause(18)
        }
        pause(150)
        mouse(.leftMouseUp, b)
    }

    static func key(_ combo: Keys.Combo) {
        var flags: CGEventFlags = []
        if combo.command { flags.insert(.maskCommand) }
        if combo.control { flags.insert(.maskControl) }
        if combo.option { flags.insert(.maskAlternate) }
        if combo.shift { flags.insert(.maskShift) }
        if combo.function { flags.insert(.maskSecondaryFn) }
        let down = CGEvent(keyboardEventSource: source, virtualKey: combo.keyCode, keyDown: true)
        down?.flags = flags
        post(down)
        pause(40)
        let up = CGEvent(keyboardEventSource: source, virtualKey: combo.keyCode, keyDown: false)
        up?.flags = flags
        post(up)
        pause(40)
    }

    /// Types text as characters, whatever the keyboard layout. A newline presses Return, a tab Tab.
    static func type(_ text: String) {
        var buffer: [UniChar] = []
        func flush() {
            guard !buffer.isEmpty else { return }
            for down in [true, false] {
                let e = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: down)
                e?.flags = []
                e?.keyboardSetUnicodeString(stringLength: buffer.count, unicodeString: buffer)
                post(e)
                pause(8)
            }
            buffer.removeAll()
        }
        for ch in text {
            if cancelled { return }
            if ch == "\n" || ch == "\r" {
                flush()
                key(Keys.Combo(keyCode: 36))
            } else if ch == "\t" {
                flush()
                key(Keys.Combo(keyCode: 48))
            } else {
                buffer.append(contentsOf: Array(String(ch).utf16))
                if buffer.count >= 12 { flush() }
            }
        }
        flush()
    }

    /// About a third of a screen in the given direction, at the pointer.
    static func scroll(_ direction: String, at p: CGPoint?) {
        if let p { move(to: p) }
        var dx: Int32 = 0, dy: Int32 = 0
        switch direction {
        case "up": dy = 60
        case "left": dx = 60
        case "right": dx = -60
        default: dy = -60
        }
        for _ in 0..<6 {
            post(CGEvent(scrollWheelEvent2Source: source, units: .pixel, wheelCount: 2, wheel1: dy, wheel2: dx, wheel3: 0))
            pause(20)
        }
    }
}
