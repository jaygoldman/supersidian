//
//  NotificationManager.swift
//  Supersidian
//
//  Manages native macOS notifications.
//

import Foundation
import UserNotifications

class NotificationManager: NSObject, UNUserNotificationCenterDelegate {
    static let shared = NotificationManager()

    private let center = UNUserNotificationCenter.current()

    private override init() {
        super.init()
        center.delegate = self
    }

    // MARK: - Permissions

    func requestPermissions() {
        center.requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            if granted {
                NSLog("NotificationManager: Notification permissions granted")
            } else if let error = error {
                NSLog("NotificationManager: Notification permissions denied: \(error)")
            }
        }
    }

    // MARK: - Sending Notifications

    func sendSyncCompleteNotification(bridgeName: String, notesConverted: Int) {
        let content = UNMutableNotificationContent()
        content.title = "Sync Complete"
        content.body = "\(bridgeName): Converted \(notesConverted) note(s)"
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )

        center.add(request) { error in
            if let error = error {
                NSLog("NotificationManager: Failed to send notification: \(error)")
            }
        }
    }

    func sendErrorNotification(title: String, message: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = message
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )

        center.add(request) { error in
            if let error = error {
                NSLog("NotificationManager: Failed to send notification: \(error)")
            }
        }
    }

    // MARK: - UNUserNotificationCenterDelegate

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        // Show notification even when app is in foreground
        completionHandler([.banner, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        // Handle notification actions here
        completionHandler()
    }
}
