//
//  BridgeStatus.swift
//  Supersidian
//
//  Model representing the current status of a bridge/vault.
//

import Foundation

struct BridgeStatus: Codable, Identifiable {
    let bridgeName: String
    let lastSyncTime: String?
    let status: String  // "success", "warning", "error", "syncing"
    let notesFound: Int
    let converted: Int
    let skipped: Int
    let noText: Int
    let tasksTotal: Int
    let tasksOpen: Int
    let tasksCompleted: Int
    let errorMessage: String?
    let toolMissing: Int
    let toolFailed: Int
    let supernoteMissing: Bool
    let vaultMissing: Bool

    // Computed properties
    var id: String { bridgeName }
    var vaultName: String { bridgeName.capitalized }

    var hasErrors: Bool {
        toolMissing > 0 || toolFailed > 0 || supernoteMissing || vaultMissing
    }

    var hasWarnings: Bool {
        noText > 0 && !hasErrors
    }

    enum CodingKeys: String, CodingKey {
        case bridgeName = "bridge_name"
        case lastSyncTime = "last_sync_time"
        case status
        case notesFound = "notes_found"
        case converted
        case skipped
        case noText = "no_text"
        case tasksTotal = "tasks_total"
        case tasksOpen = "tasks_open"
        case tasksCompleted = "tasks_completed"
        case errorMessage = "error_message"
        case toolMissing = "tool_missing"
        case toolFailed = "tool_failed"
        case supernoteMissing = "supernote_missing"
        case vaultMissing = "vault_missing"
    }
}
