# AI Video Factory — Track A (Free Local Pipeline)

Automated faceless video essay generator for TikTok & YouTube.
**Total cost: $0/month**

## Pipeline Flow

```
script.json → Kokoro TTS → Whisper Sync → FFmpeg Render → final.mp4
```

## Quick Start (Windows 11)

### Step 1 — Install FFmpeg
1. Download from: https://www.gyan.dev/ffmpeg/builds/
2. Get `ffmpeg-release-essentials.zip`
3. Extract to `C:\ffmpeg\`
4. Add `C:\ffmpeg\bin` to your Windows PATH:
   - Search "Edit the system environment variables" in Start
   - Click Environment Variables → Edit PATH → New → `C:\ffmpeg\bin`
   - Restart your terminal

### Step 2 — Run Setup
```batch
setup.bat
```
This installs all Python dependencies automatically.

### Step 3 — Add Assets
**Background videos** (put in `backgrounds/` folder):
- Download 3-5 free dark abstract loops from Pexels:
  https://www.pexels.com/search/videos/dark%20abstract/
- Recommended searches: "dark particles", "neural network", "space loop"

**Drone music** (put in `music/` folder):
- Download from YouTube Audio Library:
  https://www.youtube.com/audiolibrary
- Search: "ambient drone" or "dark atmospheric"
- Pick any track under 5 minutes

### Step 4 — Run Tests
```batch
python pipeline.py --test
```

### Step 5 — Generate Video
```batch
python pipeline.py
```

Your video will be at `output/final.mp4` — ready for TikTok/YouTube.

---

## Individual Stages

Run stages independently for debugging:

```batch
# TTS only — generates voice audio
python pipeline.py --tts

# Sync only — extracts word timestamps
python pipeline.py --sync

# Render only — builds final video
python pipeline.py --render
```

---

## File Structure

```
video_factory/
├── setup.bat              ← Run this first
├── pipeline.py            ← Main orchestrator
├── tts_kokoro.py          ← Kokoro-82M voice synthesis
├── sync_whisper.py        ← Whisper word timestamps
├── render_ffmpeg.py       ← FFmpeg video renderer
├── script.json            ← Your 34-scene script
├── backgrounds/           ← Drop dark loop .mp4 files here
├── music/                 ← Drop drone .mp3 track here
├── output/
│   ├── audio/             ← Generated voice WAV files
│   ├── sync/              ← Word timestamp JSON files
│   ├── scenes/            ← Individual scene MP4s
│   └── final.mp4          ← YOUR FINISHED VIDEO
└── tests/
    └── test_pipeline.py   ← Full TDD test suite
```

---

## Output Specs

| Setting | Value |
|---------|-------|
| Resolution | 1080x1920 (9:16 vertical) |
| FPS | 30 |
| Format | MP4 (H.264 + AAC) |
| Voice | Kokoro-82M — calm, philosophical |
| Text | Word-by-word flash cards, white + teal highlights |
| Music | Drone mixed at -22dB under voice |
| GPU | NVIDIA NVENC auto-detected, CPU fallback |

---

## Customization

### Change the voice
Edit `tts_kokoro.py` line 18:
```python
VOICE = "af_heart"   # calm female (default)
# VOICE = "am_adam"  # deep male
# VOICE = "af_sky"   # bright female
```

### Change flash card size
Edit `sync_whisper.py` line 17:
```python
fragment_size=3   # 3 words per card (default)
# fragment_size=4 # slower, more words per flash
# fragment_size=1 # word-by-word (most aggressive)
```

### Change emphasis color
Edit `render_ffmpeg.py` line 30:
```python
EMPHASIS_COLOR = "#00e5c8"  # Tinlance teal (default)
# EMPHASIS_COLOR = "#ff4d6d"  # Tinlance pink
# EMPHASIS_COLOR = "#ffff00"  # Yellow
```

### Add new emphasis words
Edit `render_ffmpeg.py` line 34:
```python
EMPHASIS_WORDS = {
    "hunting", "survival", "predator", ...
    # Add your own keywords here
}
```

---

## Scaling to Volume

To generate a new video:
1. Replace `script.json` with new 34-scene script
2. Run `python pipeline.py`
3. Move `output/final.mp4` to your upload folder
4. Repeat

For bulk automation, run multiple scripts sequentially:
```batch
for %%f in (scripts\*.json) do (
    copy %%f script.json
    python pipeline.py
    move output\final.mp4 output\%%~nf.mp4
)
```

---

## Troubleshooting

**FFmpeg not found:** Add `C:\ffmpeg\bin` to PATH (see Step 1)

**Kokoro model not downloading:** Check your internet connection — model downloads automatically on first run (~330MB)

**Whisper slow on CPU:** Normal — base model takes ~30s per scene on CPU. Upgrade to NVIDIA GPU for 10x speed.

**Black background instead of loop:** Add .mp4 files to `backgrounds/` folder

**No music in output:** Add .mp3 file to `music/` folder
