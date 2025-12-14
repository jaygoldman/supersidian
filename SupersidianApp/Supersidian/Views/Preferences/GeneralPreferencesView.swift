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
        Form {
            Section {
                HStack {
                    Text("Supernote Root:")
                        .frame(width: 140, alignment: .trailing)
                    
                    TextField("Path to Supernote/Note folder", text: Binding(
                        get: { viewModel.editedConfig.supernoteRoot },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.supernoteRoot = newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    
                    Button("Choose...") {
                        chooseSupernoteRoot()
                    }
                }
                
                HStack {
                    Text("")
                        .frame(width: 140)
                    Text("Path to your Supernote/Note folder (usually synced via Dropbox)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            
            Section {
                Toggle(isOn: Binding(
                    get: { viewModel.editedConfig.verbose },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.verbose = newValue
                        viewModel.updateEdited(config)
                    }
                )) {
                    HStack {
                        Text("Verbose Logging:")
                            .frame(width: 140, alignment: .trailing)
                        Text("Show detailed output in logs")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                HStack {
                    Text("Log Path:")
                        .frame(width: 140, alignment: .trailing)
                    
                    TextField("Optional custom log path", text: Binding(
                        get: { viewModel.editedConfig.logPath ?? "" },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.logPath = newValue.isEmpty ? nil : newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    
                    Button("Choose...") {
                        chooseLogPath()
                    }
                }
                
                HStack {
                    Text("")
                        .frame(width: 140)
                    Text("Leave empty to use default location")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .formStyle(.grouped)
        .frame(minWidth: 600, minHeight: 300)
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
