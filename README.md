# Supersidian

Supersidian is a fully automated pipeline that transforms **Supernote Real-Time Recognition notes** into clean, structured **Markdown** inside **Obsidian**, preserving your notebook hierarchy, applying intelligent formatting fixes, and correcting common recognition errors.

The goal is simple:

> *Write naturally on your Supernote. Get beautifully formatted, instantly searchable notes in Obsidian — automatically.*

Supersidian watches your Supernote-synced Dropbox folder, extracts recognized text using `supernote-tool`, cleans it up, fixes headings and indentation, applies custom corrections you maintain inside Obsidian, and writes Markdown files into your Obsidian vault.

---
## ✨ What problem does Supersidian solve?

Supernote’s handwriting recognition is excellent, but the workflow around it has limitations:

- Real-Time Recognition text is trapped inside the `.note` file.
- Manual export (TXT/DOCX) breaks your flow.
- Recognized text often merges headings or loses indentation.
- Bullet structure is not reliably preserved.
- You can't automatically sync into a note-taking system like Obsidian.

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

Set an environment variable in your `.env` file:

```
SUPERSIDIAN_WEBHOOK_URL=https://your-webhook-endpoint
```

This can be any HTTP endpoint that accepts JSON:
- ntfy.sh
- a Slack/Discord relay
- IFTTT or Zapier webhook endpoints
- a custom server or home‑automation rule

If `SUPERSIDIAN_WEBHOOK_URL` is **not** set, notifications are disabled.

### What triggers a notification?

A webhook is sent only if **any errors occur**:

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
SUPERSIDIAN_WEBHOOK_URL=https://ntfy.sh/supersidian-alerts
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