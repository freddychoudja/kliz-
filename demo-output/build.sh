#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== Step 1: Screenshot HTML scenes ==="
mkdir -p frames
for scene in scenes/*.html; do
  name=$(basename "$scene" .html)
  echo "  → $name"
  playwright screenshot --viewport-size="1920,1080" --full-page "$scene" "frames/${name}.png"
done

echo ""
echo "=== Step 2: Generate narration audio ==="
mkdir -p audio
for txt in narration/*.txt; do
  name=$(basename "$txt" .txt)
  echo "  → $name"
  edge-tts --voice en-US-GuyNeural --text "$(cat "$txt")" --write-media "audio/${name}.mp3"
done

echo ""
echo "=== Step 3: Build video with ffmpeg ==="

# Create silence padding for each scene duration
> filelist.txt
for scene in scenes/*.html; do
  name=$(basename "$scene" .html)
  dur=$(python3 -c "import json; d=json.load(open('scenes.json')); print([s['duration'] for s in d['scenes'] if s['id']=='${name}'][0])")
  # Create video from still image
  ffmpeg -y -loop 1 -i "frames/${name}.png" -i "audio/${name}.mp3" \
    -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
    -vf "scale=1920:1080" -pix_fmt yuv420p \
    -t "$dur" -shortest \
    "frames/${name}.mp4" 2>/dev/null
  echo "file 'frames/${name}.mp4'" >> filelist.txt
done

echo "  → Concatenating with crossfade..."
# Simple concat (crossfade needs complex filter, use simple concat for now)
ffmpeg -y -f concat -safe 0 -i filelist.txt -c:v libx264 -c:a aac \
  -movflags +faststart output.mp4 2>/dev/null

echo ""
echo "✅ Done! Output: output.mp4"
echo "   Duration: $(ffprobe -v error -show_entries format=duration -of csv=p=0 output.mp4)s"
