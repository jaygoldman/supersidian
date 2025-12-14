//
//  SyncProgressWindow.swift
//  Supersidian
//
//  SwiftUI window showing live sync progress.
//

import SwiftUI

struct SyncProgressWindow: View {
    @StateObject private var coordinator = SyncCoordinator()
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack(spacing: 20) {
            if coordinator.isRunning {
                // Running state
                runningView
            } else if let error = coordinator.error {
                // Error state
                errorView(error: error)
            } else if coordinator.summary != nil {
                // Success state
                successView
            } else {
                // Initial state (shouldn't normally see this)
                Text("Preparing to sync...")
                    .font(.headline)
            }
        }
        .padding(30)
        .frame(width: 600, height: 500)
        .onAppear {
            coordinator.startSync()
        }
    }
    
    // MARK: - Running State
    
    private var runningView: some View {
        VStack(spacing: 20) {
            ProgressView()
                .scaleEffect(1.5)
                .padding()
            
            Text(coordinator.currentStatus)
                .font(.headline)
            
            // Live log output
            ScrollViewReader { proxy in
                ScrollView {
                    Text(coordinator.logOutput)
                        .font(.system(.body, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color(NSColor.textBackgroundColor))
                        .cornerRadius(8)
                        .id("logOutput")
                }
                .frame(height: 300)
                .onChange(of: coordinator.logOutput) { _ in
                    // Auto-scroll to bottom
                    withAnimation {
                        proxy.scrollTo("logOutput", anchor: .bottom)
                    }
                }
            }
            
            Spacer()
            
            // Cancel button
            HStack {
                Spacer()
                Button("Cancel") {
                    coordinator.cancel()
                }
                .keyboardShortcut(.cancelAction)
            }
        }
    }
    
    // MARK: - Success State
    
    private var successView: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 64))
                .foregroundColor(.green)
            
            Text("Sync Complete!")
                .font(.title2)
                .bold()
            
            if let summary = coordinator.summary {
                VStack(alignment: .leading, spacing: 8) {
                    summaryRow(label: "Notes converted:", value: "\(summary.converted)")
                    summaryRow(label: "Notes skipped:", value: "\(summary.skipped)")
                    if summary.tasksSynced > 0 {
                        summaryRow(label: "Tasks synced:", value: "\(summary.tasksSynced)")
                    }
                }
                .font(.body)
                .padding()
                .background(Color(NSColor.controlBackgroundColor))
                .cornerRadius(8)
            }
            
            // Log output (collapsed)
            DisclosureGroup("View Log") {
                ScrollView {
                    Text(coordinator.logOutput)
                        .font(.system(.caption, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .frame(height: 150)
                .background(Color(NSColor.textBackgroundColor))
                .cornerRadius(6)
            }
            
            Spacer()
            
            // Close button
            HStack {
                Spacer()
                Button("Close") {
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
    }
    
    // MARK: - Error State
    
    private func errorView(error: Error) -> some View {
        VStack(spacing: 20) {
            Image(systemName: "xmark.circle.fill")
                .font(.system(size: 64))
                .foregroundColor(.red)
            
            Text("Sync Failed")
                .font(.title2)
                .bold()
            
            Text(error.localizedDescription)
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            
            // Log output
            DisclosureGroup("View Error Details") {
                ScrollView {
                    Text(coordinator.logOutput)
                        .font(.system(.caption, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .frame(height: 150)
                .background(Color(NSColor.textBackgroundColor))
                .cornerRadius(6)
            }
            
            Spacer()
            
            // Close button
            HStack {
                Spacer()
                Button("Close") {
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
    }
    
    // MARK: - Helper Views
    
    private func summaryRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .bold()
        }
    }
}

// MARK: - Preview

#Preview {
    SyncProgressWindow()
}
