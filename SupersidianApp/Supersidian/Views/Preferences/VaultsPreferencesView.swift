//
//  VaultsPreferencesView.swift
//  Supersidian
//
//  Vaults/Bridges preferences with simple, clean layout.
//

import SwiftUI

struct VaultsPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel
    @State private var editingBridge: BridgeConfig?

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Vaults list
            if viewModel.editedConfig.bridges.isEmpty {
                // Empty state
                VStack(spacing: 16) {
                    Image(systemName: "folder.badge.plus")
                        .font(.system(size: 48))
                        .foregroundStyle(.secondary)

                    Text("No Vaults Configured")
                        .font(.title3)
                        .bold()

                    Text("Add a vault to start syncing your Supernote notes to Obsidian")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)

                    Button {
                        addBridge()
                    } label: {
                        Label("Add Vault", systemImage: "plus.circle.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                }
                .frame(maxWidth: .infinity)
                .padding(60)
            } else {
                // Vaults list header
                HStack {
                    Text("Your Vaults")
                        .font(.headline)

                    Spacer()

                    Button {
                        addBridge()
                    } label: {
                        Label("Add Vault", systemImage: "plus")
                    }
                }
                .padding(.bottom, 8)

                // Vaults
                VStack(spacing: 12) {
                    ForEach(viewModel.editedConfig.bridges) { bridge in
                        vaultRow(bridge)
                    }
                }
            }
        }
        .sheet(item: $editingBridge) { bridge in
            VaultEditorSheet(
                bridge: bridge,
                onSave: { updated in
                    if viewModel.editedConfig.bridges.contains(where: { $0.id == updated.id }) {
                        viewModel.updateBridge(updated)
                    } else {
                        viewModel.addBridge(updated)
                    }
                    editingBridge = nil
                },
                onCancel: {
                    editingBridge = nil
                }
            )
        }
    }

    // MARK: - Vault Row

    private func vaultRow(_ bridge: BridgeConfig) -> some View {
        HStack(spacing: 16) {
            // Status indicator
            Circle()
                .fill(bridge.enabled ? Color.green : Color.gray.opacity(0.3))
                .frame(width: 12, height: 12)

            // Vault info
            VStack(alignment: .leading, spacing: 4) {
                Text(bridge.name)
                    .font(.headline)

                HStack(spacing: 6) {
                    Text(bridge.supernoteSubdir)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text("→")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)

                    Text(bridge.vaultPath)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
            }

            Spacer()

            // Actions
            HStack(spacing: 8) {
                Button {
                    editingBridge = bridge
                } label: {
                    Label("Edit", systemImage: "pencil")
                        .labelStyle(.iconOnly)
                }
                .buttonStyle(.borderless)
                .help(Text("Edit vault"))

                Button(role: .destructive) {
                    viewModel.deleteBridge(bridge)
                } label: {
                    Label("Delete", systemImage: "trash")
                        .labelStyle(.iconOnly)
                }
                .buttonStyle(.borderless)
                .help(Text("Delete vault"))
            }
        }
        .padding(16)
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(8)
    }

    // MARK: - Actions

    private func addBridge() {
        editingBridge = BridgeConfig(
            name: "",
            enabled: true,
            supernoteSubdir: "",
            supernotePath: "",
            vaultPath: "",
            defaultTags: [],
            extraTags: [],
            aggressiveCleanup: false,
            spellcheck: false,
            exportImages: true,
            imagesSubdir: "Supersidian/Assets"
        )
    }
}

// MARK: - Vault Editor Sheet

struct VaultEditorSheet: View {
    @State private var editedBridge: BridgeConfig
    let onSave: (BridgeConfig) -> Void
    let onCancel: () -> Void

    init(bridge: BridgeConfig, onSave: @escaping (BridgeConfig) -> Void, onCancel: @escaping () -> Void) {
        _editedBridge = State(initialValue: bridge)
        self.onSave = onSave
        self.onCancel = onCancel
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text(editedBridge.name.isEmpty ? "New Vault" : "Edit \(editedBridge.name)")
                    .font(.title2)
                    .bold()

                Spacer()
            }
            .padding(24)
            .background(Color(nsColor: .controlBackgroundColor))

