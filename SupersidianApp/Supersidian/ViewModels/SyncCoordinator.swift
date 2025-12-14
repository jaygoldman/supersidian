//
//  SyncCoordinator.swift
//  Supersidian
//
//  Manages sync state and coordinates live output streaming.
//

import Foundation
import Combine

@MainActor
class SyncCoordinator: ObservableObject {
    @Published var isRunning = false
    @Published var currentStatus = "Initializing..."
    @Published var logOutput = ""
    @Published var error: Error?
    @Published var summary: SyncSummary?
    
    private let supersidianRunner = SupersidianRunner.shared
    private var cancellationTask: Task<Void, Never>?
    
    // MARK: - Sync Control
    
    func startSync() {
        guard !isRunning else {
            NSLog("SyncCoordinator: Sync already running")
            return
        }
        
        // Reset state
        isRunning = true
        currentStatus = "Starting sync..."
        logOutput = ""
        error = nil
        summary = nil
        
        cancellationTask = Task {
            do {
                // Run sync with streaming output
                try await supersidianRunner.runSyncWithOutput { [weak self] line in
                    await MainActor.run {
                        self?.appendLog(line)
                    }
                }
                
                // Parse summary from output
                let parsedSummary = parseSyncSummary(from: logOutput)
                
                await MainActor.run {
                    self.isRunning = false
                    self.currentStatus = "Sync complete!"
                    self.summary = parsedSummary
                }
                
                NSLog("SyncCoordinator: Sync completed successfully")
                
            } catch is CancellationError {
                await MainActor.run {
                    self.isRunning = false
                    self.currentStatus = "Sync cancelled"
                }
                NSLog("SyncCoordinator: Sync cancelled by user")
                
            } catch {
                await MainActor.run {
                    self.isRunning = false
                    self.currentStatus = "Sync failed"
                    self.error = error
                }
                NSLog("SyncCoordinator: Sync failed: \(error.localizedDescription)")
            }
        }
    }
    
    func cancel() {
        guard isRunning else { return }
        
        cancellationTask?.cancel()
        cancellationTask = nil
        
        currentStatus = "Cancelling..."
        NSLog("SyncCoordinator: Cancellation requested")
    }
    
    // MARK: - Private Helpers
    
    private func appendLog(_ line: String) {
        logOutput += line + "\n"
        
        // Update status based on log content
        if line.contains("Processing bridge") {
            currentStatus = "Processing vaults..."
        } else if line.contains("Converted") {
            currentStatus = "Converting notes..."
        } else if line.contains("Syncing tasks") {
            currentStatus = "Syncing tasks..."
        } else if line.contains("Complete") || line.contains("Finished") {
            currentStatus = "Finalizing..."
        }
    }
    
    private func parseSyncSummary(from output: String) -> SyncSummary {
        var converted = 0
        var skipped = 0
        var tasksSynced = 0
        
        // Simple regex-free parsing
        let lines = output.components(separatedBy: "\n")
        
        for line in lines {
            if line.contains("Converted:") {
                if let number = extractNumber(from: line) {
                    converted += number
                }
            } else if line.contains("Skipped:") || line.contains("up to date") {
                if let number = extractNumber(from: line) {
                    skipped += number
                }
            } else if line.contains("task") && (line.contains("synced") || line.contains("created")) {
                if let number = extractNumber(from: line) {
                    tasksSynced += number
                }
            }
        }
        
        return SyncSummary(
            converted: converted,
            skipped: skipped,
            tasksSynced: tasksSynced
        )
    }
    
    private func extractNumber(from string: String) -> Int? {
        let components = string.components(separatedBy: CharacterSet.decimalDigits.inverted)
        for component in components {
            if let number = Int(component), number > 0 {
                return number
            }
        }
        return nil
    }
}

// MARK: - Supporting Types

struct SyncSummary {
    let converted: Int
    let skipped: Int
    let tasksSynced: Int
}
