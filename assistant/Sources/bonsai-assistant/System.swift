// The thin pieces that touch the machine: settings, global hotkeys, screen capture, system events.
import AppKit
import ApplicationServices
import AssistantCore
import Carbon.HIToolbox
import ScreenCaptureKit
import Security

// MARK: settings

final class Settings {
    static let shared = Settings()
    private let d = UserDefaults.standard

    var server: String {
        get { d.string(forKey: "server") ?? "http://localhost:1234/v1" }
        set { d.set(newValue, forKey: "server") }
    }
    var model: String {
        get { d.string(forKey: "model") ?? "" }
        set { d.set(newValue, forKey: "model") }
    }
    /// The model was picked in the menu (otherwise the app keeps choosing the best one it finds).
    var modelChosenByUser: Bool { get { flag("modelChosenByUser", default: false) } set { d.set(newValue, forKey: "modelChosenByUser") } }
    /// Longer side of the image that is sent, in pixels.
    var imageSide: Int {
        get { d.integer(forKey: "imageSide") == 896 ? 896 : 1280 }
        set { d.set(newValue, forKey: "imageSide") }
    }
    private func flag(_ key: String, default value: Bool) -> Bool { (d.object(forKey: key) as? Bool) ?? value }

    /// Steps run one after another without asking (Esc stops). Off: each step waits for Return.
    var continuous: Bool { get { flag("continuous", default: true) } set { d.set(newValue, forKey: "continuous") } }
    var speak: Bool { get { flag("speak", default: true) } set { d.set(newValue, forKey: "speak") } }
    var sentence: Bool { get { flag("sentence", default: true) } set { d.set(newValue, forKey: "sentence") } }
    var plainStepPrompt: Bool { get { flag("plainStepPrompt", default: false) } set { d.set(newValue, forKey: "plainStepPrompt") } }
    /// Read the screen as soon as the bar opens, before the request is typed.
    var readAhead: Bool { get { flag("readAhead", default: true) } set { d.set(newValue, forKey: "readAhead") } }
    /// Keep the screen read in the background whenever it changes, so an answer takes about a second.
    var watchScreen: Bool { get { flag("watchScreen", default: false) } set { d.set(newValue, forKey: "watchScreen") } }
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
    private var refs: [UInt32: EventHotKeyRef] = [:]
    private var installed = false

    private func install() {
        guard !installed else { return }
        installed = true
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetEventDispatcherTarget(), { _, event, _ -> OSStatus in
            var id = EventHotKeyID()
            let status = GetEventParameter(event, EventParamName(kEventParamDirectObject), EventParamType(typeEventHotKeyID), nil,
                                           MemoryLayout<EventHotKeyID>.size, nil, &id)
            if status == noErr {
                let n = id.id
                DispatchQueue.main.async { HotKeys.shared.handlers[n]?() }
            }
            return noErr
        }, 1, &spec, nil, nil)
    }

    @discardableResult
    func register(id: UInt32, keyCode: Int, modifiers: Int = 0, handler: @escaping () -> Void) -> Bool {
        install()
        unregister(id: id)
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
    static func ask() { _ = CGRequestScreenCaptureAccess() }

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
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: prompt] as CFDictionary
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
