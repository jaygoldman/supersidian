# Swift Package Manager Dependencies

This document lists the SPM dependencies required for the Supersidian macOS app.

## Adding Dependencies in Xcode

1. Open `Supersidian.xcodeproj` in Xcode
2. Select the project in the navigator
3. Select the "Supersidian" target
4. Go to "Package Dependencies" tab
5. Click "+" to add each package below

## Required Packages

### 1. SQLite.swift

**Purpose:** Read-only access to the Supersidian SQLite database

- **Repository:** `https://github.com/stephencelis/SQLite.swift.git`
- **Version:** `0.15.3` or later
- **Import:** `import SQLite`

### 2. Sparkle

**Purpose:** Auto-update framework for automatic app updates

- **Repository:** `https://github.com/sparkle-project/Sparkle.git`
- **Version:** `2.6.0` or later
- **Import:** `import Sparkle`

## Dependency Configuration

After adding packages:

1. Ensure both packages are linked to the "Supersidian" target
2. Build the project to download and cache dependencies
3. If build fails, try:
   - Product → Clean Build Folder
   - File → Packages → Reset Package Caches
   - File → Packages → Resolve Package Versions

## Notes

- SQLite.swift is used in read-only mode to avoid conflicts with Python writes
- Sparkle requires code signing to work properly
- Both packages are compatible with macOS 13.0+
