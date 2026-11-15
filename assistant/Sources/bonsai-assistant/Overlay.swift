// What the app draws over the screen: a small pointer (Apple's arrow in frosted glass, a tiny
// window of its own so the glass can blur what is behind it) and one small box beside it with
// a text face and a few words. None of it takes clicks or keys, and all of it is left out of
// the screenshots the model sees.
import AppKit
import AssistantCore

/// The one look every box of the app has: the note beside the pointer and the box you type in.
enum BoxLook {
    static let fill = NSColor(calibratedWhite: 0.07, alpha: 0.88)
    static let edge = NSColor(calibratedWhite: 1, alpha: 0.2)
    static let radius: CGFloat = 10
    static let height: CGFloat = 27
    static let faceFont = NSFont.monospacedSystemFont(ofSize: 11.5, weight: .semibold)
    static let textFont = NSFont.systemFont(ofSize: 12.5, weight: .medium)
    static let faceColor = NSColor(calibratedWhite: 1, alpha: 0.72)

    static func style(_ layer: CALayer) {
        layer.backgroundColor = fill.cgColor
        layer.cornerRadius = radius
        layer.cornerCurve = .continuous
        layer.borderWidth = 0.75
        layer.borderColor = edge.cgColor
    }

    /// A face, then the words.
    static func line(face: String, text: String) -> NSAttributedString {
        let out = NSMutableAttributedString(string: face, attributes: [.font: faceFont, .foregroundColor: faceColor])
        if !text.isEmpty {
            out.append(NSAttributedString(string: (face.isEmpty ? "" : "  ") + text, attributes: [.font: textFont, .foregroundColor: NSColor.white]))
        }
        return out
    }
}

/// A small rounded box of dark glass with a line of text in it.
final class Pill {
    let layer = CALayer()
    private let text = CATextLayer()
    private let maxWidth: CGFloat
    private(set) var size = CGSize.zero

    init(maxWidth: CGFloat, scale: CGFloat) {
        self.maxWidth = maxWidth
        BoxLook.style(layer)
        layer.shadowOpacity = 0.28
        layer.shadowRadius = 7
        layer.shadowOffset = CGSize(width: 0, height: -2)
        layer.anchorPoint = CGPoint(x: 0, y: 1)                  // positioned by its top-left corner
        layer.opacity = 0
        text.contentsScale = scale
        text.isWrapped = true
        text.alignmentMode = .left
        layer.addSublayer(text)
    }

    func set(_ line: NSAttributedString) {
        let box = line.boundingRect(with: CGSize(width: maxWidth, height: 600), options: [.usesLineFragmentOrigin, .usesFontLeading])
        let w = ceil(box.width) + 8, h = ceil(box.height) + 2      // a little slack: the layer wraps a hair earlier
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        text.string = line
        size = CGSize(width: w + 20, height: max(h + 10, BoxLook.height))
        layer.bounds = CGRect(origin: .zero, size: size)
        text.frame = CGRect(x: 10, y: ((size.height - h) / 2).rounded(), width: w, height: h)
        CATransaction.commit()
    }
}

/// The pointer: the shape of the Mac's own arrow, a little smaller than it, in frosted glass.
/// It is a tiny window, because only a window's glass can blur what lies behind it; the window
/// is moved so that the arrow's tip sits exactly on a point of the screen.
final class GlassPointer: NSObject {
    static let scale: CGFloat = 0.86
    static let pad: CGFloat = 4
    /// The Mac's arrow, tip first, in points with y downwards.
    static let outline: [CGPoint] = [CGPoint(x: 0, y: 0), CGPoint(x: 0, y: 17.6), CGPoint(x: 4.2, y: 13.7), CGPoint(x: 7.4, y: 21.2),
                                     CGPoint(x: 10.3, y: 19.9), CGPoint(x: 7.1, y: 12.6), CGPoint(x: 12.8, y: 12.6)]
    static let size = CGSize(width: (12.8 * scale + 2 * pad).rounded(.up), height: (21.2 * scale + 2 * pad).rounded(.up))

    /// The arrow's long axis, from its tip to the end of its tail, and the direction across it.
    static let axis: CGPoint = {
        let tail = CGPoint(x: (outline[3].x + outline[4].x) / 2, y: (outline[3].y + outline[4].y) / 2)
        let length = hypot(tail.x, tail.y)
        return CGPoint(x: tail.x / length, y: tail.y / length)
    }()

