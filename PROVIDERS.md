# Writing Custom Providers

Supersidian uses a plugin architecture that makes it easy to add support for new services. This guide explains how to write providers for each integration point.

## Provider Types

Supersidian has four types of providers:

1. **Sync Providers** - Control how Supersidian accesses note files
2. **Note Providers** - Control how notes are written and formatted  
3. **Todo Providers** - Control where tasks are synced
4. **Notification Providers** - Control how you receive run notifications

## Writing a Todo Provider

Todo providers sync tasks from your notes to external task management systems.

### 1. Create the Provider File

Create a new file under `supersidian/todo/`, for example:
```
supersidian/todo/asana.py
```

### 2. Implement the Provider Class

Subclass `BaseTodoProvider` from `supersidian/todo/base.py`:

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

### 3. Register the Provider

Add your provider to the registry in `supersidian/todo/__init__.py`:

```python
from .asana import AsanaProvider

# In _register_defaults():
if AsanaProvider is not None:
    _PROVIDER_FACTORIES["asana"] = lambda: AsanaProvider()
```

### 4. Configure and Use

Users can now enable your provider:

```bash
SUPERSIDIAN_TODO_PROVIDER=asana
SUPERSIDIAN_ASANA_API_TOKEN=...
```

### What Providers Receive

- **`tasks`**: List of `LocalTask` objects with:
  - `local_id` - Unique identifier
  - `bridge_name` - Which bridge the task came from
  - `vault_name` - Display name of the vault
  - `note_path` - Path to the note file
  - `line_no` - Line number in the note
  - `title` - Task content
  - `completed` - Whether task is done

- **`ctx`**: TodoContext with:
  - `bridge_name` - Which bridge is running
  - `vault_name` - Vault display name
  - `vault_path` - Absolute path to vault
  - `note_url_builder` - Function to generate app-specific URLs

### What Providers Return

Return a list of `TaskSyncResult` objects describing what happened:

```python
TaskSyncResult(
    local_id=task.local_id,
    provider="asana",
    external_id="asana-task-id",
    status="created",  # or "skipped", "failed"
    error=None  # or error message
)
```

### Best Practices

- **Idempotency**: Supersidian handles this - providers just create tasks
- **Error Handling**: Return errors in results, don't raise exceptions
- **Keep it focused**: Providers should be small and single-purpose
- **Use environment variables**: For API tokens and configuration

## Writing a Sync Provider

Sync providers control how Supersidian accesses your note files.

### 1. Create the Provider File

```
supersidian/sync/gdrive.py
```

### 2. Implement the Interface

Subclass `BaseSyncProvider` from `supersidian/sync/base.py`:

```python
from .base import BaseSyncProvider, SyncContext, NoteFile
from pathlib import Path
from datetime import datetime

class GoogleDriveProvider(BaseSyncProvider):
    name = "gdrive"
    
    def is_available(self, ctx: SyncContext) -> bool:
        # Check if Google Drive is accessible
        root_path = self.get_root_path(ctx)
        return root_path and root_path.exists()
    
    def get_root_path(self, ctx: SyncContext) -> Path:
        # Return the local sync folder path
        gdrive_root = Path.home() / "GoogleDrive" / "Supernote" / "Note"
        return gdrive_root / ctx.supernote_subdir
    
    def list_notes(self, ctx: SyncContext) -> list:
        root = self.get_root_path(ctx)
        if not self.is_available(ctx):
            return []
        
        notes = []
        for note_path in root.rglob("*.note"):
            stat = note_path.stat()
            relative = note_path.relative_to(root)
            
            notes.append(NoteFile(
                path=note_path,
                relative_path=relative,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size,
            ))
        return notes
```

### 3. Register and Configure

Add to `supersidian/sync/__init__.py` and set:

```bash
SUPERSIDIAN_SYNC_PROVIDER=gdrive
```

## Writing a Note Provider

Note providers control how notes are written and formatted.

### 1. Create the Provider File

```
supersidian/notes/notion.py
```

### 2. Implement the Interface

Subclass `BaseNoteProvider` from `supersidian/notes/base.py`:

