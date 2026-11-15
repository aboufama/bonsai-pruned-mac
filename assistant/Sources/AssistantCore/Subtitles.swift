import Foundation

/// One subtitle: what is said, and from when to when (seconds from the start of the video).
public struct Subtitle: Equatable {
    public let start: Double
    public let end: Double
    public let text: String

    public init(start: Double, end: Double, text: String) {
        self.start = start
        self.end = end
        self.text = text
    }
}

/// Subtitles for a recording, from what a speech model heard and when.
public enum Subtitles {
    /// What was heard in one stretch, without the marks a speech model writes that are not
    /// words: its time marks ("<|1.20|>") and its notes for sounds ("[BLANK_AUDIO]", "(music)").
    public static func clean(_ text: String) -> String {
        var t = text
        if let re = try? NSRegularExpression(pattern: #"<\|[^|]*\|>"#) {
            t = re.stringByReplacingMatches(in: t, range: NSRange(location: 0, length: (t as NSString).length), withTemplate: " ")
        }
        return PushToTalk.clean(t)
    }

    /// The stretches of speech as lines short enough to read: a long stretch is cut at
    /// spaces into lines of at most `limit` characters, and its time is shared out among
    /// them by their lengths. No line is shown for less than `least` seconds if there is room.
    public static func lines(_ pieces: [Subtitle], limit: Int = 42, least: Double = 0.8) -> [Subtitle] {
        var out: [Subtitle] = []
        for piece in pieces {
            let text = clean(piece.text)
            guard !text.isEmpty, piece.end > piece.start else { continue }
            var rows: [String] = [], row = ""
            for word in text.split(separator: " ") {
                if !row.isEmpty, row.count + 1 + word.count > limit {
                    rows.append(row)
                    row = String(word)
                } else {
                    row += (row.isEmpty ? "" : " ") + word
                }
            }
            if !row.isEmpty { rows.append(row) }
            let total = Double(rows.reduce(0) { $0 + $1.count })
            var at = piece.start
            for r in rows {
                let share = (piece.end - piece.start) * Double(r.count) / max(total, 1)
                out.append(Subtitle(start: at, end: at + share, text: r))
                at += share
            }
        }
        // a line that would flash by is held a little longer, up to where the next begins
        for i in out.indices where out[i].end - out[i].start < least {
            let room = i + 1 < out.count ? out[i + 1].start : out[i].start + least
            out[i] = Subtitle(start: out[i].start, end: max(out[i].end, min(out[i].start + least, room)), text: out[i].text)
        }
        return out
    }

    /// A time as subtitle files write it: 00:01:02,500.
    public static func stamp(_ seconds: Double) -> String {
        let ms = Int((max(0, seconds) * 1000).rounded())
        return String(format: "%02d:%02d:%02d,%03d", ms / 3_600_000, ms / 60000 % 60, ms / 1000 % 60, ms % 1000)
    }

    /// The lines as a subtitle file (SubRip, .srt).
    public static func srt(_ lines: [Subtitle]) -> String {
        lines.enumerated().map { "\($0.offset + 1)\n\(stamp($0.element.start)) --> \(stamp($0.element.end))\n\($0.element.text)\n" }.joined(separator: "\n")
    }
}
