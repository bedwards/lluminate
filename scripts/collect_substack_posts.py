#!/usr/bin/env python3
"""
Collect Substack posts from RSS feeds.
Filters for posts that are at least a 10-minute read (~2000 words).
Saves posts as text files organized by source.
"""

import argparse
import hashlib
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

# Minimum words for a ~10 minute read (200 words per minute)
MIN_WORDS = 2000

FEEDS = [
    "https://www.honest-broker.com/feed",
    "https://benthams.substack.com/feed",
    "https://www.theseedsofscience.pub/feed",
    "https://goodscience.substack.com/feed",
    "https://www.dropsitenews.com/feed",
    "https://www.asimov.press/feed",
    "https://www.the-downballot.com/feed",
    "https://www.henrikkarlsson.xyz/feed",
    "https://www.slowboring.com/feed",
    "https://savageminds.substack.com/feed",
    "https://yougovamerica.substack.com/feed",
    "https://www.wakeuptopolitics.com/feed",
    "https://blog.spec.tech/feed",
    "https://www.woman-of-letters.com/feed",
    "https://www.narratively.com/feed",
    "https://www.the-hinternet.com/feed",
    "https://chrislatray.substack.com/feed",
    "https://www.gelliottmorris.com/feed",
    "https://www.noahpinion.blog/feed",
    "https://matthewclayfield.substack.com/feed",
    "https://jessesingal.substack.com/feed",
]


def get_feed_name(url: str) -> str:
    """Extract a clean name from the feed URL."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    # Handle substack.com domains
    if "substack.com" in host:
        return host.split(".")[0]
    # Handle custom domains
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[0].replace("-", "_")
    return host.replace("-", "_").replace(".", "_")


def html_to_text(html_content: str) -> str:
    """Convert HTML content to plain text."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text(separator="\n")

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    # Unescape HTML entities
    text = html.unescape(text)

    return text


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def sanitize_filename(title: str) -> str:
    """Create a safe filename from title."""
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.replace('\n', ' ').replace('\r', '')
    safe = re.sub(r'\s+', '_', safe)
    # Truncate if too long
    if len(safe) > 100:
        safe = safe[:100]
    return safe


def fetch_full_content(url: str) -> str:
    """Fetch full article content from URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return html_to_text(response.text)
    except Exception as e:
        print(f"  Warning: Could not fetch full content from {url}: {e}")
        return ""


def process_feed(feed_url: str, output_dir: Path, max_posts: int = 100) -> dict:
    """Process a single RSS feed and save qualifying posts."""
    feed_name = get_feed_name(feed_url)
    feed_dir = output_dir / feed_name
    feed_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n==> Processing {feed_name} ({feed_url})")

    stats = {
        "name": feed_name,
        "url": feed_url,
        "total_entries": 0,
        "saved": 0,
        "skipped_short": 0,
        "skipped_exists": 0,
        "oldest_date": None,
        "newest_date": None,
    }

    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            print(f"  Error parsing feed: {feed.bozo_exception}")
            return stats

        stats["total_entries"] = len(feed.entries)
        print(f"  Found {len(feed.entries)} entries in feed")

        for entry in feed.entries:
            if stats["saved"] >= max_posts:
                break

            title = entry.get("title", "Untitled")
            link = entry.get("link", "")
            published = entry.get("published", entry.get("updated", ""))

            # Try to get date for stats
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d", entry.published_parsed)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = time.strftime("%Y-%m-%d", entry.updated_parsed)

            if pub_date:
                if stats["newest_date"] is None or pub_date > stats["newest_date"]:
                    stats["newest_date"] = pub_date
                if stats["oldest_date"] is None or pub_date < stats["oldest_date"]:
                    stats["oldest_date"] = pub_date

            # Create unique ID from link
            post_id = hashlib.md5(link.encode()).hexdigest()[:8]
            date_prefix = pub_date or "unknown"
            filename = f"{date_prefix}_{post_id}_{sanitize_filename(title)}.txt"
            filepath = feed_dir / filename

            # Skip if already exists
            if filepath.exists():
                stats["skipped_exists"] += 1
                continue

            # Also check by post_id in case filename changed
            existing = list(feed_dir.glob(f"*_{post_id}_*.txt"))
            if existing:
                stats["skipped_exists"] += 1
                continue

            # Get content from feed or fetch from URL
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = html_to_text(entry.content[0].value)
            elif hasattr(entry, "summary"):
                content = html_to_text(entry.summary)

            # If content is short, try fetching the full article
            word_count = count_words(content)
            if word_count < MIN_WORDS and link:
                full_content = fetch_full_content(link)
                if count_words(full_content) > word_count:
                    content = full_content
                    word_count = count_words(content)

            # Skip if still too short
            if word_count < MIN_WORDS:
                stats["skipped_short"] += 1
                continue

            # Build output text
            output = f"Title: {title}\n"
            output += f"Source: {feed_name}\n"
            output += f"URL: {link}\n"
            output += f"Date: {published}\n"
            output += f"Word Count: {word_count}\n"
            output += f"Estimated Read Time: {word_count // 200} minutes\n"
            output += "\n" + "=" * 80 + "\n\n"
            output += content

            # Save
            filepath.write_text(output, encoding="utf-8")
            stats["saved"] += 1
            print(f"  [{stats['saved']}/{max_posts}] Saved: {title[:50]}... ({word_count} words)")

            # Be polite
            time.sleep(0.5)

    except Exception as e:
        print(f"  Error processing feed: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Collect Substack posts from RSS feeds")
    parser.add_argument("--max-posts", type=int, default=100,
                        help="Maximum posts per feed (default: 100)")
    parser.add_argument("--output", type=str, default="transcripts/_pool/substack",
                        help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting posts from {len(FEEDS)} feeds")
    print(f"Output directory: {output_dir}")
    print(f"Minimum words per post: {MIN_WORDS} (~10 minute read)")
    print(f"Maximum posts per feed: {args.max_posts}")

    all_stats = []

    for feed_url in FEEDS:
        stats = process_feed(feed_url, output_dir, args.max_posts)
        all_stats.append(stats)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_saved = 0
    for stats in all_stats:
        print(f"\n{stats['name']}:")
        print(f"  Saved: {stats['saved']} posts")
        print(f"  Skipped (too short): {stats['skipped_short']}")
        print(f"  Skipped (exists): {stats['skipped_exists']}")
        if stats["oldest_date"] and stats["newest_date"]:
            print(f"  Date range: {stats['oldest_date']} to {stats['newest_date']}")
        total_saved += stats["saved"]

    print(f"\nTotal posts saved: {total_saved}")
    print(f"Output directory: {output_dir}")

    # Save stats to JSON
    stats_file = output_dir / "_stats.json"
    with open(stats_file, "w") as f:
        json.dump(all_stats, f, indent=2)
    print(f"Stats saved to: {stats_file}")


if __name__ == "__main__":
    main()
