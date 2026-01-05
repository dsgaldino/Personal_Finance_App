from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppBrand:
    name: str
    subtitle: str
    icon_emoji: str
    logo_path: Path | None


BRAND = AppBrand(
    name="Galfin",
    subtitle="Personal finance overview",
    icon_emoji="🧭",
    logo_path=None,  # e.g. Path("app/assets/logo.png")
)
