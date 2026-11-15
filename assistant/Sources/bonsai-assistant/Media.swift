// A recording with its own words put on it as subtitles: the sound is taken out of the
// video, a speech model on this Mac says what is said and when (Voice), and the lines are
// drawn onto a copy of the video. Nothing here uses the network.
import AppKit
import AssistantCore
import AVFoundation
import QuartzCore

struct MediaError: Error, CustomStringConvertible {
    let description: String
}

enum Media {
    /// The newest recording in the places a person keeps them: Movies, the Desktop, Downloads,
    /// and Photo Booth's library where macOS lets the app read it. Copies this app captioned
    /// are passed over.
    static func newestMovie(in place: String = "") -> URL? {
        let home = NSHomeDirectory()
        let named = ["desktop": home + "/Desktop", "movies": home + "/Movies", "downloads": home + "/Downloads"][place]
        let folders = named.map { [$0] } ?? [home + "/Movies", home + "/Desktop", home + "/Downloads", home + "/Pictures/Photo Booth Library/Pictures"]
        var best: (url: URL, date: Date)?
        for folder in folders {
            for name in (try? FileManager.default.contentsOfDirectory(atPath: folder)) ?? [] {
                let lower = name.lowercased()
                guard ["mov", "mp4", "m4v"].contains((lower as NSString).pathExtension), !lower.contains("(captioned)") else { continue }
                let url = URL(fileURLWithPath: folder + "/" + name)
                guard let date = (try? url.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate else { continue }
                if best == nil || date > best!.date { best = (url, date) }
            }
        }
        return best?.url
    }

    /// The sound of a recording as a speech model takes it: one channel, 16,000 samples a second.
    static func samples(of url: URL) async throws -> [Float] {
        let asset = AVURLAsset(url: url)
        guard let track = try await asset.loadTracks(withMediaType: .audio).first else { throw MediaError(description: "the recording has no sound") }
        return try await Task.detached {
            let reader = try AVAssetReader(asset: asset)
            let settings: [String: Any] = [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 16000, AVNumberOfChannelsKey: 1, AVLinearPCMBitDepthKey: 32,
                                           AVLinearPCMIsFloatKey: true, AVLinearPCMIsBigEndianKey: false, AVLinearPCMIsNonInterleaved: false]
            let output = AVAssetReaderTrackOutput(track: track, outputSettings: settings)
            reader.add(output)
            guard reader.startReading() else { throw MediaError(description: "the recording's sound could not be read (\(reader.error?.localizedDescription ?? "unknown"))") }
            var samples: [Float] = []
            while let buffer = output.copyNextSampleBuffer() {
                guard let block = CMSampleBufferGetDataBuffer(buffer) else { continue }
                let length = CMBlockBufferGetDataLength(block)
                var piece = [Float](repeating: 0, count: length / MemoryLayout<Float>.size)
                piece.withUnsafeMutableBytes { _ = CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: length, destination: $0.baseAddress!) }
                samples += piece
            }
            return samples
        }.value
    }

    /// One subtitle as it is drawn: white on a dark band, low in the middle of the picture.
    /// The band and the words are drawn into a picture first (a text layer is left blank when
    /// a video is written), and the picture is what the layer shows.
    private static func layer(_ text: String, in size: CGSize) -> CALayer {
        let fontSize = max(18, size.height * 0.052)
        let pad = fontSize * 0.6
        let style = NSMutableParagraphStyle()
        style.alignment = .center
        let words = NSAttributedString(string: text, attributes: [.font: NSFont.systemFont(ofSize: fontSize, weight: .semibold),
                                                                  .foregroundColor: NSColor.white, .paragraphStyle: style])
        let room = size.width * 0.9 - pad * 2
        let needed = words.boundingRect(with: CGSize(width: room, height: 10_000), options: [.usesLineFragmentOrigin])
        let width = min(room, ceil(needed.width)) + pad * 2, height = ceil(needed.height) + pad * 0.7
        let layer = CALayer()
        layer.frame = CGRect(x: (size.width - width) / 2, y: size.height * 0.07, width: width, height: height)
        let scale: CGFloat = 2
        guard let ctx = CGContext(data: nil, width: Int(width * scale), height: Int(height * scale), bitsPerComponent: 8, bytesPerRow: 0,
                                  space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return layer }
        ctx.scaleBy(x: scale, y: scale)
        ctx.addPath(CGPath(roundedRect: CGRect(x: 0, y: 0, width: width, height: height), cornerWidth: fontSize * 0.3, cornerHeight: fontSize * 0.3, transform: nil))
        ctx.setFillColor(CGColor(gray: 0, alpha: 0.62))
        ctx.fillPath()
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
        words.draw(with: CGRect(x: pad, y: (height - ceil(needed.height)) / 2, width: width - pad * 2, height: ceil(needed.height)), options: [.usesLineFragmentOrigin])
        NSGraphicsContext.restoreGraphicsState()
        layer.contents = ctx.makeImage()
        return layer
    }

    /// Writes a copy of the video with the subtitles drawn on it. Nil when the copy is there.
    static func burn(_ lines: [Subtitle], into url: URL, to out: URL) async -> String? {
        let asset = AVURLAsset(url: url)
        guard let composition = try? await AVMutableVideoComposition.videoComposition(withPropertiesOf: asset), composition.renderSize.width > 0 else {
            return "the recording has no picture that could be read"
        }
        let size = composition.renderSize
        let parent = CALayer(), video = CALayer()
        parent.frame = CGRect(origin: .zero, size: size)
        video.frame = parent.frame
        parent.addSublayer(video)
        for line in lines {
            let text = layer(line.text, in: size)
            text.opacity = 0                                                // shown only while its animation runs
            let show = CABasicAnimation(keyPath: "opacity")
            show.fromValue = 1
            show.toValue = 1
            show.beginTime = AVCoreAnimationBeginTimeAtZero + line.start
            show.duration = max(0.2, line.end - line.start)
            show.isRemovedOnCompletion = false
            text.add(show, forKey: "show")
            parent.addSublayer(text)
        }
        composition.animationTool = AVVideoCompositionCoreAnimationTool(postProcessingAsVideoLayer: video, in: parent)
        guard let export = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetHighestQuality) else { return "the video could not be prepared for writing" }
        try? FileManager.default.removeItem(at: out)
        export.videoComposition = composition
        export.outputURL = out
        export.outputFileType = .mov
        await export.export()
        guard export.status == .completed, FileManager.default.fileExists(atPath: out.path) else {
            return "the captioned copy could not be written (\(export.error?.localizedDescription ?? "unknown"))"
        }
        return nil
    }

    /// Where the captioned copy of a recording goes: Movies, under the recording's name.
    static func captionedURL(for url: URL) -> URL {
        let folder = URL(fileURLWithPath: NSHomeDirectory() + "/Movies")
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder.appendingPathComponent(url.deletingPathExtension().lastPathComponent + " (captioned).mov")
    }
}
