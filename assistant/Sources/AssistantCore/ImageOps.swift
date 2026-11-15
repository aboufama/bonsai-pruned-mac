import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

/// Image handling that needs no screen: shrinking, cropping, encoding, comparing.
public enum ImageOps {
    static let space = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()

    /// The image redrawn at the given pixel size with high-quality interpolation.
    public static func resized(_ image: CGImage, width: Int, height: Int) -> CGImage? {
        guard width > 0, height > 0,
              let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                                  bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
        ctx.interpolationQuality = .high
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return ctx.makeImage()
    }

    /// The image as it is sent: longer side at most `longSide` pixels, never enlarged.
    public static func shrunk(_ image: CGImage, longSide: Int) -> CGImage {
        let (w, h) = Geometry.fittedSize(width: image.width, height: image.height, longSide: longSide)
        if w == image.width && h == image.height { return image }
        return resized(image, width: w, height: h) ?? image
    }

    /// A zoomed look: the pixel rectangle cut out and shown with its longer side at `longSide`
    /// pixels (enlarged if it is smaller, as the playground's second look does).
    public static func zoomed(_ image: CGImage, pixelRect: CGRect, longSide: Int) -> CGImage? {
        guard let crop = image.cropping(to: pixelRect) else { return nil }
        let s = Double(longSide) / Double(max(crop.width, crop.height))
        return resized(crop, width: max(1, Int((Double(crop.width) * s).rounded())), height: max(1, Int((Double(crop.height) * s).rounded())))
    }

    public static func pngData(_ image: CGImage) -> Data? {
        let data = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(data, UTType.png.identifier as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(dest, image, nil)
        return CGImageDestinationFinalize(dest) ? data as Data : nil
    }

    /// The image as the `image_url` of a chat request.
    public static func dataURL(_ image: CGImage) -> String? {
        pngData(image).map { "data:image/png;base64," + $0.base64EncodedString() }
    }

    public static func load(path: String) -> CGImage? {
        guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil) else { return nil }
        return CGImageSourceCreateImageAtIndex(src, 0, nil)
    }

    public static func save(_ image: CGImage, path: String) -> Bool {
        guard let data = pngData(image) else { return false }
        return (try? data.write(to: URL(fileURLWithPath: path))) != nil
    }

    /// The image as RGBX bytes at the given size (for comparing two screenshots).
    public static func bytes(_ image: CGImage, width: Int, height: Int) -> [UInt8] {
        var buffer = [UInt8](repeating: 0, count: width * height * 4)
        buffer.withUnsafeMutableBytes { raw in
            guard let ctx = CGContext(data: raw.baseAddress, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4,
                                      space: space, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return }
            ctx.interpolationQuality = .low
            ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
        return buffer
    }

    /// How many pixels differ by more than `tolerance` in any colour channel.
    public static func differingPixels(_ a: [UInt8], _ b: [UInt8], tolerance: Int = 12) -> Int {
        guard a.count == b.count else { return max(a.count, b.count) / 4 }
        var n = 0, i = 0
        while i + 3 < a.count {
            if abs(Int(a[i]) - Int(b[i])) > tolerance || abs(Int(a[i + 1]) - Int(b[i + 1])) > tolerance
                || abs(Int(a[i + 2]) - Int(b[i + 2])) > tolerance { n += 1 }
            i += 4
        }
        return n
    }

    /// Whether two screenshots show the same thing: compared at 640 px wide, a handful of
    /// changed pixels (a blinking caret, the clock) does not count as a change.
    public static func differingPixels(_ a: CGImage, _ b: CGImage) -> Int {
        let w = 640, h = max(1, Int((Double(a.height) / Double(max(a.width, 1)) * 640).rounded()))
        return differingPixels(bytes(a, width: w, height: h), bytes(b, width: w, height: h))
    }

    /// Below this a click "changed nothing".
    public static let unchangedBelow = 25
    /// Below this the screen is still the one that was read ahead: a caret, the clock, a spinner
    /// or a hover highlight changes a few hundred of the 266,000 compared pixels, a new window
    /// or page far more.
    public static let sameScreenBelow = 2500

    /// A copy with a ring drawn at a pixel (y from the top), for checking answers on saved screenshots.
    public static func annotated(_ image: CGImage, at p: CGPoint, box: CGRect? = nil) -> CGImage? {
        let w = image.width, h = image.height
        guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                                  bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
        let y = CGFloat(h) - p.y                                         // the context's origin is bottom left
        let r = max(10, CGFloat(max(w, h)) / 70)
        if let box {
            ctx.setStrokeColor(CGColor(red: 0.1, green: 0.5, blue: 1, alpha: 0.9))
            ctx.setLineWidth(max(2, r / 6))
            ctx.stroke(CGRect(x: box.minX, y: CGFloat(h) - box.maxY, width: box.width, height: box.height))
        }
        ctx.setStrokeColor(CGColor(red: 1, green: 1, blue: 1, alpha: 0.95))
        ctx.setLineWidth(r / 2.2)
        ctx.strokeEllipse(in: CGRect(x: p.x - r, y: y - r, width: 2 * r, height: 2 * r))
        ctx.setStrokeColor(CGColor(red: 0.95, green: 0.2, blue: 0.25, alpha: 1))
        ctx.setLineWidth(r / 4)
        ctx.strokeEllipse(in: CGRect(x: p.x - r, y: y - r, width: 2 * r, height: 2 * r))
        ctx.setFillColor(CGColor(red: 0.95, green: 0.2, blue: 0.25, alpha: 1))
        ctx.fillEllipse(in: CGRect(x: p.x - r / 5, y: y - r / 5, width: r / 2.5, height: r / 2.5))
        return ctx.makeImage()
    }
}