    /// The arrow in a view of `size` (y upwards): the tip is `pad` in from the top left.
    /// `turn` is the cosine of how far the arrow has turned about its long axis: a flat shape
    /// turning about a line in its own plane is seen squeezed across that line by the cosine
    /// (1: face on, 0: edge on, -1: its other side). `grow` shrinks it towards its tip.
    static func path(turn: CGFloat = 1, grow: CGFloat = 1) -> CGPath {
        let a = axis, n = CGPoint(x: -a.y, y: a.x)
        let shape = CGMutablePath()
        for (i, p) in outline.enumerated() {
            let along = (p.x * a.x + p.y * a.y) * grow, across = (p.x * n.x + p.y * n.y) * turn * grow
            let t = CGPoint(x: a.x * along + n.x * across, y: a.y * along + n.y * across)
            let q = CGPoint(x: pad + t.x * scale, y: size.height - pad - t.y * scale)
            if i == 0 { shape.move(to: q) } else { shape.addLine(to: q) }
        }
        shape.closeSubpath()
        return shape
    }

    /// The arrow as a mask: solid where the glass is.
    static func mask(turn: CGFloat = 1, grow: CGFloat = 1) -> NSImage {
        NSImage(size: size, flipped: false) { _ in
            guard let ctx = NSGraphicsContext.current?.cgContext else { return false }
            ctx.addPath(path(turn: turn, grow: grow))
            ctx.setLineJoin(.round)
            ctx.setLineWidth(1.0)                                    // softens the corners; keeps a sliver when edge on
            ctx.setFillColor(CGColor(gray: 0, alpha: 1))
            ctx.setStrokeColor(CGColor(gray: 0, alpha: 1))
            ctx.drawPath(using: .fillStroke)
            return true
        }
    }

    /// What makes the glass look solid, like a little cut gem: light falls on it from the top
    /// left, so the body is brighter towards the tip, the edges facing the light carry a bright
    /// line and the edges facing away a dark one, and one clean white rim runs round it.
    static func finish(in ctx: CGContext, turn: CGFloat = 1, grow: CGFloat = 1) {
        let shape = path(turn: turn, grow: grow)
        let box = shape.boundingBoxOfPath
        ctx.saveGState()
        ctx.addPath(shape)
        ctx.clip()
        // the body: light at the tip, deep at the tail
        let colors = [CGColor(gray: 1, alpha: 0.42), CGColor(gray: 1, alpha: 0.08), CGColor(gray: 0, alpha: 0.26)] as CFArray
        if let shade = CGGradient(colorsSpace: CGColorSpaceCreateDeviceGray(), colors: colors, locations: [0, 0.5, 1]) {
            ctx.drawLinearGradient(shade, start: CGPoint(x: box.minX, y: box.maxY), end: CGPoint(x: box.maxX, y: box.minY), options: [])
        }
        if abs(turn) < 1 {                                           // a glint as it turns edge on
            ctx.setFillColor(CGColor(gray: 1, alpha: 0.3 * (1 - abs(turn))))
            ctx.fill(box)
        }
        ctx.setLineJoin(.round)
        // the bevel: a dark line inside the edges that face away from the light, a bright one inside those that face it
        var away = CGAffineTransform(translationX: -1.5, y: 1.5)
        ctx.addPath(shape.copy(using: &away) ?? shape)
        ctx.setStrokeColor(CGColor(gray: 0, alpha: 0.4))
        ctx.setLineWidth(1.5)
        ctx.strokePath()
        var toward = CGAffineTransform(translationX: 1.4, y: -1.4)
        ctx.addPath(shape.copy(using: &toward) ?? shape)
        ctx.setStrokeColor(CGColor(gray: 1, alpha: 0.6))
        ctx.setLineWidth(1.0)
        ctx.strokePath()
        // the rim
        ctx.addPath(shape)
        ctx.setStrokeColor(CGColor(gray: 1, alpha: 0.97))
        ctx.setLineWidth(2.2 * max(min(grow, 1), 0.5))               // half of it lies inside the edge
        ctx.strokePath()
        ctx.restoreGState()
    }

    private final class Finish: NSView {
        var turn: CGFloat = 1
        var grow: CGFloat = 1
        override var isOpaque: Bool { false }
        override func draw(_ dirtyRect: NSRect) {
            if let ctx = NSGraphicsContext.current?.cgContext { GlassPointer.finish(in: ctx, turn: turn, grow: grow) }
        }
    }

