from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


@dataclass
class BridgeConfig:
    name: str
    enabled: bool
    supernote_path: Path
    vault_path: Path
    default_tags: List[str]
    extra_tags: List[str]
    aggressive_cleanup: bool = False
    spellcheck: bool = False
    export_images: bool = False
    images_subdir: str = "Supersidian/Assets"


@dataclass
class SupersidianConfig:
    supernote_root: Path
    bridges: List[BridgeConfig]


def load_config(project_root: Optional[Path] = None) -> SupersidianConfig:
    """
    Load configuration from .env and supersidian.config.json
    """

    if project_root is None:
        # Assume this file is supersidian/config.py
        project_root = Path(__file__).resolve().parents[1]

    # 1) Load .env
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    supernote_root = Path(
        os.getenv("SUPERSIDIAN_SUPERNOTE_ROOT", "")
    ).expanduser()

    if not supernote_root:
        raise RuntimeError("SUPERSIDIAN_SUPERNOTE_ROOT is not set in .env")

    default_tags_raw = os.getenv("SUPERSIDIAN_DEFAULT_TAGS", "")
    default_tags = (
        [t.strip() for t in default_tags_raw.split(",") if t.strip()]
        if default_tags_raw
        else []
    )

    config_path_env = os.getenv("SUPERSIDIAN_CONFIG_PATH", "supersidian.config.json")
    config_path = (project_root / config_path_env).expanduser()

    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    bridges: List[BridgeConfig] = []

    for entry in raw.get("bridges", []):
        name = entry.get("name")
        if not name:
            continue

        enabled = bool(entry.get("enabled", True))

        subdir = entry.get("supernote_subdir")
        explicit_supernote = entry.get("supernote_path")
        if explicit_supernote:
            supernote_path = Path(explicit_supernote).expanduser()
        elif subdir:
            supernote_path = supernote_root / subdir
        else:
            # skip incomplete entries
            continue

        vault_path_raw = entry.get("vault_path")
        if not vault_path_raw:
            continue
        vault_path = Path(vault_path_raw).expanduser()

        extra_tags = entry.get("extra_tags", []) or []
        aggressive_cleanup = bool(entry.get("aggressive_cleanup", False))
        spellcheck = bool(entry.get("spellcheck", False))
        export_images = bool(entry.get("export_images", False))
        images_subdir = entry.get("images_subdir", "Supersidian/Assets")

        bridges.append(
            BridgeConfig(
                name=name,
                enabled=enabled,
                supernote_path=supernote_path,
                vault_path=vault_path,
                default_tags=list(default_tags),
                extra_tags=list(extra_tags),
                aggressive_cleanup=aggressive_cleanup,
                spellcheck=spellcheck,
                export_images=export_images,
                images_subdir=images_subdir,
            )
        )

    if not bridges:
        raise RuntimeError("No valid bridges configured in supersidian.config.json")

    return SupersidianConfig(
        supernote_root=supernote_root,
        bridges=bridges,
    )