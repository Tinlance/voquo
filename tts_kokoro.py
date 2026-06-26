"""
tts_kokoro.py
-------------
Kokoro-82M ONNX Text-to-Speech engine.
Generates one WAV file per scene from script.json.
CPU-first with CUDA auto-detection.
"""

import json
import os
import sys
import subprocess
from pathlib import Path


OUTPUT_DIR = Path("output/audio")
SCRIPT_PATH = Path("script.json")
VOICE = "am_adam"  # Dark, calm, philosophical female voice
SPEED = 0.92        # Slightly slower for dramatic pacing


def install_kokoro():
    """Install kokoro if not already installed."""
    try:
        import kokoro
    except ImportError:
        print("📦 Installing kokoro-onnx...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "kokoro-onnx", "soundfile", "numpy", "--quiet"
        ])
        print("✅ kokoro-onnx installed")


def load_script(path: Path) -> list:
    """Load and validate script JSON."""
    if not path.exists():
        raise FileNotFoundError(f"script.json not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        scenes = json.load(f)
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("script.json must be a non-empty list")
    return scenes


def synthesize_scene(kokoro_instance, scene: dict, out_dir: Path) -> Path:
    """
    Synthesize a single scene to WAV.
    Returns path to output WAV file.
    """
    scene_id = scene["id"]
    text = scene["text"].strip()
    out_path = out_dir / f"scene_{scene_id:02d}.wav"

    if out_path.exists():
        print(f"  ⏭️  Scene {scene_id:02d} already exists — skipping")
        return out_path

    print(f"  🎙️  Scene {scene_id:02d}: {text[:60]}...")
    samples, sample_rate = kokoro_instance.create(
        text,
        voice=VOICE,
        speed=SPEED,
        lang="en-us"
    )

    import numpy as np
    import soundfile as sf

    silence = np.zeros(int(sample_rate * 0.6), dtype=np.float32)
    samples_with_pause = np.concatenate([samples, silence])
    sf.write(str(out_path), samples_with_pause, sample_rate)
    print(f"  ✅  Saved → {out_path.name}")
    return out_path


def run():
    install_kokoro()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from kokoro_onnx import Kokoro
    print("🔊 Loading Kokoro-82M model...")
    k = Kokoro("kokoro-v0_19.onnx", "voices.bin")
    print("✅ Kokoro loaded\n")

    scenes = load_script(SCRIPT_PATH)
    print(f"📜 {len(scenes)} scenes found in script.json\n")

    generated = []
    for scene in scenes:
        path = synthesize_scene(k, scene, OUTPUT_DIR)
        generated.append({"id": scene["id"], "audio_path": str(path)})

    manifest_path = OUTPUT_DIR / "audio_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(generated, f, indent=2)

    print(f"\n✅ All {len(generated)} scenes synthesized")
    print(f"📋 Manifest saved → {manifest_path}")
    return generated


if __name__ == "__main__":
    run()
