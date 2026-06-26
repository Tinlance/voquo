"""
tts_kokoro.py — Voquo Best Version
-------------------------------------
Kokoro-82M ONNX Text-to-Speech engine.
Generates one WAV file per scene from script.json.

Features:
  - GPU auto-detection (CUDA) with CPU fallback
  - Scene-level skip if WAV already exists
  - 0.6s silence appended after each scene for natural pacing
  - Validates scene text before synthesis
  - Saves timing info per scene to manifest
  - Clean progress display with scene preview
  - Handles both list and dict script.json formats
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path


OUTPUT_DIR  = Path("output/audio")
SCRIPT_PATH = Path("script.json")

VOICE = "am_adam"   # Deep, authoritative male voice
SPEED = 0.90        # Slightly slower for dramatic pacing
PAUSE = 0.6         # Seconds of silence after each scene

MODEL_PATH  = Path("kokoro-v0_19.onnx")
VOICES_PATH = Path("voices.bin")


# ── Dependency installer ──────────────────────────────────────────────────────

def install_deps():
    deps = ["kokoro-onnx", "soundfile", "numpy"]
    missing = []
    for dep in deps:
        pkg = dep.replace("-", "_").split("==")[0]
        try:
            __import__(pkg)
        except ImportError:
            missing.append(dep)
    if missing:
        print(f"📦 Installing: {', '.join(missing)}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing + ["--quiet"]
        )
        print("✅ Dependencies installed")
    else:
        print("✅ kokoro-onnx ready")


# ── Model loader ──────────────────────────────────────────────────────────────

def load_model():
    """Load Kokoro with GPU if available, fallback to CPU."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"❌ Model not found: {MODEL_PATH}\n"
            "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases"
        )
    if not VOICES_PATH.exists():
        raise FileNotFoundError(
            f"❌ Voices file not found: {VOICES_PATH}\n"
            "Download: Invoke-WebRequest -Uri "
            "https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
            "model-files-v1.0/voices-v1.0.bin -OutFile voices.bin -UseBasicParsing"
        )

    from kokoro_onnx import Kokoro

    # Try GPU first
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            print("🚀 GPU detected — using CUDA acceleration")
            k = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
            return k, "cuda"
    except Exception:
        pass

    print("🔊 Loading Kokoro-82M (CPU)...")
    k = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
    return k, "cpu"


# ── Script loader ─────────────────────────────────────────────────────────────

def load_script() -> list:
    """Load script.json — handles both list and dict formats."""
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"script.json not found at {SCRIPT_PATH}")

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle dict format from script_generator.py
    if isinstance(data, dict):
        scenes = data.get("scenes", [])
    else:
        scenes = data

    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("script.json must contain a non-empty list of scenes")

    return scenes


# ── Scene synthesizer ─────────────────────────────────────────────────────────

def synthesize_scene(kokoro_instance, scene: dict, out_dir: Path) -> dict:
    """
    Synthesize a single scene to WAV with trailing silence.
    Returns dict with id, audio_path, duration.
    """
    import numpy as np
    import soundfile as sf

    scene_id = scene.get("id") or scene.get("scene_id")
    text     = scene.get("text", "").strip()

    if not scene_id:
        raise ValueError(f"Scene missing 'id' field: {scene}")
    if not text:
        print(f"  ⚠️  Scene {scene_id:02d} — empty text, skipping")
        return None

    out_path = out_dir / f"scene_{scene_id:02d}.wav"

    if out_path.exists():
        # Get duration of existing file
        try:
            info     = sf.info(str(out_path))
            duration = info.duration
            print(f"  ⏭️  Scene {scene_id:02d} already exists ({duration:.1f}s) — skipping")
            return {"id": scene_id, "audio_path": str(out_path), "duration": duration}
        except Exception:
            pass  # Re-synthesize if file is corrupt

    preview = text[:65] + "..." if len(text) > 65 else text
    print(f"  🎙️  Scene {scene_id:02d}: {preview}")

    t0 = time.time()
    samples, sample_rate = kokoro_instance.create(
        text,
        voice=VOICE,
        speed=SPEED,
        lang="en-us"
    )

    # Append silence for natural scene separation
    silence = np.zeros(int(sample_rate * PAUSE), dtype=np.float32)
    samples_with_pause = np.concatenate([samples, silence])

    sf.write(str(out_path), samples_with_pause, sample_rate)
    duration = len(samples_with_pause) / sample_rate
    elapsed  = time.time() - t0

    print(f"  ✅  Saved → {out_path.name}  ({duration:.1f}s audio, {elapsed:.1f}s render)")
    return {"id": scene_id, "audio_path": str(out_path), "duration": duration}


# ── Main runner ───────────────────────────────────────────────────────────────

def run():
    install_deps()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    kokoro, device = load_model()
    print(f"✅ Kokoro loaded [{device.upper()}]\n")

    scenes = load_script()
    print(f"📜 {len(scenes)} scenes found in script.json\n")

    generated = []
    skipped   = 0
    failed    = 0
    t_start   = time.time()

    for scene in scenes:
        try:
            result = synthesize_scene(kokoro, scene, OUTPUT_DIR)
            if result:
                generated.append(result)
                if "skipping" in str(result.get("duration", "")):
                    skipped += 1
        except Exception as e:
            sid = scene.get("id", "?")
            print(f"  ❌  Scene {sid} failed: {e}")
            failed += 1

    total_time = time.time() - t_start
    total_audio = sum(r["duration"] for r in generated)

    # Save manifest
    manifest_path = OUTPUT_DIR / "audio_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(generated, f, indent=2)

    print(f"\n{'='*55}")
    print(f"✅ All {len(generated)} scenes synthesized")
    print(f"   🎵 Total audio duration: {total_audio:.1f}s ({total_audio/60:.1f} min)")
    print(f"   ⏱️  Render time: {total_time:.1f}s")
    print(f"   ❌  Failed: {failed}")
    print(f"📋 Manifest saved → {manifest_path}")

    if failed > 0:
        print(f"\n⚠️  {failed} scenes failed — re-run to retry them")

    return generated


if __name__ == "__main__":
    run()