    private let window: NSPanel
    private let glass = NSVisualEffectView(frame: CGRect(origin: .zero, size: GlassPointer.size))
    private let rim = Finish(frame: CGRect(origin: .zero, size: GlassPointer.size))
    // One movement at a time (coming out, flying, thinking, idling, leaving), stepped once per
    // refresh of the display so it is as smooth as the screen allows.
    private var motion: CADisplayLink?
    private var step: ((Double) -> Void)?
    private var began = 0.0
    private var masks: [Int: NSImage] = [:]                          // the glass shapes already drawn, by turn and size
    private var rest = CGPoint.zero                                  // where it sits when it is not moving
    private var tip = CGPoint.zero                                   // where its tip is right now
    private(set) var isShown = false

    override init() {
        window = NSPanel(contentRect: CGRect(origin: .zero, size: GlassPointer.size), styleMask: [.borderless, .nonactivatingPanel],
                         backing: .buffered, defer: false)
        super.init()
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true
        window.ignoresMouseEvents = true
        window.level = NSWindow.Level(rawValue: NSWindow.Level.screenSaver.rawValue + 1)
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
        window.isReleasedWhenClosed = false
        window.hidesOnDeactivate = false
        window.appearance = NSAppearance(named: .vibrantDark)
        glass.material = .hudWindow                                  // dark frosted glass: reads on white pages and on dark ones
        glass.state = .active
        glass.blendingMode = .behindWindow
        glass.maskImage = GlassPointer.mask()
        glass.addSubview(rim)
        window.contentView = glass
    }

    private func place(tip p: CGPoint) {
        tip = p
        window.setFrameOrigin(CGPoint(x: p.x - GlassPointer.pad, y: p.y - (GlassPointer.size.height - GlassPointer.pad)))
    }

    private func set(turn: CGFloat, grow: CGFloat = 1) {
        // shapes are kept in steps of one sixtieth, fine enough to look continuous
        let t = (turn * 60).rounded() / 60, g = (grow * 60).rounded() / 60
        guard t != rim.turn || g != rim.grow || glass.maskImage == nil else { return }
        let key = Int((t + 2) * 60) * 1000 + Int(g * 60)
        let shape = masks[key] ?? GlassPointer.mask(turn: t, grow: g)
        masks[key] = shape
        glass.maskImage = shape
        rim.turn = t
        rim.grow = g
        rim.needsDisplay = true
    }

    private func stopMotion() {
        motion?.invalidate()
        motion = nil
        step = nil
    }

