//
//  AdditionalPreferencesViews.swift
//  Supersidian
//
//  Tasks, Notifications, and Advanced preference tabs.
//

import SwiftUI

// MARK: - Tasks Preferences

struct TasksPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel
    
    var body: some View {
        Form {
            Picker("Todo Provider:", selection: Binding(
                get: { viewModel.editedConfig.todoProvider },
                set: { newValue in
                    var config = viewModel.editedConfig
                    config.todoProvider = newValue
                    viewModel.updateEdited(config)
                }
            )) {
                Text("None").tag("noop")
                Text("Todoist").tag("todoist")
            }
            .help(Text("Where to sync tasks extracted from notes"))
            
            if viewModel.editedConfig.todoProvider == "todoist" {
                Divider()
                
                SecureField("Todoist API Token:", text: Binding(
                    get: { viewModel.editedConfig.todoistApiToken ?? "" },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.todoistApiToken = newValue.isEmpty ? nil : newValue
                        viewModel.updateEdited(config)
                    }
                ))
                .help(Text("Get your token from: https://todoist.com/prefs/integrations"))
                
                Text("Your Todoist API token (kept secure in .env)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .formStyle(.grouped)
        .frame(minWidth: 600, minHeight: 300)
    }
}

// MARK: - Notifications Preferences

struct NotificationsPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel
    
    var body: some View {
        Form {
            Section("Notification Providers") {
                Toggle("Menubar App", isOn: Binding(
                    get: { viewModel.editedConfig.notificationProviders.contains("menubar") },
                    set: { enabled in
                        var config = viewModel.editedConfig
                        if enabled {
                            if !config.notificationProviders.contains("menubar") {
                                config.notificationProviders.append("menubar")
                            }
                        } else {
                            config.notificationProviders.removeAll { $0 == "menubar" }
                        }
                        viewModel.updateEdited(config)
                    }
                ))
                .help(Text("Update menubar app on sync completion"))
                
                Toggle("Webhook", isOn: Binding(
                    get: { viewModel.editedConfig.notificationProviders.contains("webhook") },
                    set: { enabled in
                        var config = viewModel.editedConfig
                        if enabled {
                            if !config.notificationProviders.contains("webhook") {
                                config.notificationProviders.append("webhook")
                            }
                        } else {
                            config.notificationProviders.removeAll { $0 == "webhook" }
                        }
                        viewModel.updateEdited(config)
                    }
                ))
                .help(Text("Send HTTP webhooks on sync events"))
            }
            
            if viewModel.editedConfig.notificationProviders.contains("webhook") {
                Section("Webhook Settings") {
                    TextField("Webhook URL:", text: Binding(
                        get: { viewModel.editedConfig.webhookUrl ?? "" },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.webhookUrl = newValue.isEmpty ? nil : newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    .help(Text("e.g., https://ntfy.sh/your-topic"))
                    
                    TextField("Topic (optional):", text: Binding(
                        get: { viewModel.editedConfig.webhookTopic ?? "" },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.webhookTopic = newValue.isEmpty ? nil : newValue
                            viewModel.updateEdited(config)
                        }
                    ))
                    
                    Picker("When to Notify:", selection: Binding(
                        get: { viewModel.editedConfig.webhookNotifications },
                        set: { newValue in
                            var config = viewModel.editedConfig
                            config.webhookNotifications = newValue
                            viewModel.updateEdited(config)
                        }
                    )) {
                        Text("All Syncs").tag("all")
                        Text("Errors Only").tag("errors")
                        Text("None").tag("none")
                    }
                }
            }
        }
        .formStyle(.grouped)
        .frame(minWidth: 600, minHeight: 300)
    }
}

// MARK: - Advanced Preferences

struct AdvancedPreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel
    
    var body: some View {
        Form {
            Section("Providers") {
                Picker("Sync Provider:", selection: Binding(
                    get: { viewModel.editedConfig.syncProvider },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.syncProvider = newValue
                        viewModel.updateEdited(config)
                    }
                )) {
                    Text("Dropbox").tag("dropbox")
                    Text("Local").tag("local")
                }
                .help(Text("How Supersidian accesses your Supernote files"))
                
                Picker("Note Provider:", selection: Binding(
                    get: { viewModel.editedConfig.noteProvider },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.noteProvider = newValue
                        viewModel.updateEdited(config)
                    }
                )) {
                    Text("Obsidian").tag("obsidian")
                    Text("Markdown").tag("markdown")
                }
                .help(Text("How notes are formatted and written"))
            }
            
            Section("Healthcheck") {
                TextField("Healthcheck URL (optional):", text: Binding(
                    get: { viewModel.editedConfig.healthcheckUrl ?? "" },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.healthcheckUrl = newValue.isEmpty ? nil : newValue
                        viewModel.updateEdited(config)
                    }
                ))
                .help(Text("e.g., https://hc-ping.com/your-uuid"))
                
                Text("For monitoring with healthchecks.io or similar")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Section("Advanced") {
                TextField("Supernote Tool Path (optional):", text: Binding(
                    get: { viewModel.editedConfig.supernoteTool ?? "" },
                    set: { newValue in
                        var config = viewModel.editedConfig
                        config.supernoteTool = newValue.isEmpty ? nil : newValue
                        viewModel.updateEdited(config)
                    }
                ))
                .help(Text("Custom path to supernote-tool binary"))
                
                Text("Leave empty to use default (supernote-tool in PATH)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .formStyle(.grouped)
        .frame(minWidth: 600, minHeight: 300)
    }
}
