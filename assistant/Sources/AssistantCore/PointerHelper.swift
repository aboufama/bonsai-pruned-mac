import CoreGraphics
import Foundation

/// A helper that only points: a small server on this Mac (Bonsai-Pruned 4B with its pointing
/// decoder) that is asked where something is on a screenshot. It is optional. When it is not
/// running, or an answer of its cannot be used, the language model points as before.
///
///   GET  /health
///   POST /point   {"image_b64": …, "request": "the target in words", "looks": 1 or 2}
///                 -> {"x": 0…1, "y": 0…1, "seconds": …, "read_seconds": …, "cached": …}
///
/// x and y are fractions of the image's width and height.
public struct PointerHelper {
    /// What a pointing step says did the pointing, in the steps file.
    public static let name = "bonsai-pruned-4b"
    public static let languageModel = "language model"
    /// A reply that takes longer than this is not used.
    public static let limit = 30.0

    public let base: URL

    /// From an address as it is given ("http://127.0.0.1:1235", "127.0.0.1:1235/"); nil when it is not one.
    public init?(_ address: String) {
        var text = address.trimmingCharacters(in: .whitespacesAndNewlines)
        while text.hasSuffix("/") { text.removeLast() }
        guard !text.isEmpty else { return nil }
        if !text.contains("://") { text = "http://" + text }
        guard let url = URL(string: text), let scheme = url.scheme, ["http", "https"].contains(scheme), url.host != nil else { return nil }
        base = url
    }

    /// What is sent to /point: the picture exactly as the language model would have been sent
    /// it (taken out of its data URL), and the same words for the target.
    public static func body(imageURL: String, request: String, looks: Int) -> [String: Any]? {
        guard let comma = imageURL.range(of: "base64,") else { return nil }
        let picture = String(imageURL[comma.upperBound...])
        guard !picture.isEmpty else { return nil }
        return ["image_b64": picture, "request": request, "looks": looks >= 2 ? 2 : 1]
    }

    public enum Reply: Equatable {
        case point(x: Double, y: Double, seconds: Double, readSeconds: Double, cached: Bool)
        case unusable(String)            // why; the language model points instead
    }

    /// What a reply to /point amounts to. Only a 200 that came within the limit and holds x
    /// and y between 0 and 1 is a point; anything else says why it is not.
    public static func read(status: Int, data: Data, elapsed: Double) -> Reply {
        guard elapsed <= limit else { return .unusable(String(format: "its reply took %.0f s, over the limit of %.0f s", elapsed, limit)) }
        guard status == 200 else { return .unusable("it answered with status \(status)") }
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return .unusable("its reply is not a JSON object") }
        func number(_ key: String) -> Double? {
            guard let n = object[key] as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() else { return nil }      // 0 and 1 are numbers; true is not
            return n.doubleValue
        }
        guard let x = number("x"), let y = number("y") else { return .unusable("its reply has no x and y") }
        guard (0...1).contains(x), (0...1).contains(y) else { return .unusable("its point (\(x), \(y)) is outside the picture") }
        return .point(x: x, y: y, seconds: number("seconds") ?? elapsed, readSeconds: number("read_seconds") ?? 0, cached: (object["cached"] as? Bool) ?? false)
    }

    /// What is sent to /read: the picture alone, for the helper to read before anyone asks about it.
    public static func readBody(imageURL: String) -> [String: Any]? {
        guard let comma = imageURL.range(of: "base64,") else { return nil }
        let picture = String(imageURL[comma.upperBound...])
        return picture.isEmpty ? nil : ["image_b64": picture]
    }

    public enum ReadReply: Equatable {
        case read(seconds: Double, cached: Bool)
        case unusable(String)            // why; the language model reads the screen ahead instead
    }

    /// What a reply to /read amounts to: a 200 within the limit that is a JSON object means the picture is read and kept.
    public static func readReply(status: Int, data: Data, elapsed: Double) -> ReadReply {
        guard elapsed <= limit else { return .unusable(String(format: "its reply took %.0f s, over the limit of %.0f s", elapsed, limit)) }
        guard status == 200 else { return .unusable("it answered with status \(status)") }
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return .unusable("its reply is not a JSON object") }
        var seconds = elapsed
        if let n = object["read_seconds"] as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() { seconds = n.doubleValue }
        return .read(seconds: seconds, cached: (object["cached"] as? Bool) ?? false)
    }

    /// Has the helper read a picture and keep the reading, so that pointing at something on it later costs only its decoder.
    public func read(imageURL: String) async -> ReadReply {
        guard let body = PointerHelper.readBody(imageURL: imageURL), let data = try? JSONSerialization.data(withJSONObject: body) else {
            return .unusable("the picture could not be prepared for it")
        }
        var request = URLRequest(url: base.appendingPathComponent("read"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        request.timeoutInterval = PointerHelper.limit
        let start = Date()
        do {
            let (reply, response) = try await URLSession.shared.data(for: request)
            return PointerHelper.readReply(status: (response as? HTTPURLResponse)?.statusCode ?? 0, data: reply, elapsed: Date().timeIntervalSince(start))
        } catch {
            return .unusable("no answer (\(error.localizedDescription))")
        }
    }

    /// The helper's point on the grid the language model answers on (0 to 1000 across and
    /// down the picture), so that both are mapped to the screen the same way.
    public static func grid(x: Double, y: Double) -> CGPoint { CGPoint(x: x * 1000, y: y * 1000) }

    /// Whether the helper is there (one short question when the app starts).
    public func health(timeout: Double = 1) async -> (ok: Bool, note: String) {
        var request = URLRequest(url: base.appendingPathComponent("health"))
        request.timeoutInterval = timeout
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let said = String(data: data.prefix(200), encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            return (status == 200, "status \(status)" + (said.isEmpty ? "" : ": \(said)"))
        } catch {
            return (false, error.localizedDescription)
        }
    }

    /// Asks the helper to point. Never throws: what cannot be used says why.
    public func point(imageURL: String, request words: String, looks: Int) async -> Reply {
        guard let body = PointerHelper.body(imageURL: imageURL, request: words, looks: looks),
              let data = try? JSONSerialization.data(withJSONObject: body) else { return .unusable("the picture could not be prepared for it") }
        var request = URLRequest(url: base.appendingPathComponent("point"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        request.timeoutInterval = PointerHelper.limit
        let start = Date()
        do {
            let (reply, response) = try await URLSession.shared.data(for: request)
            return PointerHelper.read(status: (response as? HTTPURLResponse)?.statusCode ?? 0, data: reply, elapsed: Date().timeIntervalSince(start))
        } catch {
            return .unusable("no answer (\(error.localizedDescription))")
        }
    }
}
