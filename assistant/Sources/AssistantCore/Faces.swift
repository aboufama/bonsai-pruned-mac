import Foundation

/// The assistant's little faces: plain text emoticons, one set per mood. Nothing here is
/// random: the same mood at the same beat always gives the same face and the same words, so
/// what it shows can be relied on (and tested).
public enum Mood: Equatable {
    case hello          // it has just come out
    case listening
    case heard          // it caught what was said
    case thinking
    case acting         // it is about to do a step
    case done
    case answer         // it is telling where something is
    case lost           // it did not catch that
    case sorry          // it could not find or do it
}

public enum Faces {
    static let thinking = ["(._.)", "(o_o)", "(o_O)", "(-_-)", "(>_<)", "(@_@)", "(^_^;)", "(._. )"]
    static let thinkingWords = ["thinking", "looking", "hmm", "one sec", "let me see", "almost", "still looking", "hold on"]

    /// A beat is a short tick of time; faces that move (a blink, a change of thought) step with it.
    /// Listening blinks on every sixteenth beat; thinking changes its mind every eight beats.
    public static func face(_ mood: Mood, beat: Int = 0) -> String {
        switch mood {
        case .hello: return "(^_^)/"
        case .listening: return beat % 16 == 15 ? "(-_-)" : "(o_o)"
        case .heard: return "(^o^)"
        case .thinking: return thinking[(beat / 8) % thinking.count]
        case .acting: return "(^-^)"
        case .done: return "\\(^o^)/"
        case .answer: return "(^_^)"
        case .lost: return "(?_?)"
        case .sorry: return "(;_;)"
        }
    }

    /// The words that go with a mood when nothing more specific is given.
    public static func words(_ mood: Mood, beat: Int = 0) -> String {
        switch mood {
        case .hello: return "hi"
        case .listening: return "listening"
        case .heard: return "got it"
        case .thinking: return thinkingWords[(beat / 8) % thinkingWords.count] + String(repeating: ".", count: 1 + (beat / 2) % 3)
        case .acting: return "on it"
        case .done: return "done!"
        case .answer: return "here"
        case .lost: return "didn't catch that"
        case .sorry: return "couldn't do that"
        }
    }

    /// The face in the box you type in: friendly while it waits, attentive once you type.
    public static func typing(_ text: String) -> String {
        let t = text.trimmingCharacters(in: .whitespaces)
        if t.isEmpty { return "(^_^)" }
        if t.hasSuffix("?") { return "(o_O)" }
        return "(o_o)"
    }

    /// The little moves it makes while thinking, in a fixed order, so it is never the same
    /// thing twice in a row: a hop, a slow turn, a wiggle, a peek at its other side.
    public enum Move: Equatable { case hop, turn, wiggle, peek, rest }
    public static let moves: [Move] = [.hop, .rest, .turn, .wiggle, .rest, .peek, .hop, .turn]
    public static func move(_ index: Int) -> Move { moves[((index % moves.count) + moves.count) % moves.count] }
}
