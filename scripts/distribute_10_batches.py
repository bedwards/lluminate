#!/usr/bin/env python3
"""
Create 10 batch subdirectories with one item from each qualifying source.
Only includes sources with 10+ items. Most recent first.
"""

import shutil
from pathlib import Path

MIN_ITEMS = 10
NUM_BATCHES = 10

YOUTUBE_POOL = Path("transcripts/_pool/youtube")
SUBSTACK_POOL = Path("transcripts/_pool/substack")
OUTPUT_DIR = Path("transcripts")


def get_qualifying_sources(pool_dir: Path) -> dict:
    """Get sources with 10+ items, sorted by filename (date) descending."""
    sources = {}

    if not pool_dir.exists():
        return sources

    for source_dir in pool_dir.iterdir():
        if not source_dir.is_dir() or source_dir.name.startswith("_"):
            continue

        files = sorted(
            [f for f in source_dir.glob("*.txt") if f.is_file() and "video_ids" not in f.name],
            key=lambda f: f.name,
            reverse=True  # Newest first
        )

        if len(files) >= MIN_ITEMS:
            sources[source_dir.name] = files

    return sources


def main():
    # Gather qualifying sources
    youtube = get_qualifying_sources(YOUTUBE_POOL)
    substack = get_qualifying_sources(SUBSTACK_POOL)

    print(f"Qualifying YouTube channels: {len(youtube)}")
    for name, files in sorted(youtube.items()):
        print(f"  {name}: {len(files)}")

    print(f"\nQualifying Substack feeds: {len(substack)}")
    for name, files in sorted(substack.items()):
        print(f"  {name}: {len(files)}")

    all_sources = {}
    for name, files in youtube.items():
        all_sources[f"youtube_{name}"] = files
    for name, files in substack.items():
        all_sources[f"substack_{name}"] = files

    print(f"\nTotal qualifying sources: {len(all_sources)}")
    print(f"Creating {NUM_BATCHES} batches...\n")

    # Create batches
    for batch_num in range(1, NUM_BATCHES + 1):
        batch_name = f"batch_{batch_num:03d}"
        batch_dir = OUTPUT_DIR / batch_name
        batch_dir.mkdir(parents=True, exist_ok=True)

        files_copied = 0

        for source_name, files in sorted(all_sources.items()):
            idx = batch_num - 1  # 0-indexed
            if idx < len(files):
                src_file = files[idx]
                dest_file = batch_dir / f"{source_name}_{src_file.name}"
                shutil.copy2(src_file, dest_file)
                files_copied += 1

        print(f"Created {batch_name}: {files_copied} files")

    print(f"\nDone! Created {NUM_BATCHES} batches in {OUTPUT_DIR}/")
    print(f"Each batch contains {len(all_sources)} items (1 from each source)")


if __name__ == "__main__":
    main()
