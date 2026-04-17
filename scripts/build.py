"""Build script for D&D SRD Library desktop app.

Steps:
1. Generate icon files (icon.png + icon.ico) via Pillow.
2. Run PyInstaller with dnd_lib.spec.

Usage:
    python scripts/build.py [--skip-icons]
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def create_icons() -> None:
    print("==> Generating icons...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "create_icons.py")],
        check=False,
    )
    if result.returncode != 0:
        print("WARNING: Icon generation failed — using fallback icon at runtime.")


def run_pyinstaller() -> None:
    print("==> Running PyInstaller...")
    spec = ROOT / "dnd_lib.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--clean"],
        cwd=str(ROOT),
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build D&D SRD Library desktop app")
    parser.add_argument("--skip-icons", action="store_true", help="Skip icon generation step")
    args = parser.parse_args()

    if not args.skip_icons:
        create_icons()

    run_pyinstaller()
    print("==> Build complete. Output is in dist/")


if __name__ == "__main__":
    main()
