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

struct BridgeConfig: Codable, Identifiable, Equatable, Hashable {
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

    // CodingKeys without explicit rawValues - let convertFromSnakeCase handle the mapping
    enum CodingKeys: String, CodingKey {
        case name
        case enabled
        case supernoteSubdir
        case supernotePath
        case vaultPath
        case defaultTags
        case extraTags
        case aggressiveCleanup
        case spellcheck
        case exportImages
        case imagesSubdir
    }

    // Custom decoder to handle missing fields with defaults
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        name = try container.decode(String.self, forKey: .name)
        enabled = try container.decodeIfPresent(Bool.self, forKey: .enabled) ?? true
        supernoteSubdir = try container.decode(String.self, forKey: .supernoteSubdir)
        supernotePath = try container.decodeIfPresent(String.self, forKey: .supernotePath) ?? ""
        vaultPath = try container.decode(String.self, forKey: .vaultPath)
        defaultTags = try container.decodeIfPresent([String].self, forKey: .defaultTags) ?? []
        extraTags = try container.decodeIfPresent([String].self, forKey: .extraTags) ?? []
        aggressiveCleanup = try container.decodeIfPresent(Bool.self, forKey: .aggressiveCleanup) ?? false
        spellcheck = try container.decodeIfPresent(Bool.self, forKey: .spellcheck) ?? false
        exportImages = try container.decodeIfPresent(Bool.self, forKey: .exportImages) ?? true
        imagesSubdir = try container.decodeIfPresent(String.self, forKey: .imagesSubdir) ?? "Supersidian/Assets"
    }

    // Regular init for programmatic creation
    init(name: String, enabled: Bool, supernoteSubdir: String, supernotePath: String, vaultPath: String, defaultTags: [String], extraTags: [String], aggressiveCleanup: Bool, spellcheck: Bool, exportImages: Bool, imagesSubdir: String) {
        self.name = name
        self.enabled = enabled
        self.supernoteSubdir = supernoteSubdir
        self.supernotePath = supernotePath
        self.vaultPath = vaultPath
        self.defaultTags = defaultTags
        self.extraTags = extraTags
        self.aggressiveCleanup = aggressiveCleanup
        self.spellcheck = spellcheck
        self.exportImages = exportImages
        self.imagesSubdir = imagesSubdir
    }
}

enum ConfigurationError: LocalizedError {
    case projectNotFound
    case invalidConfiguration
    case backupFailed
    
    // Validation errors
    case missingSupernoteRoot
    case supernoteRootNotFound(String)
    case noBridges
    case invalidBridgeName
    case missingSupernoteSubdir(String)
    case missingVaultPath(String)
    case vaultPathNotFound(String, String)
    case missingTodoistToken
    case missingWebhookUrl
    case missingHealthcheckUrl
    
    var errorDescription: String? {
        switch self {
        case .projectNotFound:
            return "Project configuration not found"
        case .invalidConfiguration:
            return "Invalid configuration"
        case .backupFailed:
            return "Failed to create configuration backup"
        case .missingSupernoteRoot:
            return "Supernote root path is required"
        case .supernoteRootNotFound(let path):
            return "Supernote root not found: \(path)"
        case .noBridges:
            return "At least one vault must be configured"
        case .invalidBridgeName:
            return "Bridge name cannot be empty"
        case .missingSupernoteSubdir(let name):
            return "Supernote subdirectory is required for bridge '\(name)'"
        case .missingVaultPath(let name):
            return "Vault path is required for bridge '\(name)'"
        case .vaultPathNotFound(let name, let path):
            return "Vault path not found for bridge '\(name)': \(path)"
        case .missingTodoistToken:
            return "Todoist API token is required when Todoist provider is enabled"
        case .missingWebhookUrl:
            return "Webhook URL is required when webhook notifications are enabled"
        case .missingHealthcheckUrl:
            return "Healthcheck URL is required when healthcheck is enabled"
        }
    }
}

// MARK: - BridgeConfig Extensions

extension BridgeConfig {
    func validate() throws {
        // Skip validation for disabled bridges
        guard enabled else { return }

        guard !name.isEmpty else {
            throw ConfigurationError.invalidBridgeName
        }

        guard !supernoteSubdir.isEmpty else {
            throw ConfigurationError.missingSupernoteSubdir(name)
        }

        guard !vaultPath.isEmpty else {
            throw ConfigurationError.missingVaultPath(name)
        }

        let vaultURL = URL(fileURLWithPath: (vaultPath as NSString).expandingTildeInPath)
        guard FileManager.default.fileExists(atPath: vaultURL.path) else {
            throw ConfigurationError.vaultPathNotFound(name, vaultPath)
        }
    }
    
    func toJSON() -> AppConfiguration.BridgeJSON {
        AppConfiguration.BridgeJSON(
            name: name,
            enabled: enabled,
            supernoteSubdir: supernoteSubdir,
            vaultPath: vaultPath,
            extraTags: extraTags,
            aggressiveCleanup: aggressiveCleanup,
            spellcheck: spellcheck,
            exportImages: exportImages,
            imagesSubdir: imagesSubdir
        )
    }
}
