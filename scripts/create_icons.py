"""Generate icon.png and icon.ico for the D&D SRD Library desktop app.

Run this script once before building with PyInstaller:
    python scripts/create_icons.py

Output files:
    src/dnd_lib/static/icon.png   (tray icon, 256×256 RGBA)
    src/dnd_lib/static/icon.ico   (Windows executable icon, multi-size)
"""

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow is required: pip install Pillow")

STATIC_DIR = Path(__file__).resolve().parent.parent / "src" / "dnd_lib" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _draw_d20_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r_outer = int(size * 0.46)
    r_inner = int(size * 0.34)

    # Hexagon (main shape)
    hex_pts = [
        (cx + r_outer * math.cos(math.radians(a)),
         cy + r_outer * math.sin(math.radians(a)))
        for a in range(30, 390, 60)
    ]
    draw.polygon(hex_pts, fill=(139, 0, 0), outline=(210, 180, 140))

    # Inner triangle hints
    tri_pts = [
        (cx + r_inner * math.cos(math.radians(a)),
         cy + r_inner * math.sin(math.radians(a)))
        for a in (270, 30, 150)
    ]
    draw.line(tri_pts + [tri_pts[0]], fill=(210, 180, 140), width=max(1, size // 32))

    # "20" label
    font_size = max(8, size // 4)
    font = None
    for font_name in ("arialbd.ttf", "Arial Bold.ttf", "arial.ttf", "Arial.ttf"):
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except (OSError, IOError):
            pass
    if font is None:
        font = ImageFont.load_default()

    text = "20"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 + size // 20), text, fill=(255, 255, 220), font=font)

    return img


def main() -> None:
    # PNG (256×256) — used by tray and macOS/Linux
    png_path = STATIC_DIR / "icon.png"
    img_256 = _draw_d20_icon(256)
    img_256.save(png_path, "PNG")
    print(f"Saved {png_path}")

    # ICO (multi-size) — used by Windows executable.
    # Pillow's ICO plugin resizes the source image to each listed size, so pass
    # the largest frame and let it downsample.
    ico_path = STATIC_DIR / "icon.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    img_256.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"Saved {ico_path}")


if __name__ == "__main__":
    main()
