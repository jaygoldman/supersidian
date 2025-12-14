//
//  DatabaseManager.swift
//  Supersidian
//
//  Manages read-only access to the Supersidian SQLite database.
//

import Foundation
import SQLite

class DatabaseManager {
    static let shared = DatabaseManager()

    private var db: Connection?
    private let dbPath: String

    // Table references
    private let bridgeStatusTable = Table("bridge_status")
    private let syncHistoryTable = Table("sync_history")
    private let tasksTable = Table("tasks")

    // Column definitions for bridge_status
    private let bridgeName = Expression<String>("bridge_name")
    private let lastSyncTime = Expression<String?>("last_sync_time")
    private let status = Expression<String>("status")
    private let notesFound = Expression<Int>("notes_found")
    private let converted = Expression<Int>("converted")
    private let skipped = Expression<Int>("skipped")
    private let noText = Expression<Int>("no_text")
    private let tasksTotal = Expression<Int>("tasks_total")
    private let tasksOpen = Expression<Int>("tasks_open")
    private let tasksCompleted = Expression<Int>("tasks_completed")
    private let errorMessage = Expression<String?>("error_message")
    private let toolMissing = Expression<Int>("tool_missing")
    private let toolFailed = Expression<Int>("tool_failed")
    private let supernoteMissing = Expression<Int>("supernote_missing")
    private let vaultMissing = Expression<Int>("vault_missing")

    private init() {
        // Database is at ~/.supersidian.db
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        dbPath = homeDir.appendingPathComponent(".supersidian.db").path

        openDatabase()
    }

    private func openDatabase() {
        do {
            // Open in read-only mode (Python writes, Swift reads)
            db = try Connection(dbPath, readonly: true)
            NSLog("DatabaseManager: Connected to \(dbPath)")
        } catch {
            NSLog("DatabaseManager: Failed to open database: \(error)")
        }
    }

    func fetchBridgeStatuses() -> [BridgeStatus] {
        guard let db = db else {
            NSLog("DatabaseManager: Database not connected")
            return []
        }

        var statuses: [BridgeStatus] = []

        do {
            for row in try db.prepare(bridgeStatusTable) {
                let status = BridgeStatus(
                    bridgeName: row[bridgeName],
                    lastSyncTime: row[lastSyncTime],
                    status: row[status],
                    notesFound: row[notesFound],
                    converted: row[converted],
                    skipped: row[skipped],
                    noText: row[noText],
                    tasksTotal: row[tasksTotal],
                    tasksOpen: row[tasksOpen],
                    tasksCompleted: row[tasksCompleted],
                    errorMessage: row[errorMessage],
                    toolMissing: row[toolMissing],
                    toolFailed: row[toolFailed],
                    supernoteMissing: row[supernoteMissing] != 0,
                    vaultMissing: row[vaultMissing] != 0
                )
                statuses.append(status)
            }
        } catch {
            NSLog("DatabaseManager: Failed to fetch bridge statuses: \(error)")
        }

        return statuses
    }

    func fetchSyncHistory(for bridgeName: String, limit: Int = 30) -> [SyncHistoryRecord] {
        guard let db = db else {
            NSLog("DatabaseManager: Database not connected")
            return []
        }

        var history: [SyncHistoryRecord] = []

        // Column definitions for sync_history
        let id = Expression<Int>("id")
        let bridgeNameCol = Expression<String>("bridge_name")
        let syncTime = Expression<String>("sync_time")
        let durationSeconds = Expression<Double?>("duration_seconds")
        let notesConverted = Expression<Int>("notes_converted")
        let notesSkipped = Expression<Int>("notes_skipped")
        let tasksSynced = Expression<Int>("tasks_synced")
        let success = Expression<Int>("success")

        do {
            let query = syncHistoryTable
                .filter(bridgeNameCol == bridgeName)
                .order(syncTime.desc)
                .limit(limit)

            for row in try db.prepare(query) {
                let record = SyncHistoryRecord(
                    id: row[id],
                    bridgeName: row[bridgeNameCol],
                    syncTime: row[syncTime],
                    durationSeconds: row[durationSeconds],
                    notesConverted: row[notesConverted],
                    notesSkipped: row[notesSkipped],
                    tasksSynced: row[tasksSynced],
                    success: row[success] != 0
                )
                history.append(record)
            }
        } catch {
            NSLog("DatabaseManager: Failed to fetch sync history: \(error)")
        }

        return history
    }

    func reconnect() {
        db = nil
        openDatabase()
    }
}

// MARK: - Supporting Models

struct SyncHistoryRecord: Identifiable {
    let id: Int
    let bridgeName: String
    let syncTime: String
    let durationSeconds: Double?
    let notesConverted: Int
    let notesSkipped: Int
    let tasksSynced: Int
    let success: Bool
}
