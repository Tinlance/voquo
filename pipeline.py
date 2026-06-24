"""
pipeline.py
-----------
Main orchestrator for the AI Video Factory Track A pipeline.

Run order:
  1. tts_kokoro.py     — synthesize voice audio per scene
  2. sync_whisper.py   — extract word timestamps
  3. render_ffmpeg.py  — render final video

Usage:
  python pipeline.py              # Run full pipeline
  python pipeline.py --tts        # TTS only
  python pipeline.py --sync       # Sync only
  python pipeline.py --render     # Render only
  python pipeline.py --test       # Run test suite
"""

import sys
import argparse
import time
from pathlib import Path


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║        AI VIDEO FACTORY — Track A Pipeline           ║
║   Script → Voice → Sync → Render → final.mp4        ║
╚══════════════════════════════════════════════════════╝
""")


def check_prerequisites():
    """Check all required files exist before running."""
    errors = []

    if not Path("script.json").exists():
        errors.append("❌ script.json not found")

    if not Path("backgrounds").exists() or not list(Path("backgrounds").glob("*.mp4")):
        print("⚠️  Warning: No background videos found in backgrounds/")
        print("   Download free dark abstract loops from:")
        print("   https://www.pexels.com/search/videos/dark%20abstract/")
        print("   Place .mp4 files in the backgrounds/ folder\n")

    if not Path("music").exists() or not (
        list(Path("music").glob("*.mp3")) + list(Path("music").glob("*.wav"))
    ):
        print("⚠️  Warning: No music found in music/")
        print("   Download free drone tracks from:")
        print("   https://www.youtube.com/audiolibrary")
        print("   Place .mp3 files in the music/ folder\n")

    if errors:
        for e in errors:
            print(e)
        sys.exit(1)


def run_stage(name: str, module_func):
    """Run a pipeline stage with timing and error handling."""
    print(f"\n{'='*54}")
    print(f"  STAGE: {name}")
    print(f"{'='*54}\n")
    start = time.time()
    try:
        result = module_func()
        elapsed = time.time() - start
        print(f"\n✅ {name} complete ({elapsed:.1f}s)")
        return result
    except Exception as e:
        print(f"\n❌ {name} failed: {e}")
        sys.exit(1)


def run_tests():
    """Run the test suite."""
    import subprocess
    print("\n🧪 Running test suite...\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=False
    )
    if result.returncode != 0:
        print("\n❌ Tests failed. Fix failing tests before running pipeline.")
        sys.exit(1)
    print("\n✅ All tests passed")


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="AI Video Factory Pipeline")
    parser.add_argument("--tts", action="store_true", help="Run TTS stage only")
    parser.add_argument("--sync", action="store_true", help="Run sync stage only")
    parser.add_argument("--render", action="store_true", help="Run render stage only")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    check_prerequisites()

    if args.tts:
        from tts_kokoro import run as tts_run
        run_stage("TTS — Kokoro Voice Synthesis", tts_run)

    elif args.sync:
        from sync_whisper import run as sync_run
        run_stage("SYNC — Whisper Word Timestamps", sync_run)

    elif args.render:
        from render_ffmpeg import run as render_run
        run_stage("RENDER — FFmpeg Video Render", render_run)

    else:
        # Full pipeline
        total_start = time.time()

        from tts_kokoro import run as tts_run
        from sync_whisper import run as sync_run
        from render_ffmpeg import run as render_run

        run_stage("TTS — Kokoro Voice Synthesis", tts_run)
        run_stage("SYNC — Whisper Word Timestamps", sync_run)
        run_stage("RENDER — FFmpeg Video Render", render_run)

        total_elapsed = time.time() - total_start
        print(f"\n{'='*54}")
        print(f"  🎉 FULL PIPELINE COMPLETE ({total_elapsed:.1f}s)")
        print(f"  📁 Output: output/final.mp4")
        print(f"{'='*54}\n")


if __name__ == "__main__":
    main()
