#!/usr/bin/env python3
"""Build Phase 2 processed datasets (dual taxonomy + role mappings)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from statskill.main import run_build  # noqa: E402


def main() -> None:
    stats = run_build()
    print("StatSkill AI — Phase 2 build complete")
    print("-" * 50)
    for key, value in stats.items():
        print(f"  {key:28s}: {value}")


if __name__ == "__main__":
    main()
