import Foundation

public struct PointOutcome {
    public let answer: PointAnswer
    public let chat: ChatResult
    public let asked: String
    public let note: String?             // something the log should say (a retry, thinking that was not switched off)
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
    public var plainStepPrompt = false          // true: system line, request and tool exactly as in step training
    private var toolsUnsupported = false
    private var thinks = false                  // the server did not switch the model's thinking off

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
    public func point(imageURL: String, instruction: String) async throws -> PointOutcome {
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
        return PointOutcome(answer: answer, chat: chat, asked: asked, note: note)
    }

    /// One short sentence about the request, to show and to speak.
    public func sentence(imageURL: String, request: String) async throws -> ChatResult {
        try await client.chat(model: model, messages: messages(imageURL: imageURL, text: Prompts.sentence(request)), maxTokens: 80)
    }

    /// What is the next step?
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
        let text = Prompts.stepSystem + Prompts.stepJSON + "\n" + asked
        var chat = try await client.chat(model: model, messages: messages(imageURL: imageURL, text: text), maxTokens: 512)
        chat.seconds += spent
        return StepOutcome(step: Parsing.parseStep(content: chat.content, toolCalls: chat.toolCalls), chat: chat, asked: asked, note: note)
    }
}
