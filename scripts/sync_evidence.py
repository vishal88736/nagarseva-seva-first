#!/usr/bin/env python3
"""Refresh the standalone workbench served by the merged Vite application."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / "prototype/dist/standalone.html"
website = root / "nagarseva/website"
if not website.is_dir():
    raise SystemExit("NagarSeva has not been merged yet; run scripts/merge_source.py first.")
target = website / "public/evidence/index.html"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, target)
print(f"Updated {target.relative_to(root)} ({target.stat().st_size} bytes)")
