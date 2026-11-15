import CoreGraphics

/// The way the pointer travels from one place to another: a gentle arc. Worked out as a list
/// of points so that a window can be moved along it.
public enum Flight {
    static func cubic(_ a: CGPoint, _ b: CGPoint, _ c: CGPoint, _ d: CGPoint, _ t: CGFloat) -> CGPoint {
        let m = 1 - t
        let x = m * m * m * a.x + 3 * m * m * t * b.x + 3 * m * t * t * c.x + t * t * t * d.x
        let y = m * m * m * a.y + 3 * m * m * t * b.y + 3 * m * t * t * c.y + t * t * t * d.y
        return CGPoint(x: x, y: y)
    }

    /// The points of a flight: one gentle arc from the start to the target, bowed a little to
    /// one side so it does not look like a ruler line.
    public static func points(from s: CGPoint, to t: CGPoint) -> [CGPoint] {
        let dx = t.x - s.x, dy = t.y - s.y
        let length = max(hypot(dx, dy), 1)
        let bow = min(length * 0.1, 46)
        let control = CGPoint(x: (s.x + t.x) / 2 + dy / length * bow, y: (s.y + t.y) / 2 - dx / length * bow)
        var out: [CGPoint] = [s]
        for i in 1...48 {
            let k = CGFloat(i) / 48, m = 1 - k
            out.append(CGPoint(x: m * m * s.x + 2 * m * k * control.x + k * k * t.x, y: m * m * s.y + 2 * m * k * control.y + k * k * t.y))
        }
        return out
    }

    /// The place a share (0...1) of the way along the points, measured by distance.
    public static func position(on points: [CGPoint], at share: CGFloat) -> CGPoint {
        guard let first = points.first, let last = points.last else { return .zero }
        if share <= 0 { return first }
        if share >= 1 { return last }
        var total: CGFloat = 0
        for i in 1..<points.count { total += hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y) }
        var want = total * share
        for i in 1..<points.count {
            let step = hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
            if want <= step, step > 0 {
                let k = want / step
                return CGPoint(x: points[i - 1].x + (points[i].x - points[i - 1].x) * k, y: points[i - 1].y + (points[i].y - points[i - 1].y) * k)
            }
            want -= step
        }
        return last
    }

    /// Slow out of the start, quick through the loop, slow into the landing.
    public static func eased(_ x: CGFloat) -> CGFloat {
        let t = min(max(x, 0), 1)
        return t < 0.5 ? 4 * t * t * t : 1 - pow(-2 * t + 2, 3) / 2
    }
}
