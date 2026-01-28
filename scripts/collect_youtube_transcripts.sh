#!/usr/bin/env bash
set -euo pipefail

MAX_TRANSCRIPTS="${1:-100}"
POOL_ROOT="transcripts/_pool/youtube"

# Channel list: handle|url
CHANNELS=(
  "heathercoxrichardson|https://www.youtube.com/@heathercoxrichardson"
  "NateBJones|https://www.youtube.com/@NateBJones"
  "philosophizethispodcast|https://www.youtube.com/@philosophizethispodcast"
  "PolarityMusic|https://www.youtube.com/@PolarityMusic"
  "BRicey|https://www.youtube.com/@BRicey"
  "closereadingpoetry|https://www.youtube.com/@closereadingpoetry"
  "3blue1brown|https://www.youtube.com/@3blue1brown"
  "veritasium|https://www.youtube.com/@veritasium"
  "NovaraMedia|https://www.youtube.com/@NovaraMedia"
  "profjeffreykaplan|https://www.youtube.com/@profjeffreykaplan"
  "aiexplained-official|https://www.youtube.com/@aiexplained-official"
  "StefanMilo|https://www.youtube.com/@StefanMilo"
  "KnowingBetter|https://www.youtube.com/@KnowingBetter"
  "dancarlinpodcaster|https://www.youtube.com/@dancarlinpodcaster"
  "ContraPoints|https://www.youtube.com/@ContraPoints"
  "hellswelles|https://www.youtube.com/@hellswelles"
  "joshstarmer|https://www.youtube.com/c/joshstarmer"
)

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

convert_srt_to_txt() {
  local srt_file="$1"
  local txt_file="${srt_file%.srt}.txt"
  # Remove sequence numbers, timestamps, and blank lines
  sed '/^[0-9]*$/d; /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]/d; /^$/d' "$srt_file" > "$txt_file"
}

pick_preferred_srt() {
  local files=("$@")
  local preferred=""

  for f in "${files[@]}"; do
    if [[ "$f" == *.en.srt ]]; then
      preferred="$f"
      break
    fi
  done

  if [ -z "$preferred" ]; then
    for f in "${files[@]}"; do
      if [[ "$f" == *.en-US.srt ]]; then
        preferred="$f"
        break
      fi
    done
  fi

  if [ -z "$preferred" ]; then
    preferred="${files[0]}"
  fi

  echo "$preferred"
}

require_command yt-dlp
require_command sed

mkdir -p "$POOL_ROOT"

for entry in "${CHANNELS[@]}"; do
  IFS='|' read -r handle url <<< "$entry"
  channel_dir="$POOL_ROOT/$handle"
  mkdir -p "$channel_dir"

  echo "==> Fetching transcripts for $handle"

  existing=$(find "$channel_dir" -maxdepth 1 -type f -name "*.txt" | wc -l | tr -d ' ')
  count="$existing"
  if [ "$count" -ge "$MAX_TRANSCRIPTS" ]; then
    echo "  Already have $count transcripts for $handle; skipping."
    continue
  fi

  # Get video IDs in reverse chronological order
  list_file="$channel_dir/video_ids.txt"
  yt-dlp --flat-playlist --print "%(id)s" "${url}/videos" > "$list_file" 2>/dev/null || true
  while IFS= read -r video_id; do
    if [ "$count" -ge "$MAX_TRANSCRIPTS" ]; then
      break
    fi
    if [ -z "$video_id" ]; then
      continue
    fi
    if ls "$channel_dir"/*"${video_id}"*.txt >/dev/null 2>&1; then
      continue
    fi

    yt-dlp \
      --write-auto-sub \
      --sub-lang "en,en-US,en-GB" \
      --sub-format srt \
      --skip-download \
      --ignore-errors \
      --sleep-interval 1 \
      --max-sleep-interval 3 \
      --no-progress \
      --output "$channel_dir/%(upload_date)s_%(id)s.%(ext)s" \
      "https://www.youtube.com/watch?v=${video_id}" >/dev/null 2>&1 || true

    shopt -s nullglob
    srt_candidates=("$channel_dir"/*"${video_id}"*.srt)
    shopt -u nullglob

    if [ "${#srt_candidates[@]}" -gt 0 ]; then
      preferred_srt=$(pick_preferred_srt "${srt_candidates[@]}")

      for f in "${srt_candidates[@]}"; do
        if [ "$f" != "$preferred_srt" ]; then
          rm -f "$f"
        fi
      done

      convert_srt_to_txt "$preferred_srt"
      rm -f "$preferred_srt"

      count=$((count + 1))
      echo "  [$count/$MAX_TRANSCRIPTS] $handle -> $video_id"
    fi
  done < "$list_file"

  if [ "$count" -lt "$MAX_TRANSCRIPTS" ]; then
    echo "Warning: $handle only has $count transcripts available in the channel list." >&2
  fi

done

echo "Done. Transcripts saved under $POOL_ROOT/"
