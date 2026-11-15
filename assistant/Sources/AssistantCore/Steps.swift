import Foundation

/// One step of a task, as the model says it in a `next_step` call (docs/ACTION_FORMAT.md,
/// "Orchestrator steps"): what to do and the target in plain words, never coordinates.
public struct Step: Equatable {
    public enum Action: String, CaseIterable {
        case click, double_click, right_click, drag, type, key, scroll, done
    }

    public var action: Action
    public var target: String?
    public var targetEnd: String?
    public var text: String?
    public var keys: [String]
    public var direction: String?

    public init(action: Action, target: String? = nil, targetEnd: String? = nil, text: String? = nil,
                keys: [String] = [], direction: String? = nil) {
        self.action = action
        self.target = target
        self.targetEnd = targetEnd
        self.text = text
        self.keys = keys
        self.direction = direction
    }

    public var isClick: Bool { action == .click || action == .double_click || action == .right_click }

    /// Why this step cannot be carried out as written, or nil when it can.
    public func problem() -> String? {
        let has = { (s: String?) in !(s ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        switch action {
        case .click, .double_click, .right_click:
            return has(target) ? nil : "\(action.rawValue) without a target"
        case .drag:
            return has(target) && has(targetEnd) ? nil : "drag needs a target and a target_end"
        case .type:
            return (text ?? "").isEmpty ? "type without text" : nil
        case .key:
            if keys.isEmpty { return "key without keys" }
            return Keys.combo(keys) == nil ? "unknown key in \(keys.joined(separator: "+"))" : nil
        case .scroll:
            return ["up", "down", "left", "right"].contains(direction ?? "") ? nil : "scroll without a direction"
        case .done:
            return nil
        }
    }

    /// The line kept as history and shown to the model on the next step. Same wording as
    /// `describe_step` in weightlab/actions.py, so that use matches training.
    public var historyLine: String {
        switch action {
        case .click, .double_click, .right_click:
            return "\(action.rawValue.replacingOccurrences(of: "_", with: "-")) \(target ?? "")"
        case .drag:
            return "drag \(target ?? "") to \(targetEnd ?? "")"
        case .type:
            let t = text ?? ""
            let shown = t.count <= 80 ? String(t.reversed().drop(while: { $0 == "\n" }).reversed()) : String(t.prefix(77)) + "..."
            var line = "type " + Step.quoted(shown)
            if let target, !target.isEmpty { line += " in \(target)" }
            if t.hasSuffix("\n") { line += " and press Return" }
            return line
        case .key:
            return "press " + keys.joined(separator: "+")
        case .scroll:
            var line = "scroll \(direction ?? "")".trimmingCharacters(in: .whitespaces)
            if let target, !target.isEmpty { line += " in \(target)" }
            return line
        case .done:
            return "done"
        }
    }

    /// A string as JSON writes it (quotes and escapes), which is how training wrote typed text.
    static func quoted(_ s: String) -> String {
        if let d = try? JSONSerialization.data(withJSONObject: [s], options: [.withoutEscapingSlashes]),
           let t = String(data: d, encoding: .utf8), t.count >= 2 {
            return String(t.dropFirst().dropLast())
        }
        return "\"\(s)\""
    }
}
