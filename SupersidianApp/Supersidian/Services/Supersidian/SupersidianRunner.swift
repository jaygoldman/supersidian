//
//  SupersidianRunner.swift
//  Supersidian
//
//  Handles running the supersidian Python script and parsing output.
//

import Foundation

class SupersidianRunner {
    static let shared = SupersidianRunner()

    private let configManager = ConfigurationManager.shared

    private init() {}

    // MARK: - Finding Supersidian

    func findSupersidianExecutable() -> String? {
        // Try common installation locations first (GUI apps don't inherit PATH)
        let commonPaths = [
            "/opt/homebrew/bin/supersidian",  // Homebrew on Apple Silicon
            "/usr/local/bin/supersidian",     // Homebrew on Intel
            "/usr/bin/supersidian",            // System install
        ]

        for path in commonPaths {
            if FileManager.default.fileExists(atPath: path) {
                NSLog("SupersidianRunner: Found executable at \(path)")
                return path
            }
        }

        // Try python module directly from project
        if let projectRoot = configManager.getProjectRoot() {
            let venvPython = projectRoot.appendingPathComponent(".venv/bin/python3")
            if FileManager.default.fileExists(atPath: venvPython.path) {
                NSLog("SupersidianRunner: Using venv python at \(venvPython.path)")
                return venvPython.path
            }
        }

        NSLog("SupersidianRunner: No executable found")
        return nil
    }

    // MARK: - Running Sync
    
    func runSync() async throws {
        guard let executable = findSupersidianExecutable() else {
            throw SupersidianError.executableNotFound
        }
        
        let process = Process()
        
        if executable.hasSuffix("python3") {
            // Running via Python module
            guard let projectRoot = configManager.getProjectRoot() else {
                throw SupersidianError.projectNotFound
            }
            
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["-m", "supersidian.supersidian"]
            process.currentDirectoryURL = projectRoot
        } else {
            // Running via installed command
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = []
        }
        
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus != 0 {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
                throw SupersidianError.syncFailed(errorMessage)
            }
        } catch let error as SupersidianError {
            throw error
        } catch {
            throw SupersidianError.executionFailed(error)
        }
    }
    
    // MARK: - Running Sync with Streaming Output
    
    func runSyncWithOutput(lineHandler: @escaping @Sendable (String) async -> Void) async throws {
        guard let executable = findSupersidianExecutable() else {
            throw SupersidianError.executableNotFound
        }
        
        let process = Process()
        
        if executable.hasSuffix("python3") {
            // Running via Python module with verbose output
            guard let projectRoot = configManager.getProjectRoot() else {
                throw SupersidianError.projectNotFound
            }
            
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["-m", "supersidian.supersidian", "--verbose"]
            process.currentDirectoryURL = projectRoot
        } else {
            // Running via installed command with verbose output
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["--verbose"]
        }
        
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        
        // Stream stdout
        let outputHandle = outputPipe.fileHandleForReading
        outputHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let output = String(data: data, encoding: .utf8) {
                Task {
                    await lineHandler(output)
                }
            }
        }
        
        // Stream stderr
        let errorHandle = errorPipe.fileHandleForReading
        errorHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let output = String(data: data, encoding: .utf8) {
                Task {
                    await lineHandler(output)
                }
            }
        }
        
        do {
            try process.run()
            
            // Wait for process to complete
            await withCheckedContinuation { continuation in
                process.terminationHandler = { _ in
                    continuation.resume()
                }
            }
            
            // Stop reading handlers
            outputHandle.readabilityHandler = nil
            errorHandle.readabilityHandler = nil
            
            // Check if process was cancelled
            try Task.checkCancellation()
            
            if process.terminationStatus != 0 {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
                throw SupersidianError.syncFailed(errorMessage)
            }
        } catch is CancellationError {
            // Kill process if task was cancelled
            if process.isRunning {
                process.terminate()
            }
            throw CancellationError()
        } catch let error as SupersidianError {
            throw error
        } catch {
            throw SupersidianError.executionFailed(error)
        }
    }

    // MARK: - Export Status

    func exportStatus() async throws -> SupersidianStatus {
        guard let executable = findSupersidianExecutable() else {
            throw SupersidianError.executableNotFound
        }

        let process = Process()

        if executable.hasSuffix("python3") {
            guard let projectRoot = configManager.getProjectRoot() else {
                throw SupersidianError.projectNotFound
            }

            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["-m", "supersidian.supersidian", "--export-status"]
            process.currentDirectoryURL = projectRoot
        } else {
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["--export-status"]
        }

        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        do {
            try process.run()
            process.waitUntilExit()

            if process.terminationStatus != 0 {
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let errorMessage = String(data: errorData, encoding: .utf8) ?? "Unknown error"
                throw SupersidianError.exportFailed(errorMessage)
            }

            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase

            return try decoder.decode(SupersidianStatus.self, from: outputData)
        } catch let error as SupersidianError {
            throw error
        } catch {
            throw SupersidianError.decodingFailed(error)
        }
    }
}

// MARK: - Models

struct SupersidianStatus: Codable {
    let version: String
    let bridges: [ExportedBridge]
    let databasePath: String
    let logPath: String
    let supernoteRoot: String
    let providers: Providers
    let settings: Settings

    struct ExportedBridge: Codable {
        let name: String
        let enabled: Bool
        let supernotePath: String
        let vaultPath: String
        let vaultName: String
        let defaultTags: [String]
        let extraTags: [String]
        let aggressiveCleanup: Bool
        let spellcheck: Bool
        let exportImages: Bool
        let imagesSubdir: String
        let status: BridgeStatusData?

        struct BridgeStatusData: Codable {
            let bridgeName: String
            let lastSyncTime: String
            let status: String
            let notesFound: Int
            let converted: Int
            let skipped: Int
            let noText: Int
            let tasksTotal: Int
            let tasksOpen: Int
            let tasksCompleted: Int
            let errorMessage: String?
        }
    }

    struct Providers: Codable {
        let notification: [String]
        let sync: String
        let todo: String
        let notes: String
    }

    struct Settings: Codable {
        let verbose: Bool
        let notifyMode: String
        let supernoteTool: String
    }
}

enum SupersidianError: LocalizedError {
    case executableNotFound
    case projectNotFound
    case syncFailed(String)
    case exportFailed(String)
    case executionFailed(Error)
    case decodingFailed(Error)

    var errorDescription: String? {
        switch self {
        case .executableNotFound:
            return "Could not find supersidian executable. Please ensure it is installed."
        case .projectNotFound:
            return "Could not find supersidian project directory."
        case .syncFailed(let message):
            return "Sync failed: \(message)"
        case .exportFailed(let message):
            return "Failed to export status: \(message)"
        case .executionFailed(let error):
            return "Failed to execute supersidian: \(error.localizedDescription)"
        case .decodingFailed(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        }
    }
}
