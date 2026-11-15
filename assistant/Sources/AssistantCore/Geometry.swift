import CoreGraphics

/// Three units meet in this app and must never be mixed up:
///
///   grid     the model's answer: 0...1000 on each axis over the image it was shown
///   pixels   an image: the full-resolution capture, or the shrunk copy that was sent
///   points   the screen in Quartz global coordinates: origin at the top left of the main
///            display, y grows downwards. A Retina display has 2 pixels per point.
///
/// Every conversion goes through this file.
public enum Geometry {
    public static let grid: CGFloat = 1000

    /// The conversion the pointer and every click depend on: a model answer to a place on screen.
    /// `region` is the part of the screen, in points, covered by the image the model was shown:
    /// the whole display for a first look, a smaller window for a zoomed look. The size of the
    /// image in pixels does not enter: the grid is relative to the image, whatever its size.
    public static func screenPoint(grid p: CGPoint, region: CGRect) -> CGPoint {
        let fx = min(max(p.x, 0), grid) / grid
        let fy = min(max(p.y, 0), grid) / grid
        // An answer of exactly 1000 would land one point outside the region; keep it inside.
        let x = min(region.minX + fx * region.width, region.maxX - 1)
        let y = min(region.minY + fy * region.height, region.maxY - 1)
        return CGPoint(x: max(x, region.minX), y: max(y, region.minY))
    }

    /// The inverse, for the log and the history: a place on screen as the model would write it.
    public static func gridPoint(screen p: CGPoint, region: CGRect) -> CGPoint {
        guard region.width > 0, region.height > 0 else { return .zero }
        let x = (p.x - region.minX) / region.width * grid
        let y = (p.y - region.minY) / region.height * grid
        return CGPoint(x: min(max(x.rounded(), 0), grid), y: min(max(y.rounded(), 0), grid))
    }

    /// A model answer as a pixel of an image of the given size (for drawing on a saved screenshot).
    public static func pixel(grid p: CGPoint, imageWidth: Int, imageHeight: Int) -> CGPoint {
        CGPoint(x: min(max(p.x, 0), grid) / grid * CGFloat(imageWidth),
                y: min(max(p.y, 0), grid) / grid * CGFloat(imageHeight))
    }

    /// The size an image is shrunk to before it is sent: its longer side at most `longSide`
    /// pixels, shape kept, never enlarged (the rule the models were tuned and measured with).
    public static func fittedSize(width: Int, height: Int, longSide: Int) -> (width: Int, height: Int) {
        let longest = max(width, height)
        guard longest > longSide, longest > 0 else { return (width, height) }
        let s = Double(longSide) / Double(longest)
        return (max(1, Int((Double(width) * s).rounded())), max(1, Int((Double(height) * s).rounded())))
    }

    /// The window of a zoomed second look: 1/zoom of each side of `region`, centred on `p`
    /// and pushed back inside the region where it would stick out. Points in, points out.
    public static func zoomWindow(around p: CGPoint, in region: CGRect, zoom: CGFloat) -> CGRect {
        let w = region.width / zoom, h = region.height / zoom
        let cx = min(max(p.x, region.minX + w / 2), region.maxX - w / 2)
        let cy = min(max(p.y, region.minY + h / 2), region.maxY - h / 2)
        return CGRect(x: cx - w / 2, y: cy - h / 2, width: w, height: h)
    }

    /// The window of a second look: a square of the given side around a point, moved so that
    /// it stays inside the region (and cut to the region where the region is smaller than it).
    public static func squareWindow(around p: CGPoint, in region: CGRect, side: CGFloat) -> CGRect {
        let w = min(side, region.width), h = min(side, region.height)
        let cx = min(max(p.x, region.minX + w / 2), region.maxX - w / 2)
        let cy = min(max(p.y, region.minY + h / 2), region.maxY - h / 2)
        return CGRect(x: cx - w / 2, y: cy - h / 2, width: w, height: h)
    }

    /// A screen region as whole pixels of the full-resolution capture of a display.
    /// `displayOrigin` is the display's top-left corner in points, `scale` its pixels per point.
    public static func pixelRect(points r: CGRect, displayOrigin: CGPoint, scale: CGFloat) -> CGRect {
        let x0 = ((r.minX - displayOrigin.x) * scale).rounded(.down)
        let y0 = ((r.minY - displayOrigin.y) * scale).rounded(.down)
        let x1 = ((r.maxX - displayOrigin.x) * scale).rounded(.up)
        let y1 = ((r.maxY - displayOrigin.y) * scale).rounded(.up)
        return CGRect(x: x0, y: y0, width: x1 - x0, height: y1 - y0)
    }

    /// The screen region that a pixel rectangle of the capture really covers (after the rounding
    /// of `pixelRect`), so that answers on a cropped image map back exactly.
    public static func pointsRect(pixels r: CGRect, displayOrigin: CGPoint, scale: CGFloat) -> CGRect {
        CGRect(x: displayOrigin.x + r.minX / scale, y: displayOrigin.y + r.minY / scale,
               width: r.width / scale, height: r.height / scale)
    }

    /// Quartz points (origin top left, y down) to AppKit points (origin bottom left, y up), for
    /// windows. `mainScreenHeight` is the height in points of the screen that holds the menu bar.
    public static func appKitPoint(quartz p: CGPoint, mainScreenHeight: CGFloat) -> CGPoint {
        CGPoint(x: p.x, y: mainScreenHeight - p.y)
    }
}
