import Foundation

public struct LMError: Error, CustomStringConvertible {
    public enum Kind { case unreachable, http, notFound, unauthorized, toolsRejected, badAnswer }
    public let kind: Kind
    public let message: String
    public var description: String { message }
}

/// One answer of the server, with what is needed to judge it.
public struct ChatResult {
    public var content = ""              // what the model wrote (its thinking removed)
    public var reasoning = ""            // its thinking, if the server returned any
    public var toolCalls: [[String: Any]] = []
    public var finishReason: String?
    public var promptTokens: Int?
    public var completionTokens: Int?
    public var firstTokenSeconds: Double?
    public var tokensPerSecond: Double?
    public var seconds = 0.0
    public var model: String?

    /// What the model wrote, for the log: text, or the tool calls when there is no text.
    public var written: String {
        if !content.isEmpty { return content }
        if let d = try? JSONSerialization.data(withJSONObject: toolCalls, options: [.sortedKeys]),
           !toolCalls.isEmpty, let s = String(data: d, encoding: .utf8) { return s }
        return reasoning.isEmpty ? "(nothing)" : "(only thinking) " + reasoning
    }

    public var tokenNote: String {
        var parts: [String] = []
        if let p = promptTokens { parts.append("prompt \(p) tok") }
        if let c = completionTokens { parts.append("answer \(c) tok") }
        if let f = firstTokenSeconds { parts.append(String(format: "first token %.2f s", f)) }
        if let t = tokensPerSecond { parts.append(String(format: "%.0f tok/s", t)) }
        return parts.joined(separator: ", ")
    }
}

/// A model as LM Studio's own API lists it (GET /api/v1/models).
public struct StudioModel: Equatable {
    public let key: String
    public let type: String                  // "llm", "embedding", "decision"
    public let vision: Bool?
    public let loaded: [String]              // ids of its loaded instances
    public let contextLength: Int?           // of the first loaded instance
    public let reasoningOptions: [String]    // e.g. ["off", "on"]; empty when the model has no such setting
    public let reasoningDefault: String?
}

/// A client for an OpenAI-compatible server (LM Studio, llama-server, mlx-vlm's server), plus
/// the part of LM Studio's own REST API that lists, loads and unloads models.
public final class LMClient {
    public var base: URL                              // ends in /v1
    public var timeout: TimeInterval = 240            // the first request may wait for the model to load
    /// The API token, asked for at the moment of each request and sent as the bearer token.
    /// It is never stored here, logged or put into an error message.
    public var token: (() -> String?)?
    private var extrasRejected = false

    public init(base: URL) { self.base = base }

    public static func url(from text: String) -> URL? {
        var t = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if t.isEmpty { return nil }
        if !t.contains("://") { t = "http://" + t }
        while t.hasSuffix("/") { t.removeLast() }
        if !t.hasSuffix("/v1") { t += "/v1" }
        return URL(string: t)
    }

    /// The server's address without the /v1 of the OpenAI-compatible API.
    public var root: URL { base.deletingLastPathComponent() }
    public var isLocal: Bool { ["localhost", "127.0.0.1", "::1"].contains(base.host ?? "") }

    /// The request as it is sent. Kept apart so that a test can look at it.
    public func request(_ url: URL, body: [String: Any]?, timeout: TimeInterval) throws -> URLRequest {
        var req = URLRequest(url: url)
        req.timeoutInterval = timeout
        if let t = token?(), !t.isEmpty { req.setValue("Bearer " + t, forHTTPHeaderField: "Authorization") }
        if let body {
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        return req
    }

    func send(_ url: URL, body: [String: Any]?, timeout: TimeInterval? = nil) async throws -> (Data, Int) {
        let req = try request(url, body: body, timeout: timeout ?? self.timeout)
        do {
            let (data, response) = try await URLSession.shared.data(for: req)
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            if code == 401 || code == 403 {
                let sent = req.value(forHTTPHeaderField: "Authorization") != nil
                throw LMError(kind: .unauthorized, message: sent
                    ? "The server refused the API token (\(code)). Set a valid one in the leaf menu: API token…"
                    : "The server wants an API token (\(code)). Set it in the leaf menu: API token…")
            }
            return (data, code)
        } catch let e as LMError {
            throw e
        } catch is CancellationError {
            throw CancellationError()
        } catch let e as URLError where e.code == .cancelled {
            throw CancellationError()
        } catch {
            throw LMError(kind: .unreachable, message: "No answer from \(base.absoluteString): \(error.localizedDescription)")
        }
    }

    static func errorText(_ data: Data) -> String {
        if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let e = obj["error"] as? [String: Any], let m = e["message"] as? String { return m }
            if let e = obj["error"] as? String { return e }
        }
        return String(data: data.prefix(300), encoding: .utf8) ?? ""
    }

    // MARK: the OpenAI-compatible API

    /// The ids of the models the server offers.
    public func models() async throws -> [String] {
        let (data, code) = try await send(base.appendingPathComponent("models"), body: nil, timeout: 6)
        guard code == 200, let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let list = obj["data"] as? [[String: Any]] else {
            throw LMError(kind: .http, message: "The server answered \(code) to /v1/models")
        }
        return list.compactMap { $0["id"] as? String }
    }

