// The always-on-top transparent overlay: a pointer with a label, and a status line at the top.
// It never takes clicks or keys and is left out of the screenshots the model sees.
import AppKit
import AssistantCore

/// A dark rounded label.
final class Pill {
    let layer = CALayer()
    private let text = CATextLayer()
    private let font: NSFont
    private let maxWidth: CGFloat
    private(set) var size = CGSize.zero

    init(font: NSFont, maxWidth: CGFloat, scale: CGFloat) {
        self.font = font
        self.maxWidth = maxWidth
        layer.backgroundColor = NSColor(calibratedWhite: 0.06, alpha: 0.93).cgColor
        layer.cornerRadius = 11
        layer.borderWidth = 0.5
        layer.borderColor = NSColor(calibratedWhite: 1, alpha: 0.2).cgColor
        layer.shadowOpacity = 0.4
        layer.shadowRadius = 9
        layer.shadowOffset = CGSize(width: 0, height: -2)
        layer.anchorPoint = CGPoint(x: 0, y: 1)                  // positioned by its top-left corner
        layer.opacity = 0
        text.contentsScale = scale
        text.isWrapped = true
        text.alignmentMode = .left
        layer.addSublayer(text)
    }

    func set(_ string: String) {
        let attributed = NSAttributedString(string: string, attributes: [.font: font, .foregroundColor: NSColor.white])
        let box = attributed.boundingRect(with: CGSize(width: maxWidth, height: 600), options: [.usesLineFragmentOrigin, .usesFontLeading])
        let w = ceil(box.width) + 8, h = ceil(box.height) + 2      // a little slack: the layer wraps a hair earlier
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        text.string = attributed
        size = CGSize(width: w + 26, height: h + 16)
        layer.bounds = CGRect(origin: .zero, size: size)
        text.frame = CGRect(x: 13, y: 8, width: w, height: h)
        CATransaction.commit()
    }
}

final class Overlay {
    private let window: NSWindow
    private let root = CALayer()
    private let pointer = CALayer()
    private let endPointer = CALayer()
    private let line = CAShapeLayer()
    private let label: Pill
    private let hud: Pill
    private var screenFrame = CGRect.zero
    private var pointerShown = false
    private var lastPoint = CGPoint.zero
    static let accent = NSColor(calibratedRed: 0.16, green: 0.82, blue: 0.45, alpha: 1)

    init() {
        let screen = NSScreen.screens.first ?? NSScreen.main!
        let scale = screen.backingScaleFactor
        window = NSWindow(contentRect: screen.frame, styleMask: .borderless, backing: .buffered, defer: false)
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.ignoresMouseEvents = true
        window.level = .screenSaver
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
        window.isReleasedWhenClosed = false
        let view = NSView(frame: CGRect(origin: .zero, size: screen.frame.size))
        view.layer = root
        view.wantsLayer = true
        window.contentView = view

        label = Pill(font: .systemFont(ofSize: 14, weight: .medium), maxWidth: 340, scale: scale)
        hud = Pill(font: .monospacedDigitSystemFont(ofSize: 12.5, weight: .medium), maxWidth: 720, scale: scale)

        line.fillColor = nil
        line.strokeColor = Overlay.accent.cgColor
        line.lineWidth = 3
        line.lineDashPattern = [7, 6]
        line.lineCap = .round
        line.shadowOpacity = 0.5
        line.shadowRadius = 3
        line.shadowOffset = .zero
        line.opacity = 0
        root.addSublayer(line)
        Overlay.build(endPointer, pulsing: false)
        root.addSublayer(endPointer)
        Overlay.build(pointer, pulsing: true)
        root.addSublayer(pointer)
        root.addSublayer(label.layer)
        root.addSublayer(hud.layer)
    }

