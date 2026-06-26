"""
render_ffmpeg.py — v6 (Image + Video Background Support)
----------------------------------------------------------
Supports per-scene backgrounds:
  - scene_01.jpg / scene_01.png → static image background
  - scene_01.mp4 / scene_01.mov → video background
  - Falls back to broll_*.mp4 cycling if no scene file found
  - Falls back to black if no backgrounds at all
"""

import json
import os
import re as _re
import shutil
import subprocess
import sys
from pathlib import Path


SYNC_DIR     = Path("output/sync")
SCENE_DIR    = Path("output/scenes")
ASS_DIR      = Path("output/ass")
FINAL_DIR    = Path("output")
MUSIC_DIR    = Path("music")

WIDTH        = 1080
HEIGHT       = 1920
FPS          = 30
MUSIC_VOLUME = "0.15"

COLOR_WHITE  = "&H00FFFFFF"
COLOR_TEAL   = "&H00C8E500"
COLOR_BG     = "&H99000000"

EMPHASIS_WORDS = {
    "hunting","survival","predator","paranoia","apophenia",
    "pareidolia","pattern","brain","evolution","death",
    "ancestors","neurons","ancient","threat","randomness",
    "hyper-vigilant","invents","misfiring","irresistible",
    "descendants","terror","fear","mind","consciousness",
    "darkness","dark","shadow","blood","silence","void"
}


def word_is_emphasis(word):
    clean = _re.sub(r"[^a-zA-Z\-]", "", word).lower()
    return clean in EMPHASIS_WORDS


