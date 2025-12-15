//
//  SyncView.swift
//  Supersidian
//
//  Integrated sync view for the main window.
//

import SwiftUI

struct SyncView: View {
    @StateObject private var coordinator = SyncCoordinator()
    @State private var showingLog = false

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
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
                // Idle state - ready to sync
                idleView
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    // MARK: - Idle State

    private var idleView: some View {
        VStack(alignment: .center, spacing: 24) {
            Spacer()

            Image(systemName: "arrow.triangle.2.circlepath")
                .font(.system(size: 64))
                .foregroundColor(.accentColor)

            Text("Ready to Sync")
                .font(.title)
                .bold()

            Text("Click the button below to start syncing your Supernote notes")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button {
                coordinator.startSync()
            } label: {
                Label("Sync Now", systemImage: "arrow.triangle.2.circlepath")
                    .font(.headline)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            Spacer()
        }
        .frame(maxWidth: .infinity)
        .padding(32)
    }

    // MARK: - Running State

    private var runningView: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                ProgressView()
                    .scaleEffect(0.8)

                Text(coordinator.currentStatus)
                    .font(.headline)

                Spacer()

                Button("Cancel") {
                    coordinator.cancel()
                }
                .buttonStyle(.borderless)
            }

            Divider()

            // Live log output
            VStack(alignment: .leading, spacing: 8) {
                Text("Log Output")
                    .font(.headline)

                ScrollViewReader { proxy in
                    ScrollView {
                        Text(coordinator.logOutput)
                            .font(.system(.caption, design: .monospaced))
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
            }

            Spacer()
        }
    }

    // MARK: - Success State

    private var successView: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(spacing: 16) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.green)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Sync Complete!")
                        .font(.title2)
                        .bold()

                    Text("Your notes have been successfully synced")
                        .font(.body)
                        .foregroundColor(.secondary)
                }
            }

            Divider()

            if let summary = coordinator.summary {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Summary")
                        .font(.headline)

                    GroupBox {
                        VStack(alignment: .leading, spacing: 8) {
                            summaryRow(label: "Notes converted:", value: "\(summary.converted)")
                            if summary.skipped > 0 {
                                summaryRow(label: "Notes skipped:", value: "\(summary.skipped)")
                            }
                            if summary.tasksSynced > 0 {
                                summaryRow(label: "Tasks synced:", value: "\(summary.tasksSynced)")
                            }
                        }
                        .padding(8)
                    }
                }
            }

            // Log output (collapsed)
            DisclosureGroup(isExpanded: $showingLog) {
                ScrollView {
                    Text(coordinator.logOutput)
                        .font(.system(.caption, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .frame(height: 200)
                .background(Color(NSColor.textBackgroundColor))
                .cornerRadius(6)
            } label: {
                Text("Log Output")
                    .font(.headline)
            }

            Spacer()

            Button {
                coordinator.startSync()
            } label: {
                Label("Sync Again", systemImage: "arrow.triangle.2.circlepath")
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Error State

    private func errorView(error: Error) -> some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(spacing: 16) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.red)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Sync Failed")
                        .font(.title2)
                        .bold()

                    Text(error.localizedDescription)
                        .font(.body)
                        .foregroundColor(.secondary)
                }
            }

            Divider()

            // Error details
            DisclosureGroup(isExpanded: $showingLog) {
                ScrollView {
                    Text(coordinator.logOutput)
                        .font(.system(.caption, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                }
                .frame(height: 200)
                .background(Color(NSColor.textBackgroundColor))
                .cornerRadius(6)
            } label: {
                Text("Error Details")
                    .font(.headline)
            }

            Spacer()

            Button {
                coordinator.startSync()
            } label: {
                Label("Try Again", systemImage: "arrow.triangle.2.circlepath")
            }
            .buttonStyle(.borderedProminent)
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
    SyncView()
}
