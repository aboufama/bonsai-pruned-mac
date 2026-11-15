import Foundation

public struct PointOutcome {
    public let answer: PointAnswer
    public let chat: ChatResult
    public let asked: String
    public let note: String?             // something the log should say (a retry, thinking that was not switched off)
    /// What did the pointing: PointerHelper.name, or PointerHelper.languageModel.
    public var pointer = PointerHelper.languageModel
}

public struct StepOutcome {
    public let step: Step?
    public let chat: ChatResult
    public let asked: String
    public let note: String?
}

/// The questions the app asks a model about one screenshot. No screen is needed: the image
/// comes in as a data URL, so the same code runs on saved screenshots.
///
/// Reading a screenshot is the slow part (about 11 s for the 9B on a 13-inch M4 MacBook through
/// llama.cpp; the answer itself takes well under a second). The server can keep that read for
/// the next question only if a new user message starts right after the image, because these
/// models have recurrent layers and can only go back to such a point. So by default the
/// screenshot goes in its own user message and the question in a second one: every question
/// after the first about the same screenshot then costs about a second, and the screenshot can
/// be read ahead (`readAhead`) before the question is known. `separateImage = false` gives the
/// layout the models were measured with in the lab (image and question in one message), where
/// every question pays the full read.
public final class Pipeline {
    public let client: LMClient
    public var model: String
    public var separateImage = true
    /// New tokens allowed for one planning reply. A step that types a long text (the body of a
    /// message) needs room: a reply cut off at the limit cannot be read as a step.
    public static let planTokens = 384
    /// Replaces the planner's system text for this run (for trying a wording without a rebuild);
    /// nil: the built-in text. Nothing else about a planning request changes.
    public var plannerSystem: String?
    public var plainStepPrompt = false          // true: system line, request and tool exactly as in step training
    private var toolsUnsupported = false
    private var thinks = false                  // the server did not switch the model's thinking off
    /// A helper that only points, when one was named for this run; nil: the language model points.
    public var pointer: PointerHelper?
    private var pointerRestsUntil = Date.distantPast      // after a slow failure it is left alone for a while
    /// Whether the helper answered the last time it was asked anything (its health at start, a point, a read).
    public private(set) var pointerAnswered = false
    public func pointerSaid(_ answered: Bool) { pointerAnswered = answered }

    /// Has the screenshot read before any question about it is known, by whoever will point
    /// at things on it: the helper when it has answered (the language model's long read of the
    /// picture is then not spent), else the language model as always. If the helper does not
    /// take it, the language model reads it and the note says why.
    public func readAheadForPointing(imageURL: String) async throws -> (seconds: Double, by: String, note: String?) {
        var note: String?
        if let pointer, pointerAnswered, Date() >= pointerRestsUntil {
            let start = Date()
            switch await pointer.read(imageURL: imageURL) {
            case .read(let seconds, let cached):
                return (seconds, PointerHelper.name, cached ? "the helper had already read this picture" : nil)
            case .unusable(let why):
                pointerAnswered = false
                if Date().timeIntervalSince(start) > 5 { pointerRestsUntil = Date().addingTimeInterval(60) }
                note = "the pointer helper did not take the screenshot (\(why)): read ahead by the language model instead"
            }
        }
        let chat = try await readAhead(imageURL: imageURL)
        return (chat.seconds, PointerHelper.languageModel, note)
    }

    public init(client: LMClient, model: String) {
        self.client = client
        self.model = model
    }

    /// The messages for one question about a screenshot.
    public func messages(imageURL: String, text: String) -> [[String: Any]] {
        separateImage ? [Prompts.imageMessage(imageURL), ["role": "user", "content": text]]
                      : [Prompts.userMessage(imageURL: imageURL, text: text)]
    }

    /// Has the server read the screenshot before any question is known, so that the questions
    /// that follow find it read. Only useful with `separateImage`.
    public func readAhead(imageURL: String) async throws -> ChatResult {
        try await client.chat(model: model, messages: messages(imageURL: imageURL, text: "Wait."), maxTokens: 1)
    }