def seconds_to_ass(secs):
    h  = int(secs // 3600)
    m  = int((secs % 3600) // 60)
    s  = int(secs % 60)
    cs = int((secs - int(secs)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass_file(flash_cards, audio_duration, out_path):
    if not flash_cards:
        return False

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: White,Arial,72,{COLOR_WHITE},&H000000FF,&H00000000,{COLOR_BG},-1,0,0,0,100,100,0,0,3,3,0,5,60,60,80,1
Style: Teal,Arial,72,{COLOR_TEAL},&H000000FF,&H00000000,{COLOR_BG},-1,0,0,0,100,100,0,0,3,3,0,5,60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for card in flash_cards:
        start = card["start"]
        end   = min(card["end"] + 0.05, audio_duration)
        text  = card["text"].strip()
        text  = text.replace("{", "").replace("}", "").replace("\n", " ")
        text  = text.replace("'", "\\'")
        style = "Teal" if any(word_is_emphasis(w) for w in text.split()) else "White"
        lines.append(
            f"Dialogue: 0,{seconds_to_ass(start)},{seconds_to_ass(end)},"
            f"{style},,0,0,0,,{text}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))
    return True


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print("❌ FFmpeg not found.")
        sys.exit(1)
    print("✅ FFmpeg found")


def detect_gpu():
    print("ℹ️  Using CPU encoder (libx264)")
    return "cpu"


def get_scene_background(scene_id):
    """
    Check backgrounds/ for a scene-specific file.
    Returns (path, is_image) tuple.
    Checks for exact scene match first, then falls back to cycling broll clips.
    """
    # Check for exact scene match — image or video
    for ext in [".mp4", ".mov", ".jpg", ".jpeg", ".png"]:
        path = Path(f"backgrounds/scene_{scene_id:02d}{ext}")
        if path.exists():
            is_image = ext in [".jpg", ".jpeg", ".png"]
            return str(path), is_image

    # Fall back to cycling broll clips
    clips = sorted(Path("backgrounds").glob("broll_*.mp4"))
    if clips:
        return str(clips[scene_id % len(clips)]), False

    # No background found
    return None, False


def get_music():
    files = (
        list(MUSIC_DIR.glob("*.mp3")) +
        list(MUSIC_DIR.glob("*.wav")) +
        list(MUSIC_DIR.glob("*.m4a"))
    )
    return str(files[0]) if files else None


def render_scene(scene, music_path, ass_path, gpu_mode, out_path,
                 bg_path=None, is_image=False):
    if out_path.exists():
        print(f"  ⏭️  Scene {scene['id']:02d} already rendered — skipping")
        return True

    audio_path = scene["audio_path"]
    duration   = scene["total_duration"]

    if not Path(audio_path).exists():
        print(f"  ❌ Scene {scene['id']:02d} — audio missing: {audio_path}")
        return False

    if not ass_path.exists():
        print(f"  ❌ Scene {scene['id']:02d} — .ass missing: {ass_path}")
        return False

    has_music = music_path and Path(music_path).exists()
    has_bg    = bg_path and Path(bg_path).exists()

    # Windows-safe ASS path
    ass_win = str(ass_path.resolve()).replace("\\", "/").replace(":/", "\\:/", 1)

    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"format=yuv420p,"
        f"ass='{ass_win}'"
    )

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

    # ── Video/Image source ───────────────────────────────────────────
    if has_bg and is_image:
        # Static image — loop for duration of scene
        cmd += ["-loop", "1", "-i", bg_path]
    elif has_bg:
        # Video clip — stream loop
        cmd += ["-stream_loop", "-1", "-i", bg_path]
    else:
        # Pure black background
        cmd += [
            "-f", "lavfi",
            "-i", f"color=c=0x080808:size={WIDTH}x{HEIGHT}:rate={FPS}"
        ]

    # ── Audio ────────────────────────────────────────────────────────
    cmd += ["-i", audio_path]

    if has_music:
        cmd += ["-stream_loop", "-1", "-i", music_path]
        cmd += [
            "-filter_complex",
            (
                f"[1:a]volume=1.0[v];"
                f"[2:a]volume={MUSIC_VOLUME}[m];"
                f"[v][m]amix=inputs=2:duration=first[aout]"
            ),
            "-map", "0:v",
            "-map", "[aout]",
            "-vf", vf
        ]
    else:
        cmd += [
            "-vf", vf,
            "-map", "0:v",
            "-map", "1:a"
        ]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ]

    bg_label = Path(bg_path).name if has_bg else "black"
    bg_type  = "image" if is_image else "video"
    print(f"  🎬 Rendering scene {scene['id']:02d} [{bg_label}] [{bg_type}] ...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ FFmpeg error on scene {scene['id']:02d}:")
        print("     " + result.stderr[-500:].replace("\n", "\n     "))
        return False

    print(f"  ✅ Scene {scene['id']:02d} → {out_path.name}")
    return True


def concatenate_scenes(scene_paths, output_path):
    concat_list = FINAL_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in scene_paths:
            safe = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{safe}'\n")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path)
    ]
    print("\n🔗 Concatenating scenes → final.mp4 ...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Concat failed:")
        print(result.stderr[-400:])
        return False

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✅ final.mp4 → {output_path}  ({size_mb:.1f} MB)")
    return True


def extract_tiktok_cut(scene_paths, output_path):
    hook    = scene_paths[:4]
    payoff  = scene_paths[27:34] if len(scene_paths) >= 34 else scene_paths[-7:]
    clips   = [p for p in hook + payoff if p.exists()]

    if len(clips) < 4:
        print("⚠️  Not enough scenes for TikTok cut — skipping")
        return False

    concat_list = FINAL_DIR / "tiktok_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in clips:
            safe = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{safe}'\n")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path)
    ]
    print("\n✂️  Extracting TikTok 60-sec cut ...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("⚠️  TikTok cut failed")
        return False

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✅ TikTok cut → {output_path}  ({size_mb:.1f} MB)")
    return True


def run(cleanup=False):
    check_ffmpeg()
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    ASS_DIR.mkdir(parents=True, exist_ok=True)

    music_path = get_music()

    if music_path:
        print(f"🎵 Music: {Path(music_path).name}\n")
    else:
        print("ℹ️  No music found — voice only\n")

    manifest_path = SYNC_DIR / "sync_manifest.json"
    if not manifest_path.exists():
        print("❌ sync_manifest.json not found. Run sync stage first.")
        sys.exit(1)

    with open(manifest_path, encoding="utf-8") as f:
        sync_data = json.load(f)

    print(f"🎬 Building .ass files + rendering {len(sync_data)} scenes...\n")

    rendered = []
    failed   = []

    for scene in sync_data:
        sid      = scene["id"]
        out_path = SCENE_DIR / f"scene_{sid:02d}.mp4"
        ass_path = ASS_DIR   / f"scene_{sid:02d}.ass"

        # Get background — image or video
        bg_path, is_image = get_scene_background(sid)

        ok = build_ass_file(scene["flash_cards"], scene["total_duration"], ass_path)
        if not ok:
            print(f"  ⚠️  Scene {sid:02d} — no flash cards, skipping")
            failed.append(sid)
            continue

        ok = render_scene(
            scene, music_path, ass_path, "cpu",
            out_path, bg_path, is_image
        )
        if ok:
            rendered.append(out_path)
        else:
            failed.append(sid)

    print(f"\n📊 Rendered: {len(rendered)}/{len(sync_data)}  |  Failed: {len(failed)}")
    if failed:
        print(f"⚠️  Failed scenes: {failed}")

    if not rendered:
        print("❌ Nothing rendered.")
        sys.exit(1)

    final_path  = FINAL_DIR / "final.mp4"
    success     = concatenate_scenes(rendered, final_path)

    tiktok_path = FINAL_DIR / "tiktok_cut.mp4"
    extract_tiktok_cut(rendered, tiktok_path)

    if success:
        print(f"\n🎉 PIPELINE COMPLETE!")
        print(f"📁 Full video:  {final_path.resolve()}")
        print(f"📱 TikTok cut:  {tiktok_path.resolve()}")

    if cleanup:
        for wav in Path("output/audio").glob("*.wav"):
            wav.unlink()
        for mp4 in SCENE_DIR.glob("*.mp4"):
            mp4.unlink()
        print("🧹 Temp files cleaned")

    return rendered


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    run(cleanup=args.cleanup)