    /// Runs `step` with the seconds since now, once for every refresh of the display.
    private func run(_ step: @escaping (Double) -> Void) {
        stopMotion()
        self.step = step
        began = CACurrentMediaTime()
        guard let screen = NSScreen.screens.first ?? NSScreen.main else { return }
        let link = screen.displayLink(target: self, selector: #selector(tick(_:)))
        link.add(to: .main, forMode: .common)
        motion = link
    }

    @objc private func tick(_ link: CADisplayLink) {
        step?(CACurrentMediaTime() - began)
    }

    /// Settles the arrow face on and full size at its resting place.
    private func settle() {
        stopMotion()
        set(turn: 1)
        place(tip: rest)
        window.invalidateShadow()
    }

    /// Puts the arrow at `p`. If it is not out yet it grows out of `origin` (the tip of the
    /// Mac's own cursor) and slides the short way to `p`.
    func show(at p: CGPoint, from origin: CGPoint? = nil) {
        rest = p
        guard !isShown else { return settle() }
        isShown = true
        let from = origin ?? p
        set(turn: 1, grow: 0.3)
        place(tip: from)
        window.alphaValue = 1
        window.orderFrontRegardless()
        run { [weak self] elapsed in
            guard let self else { return }
            let k = min(elapsed / 0.26, 1), e = CGFloat(1 - pow(1 - k, 3))
            self.set(turn: 1, grow: 0.3 + 0.7 * e)
            self.place(tip: CGPoint(x: from.x + (p.x - from.x) * e, y: from.y + (p.y - from.y) * e))
            if k >= 1 { self.settle() }
        }
    }

    /// Waiting to be told something: it drifts a little about its place and sways as if
    /// breathing, so it is plainly alive. The place itself (and any box beside it) stays put.
    func idle() {
        guard isShown else { return }
        run { [weak self] elapsed in
            guard let self else { return }
            let t = CGFloat(elapsed)
            let dx = -3.5 + 4.5 * sin(0.9 * t) + 1.2 * sin(2.6 * t), dy = 3.2 * sin(1.3 * t + 1)
            self.set(turn: 0.87 + 0.13 * cos(1.7 * t))
            self.place(tip: CGPoint(x: self.rest.x + dx, y: self.rest.y + dy))
        }
    }

    /// It has been spoken to: it stops drifting and comes smartly to attention at its place.
    func lockIn() {
        guard isShown else { return }
        let from = tip
        run { [weak self] elapsed in
            guard let self else { return }
            let k = CGFloat(min(elapsed / 0.2, 1)), e = 1 - pow(1 - k, 3)
            self.set(turn: 1, grow: 1 + 0.12 * sin(.pi * k))
            self.place(tip: CGPoint(x: from.x + (self.rest.x - from.x) * e, y: from.y + (self.rest.y - from.y) * e))
            if k >= 1 { self.settle() }
        }
    }

    /// Done: it darts back to the Mac's cursor and shrinks away into it.
    func leave(into cursor: CGPoint, then done: @escaping () -> Void) {
        guard isShown else { return done() }
        let from = tip
        run { [weak self] elapsed in
            guard let self else { return }
            let k = CGFloat(min(elapsed / 0.26, 1)), e = k * k
            self.set(turn: 1, grow: 1 - 0.78 * e)
            self.place(tip: CGPoint(x: from.x + (cursor.x - from.x) * e, y: from.y + (cursor.y - from.y) * e))
            if k >= 1 {
                self.hide()
                done()
            }
        }
    }

    /// Follows the mouse while it waits (no animation, unless one is running).
    func follow(to p: CGPoint) {
        rest = p
        if motion == nil { place(tip: p) }
    }

    /// Thinking: small moves, one after another in a fixed order, so it looks alive without
    /// fuss: a hop, a pause, a slow turn about its long axis, a wiggle, a peek at its other side.
    func think(_ on: Bool) {
        guard isShown else { return }
        guard on else { return settle() }
        let length = 1.25
        run { [weak self] elapsed in
            guard let self else { return }
            let index = Int(elapsed / length)
            let phase = CGFloat(elapsed / length - Double(index))
            var turn: CGFloat = 1, dx: CGFloat = 0, dy: CGFloat = 0
            switch Faces.move(index) {
            case .hop: dy = 4 * sin(.pi * min(phase * 1.6, 1))
            case .turn: turn = cos(2 * .pi * Flight.eased(phase))
            case .wiggle: dx = 2.2 * sin(6 * .pi * phase) * (1 - phase)
            case .peek: turn = cos(.pi * sin(.pi * phase))
            case .rest: break
            }
            self.set(turn: turn)
            self.place(tip: CGPoint(x: self.rest.x + dx, y: self.rest.y + dy))
        }
    }

    /// Flies along the points: a small pull back against the way it is about to go, then off,
    /// easing into the landing. Returns the seconds the whole movement takes.
    @discardableResult
    func fly(along points: [CGPoint], seconds: Double) -> Double {
        guard let last = points.last else { return 0 }
        rest = last
        set(turn: 1)
        guard seconds > 0, points.count > 1 else {
            settle()
            return 0
        }
        let from = points[0], ahead = points[min(8, points.count - 1)]
        let reach = max(hypot(ahead.x - from.x, ahead.y - from.y), 0.001)
        let back = CGPoint(x: from.x - (ahead.x - from.x) / reach * 5, y: from.y - (ahead.y - from.y) / reach * 5)
        let windUp = 0.1
        run { [weak self] elapsed in
            guard let self else { return }
            if elapsed < windUp {
                let k = CGFloat(sin(elapsed / windUp * .pi / 2))
                self.place(tip: CGPoint(x: from.x + (back.x - from.x) * k, y: from.y + (back.y - from.y) * k))
                return
            }
            let share = CGFloat(min((elapsed - windUp) / seconds, 1))
            self.place(tip: Flight.position(on: points, at: 1 - pow(1 - share, 2.2)))
            if share >= 1 { self.settle() }
        }
        return seconds + windUp
    }

    func hide() {
        stopMotion()
        isShown = false
        window.orderOut(nil)
    }
}

final class Overlay {
    private let window: NSWindow
    private let root = CALayer()
    private let glass: GlassPointer?            // nil when nothing may be put on the display
    private let burst = CAShapeLayer()          // the small ring that goes out when a click is made
    private let endMark = CALayer()             // where a drag ends
    private let line = CAShapeLayer()
    private let label: Pill
    private let hud: Pill
    private let badge: Pill                     // "offline": shown while the Mac is off the network
    private var offline = false
    private var screenFrame = CGRect.zero
    private var pointerShown = false
    private var lastPoint = CGPoint.zero        // the arrow's tip, AppKit coordinates
    private var landing = 0                     // counts movements, so a late step does not act on a newer one
    // keeping company with the Mac's own cursor: where the mouse was last seen, since when it has
    // been still, and until when a flight to it is under way (the box waits for the flight to land)
    private var mouseAt = CGPoint.zero
    private var mouseStillSince = Date()
    private var flyingUntil = Date.distantPast
    /// The flights to a place made since they were last taken (start and end, in the screen
    /// points clicks use), for the account of a step: every step that acts should have one.
    private var flights: [(from: CGPoint, to: CGPoint)] = []
    var hasFlown: Bool { !flights.isEmpty }
    func takeFlights() -> [(from: CGPoint, to: CGPoint)] {
        defer { flights = [] }
        return flights
    }
    private let offscreen: Bool

