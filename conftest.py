# conftest.py — root pytest configuration for RetroRevive
import os
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Set headless drivers for CI/test environments (safe to set; ignored when display is available)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

