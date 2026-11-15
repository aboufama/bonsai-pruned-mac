// The floating input bar and the log window.
import AppKit
import AssistantCore

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

/// Small drawings shared by the bar and the menu, so that the app has one look.
enum Look {
    /// A stretchable rounded rectangle. As the mask of a visual-effect view it gives the window
    /// itself the rounded shape, so its shadow and edge follow the curve (a corner radius on the
    /// layer leaves the window square, which shows as a rectangle around the glass).
    static func roundedMask(radius: CGFloat) -> NSImage {
        let edge = radius * 2 + 1
        let image = NSImage(size: NSSize(width: edge, height: edge), flipped: false) { rect in
            NSColor.black.setFill()
            NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius).fill()
            return true
        }
        image.capInsets = NSEdgeInsets(top: radius, left: radius, bottom: radius, right: radius)
        image.resizingMode = .stretch
        return image
    }

    /// The pointer's arrow as a small picture: clear glass with a bright rim, no colour.
    static func arrow(height: CGFloat) -> NSImage {
        let k = height / 24
        return NSImage(size: NSSize(width: 22 * k, height: 25 * k), flipped: true) { _ in
            let shape = NSBezierPath()
            shape.move(to: NSPoint(x: 2.5 * k, y: 2.5 * k))
            shape.line(to: NSPoint(x: 6.9 * k, y: 22.5 * k))
            shape.line(to: NSPoint(x: 11.2 * k, y: 15.4 * k))
            shape.line(to: NSPoint(x: 19.8 * k, y: 13.2 * k))
            shape.close()
            shape.lineJoinStyle = .round
            NSColor(calibratedWhite: 0, alpha: 0.3).setStroke()
            shape.lineWidth = 3.6 * k
            shape.stroke()
            NSGradient(colors: [NSColor(calibratedWhite: 1, alpha: 0.8), NSColor(calibratedWhite: 1, alpha: 0.22)])?
                .draw(in: shape, angle: 60)
            NSColor(calibratedWhite: 1, alpha: 0.96).setStroke()
            shape.lineWidth = 1.5 * k
            shape.stroke()
            return true
        }
    }
}

/// Typing instead of speaking: the same small box as the note beside the pointer, with a
/// face that watches what is typed. Return does it, Command-Return only points, Esc closes it.
final class InputBar: NSObject, NSTextFieldDelegate {
    static let size = CGSize(width: 264, height: BoxLook.height)

    private let panel: InputPanel
    private let face = NSTextField(labelWithString: Faces.typing(""))
    private let field = NSTextField()
    /// (the request, true for "only show me, do nothing")
    var onSubmit: ((String, Bool) -> Void)?
    var onCancel: (() -> Void)?
    /// Called when the box goes from empty to holding text (true) or back (false).
    var onTyping: ((Bool) -> Void)?
    private var holdsText = false
    var isShown: Bool { panel.isVisible }

