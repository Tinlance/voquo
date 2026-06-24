"""
sync_whisper.py
---------------
OpenAI Whisper word-level timestamp extractor.
Processes each scene WAV → precise millisecond word boundaries.
Used by FFmpeg renderer to flash text cards in sync with voice.
"""

import json
import sys
import subprocess
from pathlib import Path


AUDIO_DIR = Path("output/audio")
SYNC_DIR = Path("output/sync")
WHISPER_MODEL = "base"  # Fast + accurate enough. Upgrade to "small" for better accuracy.


def install_whisper():
    """Install openai-whisper if not already installed."""
    try:
        import whisper
    except ImportError:
        print("📦 Installing openai-whisper...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "openai-whisper", "--quiet"
        ])
        print("✅ openai-whisper installed")


def load_manifest(path: Path) -> list:
    """Load audio manifest from TTS stage."""
    manifest_path = path / "audio_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            "audio_manifest.json not found. Run tts_kokoro.py first."
        )
    with open(manifest_path, "r") as f:
        return json.load(f)


def extract_word_timestamps(model, audio_path: str) -> list:
    """
    Run Whisper with word_timestamps=True.
    Returns list of word dicts: {word, start, end}
    """
    result = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
        fp16=False  # CPU-safe — auto-uses CUDA if available
    )

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": round(w["start"], 4),
                "end": round(w["end"], 4)
            })
    return words


def build_flash_cards(words: list, fragment_size: int = 3) -> list:
    """
    Group words into flash card fragments (3-4 words each).
    Matches the Bliss Point Pacing rule from the pipeline spec.
    Returns list of {text, start, end} cards.
    """
    cards = []
    i = 0
    while i < len(words):
        chunk = words[i:i + fragment_size]
        card_text = " ".join(w["word"] for w in chunk).strip()
        card_start = chunk[0]["start"]
        card_end = chunk[-1]["end"]
        cards.append({
            "text": card_text,
            "start": round(card_start, 4),
            "end": round(card_end, 4)
        })
        i += fragment_size
    return cards


def run():
    install_whisper()
    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    import whisper
    print(f"🧠 Loading Whisper '{WHISPER_MODEL}' model...")
    model = whisper.load_model(WHISPER_MODEL)
    print("✅ Whisper loaded\n")

    manifest = load_manifest(AUDIO_DIR)
    print(f"🎵 Processing {len(manifest)} audio files...\n")

    all_sync = []
    for item in manifest:
        scene_id = item["id"]
        audio_path = item["audio_path"]
        out_path = SYNC_DIR / f"scene_{scene_id:02d}_sync.json"

        if out_path.exists():
            print(f"  ⏭️  Scene {scene_id:02d} sync already exists — skipping")
            with open(out_path) as f:
                sync_data = json.load(f)
            all_sync.append(sync_data)
            continue

        print(f"  🔍 Scene {scene_id:02d}: extracting word timestamps...")
        words = extract_word_timestamps(model, audio_path)
        cards = build_flash_cards(words, fragment_size=3)

        sync_data = {
            "id": scene_id,
            "audio_path": audio_path,
            "words": words,
            "flash_cards": cards,
            "total_duration": words[-1]["end"] if words else 0
        }

        with open(out_path, "w") as f:
            json.dump(sync_data, f, indent=2)

        print(f"  ✅  {len(cards)} flash cards → {out_path.name}")
        all_sync.append(sync_data)

    master_path = SYNC_DIR / "sync_manifest.json"
    with open(master_path, "w") as f:
        json.dump(all_sync, f, indent=2)

    print(f"\n✅ All {len(all_sync)} scenes synced")
    print(f"📋 Sync manifest → {master_path}")
    return all_sync


if __name__ == "__main__":
    run()
