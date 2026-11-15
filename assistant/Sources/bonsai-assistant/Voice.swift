// Spoken requests, turned into text on the Mac itself by Argmax's WhisperKit (open-source SDK).
// Nothing leaves the machine: once the model is on disk it is loaded from there with the
// network switched off.
import Foundation
import WhisperKit

struct VoiceError: Error, CustomStringConvertible {
    let description: String
}

final class Voice {
    static let modelName = "base.en"                                          // about 150 MB
    /// Outside ~/Documents (the SDK's default place).
    static let folder = NSHomeDirectory() + "/Bonsai-demo/models/argmax"

    private var kit: WhisperKit?
    private var loading: Task<WhisperKit, Error>?
    private(set) var listening = false

    /// The folder of the model if it is already on disk.
    static func localModel() -> String? {
        guard let walker = FileManager.default.enumerator(atPath: folder) else { return nil }
        for case let path as String in walker where path.hasSuffix("openai_whisper-" + modelName) {
            return folder + "/" + path
        }
        return nil
    }

    /// Loads the model: from disk when it is there, otherwise it is downloaded once.
    func prepare() async throws {
        if kit != nil { return }
        if loading == nil {
            loading = Task {
                try? FileManager.default.createDirectory(atPath: Voice.folder, withIntermediateDirectories: true)
                if let local = Voice.localModel() {
                    // Model and tokenizer both from our folder, nothing fetched. The tokenizer folder must
                    // be named: left out, the SDK looks under ~/Documents/huggingface and downloads it there.
                    return try await WhisperKit(WhisperKitConfig(model: Voice.modelName, modelFolder: local,
                                                                 tokenizerFolder: URL(fileURLWithPath: Voice.folder),
                                                                 verbose: false, logLevel: .error, download: false))
                }
                return try await WhisperKit(WhisperKitConfig(model: Voice.modelName, downloadBase: URL(fileURLWithPath: Voice.folder),
                                                             verbose: false, logLevel: .error, download: true))
            }
        }
        do {
            kit = try await loading?.value
            loading = nil
        } catch {
            loading = nil
            throw VoiceError(description: "The speech model could not be loaded (\(error.localizedDescription)). "
                + "The first use downloads it (about 150 MB) and needs the network once.")
        }
    }

    private static let options = DecodingOptions(skipSpecialTokens: true, withoutTimestamps: true)

    private func text(of results: [TranscriptionResult]) -> String {
        results.map(\.text).joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Starts recording from the microphone.
    func start() async throws {
        guard await AudioProcessor.requestRecordPermission() else {
            throw VoiceError(description: "The microphone is not allowed for the app this was started from (Terminal, or Claude if started in its "
                + "terminal panel): allow it in System Settings > Privacy & Security > Microphone")
        }
        try await prepare()
        guard let kit else { return }
        try kit.audioProcessor.startRecordingLive(inputDeviceID: nil, callback: nil)
        listening = true
    }

    /// Stops recording and returns what was said, the seconds of sound and the seconds it took to read them.
    func finish() async throws -> (text: String, heard: Double, seconds: Double) {
        guard listening, let kit else { return ("", 0, 0) }
        listening = false
        kit.audioProcessor.stopRecording()
        let samples = Array(kit.audioProcessor.audioSamples)
        let start = Date()
        let results: [TranscriptionResult] = try await kit.transcribe(audioArray: samples, decodeOptions: Voice.options)
        return (text(of: results), Double(samples.count) / 16000, Date().timeIntervalSince(start))
    }

    func cancel() {
        guard listening else { return }
        listening = false
        kit?.audioProcessor.stopRecording()
    }

    /// A sound file as text (for checking the speech model without a microphone).
    func transcribe(file: String) async throws -> (text: String, seconds: Double) {
        try await prepare()
        guard let kit else { return ("", 0) }
        let start = Date()
        let results: [TranscriptionResult] = try await kit.transcribe(audioPath: file, decodeOptions: Voice.options)
        return (text(of: results), Date().timeIntervalSince(start))
    }
}
