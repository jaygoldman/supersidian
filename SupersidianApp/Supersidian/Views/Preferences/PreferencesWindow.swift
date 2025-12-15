//
//  PreferencesWindow.swift
//  Supersidian
//
//  Main preferences window with System Settings-style sidebar.
//

import SwiftUI

enum PreferenceSection: String, CaseIterable, Identifiable {
    case general = "General"
    case vaults = "Vaults"
    case tasks = "Tasks"
    case healthcheck = "Healthcheck"
    case notifications = "Notifications"
    case advanced = "Advanced"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .general: return "gear"
        case .vaults: return "folder.badge.gearshape"
        case .tasks: return "checkmark.circle"
        case .healthcheck: return "heart.text.square"
        case .notifications: return "bell"
        case .advanced: return "slider.horizontal.3"
        }
    }

    var description: String {
        switch self {
        case .general:
            return "Configure core settings like Supernote sync folder, logging, and preferences"
        case .vaults:
            return "Manage your Obsidian vaults and note syncing bridges"
        case .tasks:
            return "Configure task synchronization with Todoist or other providers"
        case .healthcheck:
            return "Monitor sync health with automated ping notifications"
        case .notifications:
            return "Set up webhooks and menubar notifications"
        case .advanced:
            return "Advanced options for power users"
        }
    }
}

struct PreferencesWindow: View {
    @StateObject private var viewModel = PreferencesViewModel()
    @State private var selectedSection: PreferenceSection = .general

    var body: some View {
        NavigationSplitView(columnVisibility: .constant(.all)) {
            // Sidebar
            List(PreferenceSection.allCases, selection: $selectedSection) { section in
                Label(section.rawValue, systemImage: section.icon)
                    .tag(section)
                    .listRowInsets(EdgeInsets(top: 4, leading: 12, bottom: 4, trailing: 12))
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 250)
        } detail: {
            // Detail content
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // Section header
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 12) {
                            Image(systemName: selectedSection.icon)
                                .font(.title)
                                .foregroundStyle(.secondary)

                            Text(selectedSection.rawValue)
                                .font(.largeTitle)
                                .bold()
                        }

                        Text(selectedSection.description)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.bottom, 8)

                    Divider()

                    // Section content
                    sectionContent(for: selectedSection)
                }
                .padding(32)
            }
            .frame(minWidth: 600)
            .background(Color(nsColor: .windowBackgroundColor))
            .toolbar {
                ToolbarItemGroup(placement: .automatic) {
                    // Validation error indicator
                    if let error = viewModel.validationError {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.red)
                            Text(error)
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                    }

                    Spacer()

                    // Action buttons group
                    HStack(spacing: 12) {
                        // Unsaved indicator
                        if viewModel.hasChanges {
                            Text("Unsaved")
                                .font(.caption)
                                .foregroundColor(.orange)
                                .padding(.leading, 12)
                        }

                        Button("Revert") {
                            viewModel.revert()
                        }
                        .disabled(!viewModel.hasChanges)

                        Button("Apply") {
                            Task {
                                do {
                                    try await viewModel.apply()
                                } catch {
                                    // Error shown in validationError
                                }
                            }
                        }
                        .disabled(!viewModel.hasChanges || viewModel.isSaving)
                        .keyboardShortcut(.defaultAction)

                        if viewModel.isSaving {
                            ProgressView()
                                .scaleEffect(0.6)
                        }
                    }
                }
            }
        }
        .navigationSplitViewStyle(.prominentDetail)
        .frame(minWidth: 900, minHeight: 650)
        .onAppear {
            viewModel.load()
        }
    }

    // MARK: - Section Content

    @ViewBuilder
    private func sectionContent(for section: PreferenceSection) -> some View {
        switch section {
        case .general:
            GeneralPreferencesView(viewModel: viewModel)
        case .vaults:
            VaultsPreferencesView(viewModel: viewModel)
        case .tasks:
            TasksPreferencesView(viewModel: viewModel)
        case .healthcheck:
            HealthcheckPreferencesView(viewModel: viewModel)
        case .notifications:
            NotificationsPreferencesView(viewModel: viewModel)
        case .advanced:
            AdvancedPreferencesView(viewModel: viewModel)
        }
    }
}

// MARK: - Preview

#Preview {
    PreferencesWindow()
        .frame(width: 900, height: 650)
}