    override init() {
        panel = InputPanel(contentRect: CGRect(origin: .zero, size: InputBar.size), styleMask: [.borderless, .nonactivatingPanel],
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
        panel.appearance = NSAppearance(named: .darkAqua)
        panel.onCommandReturn = { [weak self] in self?.submit(showOnly: true) }
        panel.onEscape = { [weak self] in self?.cancel() }
        panel.contentView = InputBar.content(face: face, field: field)
        field.delegate = self
    }

    /// The box's contents: the look every box has, a face, and the field.
    static func content(face: NSTextField, field: NSTextField) -> NSView {
        let size = InputBar.size
        let box = NSView(frame: CGRect(origin: .zero, size: size))
        box.wantsLayer = true
        if let layer = box.layer { BoxLook.style(layer) }

        face.font = BoxLook.faceFont
        face.textColor = BoxLook.faceColor
        face.frame = CGRect(x: 10, y: ((size.height - 15) / 2).rounded(), width: 46, height: 15)
        box.addSubview(face)

        field.frame = CGRect(x: 60, y: ((size.height - 17) / 2).rounded(), width: size.width - 60 - 10, height: 17)
        field.font = BoxLook.textFont
        field.isBordered = false
        field.drawsBackground = false
        field.focusRingType = .none
        field.textColor = .white
        field.placeholderAttributedString = NSAttributedString(string: "type what to do", attributes: [
            .font: BoxLook.textFont, .foregroundColor: NSColor(calibratedWhite: 1, alpha: 0.4)])
        field.cell?.usesSingleLineMode = true
        field.cell?.isScrollable = true
        box.addSubview(field)
        return box
    }

    /// Shows the box with its top-left corner at a place on screen (where the note would be).
    func show(corner: CGPoint) {
        field.stringValue = ""
        holdsText = false
        face.stringValue = Faces.typing("")
        panel.setFrameOrigin(CGPoint(x: corner.x.rounded(), y: (corner.y - InputBar.size.height).rounded()))
        panel.makeKeyAndOrderFront(nil)
        panel.invalidateShadow()
        panel.makeFirstResponder(field)
    }

    func hide() { panel.orderOut(nil) }

    private func cancel() {
        hide()
        onCancel?()
    }

    private func submit(showOnly: Bool) {
        let text = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        hide()
        onSubmit?(text, showOnly)
    }

    func controlTextDidChange(_ notification: Notification) {
        face.stringValue = Faces.typing(field.stringValue)
        let typing = !field.stringValue.trimmingCharacters(in: .whitespaces).isEmpty
        if typing != holdsText {
            holdsText = typing
            onTyping?(typing)
        }
    }

    func control(_ control: NSControl, textView: NSTextView, doCommandBy selector: Selector) -> Bool {
        if selector == #selector(NSResponder.insertNewline(_:)) {
            submit(showOnly: NSEvent.modifierFlags.contains(.command))
            return true
        }
        if selector == #selector(NSResponder.cancelOperation(_:)) {
            cancel()
            return true
        }
        return false
    }
}

/// The top of the leaf's menu: the app's name and, under it, one line on how things stand.
final class MenuHeader: NSView {
    enum State { case ready, busy, problem }
    private let name = NSTextField(labelWithString: "Bonsai")
    private let status = NSTextField(labelWithString: "")
    private let dot = NSView()

    init() {
        super.init(frame: CGRect(x: 0, y: 0, width: 286, height: 50))
        let arrow = NSImageView(frame: CGRect(x: 14, y: 25, width: 15, height: 17))
        arrow.image = Look.arrow(height: 16)
        arrow.imageScaling = .scaleNone
        addSubview(arrow)
        name.frame = CGRect(x: 34, y: 25, width: 230, height: 17)
        name.font = .systemFont(ofSize: 13, weight: .semibold)
        name.textColor = .labelColor
        addSubview(name)
        dot.frame = CGRect(x: 17, y: 11, width: 7, height: 7)
        dot.wantsLayer = true
        dot.layer?.cornerRadius = 3.5
        addSubview(dot)
        status.frame = CGRect(x: 34, y: 6, width: 240, height: 15)
        status.font = .systemFont(ofSize: 11.5, weight: .regular)
        status.textColor = .secondaryLabelColor
        status.lineBreakMode = .byTruncatingMiddle
        addSubview(status)
    }

    required init?(coder: NSCoder) { nil }

    func set(_ text: String, _ state: State) {
        status.stringValue = text
        switch state {
        case .ready: dot.layer?.backgroundColor = NSColor.labelColor.withAlphaComponent(0.75).cgColor
        case .busy: dot.layer?.backgroundColor = NSColor.systemOrange.cgColor
        case .problem: dot.layer?.backgroundColor = NSColor.systemRed.cgColor
        }
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

        if let chosen = Launch.log {
            path = (chosen as NSString).expandingTildeInPath
            try? FileManager.default.createDirectory(atPath: (path as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
        } else {
            let dir = NSHomeDirectory() + "/Library/Logs/BonsaiAssistant"
            try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            path = dir + "/assistant.log"
        }
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
