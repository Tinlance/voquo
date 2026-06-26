"""
broll_downloader.py — Voquo v2.0
----------------------------------
Downloads B-roll video clips from Pexels API
based on keywords extracted from the script.
Maps clips to scenes for render_ffmpeg.py.

- Extracts keywords from scene text
- Queries Pexels for vertical video clips
- Downloads up to 5 unique clips
- Cycles clips across 34 scenes
- Falls back to black background if no clips found
"""

import json
import os
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


BACKGROUNDS_DIR = Path("backgrounds")
SCRIPT_PATH     = Path("script.json")
MAPPING_PATH    = Path("backgrounds/scene_mapping.json")

PEXELS_API      = "https://api.pexels.com/videos/search"
MAX_CLIPS       = 5
MIN_DURATION    = 5   # seconds
ORIENTATION     = "portrait"  # 9:16 vertical

# Keywords that work well for dark philosophy/cybersecurity content
FALLBACK_KEYWORDS = [
    "dark abstract",
    "particle background dark",
    "dark space stars",
    "dark waves",
    "dark forest"
]

# Scene keyword extraction — map common themes to search terms
KEYWORD_MAP = {
    # Philosophy / neuroscience
    "brain": "neuron brain abstract",
    "mind": "dark abstract mind",
    "consciousness": "dark particle consciousness",
    "fear": "dark shadow forest",
    "dark": "dark abstract black",
    "darkness": "dark night abstract",
    "death": "dark dramatic sky",
    "ancestors": "ancient dark forest",
    "evolution": "dark nature abstract",
    "pattern": "dark geometric pattern",
    "memory": "dark light bokeh",
    "dream": "dark surreal abstract",

    # Cybersecurity / tech
    "hack": "computer code dark",
    "hacker": "dark terminal code",
    "computer": "dark technology server",
    "code": "matrix code dark",
    "network": "dark network abstract",
    "server": "dark server room",
    "data": "dark data stream",
    "cyber": "dark cyber abstract",
    "virus": "dark particles abstract",
    "security": "dark lock technology",

    # Universal dramatic
    "war": "dramatic dark sky",
    "power": "dark lightning storm",
    "control": "dark city night",
    "time": "dark clock abstract",
    "human": "dark silhouette dramatic",
}


def extract_keywords(scenes: list) -> list:
    """Extract search keywords from scene texts."""
    all_text = " ".join(s.get("text", "") for s in scenes).lower()
    all_text = re.sub(r"[^a-z\s]", " ", all_text)
    words = set(all_text.split())

    found_terms = []
    for word, search_term in KEYWORD_MAP.items():
        if word in words and search_term not in found_terms:
            found_terms.append(search_term)
        if len(found_terms) >= MAX_CLIPS:
            break

    # Fill remaining slots with fallbacks
    for fb in FALLBACK_KEYWORDS:
        if len(found_terms) >= MAX_CLIPS:
            break
        if fb not in found_terms:
            found_terms.append(fb)

    return found_terms[:MAX_CLIPS]


def search_pexels(query: str, api_key: str) -> dict:
    """Search Pexels for a vertical video clip."""
    headers = {"Authorization": api_key}
    params  = {
        "query":       query,
        "orientation": ORIENTATION,
        "size":        "medium",
        "per_page":    5,
    }

    try:
        response = requests.get(PEXELS_API, headers=headers,
                                params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            for video in videos:
                duration = video.get("duration", 0)
                if duration >= MIN_DURATION:
                    # Get best quality HD file
                    for vf in video.get("video_files", []):
                        if (vf.get("quality") in ["hd", "sd"] and
                                vf.get("height", 0) >= 720):
                            return {
                                "id":    video["id"],
                                "url":   vf["link"],
                                "query": query,
                                "duration": duration
                            }
    except Exception as e:
        print(f"  ⚠️  Pexels search failed for '{query}': {e}")

    return None


def download_clip(url: str, path: Path) -> bool:
    """Download a video clip from URL."""
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  ✅ Downloaded: {path.name} ({size_mb:.1f} MB)")
            return True
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
    return False


def build_scene_mapping(clips: list, total_scenes: int) -> dict:
    """
    Map clips to scenes by cycling.
    scenes 1-7 → clip 1
    scenes 8-14 → clip 2
    etc.
    """
    mapping = {}
    if not clips:
        return mapping

    scenes_per_clip = max(1, total_scenes // len(clips))

    for scene_id in range(1, total_scenes + 1):
        clip_index = min((scene_id - 1) // scenes_per_clip, len(clips) - 1)
        mapping[str(scene_id)] = clips[clip_index]

    return mapping


def run():
    """Main B-roll download function."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("❌ PEXELS_API_KEY not found in .env")
        print("   Add: PEXELS_API_KEY=your-key-here")
        return False

    if not SCRIPT_PATH.exists():
        print("❌ script.json not found. Run script generator first.")
        return False

    with open(SCRIPT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    scenes = data if isinstance(data, list) else data.get("scenes", [])
    if not scenes:
        print("❌ No scenes found in script.json")
        return False

    BACKGROUNDS_DIR.mkdir(exist_ok=True)

    print(f"🔍 Extracting keywords from {len(scenes)} scenes...")
    keywords = extract_keywords(scenes)
    print(f"📝 Search terms: {keywords}\n")

    downloaded_clips = []
    existing = list(BACKGROUNDS_DIR.glob("broll_*.mp4"))

    # Clear old B-roll clips for fresh download
    for old in existing:
        old.unlink()

    for i, query in enumerate(keywords):
        print(f"🌐 Searching Pexels: '{query}'...")
        result = search_pexels(query, api_key)

        if result:
            filename = f"broll_{i+1:02d}.mp4"
            filepath = BACKGROUNDS_DIR / filename
            if download_clip(result["url"], filepath):
                downloaded_clips.append(str(filepath))
                result["local_path"] = str(filepath)
        else:
            print(f"  ⚠️  No clip found for '{query}' — will use black bg")

        # Rate limit protection
        time.sleep(0.5)

    print(f"\n📊 Downloaded: {len(downloaded_clips)}/{len(keywords)} clips")

    if not downloaded_clips:
        print("⚠️  No clips downloaded — render will use black background")
        return True

    # Build scene mapping
    mapping = build_scene_mapping(downloaded_clips, len(scenes))

    # Save mapping for render_ffmpeg.py
    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "clips":   downloaded_clips,
            "mapping": mapping,
            "total_scenes": len(scenes)
        }, f, indent=2)

    print(f"✅ Scene mapping saved → {MAPPING_PATH}")
    print(f"🎬 {len(downloaded_clips)} clips cycling across {len(scenes)} scenes")

    return True


if __name__ == "__main__":
    run()
