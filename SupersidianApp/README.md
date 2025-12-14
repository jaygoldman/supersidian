# Supersidian macOS Menubar App

Native macOS menubar application for monitoring and controlling Supersidian sync status.

## Features

- **Real-time Status:** Live sync status displayed in menubar with SF Symbol icons
- **Per-Vault Stats:** Submenu for each vault showing notes, tasks, and last sync time
- **Manual Sync:** Trigger sync on-demand via "Sync Now" menu item
- **Native Notifications:** macOS notification center integration
- **Preferences UI:** Full-featured preferences window for configuration
- **Auto-Updates:** Built-in update mechanism via Sparkle framework
- **Darwin Notifications:** Efficient IPC with Python script

## Architecture

### Communication

- **SQLite Database:** Python writes, Swift reads (read-only mode)
- **Darwin Notifications:** Python signals sync completion via `notifyutil`
- **Process Execution:** Swift can trigger Python sync via `subprocess`

### Project Structure

```
SupersidianApp/
├── Supersidian/
│   ├── App/
│   │   ├── SupersidianApp.swift      # App entry point
│   │   └── AppDelegate.swift         # Menubar setup and lifecycle
│   ├── Models/
│   │   └── BridgeStatus.swift        # Data models
│   ├── Services/
│   │   ├── Database/
│   │   │   └── DatabaseManager.swift # SQLite read-only access
│   │   ├── Configuration/
│   │   │   └── ConfigurationManager.swift  # .env and config.json
│   │   ├── Supersidian/
│   │   │   └── SupersidianRunner.swift     # Python script runner
│   │   └── Notifications/
│   │       └── NotificationManager.swift   # macOS notifications
│   ├── Views/
│   │   ├── Preferences/              # (Phase 5)
│   │   ├── Welcome/                  # (Phase 6)
│   │   └── Sync/                     # (Phase 4)
│   ├── Utilities/
│   └── Resources/
│       ├── Assets.xcassets/
│       ├── Info.plist
│       └── Supersidian.entitlements
├── Tests/
│   ├── SupersidianTests/
│   └── SupersidianIntegrationTests/
├── Scripts/
├── DEPENDENCIES.md
└── README.md
```

## Building

### Prerequisites

- macOS 13.0 or later
- Xcode 15.0 or later
- Swift 5.9 or later

### Setup

1. **Open project:**
   ```bash
   cd SupersidianApp
   open Supersidian.xcodeproj
   ```

2. **Add SPM dependencies:**
   - See `DEPENDENCIES.md` for instructions
   - SQLite.swift: `https://github.com/stephencelis/SQLite.swift.git`
   - Sparkle: `https://github.com/sparkle-project/Sparkle.git`

3. **Configure signing:**
   - Select "Supersidian" target
   - Go to "Signing & Capabilities"
   - Select your Apple Developer team
   - Bundle ID: `com.appetizerlabs.supersidian`

4. **Build:**
   ```bash
   xcodebuild -scheme Supersidian -configuration Debug
   ```

### Running

- Press Cmd+R in Xcode, or
- Run built app from `build/Debug/Supersidian.app`

## Development

### Current Status (Phase 1 Complete)

✅ **Completed:**
- Project structure created
- Core services implemented:
  - DatabaseManager (SQLite read-only)
  - ConfigurationManager (.env and config.json)
  - SupersidianRunner (Python script execution)
  - NotificationManager (macOS notifications)
- AppDelegate with menubar setup
- Darwin notification subscription
- Menu generation with vault submenus
- SF Symbol placeholder icons

🚧 **In Progress:**
- None (Phase 1 complete)

⏳ **Upcoming:**
- Phase 2: Additional utilities and helpers
- Phase 3: Enhanced menubar features
- Phase 4: Sync progress window
- Phase 5: Preferences UI
- Phase 6: Welcome flow
- Phase 7: Notification actions
- Phase 8: Testing and polish
- Phase 9: Distribution

### Adding Features

1. Create new Swift files in appropriate directories
2. Import required frameworks
3. Follow existing patterns for managers (singletons)
4. Add tests in corresponding test directory

### Debugging

- Enable verbose logging: Set breakpoints in service classes
- Check console for `NSLog` output
- Verify database exists at `~/.supersidian.db`
- Test Darwin notifications: `notifyutil -p com.supersidian.sync.complete`

## Testing

### Unit Tests

```bash
xcodebuild test -scheme Supersidian -destination 'platform=macOS'
```

### Integration Tests

```bash
xcodebuild test -scheme SupersidianIntegrationTests -destination 'platform=macOS'
```

### Manual Testing

1. Run Python script to populate database
2. Launch menubar app
3. Verify menubar icon appears
4. Click icon to check menu generation
5. Test "Sync Now" functionality
6. Verify Darwin notifications trigger updates

## Distribution

### Debug Build

```bash
xcodebuild -scheme Supersidian -configuration Debug
```

### Release Build

```bash
xcodebuild -scheme Supersidian -configuration Release
```

### Code Signing

For distribution outside Xcode:
1. Archive: Product → Archive
2. Distribute: Select "Developer ID" distribution
3. Upload to App Store Connect or distribute directly
4. Notarize with Apple

### Auto-Updates

- Sparkle framework handles updates
- Configure appcast URL in Info.plist
- Generate release notes and deltas
- Host on GitHub Releases or custom server

## Platform Requirements

- **Minimum:** macOS 13.0 (Ventura)
- **Recommended:** macOS 14.0 (Sonoma) or later
- **Architecture:** Universal (Apple Silicon + Intel)

## Configuration

The app reads configuration from the Python script's files:
- `.env` - Environment variables
- `supersidian.config.json` - Bridge configurations

No separate configuration is needed for the menubar app.

## Troubleshooting

### App doesn't appear in menubar

- Check Console.app for errors
- Verify LSUIElement is set to true in Info.plist
- Ensure no conflicting menubar apps

### Database not found

- Verify Python script has run at least once
- Check `~/.supersidian.db` exists
- Ensure database is readable (not locked)

### Sync doesn't work

- Verify supersidian is in PATH or .venv exists
- Check Python script runs manually: `python3 -m supersidian.supersidian`
- Review logs in `~/.supersidian.log`

### Darwin notifications not received

- Test with: `notifyutil -p com.supersidian.sync.complete`
- Verify app is running and not suspended
- Check Console.app for notification errors

## Contributing

This is part of the Supersidian project. See main README for contribution guidelines.

## License

Same as Supersidian main project.

## Support

For issues specific to the macOS app:
1. Check this README
2. Review [MAC_PLAN.md](../MAC_PLAN.md) for architecture details
3. Open issue on GitHub with "macOS app" label