    // what the box says: a mood (which gives the face), words, and a beat that keeps it alive
    private var mood: Mood?
    private var words = ""
    private var beat = 0
    private var shown = ""
    private var ticker: Timer?

    /// `offscreen`: never put on the display (for drawing a picture to a file).
    init(offscreen: Bool = false) {
        self.offscreen = offscreen
        glass = offscreen ? nil : GlassPointer()
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

        label = Pill(maxWidth: 300, scale: scale)
        hud = Pill(maxWidth: 640, scale: scale)
        badge = Pill(maxWidth: 320, scale: scale)
        badge.set(BoxLook.line(face: "", text: "offline · everything runs on this Mac"))

        line.fillColor = nil
        line.strokeColor = NSColor(calibratedWhite: 1, alpha: 0.9).cgColor
        line.lineWidth = 1.8
        line.lineDashPattern = [5, 5]
        line.lineCap = .round
        line.shadowOpacity = 0.55
        line.shadowRadius = 2.5
        line.shadowOffset = .zero
        line.opacity = 0
        root.addSublayer(line)

        endMark.bounds = .zero
        endMark.opacity = 0
        let circle = CAShapeLayer()
        circle.path = Overlay.ring(6)
        circle.fillColor = NSColor(calibratedWhite: 0.07, alpha: 0.5).cgColor
        circle.strokeColor = NSColor(calibratedWhite: 1, alpha: 0.95).cgColor
        circle.lineWidth = 1.8
        circle.shadowOpacity = 0.45
        circle.shadowRadius = 2.5
        circle.shadowOffset = .zero
        endMark.addSublayer(circle)
        root.addSublayer(endMark)

        burst.path = Overlay.ring(9)
        burst.fillColor = nil
        burst.strokeColor = NSColor(calibratedWhite: 1, alpha: 0.95).cgColor
        burst.lineWidth = 1.6
        burst.shadowOpacity = 0.5
        burst.shadowRadius = 2
        burst.shadowOffset = .zero
        burst.opacity = 0
        root.addSublayer(burst)
        root.addSublayer(label.layer)
        root.addSublayer(hud.layer)
        root.addSublayer(badge.layer)
    }

    private static func ring(_ radius: CGFloat) -> CGPath {
        CGPath(ellipseIn: CGRect(x: -radius, y: -radius, width: 2 * radius, height: 2 * radius), transform: nil)
    }

    // MARK: placing things. Callers speak Quartz points (origin top left); layers want AppKit's.

    private func show() {
        if let screen = NSScreen.screens.first, screen.frame != screenFrame {
            screenFrame = screen.frame
            window.setFrame(screen.frame, display: true)
            root.frame = CGRect(origin: .zero, size: screen.frame.size)
        }
        placeBadge()
        if !offscreen { window.orderFrontRegardless() }
    }

    /// The badge sits in the top right corner, just under the menu bar, whenever the
    /// assistant is out and the Mac is off the network.
    private func placeBadge() {
        let top = NSScreen.screens.first?.visibleFrame.maxY ?? screenFrame.height - 30
        now {
            badge.layer.position = CGPoint(x: (screenFrame.width - badge.size.width - 12).rounded(), y: (top - 8).rounded())
            badge.layer.opacity = offline ? 1 : 0
        }
    }

