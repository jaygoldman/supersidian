# SupersidianMac Setup Guide

The Xcode project has been generated and is ready to open!

## Quick Start

1. **Open the project:**
   ```bash
   cd SupersidianApp
   open SupersidianMac.xcodeproj
   ```

2. **Configure signing (required):**
   - Select "SupersidianMac" project in the navigator
   - Select "Supersidian" target
   - Go to "Signing & Capabilities" tab
   - **Select your Team** from the dropdown (your Apple Developer account)
   - The rest is already configured:
     - Bundle ID: `com.appetizerlabs.supersidian`
     - Code Signing: Automatic
     - Product Name: `Supersidian`

3. **Wait for dependencies to download:**
   - Xcode will automatically fetch SPM packages:
     - SQLite.swift (0.15.3+)
     - Sparkle (2.6.0+)
   - This happens automatically, just wait for the progress indicator
   - If it doesn't start: File → Packages → Resolve Package Versions

4. **Build the project:**
   - Press `⌘B` or Product → Build
   - First build may take a minute while dependencies compile

5. **Run the app:**
   - Press `⌘R` or Product → Run
   - The menubar icon should appear in your menu bar (cloud icon)
   - Click it to see the menu

## What's Configured

✅ **Project Structure:**
- Project name: SupersidianMac
- Product name: Supersidian (the actual app is called "Supersidian.app")
- Bundle identifier: com.appetizerlabs.supersidian

✅ **Build Settings:**
- macOS 13.0+ deployment target
- Swift 5.0
- Hardened runtime enabled
- LSUIElement = YES (menubar-only app, no dock icon)

✅ **Dependencies (auto-downloaded):**
- SQLite.swift for database access
- Sparkle for auto-updates

✅ **Files Included:**
- SupersidianApp.swift (entry point)
- AppDelegate.swift (menubar logic)
- BridgeStatus.swift (data model)
- DatabaseManager.swift (SQLite)
- ConfigurationManager.swift (.env/config)
- SupersidianRunner.swift (Python execution)
- NotificationManager.swift (macOS notifications)
- Info.plist
- Supersidian.entitlements
- Assets.xcassets

## Testing the App

### Prerequisites
1. Ensure Python supersidian has run at least once:
   ```bash
   cd ~/Dev/supersidian
   python3 -m supersidian.supersidian
   ```
   This creates `~/.supersidian.db` that the app reads.

2. Add menubar provider to your .env:
   ```bash
   echo "SUPERSIDIAN_NOTIFICATION_PROVIDERS=menubar,webhook" >> .env
   ```

### Run Tests
1. In Xcode, press `⌘U` or Product → Test
2. Currently no tests written (Phase 8)

### Manual Testing
1. Run the app (⌘R)
2. Look for cloud icon in menubar
3. Click icon → verify menu appears
4. Check vault submenus show stats
5. Try "Sync Now" → icon should change to syncing

### Debugging
- Console output: View → Debug Area → Show Debug Area
- Set breakpoints in Swift files
- Check logs: `tail -f ~/.supersidian.log`

## Troubleshooting

### "No such module 'SQLite'"
- Wait for package resolution to finish
- File → Packages → Reset Package Caches
- Clean build folder: Shift+⌘K

### "The file couldn't be opened"
- Check that all source files exist in `SupersidianApp/Supersidian/`
- Verify paths in project navigator

### "Code signing error"
- You must select your Team in Signing & Capabilities
- Requires a (free or paid) Apple Developer account

### "Database not found"
- Run Python script first: `python3 -m supersidian.supersidian`
- Check `~/.supersidian.db` exists

### Menubar icon doesn't appear
- Check Console for errors
- Verify Info.plist has LSUIElement = YES
- Try running from Xcode (⌘R) instead of .app

## Next Steps

After successfully building:
- [ ] Test menubar functionality
- [ ] Verify database reads work
- [ ] Test "Sync Now" button
- [ ] Check Darwin notifications (run Python sync, see if menu updates)
- [ ] Proceed with Phase 2-9 from MAC_PLAN.md

## File Structure

```
SupersidianApp/
├── SupersidianMac.xcodeproj/    ← The Xcode project (generated)
│   ├── project.pbxproj
│   ├── project.xcworkspace/
│   └── xcshareddata/
├── Supersidian/                  ← Source code directory
│   ├── App/
│   ├── Models/
│   ├── Services/
│   └── Resources/
├── Tests/
├── Scripts/
├── DEPENDENCIES.md
├── README.md
└── SETUP.md                      ← You are here
```

## Support

If you encounter issues:
1. Check this guide
2. Review DEPENDENCIES.md for package info
3. Check README.md for architecture details
4. Review MAC_PLAN.md for full implementation plan

---

Ready to build? Run:
```bash
open SupersidianMac.xcodeproj
```

Then press ⌘R to run!
