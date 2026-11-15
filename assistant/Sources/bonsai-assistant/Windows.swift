// The floating input bar and the log window.
import AppKit

/// A panel that takes typing without making this app the active one, so the app the user was
/// in stays in front (as Spotlight does).
final class InputPanel: NSPanel {
    var onCommandReturn: (() -> Void)?
    var onEscape: (() -> Void)?

    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        guard event.type == .keyDown, event.modifierFlags.contains(.command) else { return super.performKeyEquivalent(with: event) }
        if event.keyCode == 36 || event.keyCode == 76 {
            onCommandReturn?()
            return true
        }
        // An accessory app has no Edit menu; the usual editing keys are passed on by hand.
        let actions: [String: Selector] = ["v": #selector(NSText.paste(_:)), "c": #selector(NSText.copy(_:)),
                                           "x": #selector(NSText.cut(_:)), "a": #selector(NSText.selectAll(_:))]
        if let key = event.charactersIgnoringModifiers?.lowercased(), let action = actions[key] {
            return NSApp.sendAction(action, to: nil, from: self)
        }
        return super.performKeyEquivalent(with: event)
    }

    override func cancelOperation(_ sender: Any?) { onEscape?() }
}

final class InputBar: NSObject, NSTextFieldDelegate {
    private let panel: InputPanel
    private let field = NSTextField()
    private let hint = NSTextField(labelWithString: "")
    /// (the request, true for "only show me, do nothing")
    var onSubmit: ((String, Bool) -> Void)?
    var isShown: Bool { panel.isVisible }

    override init() {
        let size = CGSize(width: 660, height: 92)
        panel = InputPanel(contentRect: CGRect(origin: .zero, size: size), styleMask: [.borderless, .nonactivatingPanel],
                           backing: .buffered, defer: false)
        super.init()
        panel.isFloatingPanel = true
        panel.level = NSWindow.Level(rawValue: NSWindow.Level.screenSaver.rawValue + 1)
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.hidesOnDeactivate = false
        panel.isReleasedWhenClosed = false
        panel.appearance = NSAppearance(named: .vibrantDark)
        panel.onCommandReturn = { [weak self] in self?.submit(showOnly: true) }
        panel.onEscape = { [weak self] in self?.hide() }

        let glass = NSVisualEffectView(frame: CGRect(origin: .zero, size: size))
        glass.material = .hudWindow
        glass.state = .active
        glass.blendingMode = .behindWindow
        glass.wantsLayer = true
        glass.layer?.cornerRadius = 18
        glass.layer?.masksToBounds = true
        glass.layer?.borderWidth = 0.5
        glass.layer?.borderColor = NSColor(calibratedWhite: 1, alpha: 0.22).cgColor
        panel.contentView = glass

        let leaf = NSImageView(frame: CGRect(x: 20, y: 46, width: 26, height: 26))
        leaf.image = NSImage(systemSymbolName: "leaf.fill", accessibilityDescription: "Bonsai")
        leaf.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 20, weight: .semibold)
        leaf.contentTintColor = Overlay.accent
        glass.addSubview(leaf)

        field.frame = CGRect(x: 56, y: 42, width: size.width - 76, height: 32)
        field.font = .systemFont(ofSize: 21, weight: .regular)
        field.isBordered = false
        field.drawsBackground = false
        field.focusRingType = .none
        field.textColor = .white
        field.placeholderString = "Ask about what is on your screen"
        field.delegate = self
        field.cell?.usesSingleLineMode = true
        field.cell?.isScrollable = true
        glass.addSubview(field)

        hint.frame = CGRect(x: 22, y: 14, width: size.width - 44, height: 16)
        hint.font = .systemFont(ofSize: 11.5, weight: .medium)
        hint.textColor = NSColor(calibratedWhite: 1, alpha: 0.6)
        hint.lineBreakMode = .byTruncatingTail
        glass.addSubview(hint)
    }

    func show(model: String) {
        let screen = NSScreen.screens.first ?? NSScreen.main
        if let frame = screen?.frame {
            let size = panel.frame.size
            panel.setFrameOrigin(CGPoint(x: frame.midX - size.width / 2, y: frame.minY + frame.height * 0.66))
        }
        hint.stringValue = "Return  do it (a question is answered by pointing)      ⌘ Return  only point      Esc  close      ·      " + (model.isEmpty ? "no model chosen" : model)
        panel.makeKeyAndOrderFront(nil)
        panel.makeFirstResponder(field)
        field.selectText(nil)
    }

    func hide() { panel.orderOut(nil) }

    private func submit(showOnly: Bool) {
        let text = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        hide()
        onSubmit?(text, showOnly)
    }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        if selector == #selector(NSResponder.insertNewline(_:)) {
            submit(showOnly: NSEvent.modifierFlags.contains(.command))
            return true
        }
        if selector == #selector(NSResponder.cancelOperation(_:)) {
            hide()
            return true
        }
        return false
    }
}

/// Every step with what was asked, what the model wrote, the action and the timings.
/// The same lines go to ~/Library/Logs/BonsaiAssistant/assistant.log.
final class LogWindow {
    private let window: NSWindow
    private let text: NSTextView
    private let file: FileHandle?
    private let clock: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()
    let path: String

    init() {
        let frame = CGRect(x: 0, y: 0, width: 780, height: 420)
        window = NSWindow(contentRect: frame, styleMask: [.titled, .closable, .resizable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Bonsai assistant: log"
        window.isReleasedWhenClosed = false
        let scroll = NSTextView.scrollableTextView()
        scroll.frame = frame
        scroll.autoresizingMask = [.width, .height]
        text = scroll.documentView as! NSTextView
        text.isEditable = false
        text.font = .monospacedSystemFont(ofSize: 11.5, weight: .regular)
        text.textContainerInset = CGSize(width: 10, height: 10)
        window.contentView = scroll
        if let screen = NSScreen.screens.first {
            window.setFrameOrigin(CGPoint(x: screen.visibleFrame.maxX - frame.width - 16, y: screen.visibleFrame.minY + 16))
        }

        let dir = NSHomeDirectory() + "/Library/Logs/BonsaiAssistant"
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        path = dir + "/assistant.log"
        if !FileManager.default.fileExists(atPath: path) { FileManager.default.createFile(atPath: path, contents: nil) }
        file = FileHandle(forWritingAtPath: path)
        file?.seekToEndOfFile()
    }

    func show(activate: Bool) {
        if activate {
            NSApp.activate(ignoringOtherApps: true)
            window.makeKeyAndOrderFront(nil)
        } else {
            window.orderFrontRegardless()                // visible, but the app in front keeps the keyboard
        }
    }

    /// Where the window is on screen (AppKit coordinates), or nil while it is hidden.
    var frameOnScreen: CGRect? { window.isVisible ? window.frame : nil }
    func hide() { window.orderOut(nil) }

    /// A headline with the time, then indented detail lines.
    func add(_ headline: String, _ details: [String] = []) {
        var block = "[\(clock.string(from: Date()))] \(headline)\n"
        for line in details where !line.isEmpty { block += "    \(line)\n" }
        text.textStorage?.append(NSAttributedString(string: block, attributes: [
            .font: NSFont.monospacedSystemFont(ofSize: 11.5, weight: .regular), .foregroundColor: NSColor.labelColor]))
        text.scrollToEndOfDocument(nil)
        if let data = block.data(using: .utf8) { file?.write(data) }
    }
}
