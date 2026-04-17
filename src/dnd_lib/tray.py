"""System tray runner for D&D SRD Library desktop app.

Entry point for the packaged distribution. Starts the Waitress WSGI server in
a background thread, opens the browser after a short delay, and presents a
system tray icon with "Open in Browser" and "Quit" menu items.

Usage (dev):
    cd src && python -m dnd_lib.tray

Usage (frozen bundle):
    ./dnd_lib  (or dnd_lib.exe on Windows)
"""

import sys
import threading
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}"


# ---------------------------------------------------------------------------
# Icon helpers
# ---------------------------------------------------------------------------

def _generate_icon_image():
    """Create a simple d20-style icon programmatically using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Hexagon outline resembling a d20 face
    cx, cy = size // 2, size // 2
    r_outer = 30
    r_inner = 22
    import math
    hex_pts = [
        (cx + r_outer * math.cos(math.radians(angle)),
         cy + r_outer * math.sin(math.radians(angle)))
        for angle in range(30, 390, 60)
    ]
    draw.polygon(hex_pts, fill=(139, 0, 0), outline=(210, 180, 140))

    # Inner detail lines (triangle hints)
    tri_pts = [
        (cx + r_inner * math.cos(math.radians(a)),
         cy + r_inner * math.sin(math.radians(a)))
        for a in (270, 30, 150)
    ]
    draw.line(tri_pts + [tri_pts[0]], fill=(210, 180, 140), width=1)

    # "20" label
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()
    text = "20"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2), text, fill=(255, 255, 220), font=font)

    return img


def _get_icon_image():
    """Load icon.png from static dir, falling back to a generated icon."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        icon_path = Path(sys._MEIPASS) / "static" / "icon.png"
    else:
        icon_path = Path(__file__).resolve().parent / "static" / "icon.png"

    if icon_path.exists():
        from PIL import Image
        return Image.open(icon_path).convert("RGBA")

    return _generate_icon_image()


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------

def _run_server() -> None:
    """Start the Waitress WSGI server (runs in a daemon thread)."""
    from waitress import serve
    from dnd_lib.app import app  # noqa: PLC0415 – intentional late import

    serve(app, host=HOST, port=PORT, threads=4)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import pystray

    # Start the WSGI server in a background daemon thread so it dies when the
    # main (tray) thread exits.
    server_thread = threading.Thread(target=_run_server, daemon=True, name="waitress")
    server_thread.start()

    # Open the browser once the server has had time to bind.
    threading.Timer(1.5, webbrowser.open, args=[URL]).start()

    # Build tray menu.
    def on_open(icon, item):  # noqa: ARG001
        webbrowser.open(URL)

    def on_quit(icon, item):  # noqa: ARG001
        icon.stop()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open in Browser", on_open),
        pystray.MenuItem("Quit", on_quit),
    )

    icon_image = _get_icon_image()
    tray = pystray.Icon("dnd_lib", icon_image, "D&D SRD Library", menu)
    tray.run()


if __name__ == "__main__":
    main()
