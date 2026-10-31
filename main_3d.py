"""
main_3d.py - Primary Launcher for RetroRevive: The Living Empire (3D Edition).

Command-Line Options:
  --quality [low|med|high|ultra]   Set graphics fidelity (Default: high)
  --headless                       Run in headless offscreen mode (for testing)
  --fullscreen                     Launch in exclusive fullscreen display
"""

import sys
from panda3d.core import loadPrcFileData

from engine3d.app_3d import BabylonApp3D


def main() -> None:
    args = sys.argv[1:]
    headless = "--headless" in args
    fullscreen = "--fullscreen" in args

    quality = "HIGH"
    for a in args:
        if a.startswith("--quality="):
            quality = a.split("=", 1)[1].upper()
        elif a in ("--low", "-low"):
            quality = "LOW"
        elif a in ("--ultra", "-ultra"):
            quality = "ULTRA"

    # Quality preset settings
    if quality == "ULTRA":
        loadPrcFileData("", "framebuffer-multisample 1")
        loadPrcFileData("", "multisamples 8")
        loadPrcFileData("", "win-size 1920 1080")
    elif quality == "LOW":
        loadPrcFileData("", "win-size 1024 576")
    else:  # HIGH
        loadPrcFileData("", "framebuffer-multisample 1")
        loadPrcFileData("", "multisamples 4")
        loadPrcFileData("", "win-size 1280 720")

    if fullscreen:
        loadPrcFileData("", "fullscreen #t")

    app = BabylonApp3D(headless=headless, quality=quality)
    app.run()


if __name__ == "__main__":
    main()

