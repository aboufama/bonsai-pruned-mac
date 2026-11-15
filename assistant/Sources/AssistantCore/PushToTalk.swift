import Foundation

/// Holding the main hotkey and speaking. The key does two things: a short tap opens the
/// typing box, a hold records until the key is let go and then carries out what was said.
/// Which of the two it was is a matter of the two times alone.
public enum PushToTalk {
    /// Let go sooner than this, the press was a tap.
    public static let tapSeconds = 0.35
    /// A recording with less voice in it than this was not a request.
    public static let voiceSeconds = 0.3

    public enum Release: Equatable {
        case tap                     // open the typing box; what was recorded is dropped
        case hold                    // what was said is the request
    }

    public static func release(pressed: Date, released: Date) -> Release {
        released.timeIntervalSince(pressed) < tapSeconds ? .tap : .hold
    }

    /// How many seconds of a recording have a voice in them: the tenths of a second that are
    /// clearly louder than the quiet parts of the same recording. `samples`: mono, -1 to 1.
    public static func voicedSeconds(_ samples: [Float], rate: Double = 16000) -> Double {
        let frame = max(1, Int(rate / 10))
        guard samples.count >= frame / 2 else { return 0 }
        var loudness: [Float] = []
        var i = 0
        while i < samples.count {
            let end = min(i + frame, samples.count)
            if end - i >= frame / 2 {
                var sum: Float = 0
                for k in i..<end { sum += samples[k] * samples[k] }
                loudness.append((sum / Float(end - i)).squareRoot())
            }
            i = end
        }
        guard !loudness.isEmpty else { return 0 }
        let quiet = loudness.sorted()[loudness.count / 10]                // the level of its quietest tenth
        let threshold = max(0.004, min(0.02, 3 * quiet))
        return Double(loudness.filter { $0 > threshold }.count) / 10
    }

    public static func caught(voiced: Double) -> Bool { voiced >= voiceSeconds }

    /// What was heard, without the marks a speech model writes for sounds that are not words
    /// ("[BLANK_AUDIO]", "(music)", "♪").
    public static func clean(_ text: String) -> String {
        var t = text
        for pattern in [#"\[[^\]]*\]"#, #"\([^)]*\)"#, "[♪♫]"] {
            if let re = try? NSRegularExpression(pattern: pattern) {
                t = re.stringByReplacingMatches(in: t, range: NSRange(location: 0, length: (t as NSString).length), withTemplate: " ")
            }
        }
        return t.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
    }
}
