//
//  AppConfiguration.swift
//  Supersidian
//
//  Complete application configuration model.
//

import Foundation

struct AppConfiguration: Codable, Equatable {
    // Core settings
    var supernoteRoot: String
    var verbose: Bool
    var logPath: String?
    
    // Bridges
    var bridges: [BridgeConfig]
    
    // Providers
    var syncProvider: String
    var noteProvider: String
    var todoProvider: String
    var notificationProviders: [String]
    
    // Todo settings (Todoist)
    var todoistApiToken: String?
    
    // Notification settings (Webhook)
    var webhookUrl: String?
    var webhookTopic: String?
    var webhookNotifications: String  // "all", "errors", "none"
    
    // Healthcheck
    var healthcheckUrl: String?
    
    // Advanced
    var supernoteTool: String?
    
    init() {
        self.supernoteRoot = ""
        self.verbose = false
        self.logPath = nil
        self.bridges = []
        self.syncProvider = "dropbox"
        self.noteProvider = "obsidian"
        self.todoProvider = "noop"
        self.notificationProviders = ["menubar"]
        self.todoistApiToken = nil
        self.webhookUrl = nil
        self.webhookTopic = nil
        self.webhookNotifications = "errors"
        self.healthcheckUrl = nil
        self.supernoteTool = nil
    }
    
    // MARK: - Validation
    
    func validate() throws {
        // Validate supernote root exists
        guard !supernoteRoot.isEmpty else {
            throw ConfigurationError.missingSupernoteRoot
        }
        
        let rootURL = URL(fileURLWithPath: (supernoteRoot as NSString).expandingTildeInPath)
        guard FileManager.default.fileExists(atPath: rootURL.path) else {
            throw ConfigurationError.supernoteRootNotFound(supernoteRoot)
        }
        
        // Validate at least one bridge
        guard !bridges.isEmpty else {
            throw ConfigurationError.noBridges
        }
        
        // Validate each bridge
        for bridge in bridges {
            try bridge.validate()
        }
        
        // Validate todo provider settings
        if todoProvider == "todoist" {
            guard let token = todoistApiToken, !token.isEmpty else {
                throw ConfigurationError.missingTodoistToken
            }
        }
        
        // Validate webhook settings
        if notificationProviders.contains("webhook") {
            guard let url = webhookUrl, !url.isEmpty else {
                throw ConfigurationError.missingWebhookUrl
            }
        }
    }
    
    // MARK: - Conversion to .env
    
    func toEnv() -> [String: String] {
        var env: [String: String] = [:]
        
        env["SUPERSIDIAN_SUPERNOTE_ROOT"] = supernoteRoot
        env["SUPERSIDIAN_VERBOSE"] = verbose ? "1" : "0"
        
        if let logPath = logPath {
            env["SUPERSIDIAN_LOG_PATH"] = logPath
        }
        
        env["SUPERSIDIAN_SYNC_PROVIDER"] = syncProvider
        env["SUPERSIDIAN_NOTE_PROVIDER"] = noteProvider
        env["SUPERSIDIAN_TODO_PROVIDER"] = todoProvider
        env["SUPERSIDIAN_NOTIFICATION_PROVIDERS"] = notificationProviders.joined(separator: ",")
        
        if let token = todoistApiToken {
            env["SUPERSIDIAN_TODOIST_API_TOKEN"] = token
        }
        
        if let url = webhookUrl {
            env["SUPERSIDIAN_WEBHOOK_URL"] = url
        }
        
        if let topic = webhookTopic {
            env["SUPERSIDIAN_WEBHOOK_TOPIC"] = topic
        }
        
        env["SUPERSIDIAN_WEBHOOK_NOTIFICATIONS"] = webhookNotifications
        
        if let url = healthcheckUrl {
            env["SUPERSIDIAN_HEALTHCHECK_URL"] = url
        }
        
        if let tool = supernoteTool {
            env["SUPERSIDIAN_SUPERNOTE_TOOL"] = tool
        }
        
        return env
    }
    
    // MARK: - Conversion to config.json
    
    func toConfigJSON() -> ConfigJSON {
        ConfigJSON(bridges: bridges.map { $0.toJSON() })
    }
    
    struct ConfigJSON: Codable {
        let bridges: [BridgeJSON]
    }
    
    struct BridgeJSON: Codable {
        let name: String
        let enabled: Bool
        let supernoteSubdir: String
        let vaultPath: String
        let extraTags: [String]
        let aggressiveCleanup: Bool
        let spellcheck: Bool
        let exportImages: Bool
        let imagesSubdir: String
        
        enum CodingKeys: String, CodingKey {
            case name, enabled
            case supernoteSubdir = "supernote_subdir"
            case vaultPath = "vault_path"
            case extraTags = "extra_tags"
            case aggressiveCleanup = "aggressive_cleanup"
            case spellcheck
            case exportImages = "export_images"
            case imagesSubdir = "images_subdir"
        }
    }
}