    func setOffline(_ on: Bool) {
        offline = on
        placeBadge()
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

    /// Makes a layer appear a moment from now (it stays invisible until then).
    private func appear(_ layer: CALayer, to opacity: Float, after delay: Double) {
        now { layer.opacity = opacity }
        layer.removeAnimation(forKey: "appear")
        guard delay > 0 else { return }
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = 0
        fade.toValue = opacity
        fade.duration = 0.18
        fade.beginTime = CACurrentMediaTime() + delay
        fade.fillMode = .backwards
        layer.add(fade, forKey: "appear")
    }

    /// Where a box of the given size goes: off to the side of the arrow, level with it; on
    /// its other side where the screen ends. The top-left corner, in AppKit screen points.
    func boxCorner(size: CGSize) -> CGPoint {
        let p = lastPoint
        var x = p.x + GlassPointer.size.width + 3
        if x + size.width > screenFrame.width - 10 { x = p.x - 10 - size.width }
        let middle = p.y - GlassPointer.size.height / 2 + 2
        let top = min(max(middle + size.height / 2, size.height + 8), screenFrame.height - 28)
        return CGPoint(x: max(8, x).rounded(), y: top.rounded())
    }

    /// Writes the face and the words of the moment into the box beside the arrow.
    private func refresh(after delay: Double = 0) {
        guard let mood, pointerShown else { return }
        if delay == 0, Date() < flyingUntil { return }                  // the box comes back when the arrow has landed
        let text = words.isEmpty ? Faces.words(mood, beat: beat) : words
        let face = Faces.face(mood, beat: beat)
        let line = face + "\u{1}" + text
        if line != shown {
            label.set(BoxLook.line(face: face, text: text))
            shown = line
        }
        now { label.layer.position = boxCorner(size: label.size) }
        if label.layer.opacity == 0 || delay > 0 { appear(label.layer, to: 1, after: delay) }
    }

    /// The faces move a little: a blink while listening, a change of thought while thinking.
    private func keepAlive(_ on: Bool) {
        ticker?.invalidate()
        ticker = nil
        guard on, !offscreen else { return }
        let t = Timer(timeInterval: 0.16, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.beat += 1
            self.refresh()
        }
        RunLoop.main.add(t, forMode: .common)
        ticker = t
    }

    private func set(_ mood: Mood?, _ text: String) {
        if mood != self.mood { beat = 0 }
        self.mood = mood
        words = text
        keepAlive(mood == .listening || mood == .thinking)
    }

    /// Where the arrow waits beside the Mac's own cursor: just to its right, a little lower.
    private func besideMouse() -> (tip: CGPoint, cursor: CGPoint) {
        let mouse = NSEvent.mouseLocation
        return (CGPoint(x: min(mouse.x + 13, screenFrame.width - 24), y: max(mouse.y - 9, 36)), mouse)
    }

    /// The arrow comes out of the Mac's cursor and waits beside it. With a mood, the box says
    /// it ("listening"); with none, the box stays away (the typing box takes its place).
    func hover(_ mood: Mood?, _ text: String = "") {
        show()
        let place = besideMouse()
        now {
            line.opacity = 0
            endMark.opacity = 0
        }
        if pointerShown {
            set(mood, text)
            keepCompany(place)
        } else {
            glass?.show(at: place.tip, from: place.cursor)
            lastPoint = place.tip
            mouseAt = place.cursor
            mouseStillSince = Date()
            flyingUntil = .distantPast
            set(mood, text)
        }
        pointerShown = true
        landing += 1
        if mood == nil {
            shown = ""
            now { label.layer.opacity = 0 }
        } else {
            refresh()
        }
    }

    /// The arrow is its own thing beside the Mac's cursor, not tied to it. While the mouse
    /// moves it stays where it is. When the mouse has been still for about a third of a second,
    /// or has got far away, it takes ONE flight to its place beside the cursor, with the same
    /// curve and easing as a flight to a target, and only then looks again. A small move of
    /// the mouse is not followed at all.
    private func keepCompany(_ place: (tip: CGPoint, cursor: CGPoint)) {
        let time = Date()
        if hypot(place.cursor.x - mouseAt.x, place.cursor.y - mouseAt.y) > 1.5 {
            mouseAt = place.cursor
            mouseStillSince = time
        }
        guard time >= flyingUntil else { return }                        // a flight is finished before the next is decided
        let gap = hypot(place.tip.x - lastPoint.x, place.tip.y - lastPoint.y)
        guard gap >= 60, time.timeIntervalSince(mouseStillSince) >= 0.3 || gap > 250 else { return }
        let seconds = min(0.9, max(0.35, 0.3 + Double(gap) / 1500))
        now { label.layer.opacity = 0 }
        let took = glass?.fly(along: Flight.points(from: lastPoint, to: place.tip), seconds: seconds) ?? seconds
        lastPoint = place.tip
        flyingUntil = time.addingTimeInterval(took * 0.9)
        shown = ""
        refresh(after: took * 0.92)
    }

    /// Says something in the box beside the arrow (bringing the arrow out beside the cursor if
    /// it is not out). `thinking`: the arrow makes its small thinking moves meanwhile.
    func say(_ mood: Mood, _ text: String = "", thinking: Bool = false) {
        if !pointerShown { hover(mood, text) }
        now {
            line.opacity = 0
            endMark.opacity = 0
        }
        set(mood, text)
        glass?.think(thinking)
        refresh()
    }

    /// Waiting for typing: the arrow drifts and sways by its place (`true`), or comes to
    /// attention there (`false`). Boxes do not move.
    func idle(_ on: Bool) {
        if on { glass?.idle() } else { glass?.lockIn() }
    }

    /// Done with: the arrow darts back into the Mac's cursor and is gone, with everything else.
    func retreat() {
        guard pointerShown, let glass else { return hideAll() }
        pointerShown = false
        shown = ""
        landing += 1
        let leaving = landing
        set(nil, "")
        [label.layer, line, endMark].forEach { $0.removeAnimation(forKey: "appear") }
        now {
            endMark.opacity = 0
            line.opacity = 0
            label.layer.opacity = 0
            hud.layer.opacity = 0
        }
        glass.leave(into: NSEvent.mouseLocation) { [weak self] in
            guard let self, self.landing == leaving else { return }
            self.window.orderOut(nil)
        }
    }

    /// A line at the top of the screen, for trouble that needs more than a few words
    /// (a missing permission, a server that does not answer).
    func trouble(_ text: String) {
        show()
        hud.set(BoxLook.line(face: "", text: text))
        now {
            hud.layer.position = CGPoint(x: ((screenFrame.width - hud.size.width) / 2).rounded(), y: screenFrame.height - 48)
            hud.layer.opacity = 1
        }
    }

    /// Sends the arrow to a place on screen (Quartz points) and says what it is doing there.
    /// Returns the seconds the flight takes.
    @discardableResult
    func point(at quartz: CGPoint, _ mood: Mood, _ text: String) -> Double {
        show()
        let target = local(quartz)
        if !pointerShown {
            let place = besideMouse()
            glass?.show(at: place.tip, from: place.cursor)
            lastPoint = place.tip
        }
        let start = lastPoint
        let distance = hypot(target.x - start.x, target.y - start.y)
        var seconds = distance < 6 ? 0 : min(1.0, max(0.55, 0.42 + Double(distance) / 1900))
        now {
            line.opacity = 0
            endMark.opacity = 0
            label.layer.opacity = 0
        }
        seconds = glass?.fly(along: Flight.points(from: start, to: target), seconds: seconds) ?? seconds
        flights.append((CGPoint(x: start.x, y: screenFrame.height - start.y), quartz))
        pointerShown = true
        lastPoint = target
        landing += 1
        set(mood, text)
        shown = ""
        refresh(after: seconds * 0.92)
        return seconds
    }

    /// A drag: the arrow at the start, a small ring at the end, a dashed line between.
    @discardableResult
    func drag(from a: CGPoint, to b: CGPoint, _ text: String) -> Double {
        let seconds = point(at: a, .acting, text)
        let p = local(a), q = local(b)
        let length = max(hypot(q.x - p.x, q.y - p.y), 1)
        let ux = (q.x - p.x) / length, uy = (q.y - p.y) / length
        let lead = min(8, length / 3), stop = min(8, length / 3)
        let path = CGMutablePath()
        path.move(to: CGPoint(x: p.x + ux * lead, y: p.y + uy * lead))
        path.addLine(to: CGPoint(x: q.x - ux * stop, y: q.y - uy * stop))
        now {
            line.path = path
            endMark.position = q
        }
        appear(line, to: 1, after: seconds * 0.95)
        appear(endMark, to: 1, after: seconds * 0.95)
        return seconds
    }

    /// The moment of a click: a small ring goes out from the arrow's tip.
    func clickEffect() {
        guard pointerShown else { return }
        now { burst.position = lastPoint }
        let grow = CABasicAnimation(keyPath: "transform.scale")
        grow.fromValue = 0.4
        grow.toValue = 1.9
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = 0.9
        fade.toValue = 0
        let out = CAAnimationGroup()
        out.animations = [grow, fade]
        out.duration = 0.38
        out.timingFunction = CAMediaTimingFunction(name: .easeOut)
        burst.add(out, forKey: "burst")
    }

    func hidePointer() {
        pointerShown = false
        shown = ""
        landing += 1
        set(nil, "")
        glass?.hide()
        [label.layer, line, endMark].forEach { $0.removeAnimation(forKey: "appear") }
        now {
            endMark.opacity = 0
            line.opacity = 0
            label.layer.opacity = 0
        }
    }

    func hideAll() {
        hidePointer()
        now { hud.layer.opacity = 0 }
        window.orderOut(nil)
    }

    /// A picture, drawn to a file, of the arrow at its real size beside a stand-in for the
    /// Mac's cursor, the box in each mood, the typing box, and the thinking moves (the display
    /// is not involved, so the blur behind the glass and the shadows are missing).
    static func preview(to path: String) -> Bool {
        let overlay = Overlay(offscreen: true)
        overlay.show()
        let region = CGRect(x: 0, y: 0, width: 900, height: 400)
        let scale: CGFloat = 2
        guard let ctx = CGContext(data: nil, width: Int(region.width * scale), height: Int(region.height * scale), bitsPerComponent: 8,
                                  bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
        else { return false }
        ctx.scaleBy(x: scale, y: scale)
        for (i, grey) in [CGFloat(0.97), 0.17].enumerated() {                    // a light half and a dark half
            ctx.setFillColor(CGColor(gray: grey, alpha: 1))
            ctx.fill(CGRect(x: CGFloat(i) * region.width / 2, y: 0, width: region.width / 2, height: region.height))
        }
        func arrow(tip: CGPoint, turn: CGFloat = 1, grow: CGFloat = 1, solid: Bool = false) {
            ctx.saveGState()
            ctx.translateBy(x: tip.x - GlassPointer.pad, y: tip.y - (GlassPointer.size.height - GlassPointer.pad))
            ctx.addPath(GlassPointer.path(turn: turn, grow: grow))
            ctx.setFillColor(CGColor(gray: solid ? 0 : 0.13, alpha: solid ? 1 : 0.62))   // solid: the Mac's own cursor
            ctx.fillPath()
            GlassPointer.finish(in: ctx, turn: turn, grow: grow)
            ctx.restoreGState()
        }
        func box(_ mood: Mood, _ text: String, beat: Int = 0, tip: CGPoint) {
            let pill = Pill(maxWidth: 300, scale: scale)
            pill.set(BoxLook.line(face: Faces.face(mood, beat: beat), text: text.isEmpty ? Faces.words(mood, beat: beat) : text))
            overlay.lastPoint = tip
            let corner = overlay.boxCorner(size: pill.size)
            ctx.saveGState()
            ctx.translateBy(x: corner.x, y: corner.y - pill.size.height)
            pill.layer.opacity = 1
            pill.layer.render(in: ctx)
            ctx.restoreGState()
        }
        let h = region.height
        let rows: [(Mood, String, Int)] = [(.listening, "", 0), (.listening, "", 15), (.heard, "\"click the search field\"", 0), (.thinking, "", 0),
                                           (.thinking, "", 9), (.thinking, "", 20), (.acting, "click the search field", 0), (.done, "", 0),
                                           (.lost, "", 0), (.sorry, "can't find that here", 0)]
        for (i, row) in rows.enumerated() {
            let column = CGFloat(i / 5), line = CGFloat(i % 5)
            let cursor = CGPoint(x: 40 + column * 450, y: h - 40 - line * 52)
            arrow(tip: cursor, solid: true)                                      // where the Mac's cursor is
            let tip = CGPoint(x: cursor.x + 13, y: cursor.y - 9)
            arrow(tip: tip)
            box(row.0, row.1, beat: row.2, tip: tip)
        }
        for (i, turn) in [CGFloat(1), 0.6, 0.1, -0.6, -1].enumerated() {       // the slow turn, and coming out of the cursor
            arrow(tip: CGPoint(x: 60 + CGFloat(i) * 34, y: 95), turn: turn)
            arrow(tip: CGPoint(x: 510 + CGFloat(i) * 34, y: 95), grow: 0.3 + 0.175 * CGFloat(i))
        }
        for (i, x) in [CGFloat(300), 750].enumerated() {                         // the glass, four times its size
            ctx.saveGState()
            ctx.translateBy(x: x, y: 110)
            ctx.scaleBy(x: 4, y: 4)
            ctx.translateBy(x: -GlassPointer.pad, y: -(GlassPointer.size.height - GlassPointer.pad))
            ctx.addPath(GlassPointer.path())
            ctx.setFillColor(CGColor(gray: i == 0 ? 0.55 : 0.2, alpha: 0.6))     // stands in for the blurred background
            ctx.fillPath()
            GlassPointer.finish(in: ctx)
            ctx.restoreGState()
        }
        guard let image = ctx.makeImage() else { return false }
        return ImageOps.save(image, path: path)
    }
}
