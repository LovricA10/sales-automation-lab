"""Centralized configuration: paths are read from env variables with sensible defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

# src/sales_lab/config.py -> parents[0]=sales_lab, [1]=src, [2]=project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


@dataclass(frozen=True, slots=True)
class Settings:
    input_path: Path
    db_path: Path
    output_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            input_path=_path_from_env("SALES_LAB_INPUT", PROJECT_ROOT / "data" / "sales.csv"),
            db_path=_path_from_env("SALES_LAB_DB", PROJECT_ROOT / "sales.db"),
            output_dir=_path_from_env("SALES_LAB_OUTPUT", PROJECT_ROOT / "outputs"),
        )
