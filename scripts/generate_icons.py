#!/usr/bin/env python3
"""
Generate simple PNG icons for the SearchSift extension.

Requires: pip install pillow

Usage:
    python scripts/generate_icons.py
"""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Install with: pip install pillow")
    print("Or create icons manually in extension/icons/")
    sys.exit(0)


def create_icon(size: int, output_path: Path):
    """Create a simple icon with 'S' letter."""
    # Create image with blue background
    img = Image.new('RGBA', (size, size), (59, 130, 246, 255))  # Blue
    draw = ImageDraw.Draw(img)

    # Draw white 'S'
    font_size = int(size * 0.6)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Center the text
    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]

    draw.text((x, y), text, fill='white', font=font)

    # Round corners (simple approach)
    # Create a mask with rounded corners
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = size // 5
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=255)

    # Apply mask
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, mask=mask)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path, 'PNG')
    print(f"Created: {output_path}")


def main():
    project_root = Path(__file__).parent.parent
    icons_dir = project_root / 'extension' / 'icons'

    sizes = [16, 32, 48, 128]

    print("Generating extension icons...")

    for size in sizes:
        output_path = icons_dir / f'icon{size}.png'
        create_icon(size, output_path)

    print(f"\nIcons created in: {icons_dir}")


if __name__ == "__main__":
    main()
