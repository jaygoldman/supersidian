# Supersidian

Supersidian is a fully automated pipeline that transforms **Supernote Real-Time Recognition notes** into clean, structured **Markdown** inside **Obsidian**, preserving your notebook hierarchy, applying intelligent formatting fixes, and correcting common recognition errors.

The goal is simple:

> *Write naturally on your Supernote. Get beautifully formatted, instantly searchable notes in Obsidian — automatically.*

Supersidian watches your Supernote-synced Dropbox folder, extracts recognized text using `supernote-tool`, cleans it up, fixes headings and indentation, applies custom corrections you maintain inside Obsidian, and writes Markdown files into your Obsidian vault.

## Table of Contents

- [What problem does Supersidian solve?](#what-problem-does-supersidian-solve)
- [How Supersidian works](#how-supersidian-works)
- [Requirements](#requirements)
- [Logging](#logging)
- [Configuration](#configuration)
- [Running Supersidian](#running-supersidian)
- [Folder Strategy](#folder-strategy)
- [Editing Corrections Inside Obsidian](#editing-corrections-inside-obsidian)
- [Supersidian Status Notes](#supersidian-status-notes)
- [Notifications & Webhook Integration](#notifications--webhook-integration)
- [License](#license)

---
## ✨ What problem does Supersidian solve?

Supernote’s handwriting recognition is excellent, but the workflow around it has limitations:

- Real-Time Recognition text is trapped inside the `.note` file.
- Manual export (TXT/DOCX) breaks your flow.
- Recognized text often merges headings or loses indentation.
- Bullet structure is not reliably preserved.
- You can't automatically sync into a note-taking system like Obsidian.
- Supports Obsidian‑style checkboxes (`[ ]` and `[x]`) written directly on Supernote

Supersidian automates the entire pipeline:

1. **Extract text** directly from `.note` files using `supernote-tool`.
2. **Clean up the output** — unwrap lines, fix bullets, split inline headings, normalize spacing.
3. **Support nested bullets** using a simple Supernote-friendly syntax (`-`, `--`, `---`).
4. **Apply your custom word corrections** using a Markdown file *inside* your Obsidian vault.
5. **Write Markdown files** to the correct subfolders in the vault.
6. **Skip unchanged notes** using timestamp comparison.

It’s a “write once, sync forever” system.

---
## 🧩 How Supersidian works

### 1. You write in Supernote
Using **Real-Time Recognition** notes, optionally with structured bullets:

```
- Top bullet
-- Nested bullet
--- Third level
```

### 2. Supernote syncs notes into Dropbox
Your device must be configured to sync to:

```
Dropbox/Supernote/Note/<YourFolderStructure>
```

### 3. Supersidian processes only updated `.note` files
It compares modified timestamps and skips notes that haven’t changed.

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
- converts `[ ] task` and `[x] task` lines into proper Obsidian tasks (`- [ ] Task`, `- [x] Task`)

### Task Conversion
Supersidian now detects Supernote lines starting with `[ ]` or `[x]` and transforms them into Obsidian tasks:
```
[ ] follow up with client
[x] send agenda
```
becomes:
```md
- [ ] Follow up with client
- [x] Send agenda
```
```
This works alongside nested bullets and aggressive cleanup.
```

### 📝 Task Extraction & Todoist Sync
Supersidian automatically detects Supernote checkbox lines (`[ ]` and `[x]`) and converts them into Obsidian tasks. In addition, tasks now participate in a full task‑sync pipeline:

#### ✔ Local Task Registry (SQLite)
Every detected task is assigned a stable local ID and stored in a lightweight local SQLite database. This enables:
- idempotent processing across runs
- preventing duplicate syncs
- future integration with multiple providers

#### ✔ Only Open Tasks Sync to Todoist
Supersidian syncs **only unchecked tasks** (`[ ]`) to Todoist.
Completed tasks (`[x]`) are **ignored** for sync purposes and stored locally only. This keeps your Todoist inbox clean and prevents noise.

#### ✔ Todoist Integration
If you set:
```
SUPERSIDIAN_TODO_PROVIDER=todoist
SUPERSIDIAN_TODOIST_API_TOKEN=your_api_token
```
new open tasks are automatically sent to your Todoist inbox.
Each created Todoist task includes:
- the task content
- labels: `supersidian` and `vault:<VaultName>`
- a description containing vault, note path, line number, and local task ID

If no provider is configured, or Todoist is unavailable, Supersidian falls back to a safe no‑op provider and marks tasks as "skipped" without raising errors.

#### ✔ Idempotent Sync
Each task is synced only once. Supersidian never resends a task that has already been assigned a Todoist ID.

### 🔌 Plugin Architecture for Task Providers
Supersidian includes a small plugin system for task services. By default it ships with a fully functional **Todoist provider**, but the same mechanism can be used to integrate with services like **Asana**, **Monday.com**, **ClickUp**, **Things**, **Notion**, and others.

#### ✔ How Providers Fit In
Providers live under:

```
supersidian/todo/
```

Supersidian core:
- extracts tasks from Markdown into `LocalTask` objects
- determines which ones are new (using the SQLite registry)
- hands the new tasks to the active provider

The provider:
- receives a list of `LocalTask` objects plus a `TodoContext` (bridge + vault info)
- creates corresponding tasks in the external system
- returns `TaskSyncResult` objects describing what happened per task

Supersidian then persists those results back into the SQLite registry.

#### ✔ Selecting a Provider
You choose a provider via an environment variable in `.env`:

```
SUPERSIDIAN_TODO_PROVIDER=todoist
```

If this is unset or invalid, Supersidian automatically uses a safe **no-op provider** that marks tasks as skipped instead of raising errors.

#### ✔ Writing Your Own Provider
To add support for a new external task platform:

1. Create a new file under `supersidian/todo/`, for example:
   ```
   supersidian/todo/asana.py
   ```
2. Implement a class that subclasses `BaseTodoProvider` from `supersidian/todo/base.py`:
   ```python
   from .base import BaseTodoProvider, TodoContext
   from ..storage import LocalTask, TaskSyncResult

   class AsanaProvider(BaseTodoProvider):
       name = "asana"

       def sync_tasks(self, tasks, ctx):
           results = []
           for t in tasks:
               # Call Asana's API here to create a task
               external_id = "..."  # Replace with actual ID from Asana
               results.append(TaskSyncResult(
                   local_id=t.local_id,
                   provider=self.name,
                   external_id=external_id,
                   status="created",
                   error=None,
               ))
           return results
   ```
3. Register the provider name in `supersidian/todo/__init__.py` so it can be resolved from `SUPERSIDIAN_TODO_PROVIDER`.
4. Open a pull request adding your provider.

Because Supersidian handles idempotency and local history, providers can remain small and focused: receive tasks, create them in the external system, return results.

---
### 6. Custom word corrections
Inside your vault, create: 

```
Supersidian Replacements.md
```

Add corrections:

```
- Supersidain -> Supersidian
- Mehady -> Mehdi
- Conducotr -> Conductor
```

Supersidian applies these **after** formatting. It uses whole-word replacement to avoid mangling substrings.

### 7. Markdown is written into Obsidian
Supersidian mirrors your Supernote folder structure:

```
Supernote/Note/Klick/Guardrail/Foo.note
→ Obsidian/Klick/Guardrail/Foo.md
```

---
## 🛠 Requirements

> Supersidian is cross‑platform. It runs on macOS, Linux, or Windows — anywhere Python and a local Dropbox‑synced folder are available.

### Supernote
- Real-Time Recognition notes enabled
- Cloud Sync set to **Dropbox**
- Ensure your notes sync to:

```
Dropbox/Supernote/Note/
```

### Dropbox (macOS, Windows, Linux)
Supersidian does **not** require macOS. It can run on any OS where Dropbox syncs note files locally. This includes:
- macOS (native Dropbox client)
- Windows (native Dropbox client)
- Linux (official and community-supported Dropbox clients)

As long as your Supernote directory appears in a locally synced Dropbox folder, Supersidian will work.

### Obsidian
You can sync your vault using:
- Obsidian Sync **(recommended)**
- iCloud
- Dropbox

Your vault path must be accessible to Supersidian, e.g.:

```
~/Obsidian/Klick
```

### supernote-tool
Install via pip:

```
pip install supernotelib
```

Make sure `supernote-tool` is available on your PATH.

### Python
- Python 3.10+
- Recommended to use a venv:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---
## 📝 Logging

Supersidian includes built‑in logging so you can monitor activity and diagnose issues.

### Default Behavior
By default, all logs are written to a file:

```
~/.supersidian.log
```

Supersidian runs quietly unless something goes wrong. This makes it suitable for scheduled or automated execution.

### Verbose Mode (Console Output)
To see logs in the terminal while still writing to the log file, enable verbose mode by setting an environment variable:

```
export SUPERSIDIAN_VERBOSE=1
python -m supersidian.bridge
```

Verbose mode prints:
- conversions
- skips
- warnings
- errors

If `SUPERSIDIAN_VERBOSE` is not set to `1`, Supersidian suppresses console output and logs only to the file.

### Log Format
Each log entry includes:

```
2025-01-01 12:34:56 [INFO] message text
```

The log includes:
- successful conversions
- skipped notes
- text extraction errors
- replacement loading issues
- supernote‑tool failures

Logs persist between runs, allowing long‑term auditing of your sync pipeline.

---
## ⚙️ Configuration

Supersidian uses two files:

### `.env`
Environment variables (ignored by Git):

```
SUPERSIDIAN_SUPERNOTE_ROOT=/Users/you/Library/CloudStorage/Dropbox/Supernote/Note
SUPERSIDIAN_CONFIG_PATH=./supersidian.config.json

# Optional: webhook configuration
SUPERSIDIAN_WEBHOOK_URL=
SUPERSIDIAN_WEBHOOK_TOPIC=
# One of: errors, all, none (default: errors)
SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors
```

### `supersidian.config.json`
Defines one or more “bridges” mapping Supernote folders to Obsidian vaults:

```
{
  "bridges": [
    {
      "name": "klick",
      "enabled": true,
      "supernote_subdir": "Klick",
      "vault_path": "/Users/you/Obsidian/Klick",
      "aggressive_cleanup": true,
      "spellcheck": false,
      "extra_tags": ["klick"]
    }
  ]
}
```

Supersidian supports multiple vaults (“bridges”) in parallel.

---
## ▶️ Running Supersidian

From the project root:

```
source .venv/bin/activate
python -m supersidian.bridge
```


It will:
- scan all enabled bridges
- detect updated Supernote notes
- extract + clean text
- apply replacements
- write Markdown
- skip unchanged notes

### ⏱ Scheduling Supersidian
Supersidian is designed to be run repeatedly in the background so your Obsidian vault stays in sync with your Supernote. The core script is a one-shot process; you attach your own scheduler.

#### macOS: launchd (recommended)
On macOS, the native way to run Supersidian on a schedule is with a **LaunchAgent**:

1. Create a file at:
   `~/Library/LaunchAgents/com.supersidian.bridge.plist`
2. Example contents (runs every 10 minutes):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>Label</key>
     <string>com.supersidian.bridge</string>

     <key>WorkingDirectory</key>
     <string>/Users/you/Dev/supersidian</string>

     <key>ProgramArguments</key>
     <array>
       <string>/Users/you/Dev/supersidian/.venv/bin/python</string>
       <string>-m</string>
       <string>supersidian.bridge</string>
     </array>

     <key>StartInterval</key>
     <integer>600</integer>

     <key>StandardOutPath</key>
     <string>/Users/you/Library/Logs/supersidian.log</string>
     <key>StandardErrorPath</key>
     <string>/Users/you/Library/Logs/supersidian.err.log</string>
   </dict>
   </plist>
   ```
3. Load it:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.supersidian.bridge.plist
   ```

#### macOS / Linux: cron
If you prefer `cron`, you can add a line like this:

```bash
*/10 * * * * cd /Users/you/Dev/supersidian && \
  source .venv/bin/activate && \
  python -m supersidian.bridge >> ~/.supersidian.cron.log 2>&1
```

This runs Supersidian every 10 minutes, writing additional logs to `~/.supersidian.cron.log`.

### ❤️ Monitoring with healthchecks.io (optional)
Supersidian doesn’t talk to healthchecks.io directly, but you can easily pair them using your scheduler. The idea:

- healthchecks.io watches **whether Supersidian runs and exits cleanly**
- Supersidian itself continues to handle note conversion, logging, and notifications

#### Example: cron + healthchecks.io
Assume you created a check in healthchecks.io and got this URL:

```text
https://hc-ping.com/your-check-uuid
```

Update your cron entry to wrap Supersidian with pings:

```bash
*/10 * * * * HC_URL=https://hc-ping.com/your-check-uuid && \
  curl -fsS "$HC_URL/start" -m 10 || true; \
  cd /Users/you/Dev/supersidian && \
  source .venv/bin/activate && \
  python -m supersidian.bridge && \
  curl -fsS "$HC_URL" -m 10 || \
  curl -fsS "$HC_URL/fail" -m 10 || true
```

This pattern:
- sends a `/start` ping before Supersidian runs
- sends a success ping on exit code 0
- sends a `/fail` ping if the process exits non‑zero

#### Example: launchd + wrapper script
For `launchd`, you can point `ProgramArguments` to a small shell script, for example:

```bash
#!/usr/bin/env bash
set -euo pipefail

HC_URL="https://hc-ping.com/your-check-uuid"

curl -fsS "$HC_URL/start" -m 10 || true

cd /Users/you/Dev/supersidian
source .venv/bin/activate

if python -m supersidian.bridge; then
  curl -fsS "$HC_URL" -m 10 || true
else
  curl -fsS "$HC_URL/fail" -m 10 || true
fi
```

Then point your LaunchAgent’s `ProgramArguments` at this script instead of calling Python directly.

Using healthchecks.io this way turns Supersidian into a monitored background service: you’ll be alerted if the job stops running, crashes, or begins failing consistently.

---
## 📁 Folder Strategy

Supersidian mirrors whatever folder structure you maintain on your Supernote device.  
If your Supernote contains:

```
Klick/
  Guardrail/
    Intake/
    Playbooks/
```

Your Obsidian vault will contain:

```
Klick/
  Guardrail/
    Intake/
    Playbooks/
```

**Important:**  
If you later *move* a note inside Obsidian, and then update the corresponding `.note` file on Supernote, the next Supersidian run will recreate it at the original mirrored path.

---
## 🔄 Editing Corrections Inside Obsidian

Users maintain their own correction list directly inside their vault:

```
Supersidian Replacements.md
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
## 📊 Supersidian Status Notes

On every run, Supersidian generates a status report *inside your Obsidian vault* for each enabled bridge. The note is named:

```
Supersidian Status - <bridge name>.md
```

For example, for a bridge named `klick`:

```
Obsidian/Klick/Supersidian Status - klick.md
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
# Supersidian Status - klick

- Last run: 2025‑12‑01T22:34:56
- Supernote path: `/Users/.../Dropbox/Supernote/Note/Klick`
- Vault path: `/Users/.../Obsidian/Klick`

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
## 🔔 Notifications & Webhook Integration

Supersidian can optionally send notifications when something goes wrong during a run.  
If a webhook URL is provided, Supersidian will POST a JSON payload describing the errors.

### Enabling Notifications

Set environment variables in your `.env` file:

```
SUPERSIDIAN_WEBHOOK_URL=https://your-webhook-endpoint
SUPERSIDIAN_WEBHOOK_TOPIC=optional-topic-name
SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors
```

- `SUPERSIDIAN_WEBHOOK_URL` (required to enable notifications) is any HTTP endpoint that accepts JSON.
- `SUPERSIDIAN_WEBHOOK_TOPIC` (optional) is a logical topic or channel name used by services like ntfy.sh.
- `SUPERSIDIAN_WEBHOOK_NOTIFICATIONS` controls when Supersidian sends notifications and can be:
  - `errors` (default): send notifications only for runs with structural errors (missing tool, tool failures, missing Supernote or vault paths).
  - `all`: send a summary notification for **every** run, even when everything succeeds.
  - `none`: never send notifications, even if `SUPERSIDIAN_WEBHOOK_URL` is set.

This can be any HTTP endpoint that accepts JSON:
- ntfy.sh
- a Slack/Discord relay
- IFTTT or Zapier webhook endpoints
- a custom server or home‑automation rule

If `SUPERSIDIAN_WEBHOOK_URL` is **not** set, notifications are disabled.

### What triggers a notification?

By default (`SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors`), a webhook is sent only if **structural errors occur**:

- Supernote folder is missing
- Vault folder is missing
- `supernote-tool` is missing
- `supernote-tool` fails on one or more notes
- A note contains no extractable Real‑Time Recognition text

Clean runs (all converted or skipped) do **not** trigger notifications.

### JSON Payload Format

Supersidian sends a POST request with the following structure:

```json
{
  "bridge": "klick",
  "timestamp": "2025-12-01T22:34:56",
  "notes_found": 23,
  "converted": 2,
  "skipped": 21,
  "no_text": 1,
  "tool_missing": 0,
  "tool_failed": 1,
  "supernote_missing": false,
  "vault_missing": false
}
```

This provides enough detail for dashboards, alerts, or automation responses.

### Example: ntfy.sh

Add this to `.env`:

```
SUPERSIDIAN_WEBHOOK_URL=https://ntfy.sh/
SUPERSIDIAN_WEBHOOK_TOPIC=supersidian-alerts
SUPERSIDIAN_WEBHOOK_NOTIFICATIONS=errors
```

Then subscribe from any device:

```
curl -s https://ntfy.sh/supersidian-alerts/json
```

You will receive real‑time alerts like:

```
{"bridge":"klick","converted":2,"no_text":1,"tool_failed":1,"timestamp":"2025‑12‑01T22:34:56"}
```

### Example: Local Script Trigger

If you want Supersidian to trigger a local script instead of a network webhook, use a tiny local HTTP listener such as:

```
python3 -m http.server 9000
```

Then set:

```
SUPERSIDIAN_WEBHOOK_URL=http://localhost:9000
```

Your script can then respond however you prefer.

Notifications allow you to monitor sync reliability even when Supersidian runs unattended (e.g., as a scheduled job).

---
## 📜 License

MIT — use freely, improve freely, share freely.