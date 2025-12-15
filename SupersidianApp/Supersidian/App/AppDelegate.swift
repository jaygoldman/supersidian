//
//  AppDelegate.swift
//  Supersidian
//
//  Handles menubar setup, menu generation, and app lifecycle.
//

import Cocoa
import SwiftUI
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    var menu: NSMenu?

    // Managers
    let databaseManager = DatabaseManager.shared
    let configManager = ConfigurationManager.shared
    let supersidianRunner = SupersidianRunner.shared
    let notificationManager = NotificationManager.shared

    // State
    private var currentState: MenubarState = .idle
    private var bridges: [BridgeStatus] = []
    private var syncWindow: NSWindow?
    private var preferencesWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon - menubar only app
        NSApp.setActivationPolicy(.accessory)

        // Request notification permissions
        notificationManager.requestPermissions()

        // Set up menubar
        setupMenubar()

        // Subscribe to Darwin notifications
        subscribeToDarwinNotifications()

        // Load initial state
        refreshState()

        // Check if first run
        if !UserDefaults.standard.bool(forKey: "hasCompletedSetup") {
            showWelcomeWindow()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Cleanup
        unsubscribeFromDarwinNotifications()
    }

    // MARK: - Menubar Setup

    private func setupMenubar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem?.button {
            updateMenubarIcon(for: .idle)
            button.action = #selector(menubarButtonClicked)
            button.target = self
        }

        buildMenu()
    }

    @objc private func menubarButtonClicked() {
        // Refresh state before showing menu
        refreshState()
        statusItem?.menu = menu
        statusItem?.button?.performClick(nil)
        statusItem?.menu = nil
    }

    private func updateMenubarIcon(for state: MenubarState) {
        guard let button = statusItem?.button else { return }

        currentState = state

        let iconName: String
        switch state {
        case .idle:
            iconName = "cloud"
        case .syncing:
            iconName = "cloud.fill"
        case .success:
            iconName = "checkmark.circle.fill"
        case .warning:
            iconName = "exclamationmark.triangle.fill"
        case .error:
            iconName = "xmark.circle.fill"
        }

        if let image = NSImage(systemSymbolName: iconName, accessibilityDescription: nil) {
            image.isTemplate = true
            button.image = image
        }
    }

    // MARK: - Menu Building

    private func buildMenu() {
        menu = NSMenu()

        // App title
        let titleItem = NSMenuItem(title: "Supersidian", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        menu?.addItem(titleItem)

        menu?.addItem(NSMenuItem.separator())

        // Sync Now
        let syncItem = NSMenuItem(
            title: "Sync Now",
            action: #selector(syncNowClicked),
            keyEquivalent: "s"
        )
        syncItem.target = self
        menu?.addItem(syncItem)

        menu?.addItem(NSMenuItem.separator())

        // Vault submenus
        if bridges.isEmpty {
            let noVaultsItem = NSMenuItem(title: "No vaults configured", action: nil, keyEquivalent: "")
            noVaultsItem.isEnabled = false
            menu?.addItem(noVaultsItem)
        } else {
            for bridge in bridges {
                let vaultMenu = buildVaultSubmenu(for: bridge)

                // Add status icon to vault name
                let statusIcon = iconForStatus(bridge.status)
                let vaultItem = NSMenuItem(
                    title: "\(statusIcon) \(bridge.vaultName)",
                    action: nil,
                    keyEquivalent: ""
                )
                vaultItem.submenu = vaultMenu
                menu?.addItem(vaultItem)
            }
        }

        menu?.addItem(NSMenuItem.separator())

        // Preferences
        let prefsItem = NSMenuItem(
            title: "Preferences…",
            action: #selector(openPreferences),
            keyEquivalent: ","
        )
        prefsItem.target = self
        menu?.addItem(prefsItem)

        // About
        let aboutItem = NSMenuItem(
            title: "About Supersidian",
            action: #selector(openAbout),
            keyEquivalent: ""
        )
        aboutItem.target = self
        menu?.addItem(aboutItem)

        menu?.addItem(NSMenuItem.separator())

        // Quit
        let quitItem = NSMenuItem(
            title: "Quit Supersidian",
            action: #selector(quitApp),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu?.addItem(quitItem)
    }

    private func buildVaultSubmenu(for bridge: BridgeStatus) -> NSMenu {
        let submenu = NSMenu()

        // Status indicator
        let statusText = bridge.status.capitalized
        let statusItem = NSMenuItem(title: "Status: \(statusText)", action: nil, keyEquivalent: "")
        statusItem.isEnabled = false
        submenu.addItem(statusItem)

        submenu.addItem(NSMenuItem.separator())

        // Stats
        let notesItem = NSMenuItem(
            title: "Notes: \(bridge.notesFound)",
            action: nil,
            keyEquivalent: ""
        )
        notesItem.isEnabled = false
        submenu.addItem(notesItem)

        let convertedItem = NSMenuItem(
            title: "Converted: \(bridge.converted)",
            action: nil,
            keyEquivalent: ""
        )
        convertedItem.isEnabled = false
        submenu.addItem(convertedItem)

        if bridge.tasksTotal > 0 {
            let tasksItem = NSMenuItem(
                title: "Tasks: \(bridge.tasksOpen) open, \(bridge.tasksCompleted) done",
                action: nil,
                keyEquivalent: ""
            )
            tasksItem.isEnabled = false
            submenu.addItem(tasksItem)
        }

        // Last sync time
        if let lastSync = bridge.lastSyncTime {
            submenu.addItem(NSMenuItem.separator())
            submenu.addItem(NSMenuItem(title: "Last sync:", action: nil, keyEquivalent: "")) 
            let timeAgo = formatTimeAgo(lastSync)
            let syncItem = NSMenuItem(
                title: "\(timeAgo)",
                action: nil,
                keyEquivalent: ""
            )
            syncItem.isEnabled = false
            submenu.addItem(syncItem)
        }

        // Error message if present
        if let error = bridge.errorMessage {
            submenu.addItem(NSMenuItem.separator())
            let errorItem = NSMenuItem(title: "⚠️ \(error)", action: nil, keyEquivalent: "")
            errorItem.isEnabled = false
            submenu.addItem(errorItem)
        }

        return submenu
    }

    // MARK: - Actions

    @objc private func syncNowClicked() {
        // Prevent duplicate syncs
        if syncWindow != nil {
            NSLog("Sync window already open")
            syncWindow?.makeKeyAndOrderFront(nil)
            return
        }
        
        // Create and show sync progress window
        let progressView = SyncProgressWindow()
        let hostingController = NSHostingController(rootView: progressView)
        
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 500),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Sync Progress"
        window.contentViewController = hostingController
        window.center()
        window.isReleasedWhenClosed = false
        
        // Handle window close
        NotificationCenter.default.addObserver(
            forName: NSWindow.willCloseNotification,
            object: window,
            queue: .main
        ) { [weak self] _ in
            self?.syncWindow = nil
            // Refresh state after window closes
            self?.refreshState()
        }
        
        syncWindow = window
        window.makeKeyAndOrderFront(nil)
        
        // Update icon to syncing state
        updateMenubarIcon(for: .syncing)
    }

    @objc private func openPreferences() {
        // Show existing window if already open
        if let window = preferencesWindow {
            window.makeKeyAndOrderFront(nil)
            return
        }

        // Create preferences window
        let prefsView = PreferencesWindow()
        let hostingController = NSHostingController(rootView: prefsView)

        // Calculate centered position on screen
        let screenFrame = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1920, height: 1080)
        let windowFrame = NSRect(
            x: (screenFrame.width - 900) / 2 + screenFrame.origin.x,
            y: (screenFrame.height - 650) / 2 + screenFrame.origin.y,
            width: 900,
            height: 650
        )

        let window = NSWindow(
            contentRect: windowFrame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Supersidian Preferences"
        window.contentViewController = hostingController
        window.isReleasedWhenClosed = false
        window.minSize = NSSize(width: 850, height: 600)
        window.maxSize = NSSize(width: 1400, height: 1000)

        // Handle window close
        NotificationCenter.default.addObserver(
            forName: NSWindow.willCloseNotification,
            object: window,
            queue: .main
        ) { [weak self] _ in
            self?.preferencesWindow = nil
        }

        preferencesWindow = window
        window.makeKeyAndOrderFront(nil)
    }

    @objc private func openAbout() {
        NSApp.orderFrontStandardAboutPanel(nil)
    }

    @objc private func quitApp() {
        NSApp.terminate(nil)
    }

    // MARK: - State Management

    private func refreshState() {
        bridges = databaseManager.fetchBridgeStatuses()

        // Calculate overall menubar status (worst status across all bridges)
        let overallState = calculateOverallState()
        updateMenubarIcon(for: overallState)

        buildMenu()
    }

    private func calculateOverallState() -> MenubarState {
        // No bridges = idle
        guard !bridges.isEmpty else { return .idle }

        // Check for errors first (highest priority)
        if bridges.contains(where: { $0.status == "error" }) {
            return .error
        }

        // Then warnings
        if bridges.contains(where: { $0.status == "warning" }) {
            return .warning
        }

        // Then success
        if bridges.contains(where: { $0.status == "success" }) {
            return .success
        }

        // Default to idle
        return .idle
    }

    private func iconForStatus(_ status: String) -> String {
        switch status {
        case "success":
            return "✓"  // Green checkmark
        case "warning":
            return "⚠️"  // Warning triangle
        case "error":
            return "✗"  // Red X
        case "syncing":
            return "↻"  // Refresh symbol
        default:
            return "○"  // Circle for idle/unknown
        }
    }

    // MARK: - Darwin Notifications

    private func subscribeToDarwinNotifications() {
        let observer = UnsafeRawPointer(Unmanaged.passUnretained(self).toOpaque())

        // Subscribe to sync start notification
        let startNotificationName = "com.supersidian.sync.start" as CFString
        CFNotificationCenterAddObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            observer,
            { _, observer, name, _, _ in
                guard let observer = observer else { return }
                let appDelegate = Unmanaged<AppDelegate>.fromOpaque(observer).takeUnretainedValue()
                appDelegate.handleSyncStart()
            },
            startNotificationName,
            nil,
            .deliverImmediately
        )

        // Subscribe to sync complete notification
        let completeNotificationName = "com.supersidian.sync.complete" as CFString
        CFNotificationCenterAddObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            observer,
            { _, observer, name, _, _ in
                guard let observer = observer else { return }
                let appDelegate = Unmanaged<AppDelegate>.fromOpaque(observer).takeUnretainedValue()
                appDelegate.handleSyncComplete()
            },
            completeNotificationName,
            nil,
            .deliverImmediately
        )
    }

    private func unsubscribeFromDarwinNotifications() {
        let observer = UnsafeRawPointer(Unmanaged.passUnretained(self).toOpaque())
        CFNotificationCenterRemoveEveryObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            observer
        )
    }

    @objc private func handleSyncStart() {
        DispatchQueue.main.async {
            // Update icon to syncing state
            self.updateMenubarIcon(for: .syncing)
        }
    }

    @objc private func handleSyncComplete() {
        DispatchQueue.main.async {
            // Refresh state from database - this will update menubar icon
            // based on actual bridge statuses (may be success, warning, or error)
            self.refreshState()
        }
    }

    // MARK: - Welcome Window

    private func showWelcomeWindow() {
        // Will implement in Phase 6
        NSLog("Show welcome window - not yet implemented")
    }

    // MARK: - Utilities

    private func formatTimeAgo(_ dateString: String) -> String {
        let isoFormatter = ISO8601DateFormatter()
        isoFormatter.formatOptions = [.withInternetDateTime, .withDashSeparatorInDate, .withColonSeparatorInTime]

        // Try parsing with timezone first, then without
        var date = isoFormatter.date(from: dateString)
        if date == nil {
            // Try without timezone (local time)
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
            formatter.timeZone = TimeZone.current
            date = formatter.date(from: dateString)
        }

        guard let date = date else {
            return dateString
        }

        // Create date formatter for full human-readable format
        let dateFormatter = DateFormatter()
        dateFormatter.locale = Locale.current  // Use user's locale
        dateFormatter.dateFormat = "EEEE, MMMM d"  // "Saturday, December 13"

        // Get day with ordinal suffix (13th, 1st, 2nd, etc.)
        let calendar = Calendar.current
        let day = calendar.component(.day, from: date)
        let ordinalFormatter = NumberFormatter()
        ordinalFormatter.numberStyle = .ordinal
        let dayWithSuffix = ordinalFormatter.string(from: NSNumber(value: day)) ?? "\(day)"

        // Get year
        let year = calendar.component(.year, from: date)

        // Time formatter
        let timeFormatter = DateFormatter()
        timeFormatter.locale = Locale.current
        timeFormatter.timeStyle = .medium  // "10:29:03 PM"

        // Combine: "Saturday, December 13th, 2025 at 10:29:03 PM"
        let dayOfWeek = dateFormatter.weekdaySymbols[calendar.component(.weekday, from: date) - 1]
        let monthName = dateFormatter.monthSymbols[calendar.component(.month, from: date) - 1]
        let timeString = timeFormatter.string(from: date)

        return "\(dayOfWeek), \(monthName) \(dayWithSuffix), \(year) at \(timeString)"
    }
}

// MARK: - Supporting Types

enum MenubarState {
    case idle
    case syncing
    case success
    case warning
    case error
}