    /// The body of a chat request: greedy, not streamed, thinking switched off where the server
    /// understands the switch.
    public static func chatBody(model: String, messages: [[String: Any]], tools: [[String: Any]]?, maxTokens: Int,
                                extras: Bool) -> [String: Any] {
        var body: [String: Any] = ["model": model, "messages": messages, "temperature": 0, "max_tokens": maxTokens, "stream": false]
        if let tools, !tools.isEmpty { body["tools"] = tools }
        if extras {
            body["reasoning_effort"] = "none"                              // LM Studio (checked: without it the model thinks first)
            body["chat_template_kwargs"] = ["enable_thinking": false]      // llama-server
        }
        return body
    }

    public func chat(model: String, messages: [[String: Any]], tools: [[String: Any]]? = nil, maxTokens: Int) async throws -> ChatResult {
        let start = Date()
        let url = base.appendingPathComponent("chat/completions")
        var (data, code) = try await send(url, body: LMClient.chatBody(
            model: model, messages: messages, tools: tools, maxTokens: maxTokens, extras: !extrasRejected))
        if (400..<500).contains(code), !extrasRejected {             // a server that refuses the thinking switch
            extrasRejected = true
            (data, code) = try await send(url, body: LMClient.chatBody(
                model: model, messages: messages, tools: tools, maxTokens: maxTokens, extras: false))
        }
        guard code == 200 else {
            let text = LMClient.errorText(data)
            if (400..<500).contains(code), tools != nil {
                throw LMError(kind: .toolsRejected, message: "The server refused the tools field (\(code)): \(text)")
            }
            throw LMError(kind: .http, message: "The server answered \(code): \(text)")
        }
        var result = try LMClient.parseChat(data)
        result.seconds = Date().timeIntervalSince(start)
        return result
    }

    public static func parseChat(_ data: Data) throws -> ChatResult {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let choice = (obj["choices"] as? [[String: Any]])?.first,
              let message = choice["message"] as? [String: Any] else {
            throw LMError(kind: .badAnswer, message: "The server's answer has no message: " + (String(data: data.prefix(200), encoding: .utf8) ?? ""))
        }
        var r = ChatResult()
        r.model = obj["model"] as? String
        r.finishReason = choice["finish_reason"] as? String
        var text = ""
        if let s = message["content"] as? String {
            text = s
        } else if let parts = message["content"] as? [[String: Any]] {
            text = parts.compactMap { $0["text"] as? String }.joined()
        }
        r.reasoning = (message["reasoning_content"] as? String) ?? (message["reasoning"] as? String) ?? ""
        if r.reasoning.isEmpty, let m = Parsing.matches("<think>(.*?)(?:</think>|$)", text).first { r.reasoning = m[1] }
        if r.reasoning.isEmpty, let end = text.range(of: "</think>") { r.reasoning = String(text[..<end.lowerBound]) }
        r.content = Parsing.stripThinking(text)
        r.toolCalls = (message["tool_calls"] as? [[String: Any]]) ?? []
        if let usage = obj["usage"] as? [String: Any] {
            r.promptTokens = usage["prompt_tokens"] as? Int
            r.completionTokens = usage["completion_tokens"] as? Int
        }
        return r
    }

    // MARK: LM Studio's own API (/api/v1): which models there are, loading and unloading them

    func studio(_ path: String) -> URL { root.appendingPathComponent("api/v1/" + path) }

    public static func parseStudioModels(_ data: Data) -> [StudioModel]? {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let list = obj["models"] as? [[String: Any]] else { return nil }
        return list.compactMap { m in
            guard let key = m["key"] as? String else { return nil }
            let caps = m["capabilities"] as? [String: Any]
            let reasoning = caps?["reasoning"] as? [String: Any]
            let instances = (m["loaded_instances"] as? [[String: Any]]) ?? []
            return StudioModel(key: key, type: (m["type"] as? String) ?? "llm", vision: caps?["vision"] as? Bool,
                               loaded: instances.compactMap { $0["id"] as? String },
                               contextLength: (instances.first?["config"] as? [String: Any])?["context_length"] as? Int,
                               reasoningOptions: (reasoning?["allowed_options"] as? [String]) ?? [],
                               reasoningDefault: reasoning?["default"] as? String)
        }
    }

    /// Every model LM Studio has on disk, with what is loaded. Throws `.notFound` when the
    /// server is not LM Studio (it has no /api/v1).
    public func studioModels() async throws -> [StudioModel] {
        let (data, code) = try await send(studio("models"), body: nil, timeout: 6)
        if code == 404 { throw LMError(kind: .notFound, message: "This server has no LM Studio API") }
        guard code == 200, let models = LMClient.parseStudioModels(data) else {
            throw LMError(kind: .http, message: "The server answered \(code) to /api/v1/models: \(LMClient.errorText(data))")
        }
        return models
    }

    /// Loads a model; returns the id of the loaded instance and how long it took.
    public func studioLoad(_ key: String, contextLength: Int) async throws -> (instance: String, seconds: Double) {
        let (data, code) = try await send(studio("models/load"), body: ["model": key, "context_length": contextLength], timeout: 300)
        guard code == 200, let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LMError(kind: .http, message: "Loading \(key) failed (\(code)): \(LMClient.errorText(data))")
        }
        return ((obj["instance_id"] as? String) ?? key, (obj["load_time_seconds"] as? Double) ?? 0)
    }

    public func studioUnload(_ instance: String) async throws {
        let (data, code) = try await send(studio("models/unload"), body: ["instance_id": instance], timeout: 60)
        guard code == 200 else {
            throw LMError(kind: .http, message: "Unloading \(instance) failed (\(code)): \(LMClient.errorText(data))")
        }
    }
}
