import Foundation

/// The exact words the models are asked with. Pointing: `PROMPT` of playground/server.py (the
/// grounding prompt of the Qwen3.5 family; the tuned Bonsai patches were trained and measured
/// with it). Steps: the `next_step` tool, system line and request text of weightlab/actions.py.
public enum Prompts {
    public static func pointing(_ instruction: String) -> String {
        var inst = instruction.trimmingCharacters(in: .whitespacesAndNewlines)
        while inst.hasSuffix(".") { inst.removeLast() }
        return "Output the center point of the position corresponding to the following instruction: \n"
            + "\(inst). \n\n"
            + "The output should just be the coordinates of a point, in the format [x,y]. "
            + "Additionally, if the task is infeasible (e.g., the task is not related to the image), "
            + "the output should be [-1,-1]."
    }

    /// The spoken answer: one sentence about what is on the screen, HeyClicky's way.
    public static func sentence(_ request: String) -> String {
        "You are looking at the user's Mac screen. Answer in one short sentence, without coordinates: "
            + request.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public static let stepSystem = "Screen assistant on a Mac. Look at the screenshot and act on the request with the tools."

    /// For models that were never taught the loop (the stock packs): when to stop, one call only.
    public static let stepRules = " Reply with exactly one next_step call and nothing else; you will then get a new screenshot."
        + " Describe the target in plain words and never give coordinates."
        + " When the request has been carried out, or the screen shows it is already satisfied, use the action done"
        + " with one sentence for the user in text."

    /// The same fields asked for as JSON, for servers that do not accept the tools field.
    public static let stepJSON = " Reply with one JSON object and nothing else, with these fields:"
        + " \"action\": one of click, double_click, right_click, drag, type, key, scroll, done;"
        + " \"target\": the element to act on, in plain words (for click, double_click, right_click and drag);"
        + " \"target_end\": where a drag ends, in plain words;"
        + " \"text\": the text to type (a newline at the end presses Return), or for done one sentence for the user;"
        + " \"keys\": for key, the keys to press together, for example [\"cmd\", \"s\"];"
        + " \"direction\": for scroll, one of up, down, left, right."
        + " Leave out the fields the action does not need. Never give coordinates."
        + " When the request has been carried out, or the screen shows it is already satisfied, use the action done."

    /// What a planner cannot see on the screen but needs: the date and time ("tomorrow at 3"),
    /// and what to do when a step had no effect.
    public static func stepContext(now: Date = Date()) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "EEEE d MMMM yyyy, HH:mm"
        return " Today is \(f.string(from: now))."
            + " Use the app's own button or menu for what is asked; if a previous action is marked as having changed nothing,"
            + " do something different instead of repeating it."
    }

    public static let historyShown = 4

    /// The user's text of a step request: the goal and the last steps taken.
    public static func stepRequest(goal: String, history: [String]) -> String {
        let first = max(0, history.count - historyShown)
        let lines = history.enumerated().dropFirst(first).map { "Step \($0.offset + 1): \($0.element)" }
        return "\nPlease generate the next move according to the UI screenshot, instruction and previous actions.\n\n"
            + "Instruction: \(goal.trimmingCharacters(in: .whitespacesAndNewlines))\n\n"
            + "Previous actions:\n" + (lines.isEmpty ? "None" : lines.joined(separator: "\n"))
    }

    public static let nextStepTool: [String: Any] = [
        "type": "function",
        "function": [
            "name": "next_step",
            "description": "Say the next single step to take on the screen. Describe the target plainly enough that someone "
                + "could point at it: what it is, what it says, where it is. Do not give coordinates.",
            "parameters": [
                "type": "object",
                "required": ["action"],
                "properties": [
                    "action": ["type": "string", "enum": Step.Action.allCases.map(\.rawValue),
                               "description": "What to do. `done` ends the task."],
                    "target": ["type": "string", "description": "The element to act on, in plain words. For `drag`, where the drag starts. "
                        + "Required by `click`, `double_click`, `right_click` and `drag`."],
                    "target_end": ["type": "string", "description": "Where the drag ends, in plain words. Only for `drag`."],
                    "text": ["type": "string", "description": "For `type`: the text to type; a newline at the end presses Return. "
                        + "For `done`: one sentence for the user about the result."],
                    "keys": ["type": "array", "items": ["type": "string"],
                             "description": "For `key`: the keys to press together, for example [\"cmd\", \"s\"]."],
                    "direction": ["type": "string", "enum": ["up", "down", "left", "right"], "description": "For `scroll`."],
                ] as [String: Any],
            ] as [String: Any],
        ] as [String: Any],
    ]

    /// A user message holding only the screenshot (see Pipeline for why it stands alone).
    public static func imageMessage(_ imageURL: String) -> [String: Any] {
        ["role": "user", "content": [["type": "image_url", "image_url": ["url": imageURL]] as [String: Any]]]
    }

    /// A user message with the image first, then the text: the image read is then the start of
    /// the prompt, which a server can keep for a second question about the same screenshot.
    public static func userMessage(imageURL: String, text: String) -> [String: Any] {
        ["role": "user", "content": [
            ["type": "image_url", "image_url": ["url": imageURL]] as [String: Any],
            ["type": "text", "text": text] as [String: Any],
        ]]
    }
}
