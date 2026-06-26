"""
script_generator.py — Voquo v2.0
----------------------------------
Calls Claude API to generate a 34-scene cinematic script
from a topic. Outputs structured JSON compatible with
the existing v1.0 pipeline (tts_kokoro.py reads this format).

Usage:
    from script_generator import generate_script
    generate_script(topic="The Sony PlayStation hack", mode="flashcard")
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

try:
    import anthropic
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic"])
    import anthropic

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    load_dotenv()


FLASHCARD_PROMPT = """You are a cinematic script writer for a dark, philosophical YouTube channel called LloydAmbition.

Write a 34-scene video script about: {topic}

STRICT RULES:
- Exactly 34 scenes
- Each scene is 1-3 sentences maximum
- Max 20 words per sentence
- Use historical present tense ("The hacker types." not "The hacker typed.")
- Build narrative tension — start with a hook, escalate, deliver a payoff
- No emojis, no bullet points, no headers in the text
- Write for a voice narrator — spoken word style
- Dark, philosophical, authoritative tone
- Global audience — universal themes, not region-specific

OUTPUT FORMAT — return only valid JSON, no markdown, no backticks:
{{
  "title": "video title here",
  "topic": "{topic}",
  "scenes": [
    {{
      "id": 1,
      "text": "scene text here"
    }},
    ...34 scenes total...
  ]
}}"""

DOCUMENTARY_PROMPT = """You are a script writer for a dark cybersecurity documentary channel.

Write a 34-scene documentary script about: {topic}

STRICT RULES:
- Exactly 34 scenes
- Each scene is 2-4 sentences maximum
- Max 12 words per sentence
- Use historical present tense
- Build narrative tension like a true crime documentary
- Include real technical details where appropriate
- Dark, authoritative, investigative tone
- Global audience — universal stakes

OUTPUT FORMAT — return only valid JSON, no markdown, no backticks:
{{
  "title": "video title here",
  "topic": "{topic}",
  "scenes": [
    {{
      "id": 1,
      "text": "scene text here"
    }},
    ...34 scenes total...
  ]
}}"""


def generate_script(topic: str, mode: str = "flashcard", output_path: str = "script.json") -> dict:
    """
    Generate a 34-scene script using Claude API.
    
    Args:
        topic: The video topic
        mode: "flashcard" or "documentary"
        output_path: Where to save the script JSON
    
    Returns:
        Script dict with title, topic, scenes
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found.\n"
            "Add it to your .env file:\n"
            "ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    prompt_template = FLASHCARD_PROMPT if mode == "flashcard" else DOCUMENTARY_PROMPT
    prompt = prompt_template.format(topic=topic)

    print(f"✍️  Generating script: '{topic}' [{mode} mode]")
    print("🤖 Calling Claude API...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code blocks if present
    response_text = re.sub(r'^```json\s*', '', response_text)
    response_text = re.sub(r'^```\s*', '', response_text)
    response_text = re.sub(r'\s*```$', '', response_text)
    response_text = response_text.strip()

    try:
        script = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nResponse: {response_text[:500]}")

    # Validate structure
    if "scenes" not in script:
        raise ValueError("Script missing 'scenes' key")
    if len(script["scenes"]) != 34:
        print(f"⚠️  Warning: Expected 34 scenes, got {len(script['scenes'])}")

    # Add metadata
    script["mode"] = mode
    script["generated_at"] = datetime.now().isoformat()

    # Save to file
    output = Path(output_path)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print(f"✅ Script generated: '{script['title']}'")
    print(f"📜 {len(script['scenes'])} scenes → {output}")

    return script


def preview_script(script_path: str = "script.json"):
    """Print first 5 scenes for quick review."""
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)

    print(f"\n{'='*60}")
    print(f"  SCRIPT PREVIEW: {script.get('title', 'Untitled')}")
    print(f"  Topic: {script.get('topic', '')}")
    print(f"  Mode: {script.get('mode', '')}")
    print(f"  Scenes: {len(script.get('scenes', []))}")
    print(f"{'='*60}")
    for scene in script["scenes"][:5]:
        print(f"\nScene {scene['id']:02d}: {scene['text']}")
    print(f"\n... and {len(script['scenes']) - 5} more scenes")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Video topic")
    parser.add_argument("--mode", default="flashcard",
                        choices=["flashcard", "documentary"])
    parser.add_argument("--output", default="script.json")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    script = generate_script(args.topic, args.mode, args.output)

    if args.preview:
        preview_script(args.output)
