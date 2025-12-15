//
//  GeneralPreferencesView.swift
//  Supersidian
//
//  General preferences tab.
//

import SwiftUI

struct GeneralPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            // Supernote Root
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .center, spacing: 12) {
                    Text("Supernote Root")
                        .fontWeight(.regular)

                    Spacer()

                    Button("Choose...") {
                        chooseSupernoteRoot()
                    }
                }

                Text(viewModel.editedConfig.supernoteRoot.isEmpty ?
                     "/Users/jaygoldman/Library/CloudStorage/Dropbox/Supernote/Note folder" :
                     viewModel.editedConfig.supernoteRoot)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)

                Text("Path to your Supernote/Note folder (usually synced via Dropbox)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)

            Divider()

            // Verbose Logging
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Verbose Logging")
                        .fontWeight(.regular)

                    Spacer()

                    Toggle("", isOn: Binding(
                        get: { viewModel.editedConfig.verbose },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.verbose = newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    .toggleStyle(.switch)
                    .labelsHidden()
                }

                Text("Show detailed output in logs")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)

            Divider()

            // Log Path
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .center, spacing: 12) {
                    Text("Log Path")
                        .fontWeight(.regular)

                    Spacer()

                    Button("Choose...") {
                        chooseLogPath()
                    }
                }

                if let logPath = viewModel.editedConfig.logPath, !logPath.isEmpty {
                    Text(logPath)
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                } else {
                    Text("/Users/jaygoldman/Dev/supersidian/supersidian.log")
                        .font(.body)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }

                Text("Leave empty to use default location")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)

            Spacer()
        }
    }

    // MARK: - File Pickers

    private func chooseSupernoteRoot() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Select Supernote Root"
        panel.message = "Choose the Supernote/Note folder (e.g., ~/Dropbox/Supernote/Note)"

        if panel.runModal() == .OK, let url = panel.url {
            var config = viewModel.editedConfig
            config.supernoteRoot = url.path
            viewModel.updateEdited(config)
        }
    }

    private func chooseLogPath() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Select Log Directory"
        panel.message = "Choose where to store log files"

        if panel.runModal() == .OK, let url = panel.url {
            var config = viewModel.editedConfig
            config.logPath = url.appendingPathComponent("supersidian.log").path
            viewModel.updateEdited(config)
        }
    }
}
