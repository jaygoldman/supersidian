//
//  ConfigurationManager.swift
//  Supersidian
//
//  Manages reading and writing supersidian configuration files.
//

import Foundation

class ConfigurationManager {
    static let shared = ConfigurationManager()

    private let fileManager = FileManager.default
    private var projectRoot: URL?

    private init() {
        detectProjectRoot()
    }

    // MARK: - Project Detection

    private func detectProjectRoot() {
        // Try common locations for supersidian installation
        let possiblePaths = [
            fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Dev/supersidian"),
            fileManager.homeDirectoryForCurrentUser.appendingPathComponent("supersidian"),
            fileManager.homeDirectoryForCurrentUser.appendingPathComponent("Code/supersidian"),
        ]

        for path in possiblePaths {
            if fileManager.fileExists(atPath: path.path) {
                projectRoot = path
                NSLog("ConfigurationManager: Found project at \(path.path)")
                return
            }
        }

        NSLog("ConfigurationManager: Project root not found, will need setup")
    }

    func getProjectRoot() -> URL? {
        return projectRoot
    }

    func setProjectRoot(_ url: URL) {
        projectRoot = url
        UserDefaults.standard.set(url.path, forKey: "projectRoot")
    }

    // MARK: - Configuration Files

    func getEnvPath() -> URL? {
        guard let root = projectRoot else { return nil }
        return root.appendingPathComponent(".env")
    }

    func getConfigPath() -> URL? {
        guard let root = projectRoot else { return nil }
        return root.appendingPathComponent("supersidian.config.json")
    }

    // MARK: - Reading Configuration

    func loadEnvFile() -> [String: String] {
        guard let envPath = getEnvPath() else { return [:] }

        var env: [String: String] = [:]

        do {
            let content = try String(contentsOf: envPath, encoding: .utf8)
            for line in content.components(separatedBy: .newlines) {
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                if trimmed.isEmpty || trimmed.hasPrefix("#") {
                    continue
                }
                if let range = trimmed.range(of: "=") {
                    let key = String(trimmed[..<range.lowerBound]).trimmingCharacters(in: .whitespaces)
                    let value = String(trimmed[range.upperBound...]).trimmingCharacters(in: .whitespaces)
                    env[key] = value
                }
            }
        } catch {
            NSLog("ConfigurationManager: Failed to load .env: \(error)")
        }

        return env
    }

    func loadConfigJSON() -> SupersidianConfig? {
        guard let configPath = getConfigPath() else { return nil }

        do {
            let data = try Data(contentsOf: configPath)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(SupersidianConfig.self, from: data)
        } catch {
            NSLog("ConfigurationManager: Failed to load config JSON: \(error)")
            return nil
        }
    }

    // MARK: - Writing Configuration

    func saveEnvFile(_ env: [String: String]) throws {
        guard let envPath = getEnvPath() else {
            throw ConfigurationError.projectNotFound
        }

        let lines = env.map { "\($0.key)=\($0.value)" }.sorted()
        let content = lines.joined(separator: "\n") + "\n"

        try content.write(to: envPath, atomically: true, encoding: .utf8)
    }

    func saveConfigJSON(_ config: SupersidianConfig) throws {
        guard let configPath = getConfigPath() else {
            throw ConfigurationError.projectNotFound
        }

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        let data = try encoder.encode(config)
        try data.write(to: configPath, options: .atomic)
    }

    // MARK: - Backup & Restore

    func createBackup() throws -> (envBackup: URL, configBackup: URL) {
        guard let envPath = getEnvPath(), let configPath = getConfigPath() else {
            throw ConfigurationError.projectNotFound
        }

        let timestamp = ISO8601DateFormatter().string(from: Date())
        let backupDir = projectRoot!.appendingPathComponent(".backups")
        try fileManager.createDirectory(at: backupDir, withIntermediateDirectories: true)

        let envBackup = backupDir.appendingPathComponent(".env-\(timestamp)")
        let configBackup = backupDir.appendingPathComponent("supersidian.config.json-\(timestamp)")

        try fileManager.copyItem(at: envPath, to: envBackup)
        try fileManager.copyItem(at: configPath, to: configBackup)

        return (envBackup, configBackup)
    }

    func restoreBackup(envBackup: URL, configBackup: URL) throws {
        guard let envPath = getEnvPath(), let configPath = getConfigPath() else {
            throw ConfigurationError.projectNotFound
        }

        try fileManager.removeItem(at: envPath)
        try fileManager.removeItem(at: configPath)
        try fileManager.copyItem(at: envBackup, to: envPath)
        try fileManager.copyItem(at: configBackup, to: configPath)
    }
}

// MARK: - Configuration Models

struct SupersidianConfig: Codable {
    var bridges: [BridgeConfig]
}

struct BridgeConfig: Codable, Identifiable {
    var name: String
    var enabled: Bool
    var supernoteSubdir: String
    var supernotePath: String
    var vaultPath: String
    var defaultTags: [String]
    var extraTags: [String]
    var aggressiveCleanup: Bool
    var spellcheck: Bool
    var exportImages: Bool
    var imagesSubdir: String

    var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case enabled
        case supernoteSubdir = "supernote_subdir"
        case supernotePath = "supernote_path"
        case vaultPath = "vault_path"
        case defaultTags = "default_tags"
        case extraTags = "extra_tags"
        case aggressiveCleanup = "aggressive_cleanup"
        case spellcheck
        case exportImages = "export_images"
        case imagesSubdir = "images_subdir"
    }
}

enum ConfigurationError: Error {
    case projectNotFound
    case invalidConfiguration
    case backupFailed
}
