//
//  PreferencesViewModel.swift
//  Supersidian
//
//  Manages preferences state with Apply/Revert pattern.
//

import Foundation
import SwiftUI

@MainActor
class PreferencesViewModel: ObservableObject {
    @Published var currentConfig: AppConfiguration
    @Published var editedConfig: AppConfiguration
    @Published var hasChanges: Bool = false
    @Published var validationError: String?
    @Published var isSaving: Bool = false
    
    private let configManager = ConfigurationManager.shared
    
    init() {
        let loaded = Self.loadConfiguration()
        self.currentConfig = loaded
        self.editedConfig = loaded
    }
    
    // MARK: - Loading
    
    func load() {
        let loaded = Self.loadConfiguration()
        currentConfig = loaded
        editedConfig = loaded
        hasChanges = false
        validationError = nil
    }
    
    private static func loadConfiguration() -> AppConfiguration {
        var config = AppConfiguration()
        
        // Load from ConfigurationManager (reads .env and config.json)
        let envVars = ConfigurationManager.shared.loadEnvFile()
        if !envVars.isEmpty {
            config.supernoteRoot = envVars["SUPERSIDIAN_SUPERNOTE_ROOT"] ?? ""
            config.verbose = envVars["SUPERSIDIAN_VERBOSE"] == "1"
            config.logPath = envVars["SUPERSIDIAN_LOG_PATH"]
            
            config.syncProvider = envVars["SUPERSIDIAN_SYNC_PROVIDER"] ?? "dropbox"
            config.noteProvider = envVars["SUPERSIDIAN_NOTE_PROVIDER"] ?? "obsidian"
            config.todoProvider = envVars["SUPERSIDIAN_TODO_PROVIDER"] ?? "noop"
            
            if let providers = envVars["SUPERSIDIAN_NOTIFICATION_PROVIDERS"] {
                config.notificationProviders = providers.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
            }
            
            config.todoistApiToken = envVars["SUPERSIDIAN_TODOIST_API_TOKEN"]
            config.webhookUrl = envVars["SUPERSIDIAN_WEBHOOK_URL"]
            config.webhookTopic = envVars["SUPERSIDIAN_WEBHOOK_TOPIC"]
            config.webhookNotifications = envVars["SUPERSIDIAN_WEBHOOK_NOTIFICATIONS"] ?? "errors"
            config.healthcheckUrl = envVars["SUPERSIDIAN_HEALTHCHECK_URL"]

            // For backward compatibility: if healthcheck URL exists, enable it
            if let healthcheckUrl = config.healthcheckUrl, !healthcheckUrl.isEmpty {
                config.healthcheckEnabled = true
            }

            config.supernoteTool = envVars["SUPERSIDIAN_SUPERNOTE_TOOL"]
        }
        
        // Load bridges from config.json
        if let configJSON = ConfigurationManager.shared.loadConfigJSON() {
            config.bridges = configJSON.bridges
        }
        
        return config
    }
    
    // MARK: - Changes Tracking
    
    func updateEdited(_ updated: AppConfiguration) {
        editedConfig = updated
        hasChanges = (editedConfig != currentConfig)
        
        // Clear validation error when user makes changes
        if hasChanges {
            validationError = nil
        }
    }
    
    // MARK: - Apply/Revert
    
    func apply() async throws {
        // Validate first
        do {
            try editedConfig.validate()
        } catch {
            validationError = error.localizedDescription
            throw error
        }
        
        validationError = nil
        isSaving = true
        defer { isSaving = false }
        
        // Create backups
        let envBackup = try configManager.createBackup(of: .env)
        let configBackup = try configManager.createBackup(of: .configJSON)
        
        do {
            // Write .env
            let envDict = editedConfig.toEnv()
            try configManager.writeEnv(envDict)
            
            // Write config.json
            let configJSON = editedConfig.toConfigJSON()
            try configManager.writeConfigJSON(configJSON)
            
            // Success - update current config
            currentConfig = editedConfig
            hasChanges = false
            
            NSLog("PreferencesViewModel: Configuration saved successfully")
            
        } catch {
            // Rollback on failure
            NSLog("PreferencesViewModel: Save failed, rolling back: \(error)")
            
            try? configManager.restoreBackup(from: envBackup, to: .env)
            try? configManager.restoreBackup(from: configBackup, to: .configJSON)
            
            validationError = "Failed to save: \(error.localizedDescription)"
            throw error
        }
    }
    
