//
//  VaultsPreferencesView.swift
//  Supersidian
//
//  Vaults/Bridges preferences tab with add/edit/delete.
//

import SwiftUI

struct VaultsPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel
    @State private var selectedBridge: BridgeConfig?
    @State private var showingEditor = false
    @State private var editingBridge: BridgeConfig?
    
    var body: some View {
        HStack(spacing: 0) {
            // List of bridges
            List(selection: $selectedBridge) {
                ForEach(viewModel.editedConfig.bridges) { bridge in
                    HStack {
                        Image(systemName: bridge.enabled ? "checkmark.circle.fill" : "circle")
                            .foregroundColor(bridge.enabled ? .green : .secondary)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text(bridge.name)
                                .font(.headline)
                            Text(bridge.vaultPath)
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                        }
                    }
                    .tag(bridge)
                }
                .onMove { source, destination in
                    viewModel.moveBridges(from: source, to: destination)
                }
            }
            .frame(width: 250)
            .listStyle(.sidebar)
            
            // Detail view
            if let bridge = selectedBridge {
                bridgeDetailView(bridge)
            } else {
                VStack {
                    Text("Select a vault")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .toolbar {
            ToolbarItem(placement: .automatic) {
                HStack {
                    Button(action: addBridge) {
                        Label("Add", systemImage: "plus")
                    }
                    
                    Button(action: removeBridge) {
                        Label("Remove", systemImage: "minus")
                    }
                    .disabled(selectedBridge == nil)
                }
            }
        }
        .sheet(isPresented: $showingEditor) {
            if let bridge = editingBridge {
                VaultEditorSheet(
                    bridge: bridge,
                    onSave: { updated in
                        if viewModel.editedConfig.bridges.contains(where: { $0.id == updated.id }) {
                            viewModel.updateBridge(updated)
                        } else {
                            viewModel.addBridge(updated)
                        }
                        showingEditor = false
                    },
                    onCancel: {
                        showingEditor = false
                    }
                )
            }
        }
        .frame(minWidth: 700, minHeight: 400)
    }
    
    // MARK: - Detail View
    
    private func bridgeDetailView(_ bridge: BridgeConfig) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Text(bridge.name)
                    .font(.title2)
                    .bold()
                
                Spacer()
                
                Button("Edit...") {
                    editingBridge = bridge
                    showingEditor = true
                }
            }
            
            Form {
                LabeledContent("Enabled") {
                    Text(bridge.enabled ? "Yes" : "No")
                }
                
                LabeledContent("Supernote Subfolder") {
                    Text(bridge.supernoteSubdir)
                }
                
                LabeledContent("Vault Path") {
                    Text(bridge.vaultPath)
                        .font(.caption)
                }
                
                if !bridge.extraTags.isEmpty {
                    LabeledContent("Extra Tags") {
                        Text(bridge.extraTags.joined(separator: ", "))
                    }
                }
                
                LabeledContent("Aggressive Cleanup") {
                    Text(bridge.aggressiveCleanup ? "Yes" : "No")
                }
                
                LabeledContent("Export Images") {
                    Text(bridge.exportImages ? "Yes" : "No")
                }
            }
            .formStyle(.grouped)
            
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
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
        showingEditor = true
    }
    
    private func removeBridge() {
        guard let bridge = selectedBridge else { return }
        viewModel.deleteBridge(bridge)
        selectedBridge = nil
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
        VStack(spacing: 20) {
            Text(editedBridge.name.isEmpty ? "New Vault" : "Edit Vault")
                .font(.title2)
                .bold()
            
            Form {
                TextField("Name:", text: $editedBridge.name)
                    .help("Unique name for this vault")
                
                Toggle("Enabled", isOn: $editedBridge.enabled)
                
                TextField("Supernote Subfolder:", text: $editedBridge.supernoteSubdir)
                    .help("Folder within Supernote/Note (e.g., 'Personal', 'Work')")
                
                HStack {
                    TextField("Vault Path:", text: $editedBridge.vaultPath)
                    Button("Choose...") {
                        chooseVaultPath()
                    }
                }
                .help("Path to your Obsidian vault or notes folder")
                
                TextField("Extra Tags (comma-separated):", text: Binding(
                    get: { editedBridge.extraTags.joined(separator: ", ") },
                    set: { newValue in
                        editedBridge.extraTags = newValue.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }
                    }
                ))
                
                Toggle("Aggressive Cleanup", isOn: $editedBridge.aggressiveCleanup)
                    .help("More aggressive line unwrapping")
                
                Toggle("Export Images", isOn: $editedBridge.exportImages)
                    .help("Export note pages as PNG images")
                
                if editedBridge.exportImages {
                    TextField("Images Subfolder:", text: $editedBridge.imagesSubdir)
                        .help("Where to store exported images")
                }
            }
            .formStyle(.grouped)
            
            HStack {
                Button("Cancel") {
                    onCancel()
                }
                .keyboardShortcut(.cancelAction)
                
                Spacer()
                
                Button("Save") {
                    onSave(editedBridge)
                }
                .keyboardShortcut(.defaultAction)
                .disabled(editedBridge.name.isEmpty || editedBridge.supernoteSubdir.isEmpty || editedBridge.vaultPath.isEmpty)
            }
        }
        .padding()
        .frame(width: 500, height: 500)
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
