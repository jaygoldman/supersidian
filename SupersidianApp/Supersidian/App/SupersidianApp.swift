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
        // Menubar-only app - no default windows
        Settings {
            EmptyView()
        }
    }
}
