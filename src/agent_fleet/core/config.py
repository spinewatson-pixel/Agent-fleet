"""Configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_organization_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        candidates = [
            Path("config/organization.yaml"),
            Path(__file__).resolve().parents[3] / "config" / "organization.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        else:
            raise FileNotFoundError("config/organization.yaml not found")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