    /// Where is it? The pointing prompt; the answer is a point on the 0-1000 grid of the image.
    /// With a pointer helper named, it is asked first (`looks`: 2 has it look twice); whatever
    /// goes wrong there, the language model is asked as always and the log says why.
    public func point(imageURL: String, instruction: String, looks: Int = 1, helper: Bool = true) async throws -> PointOutcome {
        var fellBack: String?
        if helper, let pointer, Date() >= pointerRestsUntil {
            let start = Date()
            switch await pointer.point(imageURL: imageURL, request: instruction, looks: looks) {
            case .point(let x, let y, let seconds, let read, let cached):
                let g = PointerHelper.grid(x: x, y: y)
                pointerAnswered = true
                var chat = ChatResult()
                chat.content = "[\(Int(g.x.rounded())), \(Int(g.y.rounded()))]"
                chat.seconds = Date().timeIntervalSince(start)
                chat.model = PointerHelper.name
                let note = String(format: "pointed by the helper %@ at %@: x %.4f, y %.4f of the picture; it says %.2f s (reading the picture %.2f s%@)%@",
                                  PointerHelper.name, pointer.base.absoluteString, x, y, seconds, read, cached ? ", already read" : "", looks >= 2 ? "; two looks" : "")
                return PointOutcome(answer: .point(g), chat: chat, asked: instruction, note: note, pointer: PointerHelper.name)
            case .unusable(let why):
                let took = Date().timeIntervalSince(start)
                pointerAnswered = false
                if took > 5 { pointerRestsUntil = Date().addingTimeInterval(60) }       // a helper that hangs is not waited for again at once
                fellBack = "the pointer helper could not be used (\(why)): the language model points instead"
                    + (took > 5 ? "; the helper is left alone for the next minute" : "")
            }
        }
        let asked = Prompts.pointing(instruction)
        let messages = self.messages(imageURL: imageURL, text: asked)
        var chat = try await client.chat(model: model, messages: messages, maxTokens: thinks ? 700 : 32)
        var answer = Parsing.parsePoint(chat.content)
        var note: String? = thinks ? "the model thinks before answering; switch thinking off for it in the server for speed" : nil
        if !thinks, answer.point == nil, answer != .refusal, chat.finishReason == "length" || !chat.reasoning.isEmpty {
            // The model spent its tokens thinking. Ask again with room to finish, say so, and
            // give it that room from the start for the rest of this run of the app.
            thinks = true
            let first = chat.seconds
            chat = try await client.chat(model: model, messages: messages, maxTokens: 700)
            chat.seconds += first
            answer = Parsing.parsePoint(chat.content)
            note = "the model thinks before answering (asked twice this time); switch thinking off for it in the server for speed"
        }
        let notes = [fellBack, note].compactMap { $0 }
        return PointOutcome(answer: answer, chat: chat, asked: asked, note: notes.isEmpty ? nil : notes.joined(separator: "; "))
    }

    /// One short sentence about the request, to show and to speak.
    public func sentence(imageURL: String, request: String) async throws -> ChatResult {
        try await client.chat(model: model, messages: messages(imageURL: imageURL, text: Prompts.sentence(request)), maxTokens: 80)
    }

    private var plannerToolsOff = false
    private var plannerMisses = 0

    /// The next step from the planner (format v1, see Planner): text only, one `next_step`
    /// call through the API's tools. If the server refuses tools, or the model twice writes
    /// no call, the same arguments are asked for as JSON from then on.
    public func plan(user: String) async throws -> (step: PlannedStep?, chat: ChatResult, note: String?) {
        let system = plannerSystem ?? Planner.system
        var note: String?
        var spent = 0.0
        if !plannerToolsOff {
            do {
                let messages: [[String: Any]] = [["role": "system", "content": system], ["role": "user", "content": user]]
                var chat = try await client.chat(model: model, messages: messages, tools: [Planner.tool], maxTokens: Pipeline.planTokens)
                if let step = Planner.parse(content: chat.content, toolCalls: chat.toolCalls) { return (step, chat, nil) }
                if chat.finishReason == "length" {
                    // Cut off at the limit (a long text to type leaves the call's arguments
                    // unclosed): once more, with room to finish.
                    let first = chat.seconds
                    chat = try await client.chat(model: model, messages: messages, tools: [Planner.tool], maxTokens: Pipeline.planTokens * 3)
                    chat.seconds += first
                    if let step = Planner.parse(content: chat.content, toolCalls: chat.toolCalls) {
                        return (step, chat, "the first reply was cut off at \(Pipeline.planTokens) tokens; asked again with room for \(Pipeline.planTokens * 3)")
                    }
                }
                spent = chat.seconds
                plannerMisses += 1
                if plannerMisses >= 2 { plannerToolsOff = true }
                note = "no next_step call in the answer (\(chat.written.prefix(100))); asked again as JSON"
            } catch let e as LMError where e.kind == .toolsRejected {
                plannerToolsOff = true
                note = "the server does not take the tools field; the step is asked for as JSON"
            }
        }
        let messages: [[String: Any]] = [["role": "system", "content": system + Planner.asJSON], ["role": "user", "content": user]]
        var chat = try await client.chat(model: model, messages: messages, maxTokens: Pipeline.planTokens)
        chat.seconds += spent
        return (Planner.parse(content: chat.content, toolCalls: chat.toolCalls), chat, note)
    }

