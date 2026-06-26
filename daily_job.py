"""
daily_job.py — Voquo v2.0 (with B-roll)
-----------------------------------------
Daily orchestrator. Picks next topic, generates script,
downloads B-roll, runs full pipeline, creates thumbnail.

Usage:
    python daily_job.py
    python daily_job.py --topic "Custom topic" --mode flashcard
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from topic_bank import get_next_topic, mark_used, load_bank
from script_generator import generate_script
from thumbnail_generator import generate_thumbnail
from broll_downloader import run as download_broll


LOG_DIR  = Path("logs")
LOG_PATH = LOG_DIR / "daily_job.log"


def log(msg: str):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clear_previous_job():
    """Clear intermediate files from previous job."""
    log("Clearing previous job files...")
    cleared = 0

    for p in Path("output/audio").glob("*.wav"):
        p.unlink(); cleared += 1
    for p in Path("output/sync").glob("*.json"):
        p.unlink(); cleared += 1
    for p in Path("output/ass").glob("*.ass"):
        p.unlink(); cleared += 1
    for p in Path("output/scenes").glob("*.mp4"):
        p.unlink(); cleared += 1

    log(f"Cleared {cleared} intermediate files")


def reformat_script():
    """Convert script.json from dict format to list format for TTS."""
    script_path = Path("script.json")
    with open(script_path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        scenes = data.get("scenes", [])
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, indent=2, ensure_ascii=False)
        log(f"Script reformatted: {len(scenes)} scenes")
        return len(scenes)
    return len(data)


def run_stage(stage_flag: str, label: str) -> bool:
    """Run a pipeline.py stage."""
    log(f"Running {label}...")
    result = subprocess.run(
        [sys.executable, "pipeline.py", stage_flag],
        capture_output=False
    )
    if result.returncode == 0:
        log(f"{label} complete")
        return True
    else:
        log(f"ERROR: {label} failed")
        return False


def run(channel: str = "lloydambition",
        mode: str = "flashcard",
        topic_override: str = None,
        skip_broll: bool = False):

    log("=" * 55)
    log("VOQUO DAILY JOB STARTING")
    log("=" * 55)

    # ── Step 1: Get topic ──────────────────────────────────
    if topic_override:
        topic_data = {
            "id": None,
            "topic": topic_override,
            "mode": mode,
            "channel": channel
        }
        log(f"Topic (manual): {topic_override}")
    else:
        try:
            topic_data = get_next_topic(channel=channel, mode=mode)
            log(f"Topic [{topic_data['id']}]: {topic_data['topic']}")
        except ValueError as e:
            log(f"ERROR: {e}")
            sys.exit(1)

    topic    = topic_data["topic"]
    mode     = topic_data.get("mode", mode)
    topic_id = topic_data.get("id")

    # ── Step 2: Generate script ────────────────────────────
    log("Generating script via Claude API...")
    try:
        script = generate_script(
            topic=topic,
            mode=mode,
            output_path="script.json"
        )
        title = script.get("title", topic)
        log(f"Script: '{title}' — {len(script['scenes'])} scenes")
    except Exception as e:
        log(f"ERROR generating script: {e}")
        sys.exit(1)

    # ── Step 3: Clear old files ────────────────────────────
    clear_previous_job()

    # ── Step 4: Reformat script for TTS ───────────────────
    scene_count = reformat_script()
    log(f"Script ready: {scene_count} scenes")

    # ── Step 5: Download B-roll ────────────────────────────
    if not skip_broll and os.getenv("PEXELS_API_KEY"):
        log("Downloading B-roll from Pexels...")
        try:
            download_broll()
            log("B-roll download complete")
        except Exception as e:
            log(f"WARNING: B-roll download failed: {e} — continuing without visuals")
    else:
        if skip_broll:
            log("B-roll skipped (--skip-broll flag)")
        else:
            log("WARNING: PEXELS_API_KEY not set — rendering with black background")

    # ── Step 6: TTS ────────────────────────────────────────
    if not run_stage("--tts", "TTS (Kokoro voice synthesis)"):
        sys.exit(1)

    # ── Step 7: Whisper sync ───────────────────────────────
    if not run_stage("--sync", "Whisper word sync"):
        sys.exit(1)

    # ── Step 8: Render ─────────────────────────────────────
    if not run_stage("--render", "FFmpeg render"):
        sys.exit(1)

    # ── Step 9: Thumbnail ──────────────────────────────────
    log("Generating thumbnail...")
    try:
        bank    = load_bank()
        episode = sum(1 for t in bank if t.get("used", False)) + 1
        generate_thumbnail(
            title=title,
            episode=episode,
            channel=channel,
            output_path="output/thumbnail.jpg"
        )
        log(f"Thumbnail: output/thumbnail.jpg (EP.{episode:03d})")
    except Exception as e:
        log(f"WARNING: Thumbnail failed: {e}")

    # ── Step 10: Mark topic used ───────────────────────────
    if topic_id:
        mark_used(topic_id)
        log(f"Topic {topic_id} marked as used")

    # ── Step 11: Save summary ──────────────────────────────
    summary = {
        "date":    datetime.now().isoformat(),
        "topic":   topic,
        "title":   title,
        "mode":    mode,
        "channel": channel,
        "output": {
            "full_video": "output/final.mp4",
            "tiktok_cut": "output/tiktok_cut.mp4",
            "thumbnail":  "output/thumbnail.jpg"
        }
    }

    summary_path = LOG_DIR / f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    LOG_DIR.mkdir(exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log("=" * 55)
    log("VOQUO DAILY JOB COMPLETE")
    log(f"Full video:  output/final.mp4")
    log(f"TikTok cut:  output/tiktok_cut.mp4")
    log(f"Thumbnail:   output/thumbnail.jpg")
    log(f"Title:       {title}")
    log("=" * 55)
    log("Ready to post manually to YouTube + TikTok + X")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="lloydambition")
    parser.add_argument("--mode", default="flashcard",
                        choices=["flashcard", "documentary"])
    parser.add_argument("--topic", help="Override topic bank")
    parser.add_argument("--skip-broll", action="store_true",
                        help="Skip B-roll download")
    args = parser.parse_args()

    run(
        channel=args.channel,
        mode=args.mode,
        topic_override=args.topic,
        skip_broll=args.skip_broll
    )