    /// A ring with a white halo, a soft fill, a centre dot and (for the main pointer) a pulse.
    private static func build(_ holder: CALayer, pulsing: Bool) {
        let side: CGFloat = 96
        holder.bounds = CGRect(x: 0, y: 0, width: side, height: side)
        holder.opacity = 0
        holder.shadowOpacity = 0.5
        holder.shadowRadius = 5
        holder.shadowOffset = CGSize(width: 0, height: -1)
        func circle(_ r: CGFloat) -> CGPath { CGPath(ellipseIn: CGRect(x: side / 2 - r, y: side / 2 - r, width: 2 * r, height: 2 * r), transform: nil) }
        if pulsing {
            let pulse = CAShapeLayer()
            pulse.frame = holder.bounds
            pulse.path = circle(19)
            pulse.fillColor = accent.withAlphaComponent(0.45).cgColor
            let grow = CABasicAnimation(keyPath: "transform.scale")
            grow.fromValue = 1
            grow.toValue = 2.4
            let fade = CABasicAnimation(keyPath: "opacity")
            fade.fromValue = 0.85
            fade.toValue = 0
            let group = CAAnimationGroup()
            group.animations = [grow, fade]
            group.duration = 1.35
            group.repeatCount = .infinity
            group.timingFunction = CAMediaTimingFunction(name: .easeOut)
            group.isRemovedOnCompletion = false
            pulse.opacity = 0
            pulse.add(group, forKey: "pulse")
            holder.addSublayer(pulse)
        }
        let halo = CAShapeLayer()
        halo.path = circle(19)
        halo.fillColor = nil
        halo.strokeColor = NSColor(calibratedWhite: 1, alpha: 0.95).cgColor
        halo.lineWidth = 7.5
        holder.addSublayer(halo)
        let ring = CAShapeLayer()
        ring.path = circle(19)
        ring.fillColor = accent.withAlphaComponent(0.16).cgColor
        ring.strokeColor = accent.cgColor
        ring.lineWidth = 4.5
        holder.addSublayer(ring)
        let dot = CAShapeLayer()
        dot.path = circle(3.4)
        dot.fillColor = accent.cgColor
        dot.strokeColor = NSColor.white.cgColor
        dot.lineWidth = 1.4
        holder.addSublayer(dot)
    }

    // MARK: placing things. Callers speak Quartz points (origin top left); layers want AppKit's.

    private func show() {
        if let screen = NSScreen.screens.first, screen.frame != screenFrame {
            screenFrame = screen.frame
            window.setFrame(screen.frame, display: true)
            root.frame = CGRect(origin: .zero, size: screen.frame.size)
        }
        window.orderFrontRegardless()
    }

    private func local(_ quartz: CGPoint) -> CGPoint {
        Geometry.appKitPoint(quartz: quartz, mainScreenHeight: screenFrame.height)
    }

    private func now(_ change: () -> Void) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        change()
        CATransaction.commit()
    }

    private func animated(_ seconds: Double, _ change: () -> Void) {
        CATransaction.begin()
        CATransaction.setAnimationDuration(seconds)
        CATransaction.setAnimationTimingFunction(CAMediaTimingFunction(controlPoints: 0.16, 1, 0.3, 1))
        change()
        CATransaction.commit()
    }

    /// The status line at the top centre of the screen.
    func status(_ text: String) {
        show()
        hud.set(text)
        now {
            hud.layer.position = CGPoint(x: (screenFrame.width - hud.size.width) / 2, y: screenFrame.height - 52)
            hud.layer.opacity = 1
        }
    }

    private func place(label text: String, near p: CGPoint) {
        label.set(text)
        // below and to the right of the ring; on the other side where it would leave the screen
        var x = p.x + 30, top = p.y - 24
        if x + label.size.width > screenFrame.width - 12 { x = p.x - 30 - label.size.width }
        if top - label.size.height < 12 { top = p.y + 24 + label.size.height }
        x = max(12, x)
        let moving = label.layer.opacity > 0
        let set = {
            self.label.layer.position = CGPoint(x: x, y: top)
            self.label.layer.opacity = 1
        }
        if moving { animated(0.5, set) } else { now(set) }
    }

    /// Moves the pointer to a place on screen (Quartz points) and labels it.
    func point(at quartz: CGPoint, label text: String) {
        show()
        let p = local(quartz)
        now {
            line.opacity = 0
            endPointer.opacity = 0
            if !pointerShown { pointer.position = NSEvent.mouseLocation }       // it flies in from the mouse
        }
        animated(pointerShown ? 0.5 : 0.65) {
            pointer.position = p
            pointer.opacity = 1
        }
        pointerShown = true
        lastPoint = p
        place(label: text, near: p)
    }

    /// A drag: the pointer at the start, a second ring at the end, a dashed line between.
    func drag(from a: CGPoint, to b: CGPoint, label text: String) {
        point(at: a, label: text)
        let p = local(a), q = local(b)
        let path = CGMutablePath()
        path.move(to: p)
        path.addLine(to: q)
        now {
            line.path = path
            endPointer.position = q
        }
        animated(0.4) {
            line.opacity = 1
            endPointer.opacity = 0.9
        }
    }

    /// New words for the label at the pointer (the model's sentence arriving after the point).
    func setLabel(_ text: String) {
        guard pointerShown else { return }
        place(label: text, near: lastPoint)
    }

    func hidePointer() {
        pointerShown = false
        animated(0.2) {
            pointer.opacity = 0
            endPointer.opacity = 0
            line.opacity = 0
            label.layer.opacity = 0
        }
    }

    func hideAll() {
        hidePointer()
        now { hud.layer.opacity = 0 }
        window.orderOut(nil)
    }
}