    func revert() {
        editedConfig = currentConfig
        hasChanges = false
        validationError = nil
    }
    
    // MARK: - Bridge Management
    
    func addBridge(_ bridge: BridgeConfig) {
        var updated = editedConfig
        updated.bridges.append(bridge)
        updateEdited(updated)
    }
    
    func updateBridge(_ bridge: BridgeConfig) {
        var updated = editedConfig
        if let index = updated.bridges.firstIndex(where: { $0.id == bridge.id }) {
            updated.bridges[index] = bridge
            updateEdited(updated)
        }
    }
    
    func deleteBridge(_ bridge: BridgeConfig) {
        var updated = editedConfig
        updated.bridges.removeAll { $0.id == bridge.id }
        updateEdited(updated)
    }
    
    func moveBridges(from source: IndexSet, to destination: Int) {
        var updated = editedConfig
        updated.bridges.move(fromOffsets: source, toOffset: destination)
        updateEdited(updated)
    }
}

// MARK: - ConfigurationManager Extensions

extension ConfigurationManager {
    enum ConfigFile {
        case env
        case configJSON
        
        var filename: String {
            switch self {
            case .env: return ".env"
            case .configJSON: return "supersidian.config.json"
            }
        }
    }
    
    func createBackup(of file: ConfigFile) throws -> URL {
        guard let projectRoot = getProjectRoot() else {
            throw NSError(domain: "PreferencesViewModel", code: 1, userInfo: [NSLocalizedDescriptionKey: "Project root not found"])
        }
        
        let originalPath = projectRoot.appendingPathComponent(file.filename)
        let backupPath = projectRoot.appendingPathComponent(file.filename + ".backup")
        
        if FileManager.default.fileExists(atPath: originalPath.path) {
            try FileManager.default.copyItem(at: originalPath, to: backupPath)
        }
        
        return backupPath
    }
    
    func restoreBackup(from backup: URL, to file: ConfigFile) throws {
        guard let projectRoot = getProjectRoot() else {
            throw NSError(domain: "PreferencesViewModel", code: 2, userInfo: [NSLocalizedDescriptionKey: "Project root not found"])
        }
        
        let destination = projectRoot.appendingPathComponent(file.filename)
        
        // Remove current file
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        
        // Restore backup
        if FileManager.default.fileExists(atPath: backup.path) {
            try FileManager.default.copyItem(at: backup, to: destination)
        }
    }
    
    func writeEnv(_ env: [String: String]) throws {
        guard let projectRoot = getProjectRoot() else {
            throw NSError(domain: "ConfigurationManager", code: 3, userInfo: [NSLocalizedDescriptionKey: "Project root not found"])
        }
        
        let envPath = projectRoot.appendingPathComponent(".env")
        
        // Build .env file content
        var lines: [String] = []
        lines.append("# Supersidian Configuration")
        lines.append("# Generated by Supersidian macOS app")
        lines.append("")
        
        // Sort keys for consistent output
        for key in env.keys.sorted() {
            if let value = env[key] {
                lines.append("\(key)=\(value)")
            }
        }
        
        let content = lines.joined(separator: "\n") + "\n"
        try content.write(to: envPath, atomically: true, encoding: .utf8)
    }
    
    func writeConfigJSON(_ config: AppConfiguration.ConfigJSON) throws {
        guard let projectRoot = getProjectRoot() else {
            throw NSError(domain: "ConfigurationManager", code: 4, userInfo: [NSLocalizedDescriptionKey: "Project root not found"])
        }
        
        let configPath = projectRoot.appendingPathComponent("supersidian.config.json")
        
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        
        let data = try encoder.encode(config)
        try data.write(to: configPath, options: .atomic)
    }
}