```python
from .base import BaseNoteProvider, NoteContext, NoteMetadata
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

class NotionProvider(BaseNoteProvider):
    name = "notion"
    
    def is_available(self, ctx: NoteContext) -> bool:
        # Check if Notion API is accessible
        return True
    
    def write_note(
        self,
        content: str,
        metadata: NoteMetadata,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Path:
        # Call Notion API to create/update page
        # Return local path or identifier
        pass
    
    def get_note_modified_time(
        self,
        relative_path: Path,
        ctx: NoteContext,
    ) -> Optional[datetime]:
        # Return last modified time for change detection
        pass
    
    def build_note_url(
        self,
        relative_path: Path,
        ctx: NoteContext,
    ) -> str:
        # Return Notion URL for deep linking
        return f"https://notion.so/..."
    
    def initialize_vault(self, ctx: NoteContext) -> None:
        # Optional: Setup Notion workspace/database
        pass
    
    def load_replacements(self, ctx: NoteContext) -> Dict[str, str]:
        # Optional: Load word replacements
        return {}
    
    def write_status_note(self, stats, ctx: NoteContext) -> None:
        # Optional: Write status somewhere
        pass
```

### 3. Register and Configure

Add to `supersidian/notes/__init__.py` and set:

```bash
SUPERSIDIAN_NOTE_PROVIDER=notion
SUPERSIDIAN_NOTION_API_TOKEN=...
```

## Writing a Notification Provider

Notification providers send run notifications to external services.

### 1. Create the Provider File

```
supersidian/notifications/slack.py
```

### 2. Implement the Interface

Subclass `BaseNotificationProvider` from `supersidian/notifications/base.py`:

```python
from .base import BaseNotificationProvider, NotificationPayload, NotificationContext
import os
import json
import urllib.request

class SlackProvider(BaseNotificationProvider):
    name = "slack"
    
    def __init__(self):
        self.webhook_url = os.environ.get("SUPERSIDIAN_SLACK_WEBHOOK_URL", "")
    
    def send(
        self,
        payload: NotificationPayload,
        ctx: NotificationContext,
    ) -> bool:
        if not self.webhook_url:
            return False
        
        # Build Slack-specific blocks
        color = "danger" if payload.has_errors else "good"
        outcome = "ERROR" if payload.has_errors else "OK"
        
        slack_payload = {
            "attachments": [{
                "color": color,
                "title": f"Supersidian: {payload.vault_name} - {outcome}",
                "text": self.format_message(payload),
                "fields": [
                    {"title": "Notes", "value": str(payload.notes_found), "short": True},
                    {"title": "Converted", "value": str(payload.converted), "short": True},
                ],
            }]
        }
        
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(slack_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False
```

### 3. Register and Configure

Add to `supersidian/notifications/__init__.py` and set:

```bash
SUPERSIDIAN_NOTIFICATION_PROVIDERS=slack
SUPERSIDIAN_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## Future Provider Ideas

### Sync Providers
- **iCloud** - Monitor iCloud Drive folder
- **OneDrive** - Microsoft cloud sync
- **Syncthing** - P2P sync protocol
- **rclone** - Generic cloud storage adapter

### Note Providers
- **Logseq** - Outliner-style notes
- **Joplin** - Open source note app
- **Bear** - macOS/iOS note app
- **Standard Notes** - Encrypted notes

### Todo Providers
- **ClickUp** - Project management
- **Things** - macOS/iOS todo app
- **Microsoft To Do** - Cross-platform tasks
- **Notion** - All-in-one workspace
- **Linear** - Issue tracking

### Notification Providers
- **Discord** - Gaming/community chat
- **Email** - SMTP notifications
- **Telegram** - Messaging app
- **Pushover** - Mobile push notifications
- **Matrix** - Decentralized chat

## Contributing

To contribute a new provider:

1. Fork the Supersidian repository
2. Create your provider following the patterns above
3. Add tests for your provider
4. Update documentation
5. Submit a pull request

Providers should be:
- **Focused**: Do one thing well
- **Reliable**: Handle errors gracefully
- **Documented**: Include docstrings and examples
- **Tested**: Add unit tests
- **Configurable**: Use environment variables

## Testing Providers

Test your provider in isolation:

```python
# test_my_provider.py
from supersidian.todo.asana import AsanaProvider
from supersidian.todo.base import TodoContext
from supersidian.storage import LocalTask

provider = AsanaProvider()
task = LocalTask(
    local_id="test:note:1",
    bridge_name="test",
    vault_name="Test",
    note_path="note.md",
    line_no=1,
    title="Test task",
    completed=False,
)

ctx = TodoContext(
    bridge_name="test",
    vault_name="Test",
    vault_path=Path("/path/to/vault"),
    note_url_builder=lambda p: f"obsidian://open?file={p}",
)

results = provider.sync_tasks([task], ctx)
assert len(results) == 1
assert results[0].status == "created"
```

## Getting Help

- Open an issue for questions
- Join discussions on GitHub
- Check existing providers for examples
- Read the base classes for full interface documentation