    /// A question put to the planner in its own format: the question as the task, a list of
    /// controls, nothing done so far. One reply, read as a step if it is one; a reply in plain
    /// words is not counted as a missed call (it may be the answer).
    public func question(user: String) async throws -> (step: PlannedStep?, chat: ChatResult) {
        let system = plannerSystem ?? Planner.system
        if !plannerToolsOff {
            do {
                let messages: [[String: Any]] = [["role": "system", "content": system], ["role": "user", "content": user]]
                let chat = try await client.chat(model: model, messages: messages, tools: [Planner.tool], maxTokens: Pipeline.planTokens)
                return (Planner.parse(content: chat.content, toolCalls: chat.toolCalls), chat)
            } catch let e as LMError where e.kind == .toolsRejected {
                plannerToolsOff = true
            }
        }
        let messages: [[String: Any]] = [["role": "system", "content": system + Planner.asJSON], ["role": "user", "content": user]]
        let chat = try await client.chat(model: model, messages: messages, maxTokens: Pipeline.planTokens)
        return (Planner.parse(content: chat.content, toolCalls: chat.toolCalls), chat)
    }

    /// An answer in words from text alone (a question about the Mac, asked with the facts and
    /// the list of controls): fixed instructions as the system message.
    public func reply(system: String, user: String, maxTokens: Int = 120) async throws -> ChatResult {
        try await client.chat(model: model, messages: [["role": "system", "content": system], ["role": "user", "content": user]], maxTokens: maxTokens)
    }

    /// An answer in words about a screenshot.
    public func describe(imageURL: String, text: String, maxTokens: Int = 120) async throws -> ChatResult {
        try await client.chat(model: model, messages: messages(imageURL: imageURL, text: text), maxTokens: maxTokens)
    }

    /// A few lines of text from the model, with no screen involved (the body of an email draft).
    public func write(_ request: String, maxTokens: Int = 160) async throws -> ChatResult {
        try await client.chat(model: model, messages: [["role": "user", "content": request]], maxTokens: maxTokens)
    }

    /// What is the next step? (Planned from a screenshot.)
    ///
    /// Default: the fields of `next_step` asked for as JSON in the question itself, with nothing
    /// before the screenshot, so the step and the pointing requests that follow share one read
    /// of it. With `plainStepPrompt` (a model trained on steps): the system line and the
    /// `next_step` tool exactly as in training, through the API's tools field; as JSON if the
    /// server refuses tools or the model writes no call.
    public func nextStep(imageURL: String, goal: String, history: [String]) async throws -> StepOutcome {
        let asked = Prompts.stepRequest(goal: goal, history: history)
        var note: String?
        var spent = 0.0
        if plainStepPrompt, !toolsUnsupported {
            let messages = [["role": "system", "content": Prompts.stepSystem] as [String: Any]] + self.messages(imageURL: imageURL, text: asked)
            do {
                let chat = try await client.chat(model: model, messages: messages, tools: [Prompts.nextStepTool], maxTokens: 512)
                if let step = Parsing.parseStep(content: chat.content, toolCalls: chat.toolCalls) {
                    return StepOutcome(step: step, chat: chat, asked: asked, note: nil)
                }
                spent = chat.seconds
                note = "no next_step call in the answer (\(chat.written.prefix(120))); asked again for JSON"
            } catch let e as LMError where e.kind == .toolsRejected {
                toolsUnsupported = true
                note = "the server does not take the tools field; steps are asked for as JSON"
            }
        }
        let text = Prompts.stepSystem + Prompts.stepJSON + Prompts.stepContext() + "\n" + asked
        var chat = try await client.chat(model: model, messages: messages(imageURL: imageURL, text: text), maxTokens: 512)
        chat.seconds += spent
        return StepOutcome(step: Parsing.parseStep(content: chat.content, toolCalls: chat.toolCalls), chat: chat, asked: asked, note: note)
    }
}