            Divider()

            // Form
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // Basic settings
                    GroupBox {
                        VStack(alignment: .leading, spacing: 16) {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Vault Name")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                TextField("", text: $editedBridge.name, prompt: Text("e.g., Personal, Work"))
                                    .textFieldStyle(.roundedBorder)

                                Text("A unique name to identify this vault")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            Divider()

                            HStack {
                                Text("Enabled")
                                    .font(.body)

                                Spacer()

                                Toggle("", isOn: $editedBridge.enabled)
                                    .toggleStyle(.switch)
                                    .labelsHidden()
                                    .help(Text("Disable to temporarily stop syncing this vault"))
                            }
                        }
                    } label: {
                        Label("Basic Settings", systemImage: "gear")
                            .font(.body)
                    }

                    // Paths
                    GroupBox {
                        VStack(alignment: .leading, spacing: 16) {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Supernote Subfolder")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                TextField("", text: $editedBridge.supernoteSubdir, prompt: Text("Note/Personal"))
                                    .textFieldStyle(.roundedBorder)

                                Text("The folder within your Supernote sync directory")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            Divider()

                            VStack(alignment: .leading, spacing: 8) {
                                Text("Obsidian Vault Path")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                HStack {
                                    TextField("", text: $editedBridge.vaultPath, prompt: Text("/path/to/vault"))
                                        .textFieldStyle(.roundedBorder)
                                        .disabled(true)

                                    Button("Choose...") {
                                        chooseVaultPath()
                                    }
                                }

                                Text("The location of your Obsidian vault")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    } label: {
                        Label("Paths", systemImage: "folder")
                            .font(.body)
                    }

                    // Options
                    GroupBox {
                        VStack(alignment: .leading, spacing: 16) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Aggressive Cleanup")
                                        .font(.body)

                                    Spacer()

                                    Toggle("", isOn: $editedBridge.aggressiveCleanup)
                                        .toggleStyle(.switch)
                                        .labelsHidden()
                                }

                                Text("More aggressive text cleanup and line unwrapping")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            Divider()

                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Export Images")
                                        .font(.body)

                                    Spacer()

                                    Toggle("", isOn: $editedBridge.exportImages)
                                        .toggleStyle(.switch)
                                        .labelsHidden()
                                }

                                Text("Export note pages as PNG images")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)

                                if editedBridge.exportImages {
                                    TextField("Images Subfolder:", text: $editedBridge.imagesSubdir)
                                        .textFieldStyle(.roundedBorder)
                                }
                            }

                            Divider()

                            VStack(alignment: .leading, spacing: 8) {
                                Text("Extra Tags (comma-separated)")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                TextField("", text: Binding(
                                    get: { editedBridge.extraTags.joined(separator: ", ") },
                                    set: { newValue in
                                        editedBridge.extraTags = newValue.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
                                    }
                                ), prompt: Text("work, important"))
                                .textFieldStyle(.roundedBorder)

                                Text("Additional tags to apply to all notes from this vault")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    } label: {
                        Label("Options", systemImage: "slider.horizontal.3")
                            .font(.body)
                    }
                }
                .padding(24)
            }

            Divider()

            // Footer buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    onCancel()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button("Save") {
                    onSave(editedBridge)
                }
                .keyboardShortcut(.defaultAction)
                .buttonStyle(.borderedProminent)
                .disabled(editedBridge.name.isEmpty || editedBridge.supernoteSubdir.isEmpty || editedBridge.vaultPath.isEmpty)
            }
            .padding(24)
            .background(Color(nsColor: .controlBackgroundColor))
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .frame(width: 550, height: 700)
    }

    private func chooseVaultPath() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Select Vault"
        panel.message = "Choose your Obsidian vault or notes folder"

        if panel.runModal() == .OK, let url = panel.url {
            editedBridge.vaultPath = url.path
        }
    }
}
