"""
thumbnail_generator.py — Voquo v2.0
--------------------------------------
Generates YouTube thumbnails using Pillow.
Dark background, Tinlance teal title text,
episode number, channel branding.
"""

import json
import os
import textwrap
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

# Thumbnail dimensions (YouTube standard)
WIDTH  = 1280
HEIGHT = 720

# Brand colors
BG_COLOR      = (8, 8, 8)        # --bg-void
TEAL_COLOR    = (0, 229, 200)    # --teal-signal
WHITE_COLOR   = (240, 240, 240)  # --white-primary
MUTED_COLOR   = (136, 136, 153)  # --white-muted
ACCENT_COLOR  = (255, 77, 109)   # --pink-signal

# Font paths — Windows system fonts
FONT_PATHS = {
    "bold":    "C:/Windows/Fonts/arialbd.ttf",
    "regular": "C:/Windows/Fonts/arial.ttf",
    "narrow":  "C:/Windows/Fonts/arialn.ttf",
}


def get_font(style: str = "bold", size: int = 72):
    path = FONT_PATHS.get(style, FONT_PATHS["bold"])
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def draw_gradient_bar(draw, y, width, color, alpha=60):
    """Draw a subtle horizontal accent bar."""
    for i in range(4):
        opacity = alpha - (i * 12)
        if opacity > 0:
            draw.rectangle([(0, y + i), (width, y + i + 1)],
                          fill=(*color, opacity))


def generate_thumbnail(
    title: str,
    episode: int = None,
    channel: str = "lloydambition",
    output_path: str = "thumbnail.jpg"
) -> str:
    """
    Generate a YouTube thumbnail.

    Args:
        title: Video title (will be wrapped automatically)
        episode: Optional episode number
        channel: Channel name for branding
        output_path: Where to save the thumbnail

    Returns:
        Path to saved thumbnail
    """

    # Create base image
    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle teal gradient in top-left corner
    for i in range(300):
        opacity = max(0, 15 - int(i * 0.05))
        draw.ellipse(
            [(-100 + i//3, -100 + i//3),
             (300 - i//3, 300 - i//3)],
            fill=(*TEAL_COLOR, opacity)
        )

    # Teal accent bar at top
    draw.rectangle([(0, 0), (WIDTH, 5)], fill=TEAL_COLOR)

    # Channel name — top left
    font_channel = get_font("regular", 28)
    channel_text = f"VOQUO · {channel.upper()}"
    draw.text((48, 24), channel_text, font=font_channel, fill=MUTED_COLOR)

    # Episode number — top right
    if episode:
        font_ep = get_font("bold", 32)
        ep_text = f"EP.{episode:03d}"
        bbox = draw.textbbox((0, 0), ep_text, font=font_ep)
        ep_w = bbox[2] - bbox[0]
        draw.text(
            (WIDTH - ep_w - 48, 20),
            ep_text,
            font=font_ep,
            fill=TEAL_COLOR
        )

    # Main title — centered, wrapped
    font_title = get_font("bold", 88)
    font_title_sm = get_font("bold", 72)

    # Wrap title to fit
    max_chars = 22
    if len(title) > max_chars:
        lines = textwrap.wrap(title, width=max_chars)
        font_use = font_title_sm
        line_height = 86
    else:
        lines = [title]
        font_use = font_title
        line_height = 100

    # Limit to 3 lines
    lines = lines[:3]

    # Calculate total text block height
    total_h = len(lines) * line_height
    start_y = (HEIGHT - total_h) // 2 - 20

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_use)
        line_w = bbox[2] - bbox[0]
        x = (WIDTH - line_w) // 2
        y = start_y + (i * line_height)

        # Shadow
        draw.text((x + 3, y + 3), line, font=font_use,
                  fill=(0, 0, 0, 180))
        # Main text — white
        draw.text((x, y), line, font=font_use, fill=WHITE_COLOR)

    # Teal underline under last title line
    last_line = lines[-1]
    bbox = draw.textbbox((0, 0), last_line, font=font_use)
    last_w = bbox[2] - bbox[0]
    underline_x = (WIDTH - last_w) // 2
    underline_y = start_y + (len(lines) * line_height) + 8
    draw.rectangle(
        [(underline_x, underline_y),
         (underline_x + last_w, underline_y + 4)],
        fill=TEAL_COLOR
    )

    # Bottom bar — dark surface with metadata
    draw.rectangle([(0, HEIGHT - 60), (WIDTH, HEIGHT)],
                  fill=(17, 17, 22))
    draw.rectangle([(0, HEIGHT - 62), (WIDTH, HEIGHT - 60)],
                  fill=TEAL_COLOR)

    font_bottom = get_font("regular", 24)
    bottom_text = "VOQUO.TINLANCE.COM"
    draw.text((48, HEIGHT - 44), bottom_text,
              font=font_bottom, fill=MUTED_COLOR)

    # Save
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "JPEG", quality=95)

    print(f"✅ Thumbnail → {out}")
    return str(out)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--episode", type=int, help="Episode number")
    parser.add_argument("--channel", default="lloydambition")
    parser.add_argument("--output", default="output/thumbnail.jpg")
    args = parser.parse_args()

    generate_thumbnail(
        title=args.title,
        episode=args.episode,
        channel=args.channel,
        output_path=args.output
    )
