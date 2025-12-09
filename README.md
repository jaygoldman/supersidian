# Supersidian

> *Write naturally on your Supernote. Get beautifully formatted, instantly searchable notes in Obsidian and todos in your task app of choice automatically.*

Supersidian is a fully automated pipeline that transforms **Supernote Real-Time Recognition notes** into clean, structured **Markdown** inside **Obsidian**, preserving your notebook hierarchy, applying intelligent formatting fixes, and correcting common recognition errors. Supersidian also identifies tasks in your notes and syncs them to your **Obsidian** vault and, optionally, your todo app of choice.

With a flexible **plugin architecture**, Supersidian supports different sync services, note apps, and todo platforms, making it adaptable to your workflow.

Supersidian requires a fairly high degree of technical knowledge to install. **Important note: no support is provided. Please do not contact me for assistance.** 

## Table of Contents

- [What problem does Supersidian solve?](#what-problem-does-supersidian-solve)
- [How Supersidian works](#how-supersidian-works)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running Supersidian](#running-supersidian)
- [Folder Strategy](#folder-strategy)
- [Editing Corrections Inside Obsidian](#editing-corrections-inside-obsidian)
- [Supersidian Status Notes](#supersidian-status-notes)
- [Plugin Architecture](#plugin-architecture)
- [Logging](#logging)
- [Healthcheck Monitoring](#healthcheck-monitoring)
- [Scheduling](#scheduling)
- [License](#license)

---
<a id="what-problem-does-supersidian-solve"></a>
## ✨ What problem does Supersidian solve?

Supernote’s handwriting recognition is excellent, but the workflow around it has limitations:

- Real-Time Recognition text is trapped inside the `.note` file.
- Manual export (TXT/DOCX) breaks your flow.
- Recognized text often merges headings or loses indentation.
- Bullet structure is not reliably preserved.
- You can't automatically sync into a note-taking system like Obsidian.
- Supports Obsidian‑style checkboxes (`[ ]` and `[x]`) written directly on Supernote

Supersidian automates the entire pipeline:

1. **Extract text** directly from `.note` files using [supernote-tool](https://github.com/jya-dev/supernote-tool).
2. **Clean up the output** — unwrap lines, fix bullets, split inline headings, normalize spacing.
3. **Support nested bullets** using a simple Supernote-friendly syntax (`-`, `--`, `---`).
4. **Apply your custom word corrections** using a Markdown file *inside* your Obsidian vault.
5. **Write Markdown files** to the correct subfolders in the vault.
6. **Skip unchanged notes** using timestamp comparison.
7. **Sync your tasks** from inside Supernotes to Obsidian and your todo app of choice.

---
<a id="how-supersidian-works"></a>
## 🧩 How Supersidian works

### 1. You write in Supernote
Using **Real-Time Recognition** notes, optionally in Markdown format with structured bullets:

```
- Top bullet
-- Nested bullet
--- Third level
```

### 2. Supernote syncs notes to your computer
Your device syncs notes to a local folder. Supersidian supports:
- **Dropbox** (recommended) - Automatic cloud sync
- **Local filesystem** - Manual file transfer or other sync methods

Typically, your notes will be in:

```
Dropbox/Supernote/Note/<YourFolderStructure>
```

See [Plugin Architecture](#plugin-architecture) for more sync options.

### 3. Supersidian processes only updated `.note` files
It compares modified timestamps and skips notes that haven’t changed relative to their Obsidian counterparts.

### 4. Text extraction via supernote-tool
Supersidian shells out to the tool:

```
supernote-tool convert -t txt -a <file.note> output.txt
```

This ensures the text you see on the device is the text the system processes.

### 5. Intelligent Markdown cleanup
Supersidian:

- fixes line wrapping
- standardizes bullet styles
- splits inline headings (e.g., `some text ##Heading` → two lines)
- normalizes heading spacing (e.g. `##Title` → `## Title`)
- converts `-, --, ---` into nested Markdown indentation
- capitalizes the first letter of each separated line
- converts `[ ] task` and `[x] task` lines into proper Obsidian tasks (`- [ ] Task`, `- [x] Task`)

### 6. Tasks
Supersidian detects Supernote lines starting with `[ ]` or `[x]` and transforms them into Obsidian tasks:
```
[ ] follow up with client
[x] send agenda
```
becomes:
```md
- [ ] Follow up with client
- [x] Send agenda
```

This works alongside nested bullets and aggressive cleanup.

Tasks are automatically synced to Obsidian. You can optionally sync them to external task apps like Todoist — see [Plugin Architecture](#plugin-architecture) for details.

### 7. Supersidian Folder Creation

On the first run, Supersidian automatically creates a `Supersidian/` folder in each enabled vault containing:

- **Status Note** - Run statistics and sync status (updated on each run)
- **Replacements Note** - Custom word corrections that you can edit

These files are created automatically and don't require manual setup.

### 8. Custom word corrections
The Supersidian folder in your vault includes a special file:

```
Supersidian Replacements.md
```

That file will include a comment with the format for your replacement dictionary explained. You can add corrections:

```
- Supersidain -> Supersidian
- Mehady -> Mehdi
- Conducotr -> Conductor
```

Supersidian applies these **after** formatting. It uses whole-word replacement to avoid mangling substrings.

### 9. Markdown is written into Obsidian
Supersidian mirrors your Supernote folder structure:

```
Supernote/Note/Acme/Products/Foo.note
→ Obsidian/Acme/Products/Foo.md
```

---
<a id="installation"></a>
## 🛠 Installation

### Requirements

- **Python 3.8+** required
- **Supernote device** with Real-Time Recognition enabled
- **Sync service** - Dropbox (recommended) or manual file transfer
- **Note app** - Obsidian (recommended) or plain Markdown storage

> Supersidian is cross-platform and runs on macOS, Linux, and Windows.

### Install from PyPI (Recommended)

```bash
pip install supersidian
```

This installs Supersidian and all dependencies, including `supernotelib` (which provides `supernote-tool`).

### Install from Source (For Development)

```bash
git clone https://github.com/jaygoldman/supersidian.git
cd supersidian
pip install -e .
```

The `-e` flag installs in editable mode for development.

### Verify Installation

```bash
supersidian --version
```

---
<a id="quick-start"></a>
## 🚀 Quick Start

### 1. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your Supernote path:

```bash
SUPERSIDIAN_SUPERNOTE_ROOT=/Users/you/Dropbox/Supernote/Note
```

### 2. Configure Bridges

Copy the example configuration:

```bash
cp supersidian.config.example.json supersidian.config.json
```

Edit `supersidian.config.json` to define your vault mappings:

```json
{
  "bridges": [
    {
      "name": "personal",
      "enabled": true,
      "supernote_subdir": "Personal",
      "vault_path": "/Users/you/Documents/Obsidian/Personal",
      "extra_tags": ["supernote"],
      "aggressive_cleanup": false
    }
  ]
}
```

### 3. Run Once

```bash
supersidian
```

Or with verbose output:

```bash
supersidian --verbose
```

### 4. Schedule Automatic Runs

See [Scheduling](#scheduling) for cron or launchd setup.

---
<a id="configuration"></a>
## ⚙️ Configuration

Supersidian uses two configuration files:

### `.env` - Environment Variables

Copy `.env.example` to `.env` and configure:

**Core Settings:**
```bash
# Path to your Supernote files
SUPERSIDIAN_SUPERNOTE_ROOT=/Users/you/Dropbox/Supernote/Note

# Path to bridges configuration (optional, default: supersidian.config.json)
SUPERSIDIAN_CONFIG_PATH=./supersidian.config.json
```

**Provider Settings:**
```bash
# Sync provider: dropbox, local
SUPERSIDIAN_SYNC_PROVIDER=dropbox

# Note provider: obsidian, markdown
SUPERSIDIAN_NOTE_PROVIDER=obsidian

# Todo provider: noop, todoist
SUPERSIDIAN_TODO_PROVIDER=noop

# Notification providers (comma-separated): webhook, noop
SUPERSIDIAN_NOTIFICATION_PROVIDERS=webhook
```

**Todoist Settings (if using todoist provider):**
```bash
SUPERSIDIAN_TODOIST_API_TOKEN=your_token_here
```

**Notification Settings (if using webhook provider):**
```bash
SUPERSIDIAN_WEBHOOK_URL=https://ntfy.sh/your-topic
SUPERSIDIAN_WEBHOOK_TOPIC=  # Optional topic field
SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors  # all, errors, or none
```

See `.env.example` for all available options.

### `supersidian.config.json` - Bridge Configuration

Copy `supersidian.config.example.json` to `supersidian.config.json` and configure your bridges.

Each bridge maps a Supernote folder to a note vault:

```json
{
  "bridges": [
    {
      "name": "personal",
      "enabled": true,
      "supernote_subdir": "Personal",
      "vault_path": "/Users/you/Obsidian/Personal",
      "extra_tags": ["supernote", "personal"],
      "aggressive_cleanup": false,
      "export_images": true,
      "images_subdir": "Supersidian/Assets"
    },
    {
      "name": "work",
      "enabled": true,
      "supernote_subdir": "Work",
      "vault_path": "/Users/you/Obsidian/Work",
      "extra_tags": ["work"],
      "aggressive_cleanup": true
    }
  ]
}
```

**Bridge Options:**
- `name` - Unique identifier for the bridge
- `enabled` - Set to `false` to temporarily disable
- `supernote_subdir` - Folder within `SUPERSIDIAN_SUPERNOTE_ROOT`
- `vault_path` - Absolute path to your note vault
- `extra_tags` - Additional tags for notes from this bridge
- `aggressive_cleanup` - More aggressive line unwrapping (optional)
- `export_images` - Export note pages as PNG images (optional)
- `images_subdir` - Where to store images (optional)

Supersidian supports multiple bridges running in parallel.

---
<a id="running-supersidian"></a>
## ▶️ Running Supersidian

After configuration, run Supersidian with:

```bash
supersidian
```

With verbose output:

```bash
supersidian --verbose
```

Check version:

```bash
supersidian --version
```

### What Happens During a Run

Supersidian:
1. Scans all enabled bridges
2. Discovers Supernote `.note` files via sync provider
3. Compares timestamps (skips unchanged notes)
4. Extracts text using `supernote-tool`
5. Cleans and formats Markdown
6. Applies custom word replacements
7. Extracts and syncs tasks (if todo provider configured)
8. Writes notes via note provider
9. Updates status notes
10. Sends notifications (if configured)

For automated execution, see [Scheduling](#scheduling).

Supersidian is designed to run repeatedly in the background to keep your vault in sync.

---
<a id="folder-strategy"></a>
## 📁 Folder Strategy

Supersidian mirrors whatever folder structure you maintain on your Supernote device.  
If your Supernote contains:

```
Acme/
  Phoenix/
    Intake/
    Playbooks/
```

Your Obsidian vault will contain:

```
Acme/
  Phoenix/
    Intake/
    Playbooks/
```

**Important:**  
If you later *move* a note inside Obsidian, and then update the corresponding `.note` file on Supernote, the next Supersidian run will recreate it at the original mirrored path.

---
<a id="editing-corrections-inside-obsidian"></a>
## 🔄 Editing Corrections Inside Obsidian

Users maintain their own correction list directly inside their vault, in a special file created automatically by Supersidian:

```
Supersidian Replacements.md
```

For example, for a bridge named `acme`:

```
Obsidian/Acme/Supersidian/Replacements - acme.md
```

This enables:
- personal handwriting quirks
- domain-specific terms
- client names
- fixing repeated misrecognitions

Example:

```
- Kekr -> KKR
- Supesidian -> Supersidian
```

Every run loads this note and applies the corrections.

---
<a id="supersidian-status-notes"></a>
## 📊 Supersidian Status Notes

On every run, Supersidian generates a status report *inside your Obsidian vault* for each enabled bridge. The note is named:

```
Supersidian Status - <bridge name>.md
```

For example, for a bridge named `acme`:

```
Obsidian/Acme/Supersidian/Status - acme.md
```

### What the status note contains
Each run overwrites the status note with an updated summary:

- Last run timestamp
- Supernote source path
- Obsidian vault path
- Total notes found
- Notes converted on this run
- Notes skipped (already up to date)
- Notes with no extractable text

Example:

```
# Supersidian Status - acme

- Last run: 2025‑12‑01T22:34:56
- Supernote path: `/Users/.../Dropbox/Supernote/Note/Acme`
- Vault path: `/Users/.../Obsidian/Acme`

## Summary
- Notes found: 23
- Converted this run: 2
- Skipped (up‑to‑date): 21
- No text extracted: 0
```

### Why this exists
This gives you real‑time visibility:
- whether Supersidian ran successfully
- whether Dropbox or Supernote failed to sync
- whether extraction succeeded
- which notes were updated

It allows monitoring directly inside Obsidian without reading log files.

---
<a id="plugin-architecture"></a>
## 🔌 Plugin Architecture

Supersidian uses a flexible plugin system for four integration points:

### Sync Providers

Control how Supersidian accesses your note files:

- **`dropbox`** (default) - Dropbox-synced local folder
- **`local`** - Direct filesystem access (manual sync, other services)

**Configuration:**
```bash
SUPERSIDIAN_SYNC_PROVIDER=dropbox  # or: local
```

### Note Providers

Control how notes are written and formatted:

- **`obsidian`** (default) - Obsidian with YAML frontmatter, deep links, custom replacements
- **`markdown`** - Plain Markdown files without app-specific features

**Configuration:**
```bash
SUPERSIDIAN_NOTE_PROVIDER=obsidian  # or: markdown
```

### Todo Providers

Control where tasks are synced:

- **`noop`** (default) - No external task sync
- **`todoist`** - Sync tasks to Todoist

**Configuration:**
```bash
SUPERSIDIAN_TODO_PROVIDER=todoist
SUPERSIDIAN_TODOIST_API_TOKEN=your_token_here
```

**Features:**
- Local SQLite task registry for idempotent sync
- Only open tasks (`[ ]`) are synced to external apps
- Completed tasks (`[x]`) stay local only
- Safe no-op fallback if provider unavailable

See [PROVIDERS.md](PROVIDERS.md) for writing custom todo providers.

### Notification Providers

Control how you receive run notifications:

- **`webhook`** - Generic HTTP webhooks (ntfy.sh, custom endpoints)
- **`noop`** - No notifications

**Configuration:**
```bash
SUPERSIDIAN_NOTIFICATION_PROVIDERS=webhook
SUPERSIDIAN_WEBHOOK_URL=https://ntfy.sh/your-topic
SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors  # all, errors, or none
```

**Notification Modes:**
- `errors` (default) - Notify only on structural errors (missing folders, tool failures)
- `all` - Notify on every run
- `none` - Disable notifications

**Example: ntfy.sh**
```bash
SUPERSIDIAN_WEBHOOK_URL=https://ntfy.sh/supersidian-alerts
```

See [PROVIDERS.md](PROVIDERS.md) for writing custom notification providers.

### Why Plugin Architecture?

- **Flexibility** - Mix and match providers based on your workflow
- **Extensibility** - Easy to add support for new services
- **No Breaking Changes** - Defaults preserve existing behavior

### Future Providers

The architecture is ready for additional providers:
- **Sync**: iCloud, Google Drive, OneDrive, Syncthing
- **Notes**: Notion, Logseq, Joplin, Bear
- **Todo**: Asana, ClickUp, Things, Notion
- **Notifications**: Slack, Discord, Email, Telegram, Pushover

See [PROVIDERS.md](PROVIDERS.md) for detailed examples and best practices.

---
<a id="logging"></a>
## 📝 Logging

Supersidian includes built-in logging for monitoring and debugging.

### Default Log Location

Logs are written to:
- **macOS**: `~/Library/Logs/supersidian/supersidian.log`
- **Linux**: `~/.local/share/supersidian/logs/supersidian.log`
- **Fallback**: `~/.supersidian.log`

By default, Supersidian runs quietly (no console output), making it suitable for scheduled execution.

### Verbose Mode

Enable verbose output to see logs in the terminal:

**Option 1: Command line flag**
```bash
supersidian --verbose
```

**Option 2: Environment variable**
```bash
export SUPERSIDIAN_VERBOSE=1
supersidian
```

Verbose mode shows:
- Conversions and skips
- Warnings and errors
- Provider activity
- Notification status

### Custom Log Location

Set a custom log path:

```bash
SUPERSIDIAN_LOG_PATH=/path/to/your/supersidian.log
```

### Log Format

Each entry includes timestamp, level, and message:

```
2025-12-08 14:23:45 [INFO] [personal] OK Note.note → /path/to/vault/Note.md
2025-12-08 14:23:46 [WARNING] [work] skipped 5 notes (up to date)
```

Logs persist between runs for long-term auditing.

---
<a id="healthcheck-monitoring"></a>
## ♥️ Healthcheck Monitoring

Supersidian includes built-in support for healthcheck monitoring services like [healthchecks.io](https://healthchecks.io).

### Configuration

Set the healthcheck URL in `.env`:

```bash
SUPERSIDIAN_HEALTHCHECK_URL=https://hc-ping.com/your-uuid
```

### How It Works

Supersidian automatically pings:
- **`/start`** - When a run begins
- **Base URL** - When a run succeeds
- **`/fail`** - When a run fails

This lets healthchecks.io track:
- Whether Supersidian is running on schedule
- Whether runs are succeeding or failing
- Duration of each run

### Example

1. Create a check at healthchecks.io
2. Get your ping URL: `https://hc-ping.com/abc123...`
3. Add to `.env`:
   ```bash
   SUPERSIDIAN_HEALTHCHECK_URL=https://hc-ping.com/abc123...
   ```
4. healthchecks.io will alert you if Supersidian stops running or fails

### Combining with Notifications

- **Healthchecks** - Monitor that Supersidian runs on schedule
- **Notifications** - Receive details about what happened

Use both for complete observability.

---
<a id="scheduling"></a>
## ⏱ Scheduling

Supersidian is designed to run repeatedly in the background to keep your vault in sync. Choose your preferred scheduling method based on your operating system.

### macOS: launchd (Recommended)

Create a LaunchAgent to run Supersidian automatically.

**1. Copy the example plist file:**

```bash
cp macos_com.supersidian.plist.example ~/Library/LaunchAgents/com.supersidian.plist
```

**2. Edit the file to replace placeholders:**

Edit `~/Library/LaunchAgents/com.supersidian.plist` and replace `/Users/YOU` with your home directory.

**3. Load the LaunchAgent:**

```bash
launchctl load ~/Library/LaunchAgents/com.supersidian.plist
```

This runs Supersidian every 10 minutes (600 seconds).

> **Note:** The example file assumes supersidian is installed at `/usr/local/bin/supersidian`. If you used `pip install --user`, change the path to `~/.local/bin/supersidian`

### Linux / macOS: cron

Alternatively, use cron:

```bash
*/10 * * * * /usr/local/bin/supersidian >> ~/.supersidian.cron.log 2>&1
```

This runs every 10 minutes. Adjust the path to match your installation.

### Windows: Task Scheduler

Use Windows Task Scheduler to run `supersidian` on a schedule:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., every 10 minutes)
4. Action: Start a program
5. Program: Path to supersidian.exe (in your Python Scripts folder)

### Verifying Schedule

Check logs to confirm Supersidian is running:

```bash
# macOS/Linux
tail -f ~/.supersidian.log

# Or check status notes in your vault
```

---
<a id="license"></a>
## 📜 License

MIT — use freely, improve freely, share freely.
