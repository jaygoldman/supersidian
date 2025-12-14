//
//  PreferencesWindow.swift
//  Supersidian
//
//  Main preferences window with tabbed interface.
//

import SwiftUI

struct PreferencesWindow: View {
    @StateObject private var viewModel = PreferencesViewModel()
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack(spacing: 0) {
            // Tabbed content
            TabView {
                GeneralPreferencesView(viewModel: viewModel)
                    .tabItem {
                        Label("General", systemImage: "gear")
                    }
                
                VaultsPreferencesView(viewModel: viewModel)
                    .tabItem {
                        Label("Vaults", systemImage: "folder.badge.gearshape")
                    }
                
                TasksPreferencesView(viewModel: viewModel)
                    .tabItem {
                        Label("Tasks", systemImage: "checkmark.circle")
                    }
                
                NotificationsPreferencesView(viewModel: viewModel)
                    .tabItem {
                        Label("Notifications", systemImage: "bell")
                    }
                
                AdvancedPreferencesView(viewModel: viewModel)
                    .tabItem {
                        Label("Advanced", systemImage: "slider.horizontal.3")
                    }
            }
            .padding()
            
            Divider()
            
            // Bottom bar with Apply/Revert
            HStack(spacing: 16) {
                // Validation error
                if let error = viewModel.validationError {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                
                Spacer()
                
                // Unsaved changes indicator
                if viewModel.hasChanges {
                    Text("Unsaved changes")
                        .font(.caption)
                        .foregroundColor(.orange)
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
                            // Error is shown in validationError
                        }
                    }
                }
                .disabled(!viewModel.hasChanges || viewModel.isSaving)
                .keyboardShortcut(.defaultAction)
                
                if viewModel.isSaving {
                    ProgressView()
                        .scaleEffect(0.7)
                }
            }
            .padding()
        }
        .frame(width: 800, height: 600)
        .onAppear {
            viewModel.load()
        }
    }
}

// MARK: - Preview

#Preview {
    PreferencesWindow()
}
