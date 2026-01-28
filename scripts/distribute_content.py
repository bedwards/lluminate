#!/usr/bin/env python3
"""
Distribute content from pool directories into numbered batch subdirectories.
Each batch contains one item from each source (YouTube channel + Substack feed).
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


def get_source_files(pool_dir: Path) -> dict:
    """
    Get all source directories and their files.
    Returns dict mapping source_name -> list of file paths (sorted by date, newest first)
    """
    sources = {}

    if not pool_dir.exists():
        return sources

    for source_dir in pool_dir.iterdir():
        if not source_dir.is_dir():
            continue
        if source_dir.name.startswith("_"):
            continue

        # Get all text files, sorted by name (which includes date prefix)
        files = sorted(
            [f for f in source_dir.glob("*.txt") if f.is_file()],
            key=lambda f: f.name,
            reverse=True  # Newest first
        )

        if files:
            sources[source_dir.name] = files

    return sources


def distribute_content(
    youtube_pool: Path,
    substack_pool: Path,
    output_dir: Path,
    dry_run: bool = False
) -> dict:
    """
    Distribute content into batch directories.
    Returns statistics about the distribution.
    """
    # Gather all sources
    youtube_sources = get_source_files(youtube_pool)
    substack_sources = get_source_files(substack_pool)

    print(f"Found {len(youtube_sources)} YouTube channels")
    print(f"Found {len(substack_sources)} Substack feeds")

    all_sources = {}
    for name, files in youtube_sources.items():
        all_sources[f"youtube/{name}"] = files
    for name, files in substack_sources.items():
        all_sources[f"substack/{name}"] = files

    if not all_sources:
        print("No sources found!")
        return {"batches": 0, "sources": 0}

    # Find minimum number of items across all sources
    min_items = min(len(files) for files in all_sources.values())
    print(f"Minimum items per source: {min_items}")

    # Track which files have been used
    used_indices = {name: 0 for name in all_sources}

    stats = {
        "batches_created": 0,
        "total_files_distributed": 0,
        "sources": {},
        "last_complete_batch": None,
    }

    # Create batches
    batch_num = 1
    while True:
        # Check if we have at least one item from each source
        can_create_batch = True
        for name, files in all_sources.items():
            if used_indices[name] >= len(files):
                can_create_batch = False
                break

        if not can_create_batch:
            break

        batch_name = f"batch_{batch_num:03d}"
        batch_dir = output_dir / batch_name

        if not dry_run:
            batch_dir.mkdir(parents=True, exist_ok=True)

        files_in_batch = 0

        for source_name, files in sorted(all_sources.items()):
            idx = used_indices[source_name]
            if idx < len(files):
                src_file = files[idx]

                # Create subdirectory for source type
                source_type = source_name.split("/")[0]
                source_id = source_name.split("/")[1]

                if not dry_run:
                    dest_subdir = batch_dir / source_type
                    dest_subdir.mkdir(exist_ok=True)
                    dest_file = dest_subdir / f"{source_id}_{src_file.name}"
                    shutil.copy2(src_file, dest_file)

                used_indices[source_name] = idx + 1
                files_in_batch += 1

                # Track source stats
                if source_name not in stats["sources"]:
                    stats["sources"][source_name] = {
                        "total_available": len(files),
                        "distributed": 0,
                    }
                stats["sources"][source_name]["distributed"] += 1

        stats["batches_created"] += 1
        stats["total_files_distributed"] += files_in_batch
        stats["last_complete_batch"] = batch_name

        if batch_num % 10 == 0:
            print(f"  Created {batch_name} ({files_in_batch} files)")

        batch_num += 1

    return stats


def generate_report(stats: dict, output_dir: Path) -> str:
    """Generate a human-readable report."""
    report = []
    report.append("=" * 80)
    report.append("CONTENT DISTRIBUTION REPORT")
    report.append("=" * 80)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Output directory: {output_dir}")
    report.append(f"\nTotal batches created: {stats['batches_created']}")
    report.append(f"Total files distributed: {stats['total_files_distributed']}")
    report.append(f"Last complete batch: {stats['last_complete_batch']}")

    report.append("\n" + "-" * 80)
    report.append("SOURCE DETAILS")
    report.append("-" * 80)

    # YouTube sources
    youtube_sources = {k: v for k, v in stats["sources"].items() if k.startswith("youtube/")}
    if youtube_sources:
        report.append("\nYouTube Channels:")
        for name, data in sorted(youtube_sources.items()):
            channel = name.split("/")[1]
            report.append(f"  {channel:30} - {data['distributed']:3} / {data['total_available']:3} distributed")

    # Substack sources
    substack_sources = {k: v for k, v in stats["sources"].items() if k.startswith("substack/")}
    if substack_sources:
        report.append("\nSubstack Feeds:")
        for name, data in sorted(substack_sources.items()):
            feed = name.split("/")[1]
            report.append(f"  {feed:30} - {data['distributed']:3} / {data['total_available']:3} distributed")

    # Find limiting source
    if stats["sources"]:
        min_source = min(stats["sources"].items(), key=lambda x: x[1]["total_available"])
        report.append(f"\nLimiting source: {min_source[0]} ({min_source[1]['total_available']} items)")

    report.append("\n" + "=" * 80)

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Distribute content into batch directories")
    parser.add_argument("--youtube-pool", type=str, default="transcripts/_pool/youtube",
                        help="YouTube transcripts pool directory")
    parser.add_argument("--substack-pool", type=str, default="transcripts/_pool/substack",
                        help="Substack posts pool directory")
    parser.add_argument("--output", type=str, default="transcripts",
                        help="Output directory for batch subdirectories")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually create files")
    args = parser.parse_args()

    youtube_pool = Path(args.youtube_pool)
    substack_pool = Path(args.substack_pool)
    output_dir = Path(args.output)

    print(f"YouTube pool: {youtube_pool}")
    print(f"Substack pool: {substack_pool}")
    print(f"Output directory: {output_dir}")

    if args.dry_run:
        print("\n*** DRY RUN - no files will be created ***\n")

    stats = distribute_content(
        youtube_pool=youtube_pool,
        substack_pool=substack_pool,
        output_dir=output_dir,
        dry_run=args.dry_run
    )

    # Generate and print report
    report = generate_report(stats, output_dir)
    print(report)

    # Save report
    if not args.dry_run:
        report_file = output_dir / "_distribution_report.txt"
        report_file.write_text(report)
        print(f"\nReport saved to: {report_file}")

        # Save stats as JSON
        stats_file = output_dir / "_distribution_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"Stats saved to: {stats_file}")


if __name__ == "__main__":
    main()
