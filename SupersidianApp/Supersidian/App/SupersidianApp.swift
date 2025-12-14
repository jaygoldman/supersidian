//
//  SupersidianApp.swift
//  Supersidian
//
//  Main app entry point for the Supersidian menubar app.
//

import SwiftUI

@main
struct SupersidianApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // Menubar-only app - no windows should appear
        // We need a Scene for SwiftUI, but it should never show
        WindowGroup {
            EmptyView()
        }
        .commands {
            // Remove default menu items that could open windows
            CommandGroup(replacing: .newItem) { }
        }
    }
}
