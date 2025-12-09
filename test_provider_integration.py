#!/usr/bin/env python3
"""Quick integration test to verify provider system works correctly."""

import os
import sys
from pathlib import Path

# Ensure supersidian module can be imported
sys.path.insert(0, str(Path(__file__).parent))

def test_note_provider_defaults():
    """Verify note provider defaults to obsidian when not specified."""
    from supersidian.notes import get_provider

    # Test 1: None should default to obsidian
    provider = get_provider(None)
    assert provider.name == "obsidian", f"Expected 'obsidian', got '{provider.name}'"
    print("✓ Note provider defaults to 'obsidian' when not specified")

    # Test 2: Empty string should default to obsidian
    provider = get_provider("")
    assert provider.name == "obsidian", f"Expected 'obsidian', got '{provider.name}'"
    print("✓ Note provider defaults to 'obsidian' for empty string")

    # Test 3: Explicit obsidian
    provider = get_provider("obsidian")
    assert provider.name == "obsidian", f"Expected 'obsidian', got '{provider.name}'"
    print("✓ Note provider works with explicit 'obsidian'")

    # Test 4: Markdown provider
    provider = get_provider("markdown")
    assert provider.name == "markdown", f"Expected 'markdown', got '{provider.name}'"
    print("✓ Note provider works with 'markdown'")


def test_note_provider_env():
    """Verify provider_from_env uses env var correctly."""
    from supersidian.notes import provider_from_env

    # Save original env var
    original = os.environ.get("SUPERSIDIAN_NOTE_PROVIDER")

    try:
        # Test 1: Not set should default to obsidian
        if "SUPERSIDIAN_NOTE_PROVIDER" in os.environ:
            del os.environ["SUPERSIDIAN_NOTE_PROVIDER"]
        provider = provider_from_env()
        assert provider.name == "obsidian", f"Expected 'obsidian', got '{provider.name}'"
        print("✓ provider_from_env defaults to 'obsidian' when env var not set")

        # Test 2: Set to markdown
        os.environ["SUPERSIDIAN_NOTE_PROVIDER"] = "markdown"
        provider = provider_from_env()
        assert provider.name == "markdown", f"Expected 'markdown', got '{provider.name}'"
        print("✓ provider_from_env respects SUPERSIDIAN_NOTE_PROVIDER env var")

    finally:
        # Restore original env var
        if original is not None:
            os.environ["SUPERSIDIAN_NOTE_PROVIDER"] = original
        elif "SUPERSIDIAN_NOTE_PROVIDER" in os.environ:
            del os.environ["SUPERSIDIAN_NOTE_PROVIDER"]


def test_obsidian_provider_url():
    """Verify ObsidianProvider generates correct URLs."""
    from supersidian.notes import NoteContext
    from supersidian.notes.obsidian import ObsidianProvider
    from pathlib import Path

    provider = ObsidianProvider()
    ctx = NoteContext(
        bridge_name="test",
        vault_path=Path("/tmp/vault"),
        vault_name="MyVault"
    )

    # Test basic URL
    url = provider.get_note_url("folder/note", ctx)
    expected = "obsidian://open?vault=MyVault&file=folder%2Fnote"
    assert url == expected, f"Expected '{expected}', got '{url}'"
    print("✓ ObsidianProvider generates correct obsidian:// URLs")

    # Test URL with spaces
    url = provider.get_note_url("folder/my note", ctx)
    expected = "obsidian://open?vault=MyVault&file=folder%2Fmy%20note"
    assert url == expected, f"Expected '{expected}', got '{url}'"
    print("✓ ObsidianProvider handles spaces in note paths")


def test_todo_context_integration():
    """Verify TodoContext can use note_url_builder."""
    from supersidian.todo import TodoContext
    from supersidian.notes import NoteContext
    from supersidian.notes.obsidian import ObsidianProvider
    from pathlib import Path

    # Create note provider and context
    note_provider = ObsidianProvider()
    note_ctx = NoteContext(
        bridge_name="test",
        vault_path=Path("/tmp/vault"),
        vault_name="MyVault"
    )

    # Create todo context with note_url_builder
    todo_ctx = TodoContext(
        bridge_name="test",
        vault_name="MyVault",
        vault_path=Path("/tmp/vault"),
        note_url_builder=lambda path: note_provider.get_note_url(path, note_ctx)
    )

    # Test that the builder works
    url = todo_ctx.note_url_builder("test/note")
    assert url.startswith("obsidian://"), f"Expected obsidian:// URL, got '{url}'"
    print("✓ TodoContext note_url_builder integration works")


def main():
    """Run all tests."""
    print("Testing provider integration...\n")

    try:
        test_note_provider_defaults()
        print()
        test_note_provider_env()
        print()
        test_obsidian_provider_url()
        print()
        test_todo_context_integration()
        print()
        print("✅ All integration tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
