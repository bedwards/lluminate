# Downloading YouTube Transcripts

This guide covers how to download transcripts (subtitles/captions) from YouTube videos using `yt-dlp`.

## Prerequisites

Install yt-dlp:

```bash
# macOS
brew install yt-dlp

# Linux
pip install yt-dlp

# Windows
winget install yt-dlp
```

## Basic Usage

### Single Video

Download auto-generated subtitles for one video:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download "https://www.youtube.com/watch?v=VIDEO_ID"
```

Flags:
- `--write-auto-sub`: Download auto-generated subtitles
- `--sub-lang en`: English language (change as needed)
- `--skip-download`: Don't download the video itself

### From a Channel

Download transcripts from all videos on a channel:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download "https://www.youtube.com/@ChannelName/videos"
```

Limit to most recent N videos:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --playlist-end 100 "https://www.youtube.com/@ChannelName/videos"
```

### From a Playlist

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

## Output Formats

### SRT Format (Default)

The default output is `.en.srt` files with timestamps:

```
1
00:00:00,000 --> 00:00:03,500
Hello and welcome to this tutorial

2
00:00:03,500 --> 00:00:07,200
Today we're going to learn about
```

### VTT Format

```bash
yt-dlp --write-auto-sub --sub-lang en --sub-format vtt --skip-download "URL"
```

## Converting SRT to Plain Text

SRT files contain timestamps and sequence numbers. To extract just the text:

### Using sed

```bash
# Remove timestamps, sequence numbers, and blank lines
sed '/^[0-9]*$/d; /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d; /^$/d' input.srt > output.txt
```

### Using a Bash Script

Create `convert_srt_to_txt.sh`:

```bash
#!/bin/bash
# Convert all SRT files in current directory to TXT

for srt_file in *.srt; do
    if [ -f "$srt_file" ]; then
        txt_file="${srt_file%.srt}.txt"
        # Remove sequence numbers, timestamps, and blank lines
        sed '/^[0-9]*$/d; /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d; /^$/d' "$srt_file" > "$txt_file"
        echo "Converted: $srt_file -> $txt_file"
    fi
done
```

### Using Python

```python
#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def srt_to_text(srt_content: str) -> str:
    """Extract plain text from SRT subtitle content."""
    # Remove sequence numbers (lines that are just digits)
    text = re.sub(r'^\d+\s*$', '', srt_content, flags=re.MULTILINE)
    # Remove timestamps
    text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', text)
    # Remove HTML-like tags (some subtitles have formatting)
    text = re.sub(r'<[^>]+>', '', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

if __name__ == "__main__":
    for srt_path in Path(".").glob("*.srt"):
        txt_path = srt_path.with_suffix(".txt")
        content = srt_path.read_text(encoding="utf-8")
        txt_path.write_text(srt_to_text(content), encoding="utf-8")
        print(f"Converted: {srt_path} -> {txt_path}")
```

## Batch Download Script

A complete script to download and convert transcripts from a channel:

```bash
#!/bin/bash
# download_transcripts.sh
# Usage: ./download_transcripts.sh "https://www.youtube.com/@ChannelName/videos" [max_videos]

CHANNEL_URL="$1"
MAX_VIDEOS="${2:-50}"  # Default to 50 videos
OUTPUT_DIR="transcripts"

if [ -z "$CHANNEL_URL" ]; then
    echo "Usage: $0 <channel_url> [max_videos]"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "Downloading up to $MAX_VIDEOS transcripts..."

# Download subtitles
yt-dlp \
    --write-auto-sub \
    --sub-lang en \
    --sub-format srt \
    --skip-download \
    --playlist-end "$MAX_VIDEOS" \
    --output "%(title)s.%(ext)s" \
    "$CHANNEL_URL"

echo "Converting SRT to TXT..."

# Convert each SRT to plain text
for srt_file in *.srt; do
    if [ -f "$srt_file" ]; then
        txt_file="${srt_file%.en.srt}.txt"
        sed '/^[0-9]*$/d; /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d; /^$/d' "$srt_file" > "$txt_file"
        rm "$srt_file"  # Remove SRT after conversion
        echo "Created: $txt_file"
    fi
done

echo "Done! Transcripts saved to $OUTPUT_DIR/"
```

## Handling Common Issues

### No Subtitles Available

Some videos don't have auto-generated captions. Add `--ignore-errors` to continue past failures:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --ignore-errors "URL"
```

### Rate Limiting

YouTube may rate-limit aggressive downloads. Add delays:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --sleep-interval 2 --max-sleep-interval 5 "URL"
```

### Multiple Languages

Download all available subtitle languages:

```bash
yt-dlp --write-auto-sub --all-subs --skip-download "URL"
```

Or specify multiple:

```bash
yt-dlp --write-auto-sub --sub-lang "en,es,fr" --skip-download "URL"
```

### Filename Sanitization

Use a template to control output filenames:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download \
    --output "%(upload_date)s - %(title).50s.%(ext)s" "URL"
```

## Useful yt-dlp Options

| Flag | Description |
|------|-------------|
| `--write-sub` | Download manual subtitles (uploaded by creator) |
| `--write-auto-sub` | Download auto-generated subtitles |
| `--list-subs` | List available subtitles without downloading |
| `--sub-lang LANGS` | Subtitle language(s) to download |
| `--sub-format FORMAT` | Subtitle format: srt, vtt, ass |
| `--skip-download` | Don't download video/audio |
| `--playlist-end N` | Stop after N videos |
| `--output TEMPLATE` | Output filename template |
| `--ignore-errors` | Continue on errors |
| `--sleep-interval N` | Sleep N seconds between downloads |

## Example: Analyzing Transcripts

Once you have plain text transcripts, you can analyze them:

```bash
# Count total words across all transcripts
wc -w *.txt

# Find videos mentioning a specific term
grep -l "specific term" *.txt

# Extract all unique terms (rough)
cat *.txt | tr ' ' '\n' | sort | uniq -c | sort -rn | head -50
```

## References

- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [SRT Subtitle Format](https://en.wikipedia.org/wiki/SubRip)
