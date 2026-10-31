"""
texture_manager.py — Procedural texture generation for the Babylon 3D Engine.

Generates realistic-looking textures using PIL/Pillow and numpy, then
converts them to Panda3D Texture objects for application to geometry.

Textures produced:
  - sandstone_brick   : warm ochre bricks with darker mortar lines
  - lapis_glazed      : deep royal-blue Ishtar-Gate tiles with gold animal reliefs
  - mudbrick          : earth-tone horizontal-layered mudbrick walls
  - wood_grain        : warm brown cedar planking
  - wheat_field       : golden wheat field ground plane
  - water_caustics    : animated-ready Euphrates river surface
  - marble_floor      : light cream throne-room floor with vein lines
  - palm_bark         : rough palm-tree trunk texture
  - sky_gradient      : golden-hour sky gradient for sky dome
  - stone_pavement    : grey limestone plaza stones
"""

from __future__ import annotations

import io
import math
import random
from typing import Tuple

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    from panda3d.core import Texture, PNMImage, StringStream
    _PANDA_AVAILABLE = True
except ImportError:
    _PANDA_AVAILABLE = False


# ---------------------------------------------------------------------------
# Colour palettes (RGB tuples, matching reference images)
# ---------------------------------------------------------------------------
SANDSTONE       = (209, 178, 133)   # warm ochre
SANDSTONE_DARK  = (160, 130,  90)   # shadow / mortar
SANDSTONE_LIGHT = (235, 210, 165)   # highlight
LAPIS_BASE      = ( 20,  55, 122)   # deep royal blue
LAPIS_MID       = ( 35,  80, 160)   # mid lapis
GOLD            = (235, 198,  71)   # gold relief
GOLD_DARK       = (180, 140,  30)
MUDBRICK_BASE   = (184, 148, 102)
MUDBRICK_DARK   = (140, 108,  72)
WATER_BASE      = ( 52, 120, 180)
WATER_LIGHT     = ( 90, 165, 220)
WHEAT_GOLD      = (220, 185,  80)
WHEAT_GREEN     = (120, 165,  60)
MARBLE_BASE     = (230, 220, 205)
MARBLE_VEIN     = (180, 165, 145)
PALM_BARK       = (110,  75,  40)
PALM_BARK_LIGHT = (145, 105,  65)
SKY_ZENITH      = ( 45,  80, 155)
SKY_HORIZON     = (235, 170,  70)   # golden hour
STONE_GREY      = (195, 185, 170)
STONE_DARK      = (150, 140, 128)


def _rng_seed(s: int) -> random.Random:
    rng = random.Random(s)
    return rng


# ---------------------------------------------------------------------------
# Pillow → Panda3D Texture conversion
# ---------------------------------------------------------------------------
def _pil_to_panda_texture(img: "Image.Image", name: str) -> "Texture":
    """Convert a PIL Image (RGBA or RGB) to a Panda3D Texture."""
    if not _PANDA_AVAILABLE:
        raise RuntimeError("Panda3D not available")

    img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    tex = Texture(name)
    ss = StringStream(png_bytes)
    tex.read(ss, None, 0, False, False)
    tex.set_wrap_u(Texture.WM_repeat)
    tex.set_wrap_v(Texture.WM_repeat)
    tex.set_minfilter(Texture.FT_linear_mipmap_linear)
    tex.set_magfilter(Texture.FT_linear)
    tex.set_anisotropic_degree(4)
    return tex


# ---------------------------------------------------------------------------
# Individual texture generators
# ---------------------------------------------------------------------------

def _make_sandstone_brick(size: int = 512, seed: int = 1) -> "Image.Image":
    """Warm sandstone brick pattern with mortar seams."""
    rng = _rng_seed(seed)
    img = Image.new("RGB", (size, size), SANDSTONE)
    draw = ImageDraw.Draw(img)

    brick_w = size // 8
    brick_h = size // 16
    mortar   = 3

    for row in range(20):
        offset = (brick_w // 2) if (row % 2 == 1) else 0
        y0 = row * brick_h
        y1 = y0 + brick_h - mortar
        for col in range(-1, 10):
            x0 = col * brick_w + offset
            x1 = x0 + brick_w - mortar

            # base brick colour with slight random variation
            var = rng.randint(-15, 15)
            c = (
                min(255, max(0, SANDSTONE[0] + var)),
                min(255, max(0, SANDSTONE[1] + var - 5)),
                min(255, max(0, SANDSTONE[2] + var - 10)),
            )
            draw.rectangle([x0, y0, x1, y1], fill=c)

            # highlight on top edge
            draw.line([(x0, y0), (x1, y0)], fill=SANDSTONE_LIGHT, width=1)
            # shadow on bottom edge
            draw.line([(x0, y1), (x1, y1)], fill=SANDSTONE_DARK, width=1)

    # slight blur for realism
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    return img


def _make_lapis_glazed(size: int = 512, seed: int = 2) -> "Image.Image":
    """Deep royal-blue Ishtar Gate tile with gold animal silhouettes."""
    rng = _rng_seed(seed)
    img = Image.new("RGB", (size, size), LAPIS_BASE)
    draw = ImageDraw.Draw(img)

    tile_size = size // 8

    # tile grid
    for ty in range(8):
        for tx in range(8):
            x0, y0 = tx * tile_size, ty * tile_size
            x1, y1 = x0 + tile_size - 2, y0 + tile_size - 2

            var = rng.randint(-10, 10)
            c = (
                min(255, max(0, LAPIS_MID[0] + var)),
                min(255, max(0, LAPIS_MID[1] + var)),
                min(255, max(0, LAPIS_MID[2] + var - 5)),
            )
            draw.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=c)

            # gold border
            draw.rectangle([x0, y0, x1, y1], outline=GOLD, width=1)

    # horizontal gold relief bands every 4 tiles
    for band_y in range(0, size, tile_size * 4):
        draw.rectangle([0, band_y, size, band_y + 6], fill=GOLD_DARK)

    # simple animal silhouette (aurochs) repeated in gold
    for ay in range(tile_size, size - tile_size, tile_size * 4):
        for ax in range(tile_size // 2, size, tile_size * 2):
            # body
            draw.ellipse([ax, ay, ax + 20, ay + 12], fill=GOLD)
            # head
            draw.ellipse([ax + 16, ay - 4, ax + 26, ay + 8], fill=GOLD)
            # horns
            draw.line([(ax + 22, ay - 4), (ax + 28, ay - 10)], fill=GOLD, width=2)
            draw.line([(ax + 20, ay - 4), (ax + 15, ay - 10)], fill=GOLD, width=2)
            # legs
            for lx in [ax + 4, ax + 9, ax + 14, ax + 17]:
                draw.line([(lx, ay + 12), (lx, ay + 20)], fill=GOLD, width=2)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    return img


def _make_mudbrick(size: int = 512, seed: int = 3) -> "Image.Image":
    """Earth-tone mudbrick horizontal-layer texture."""
    rng = _rng_seed(seed)
    arr = np.zeros((size, size, 3), dtype=np.uint8)

    layer_h = 18
    for y in range(size):
        layer = y // layer_h
        t = (y % layer_h) / layer_h
        var = rng.randint(-12, 12)
        if t < 0.08:          # mortar line
            c = np.array(MUDBRICK_DARK) + var
        else:
            c = np.array(MUDBRICK_BASE) + var
        c = np.clip(c, 0, 255)
        arr[y, :] = c

    # add horizontal noise for texture
    noise = np.random.RandomState(seed).randint(-18, 18, (size, size, 3))
    arr = np.clip(arr.astype(int) + noise, 0, 255).astype(np.uint8)

    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return img


def _make_wood_grain(size: int = 256, seed: int = 4) -> "Image.Image":
    """Cedar wood grain texture — warm brown planks."""
    rng = _rng_seed(seed)
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    base = np.array([139, 90, 43])

    rng2 = np.random.RandomState(seed)
    for x in range(size):
        grain_offset = int(12 * math.sin(x * 0.15 + rng.random() * 0.5))
        for y in range(size):
            plank_line = ((y + grain_offset) % 32) / 32.0
            if plank_line < 0.05:
                c = base * 0.7
            else:
                wave = 0.85 + 0.15 * math.sin((y + grain_offset) * 0.4 + x * 0.05)
                c = base * wave
            arr[y, x] = np.clip(c, 0, 255)

    noise = rng2.randint(-10, 10, (size, size, 3))
    arr = np.clip(arr.astype(int) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _make_wheat_field(size: int = 512, seed: int = 5) -> "Image.Image":
    """Golden wheat field ground texture with green/gold variation."""
    rng2 = np.random.RandomState(seed)
    arr = np.zeros((size, size, 3), dtype=np.uint8)

    for y in range(size):
        for x in range(size):
            # blend gold ↔ green based on sine wave (rows of wheat)
            t = 0.5 + 0.5 * math.sin(y * 0.3 + x * 0.05)
            c = (
                int(WHEAT_GOLD[0] * t + WHEAT_GREEN[0] * (1 - t)),
                int(WHEAT_GOLD[1] * t + WHEAT_GREEN[1] * (1 - t)),
                int(WHEAT_GOLD[2] * t + WHEAT_GREEN[2] * (1 - t)),
            )
            arr[y, x] = c

    noise = rng2.randint(-20, 20, (size, size, 3))
    arr = np.clip(arr.astype(int) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
    return img


def _make_water_caustics(size: int = 256, seed: int = 6) -> "Image.Image":
    """Euphrates river surface with caustics / ripple shimmer."""
    arr = np.zeros((size, size, 3), dtype=np.uint8)

    for y in range(size):
        for x in range(size):
            ripple = (
                math.sin(x * 0.25 + y * 0.1) +
                math.sin(x * 0.1 - y * 0.3) +
                math.sin((x + y) * 0.15)
            ) / 3.0
            t = 0.5 + 0.5 * ripple
            c = (
                int(WATER_BASE[0] * (1 - t) + WATER_LIGHT[0] * t),
                int(WATER_BASE[1] * (1 - t) + WATER_LIGHT[1] * t),
                int(WATER_BASE[2] * (1 - t) + WATER_LIGHT[2] * t),
            )
            arr[y, x] = c

    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    return img


def _make_marble_floor(size: int = 512, seed: int = 7) -> "Image.Image":
    """Cream marble tile for throne room floor with vein lines."""
    rng2 = np.random.RandomState(seed)
    arr = np.full((size, size, 3), MARBLE_BASE, dtype=np.uint8)

    # tile grid
    tile = size // 4
    for ty in range(4):
        for tx in range(4):
            y0, x0 = ty * tile, tx * tile
            # draw grout lines
            arr[y0:y0 + 2, x0:x0 + tile] = MARBLE_VEIN
            arr[y0:y0 + tile, x0:x0 + 2] = MARBLE_VEIN

            # vein lines per tile
            for _ in range(3):
                vx = rng2.randint(x0 + 10, x0 + tile - 10)
                vy_start = rng2.randint(y0, y0 + tile // 2)
                vy_end   = rng2.randint(y0 + tile // 2, y0 + tile - 1)
                for vy in range(vy_start, vy_end):
                    vxd = vx + int(4 * math.sin(vy * 0.3))
                    if 0 <= vxd < size:
                        arr[vy, max(0, vxd - 1):vxd + 2] = MARBLE_VEIN

    noise = rng2.randint(-8, 8, (size, size, 3))
    arr = np.clip(arr.astype(int) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
    return img


def _make_palm_bark(size: int = 256, seed: int = 8) -> "Image.Image":
    """Rough palm tree trunk texture with ring scars."""
    rng2 = np.random.RandomState(seed)
    arr = np.zeros((size, size, 3), dtype=np.uint8)

    ring_spacing = 14
    for y in range(size):
        ring_t = (y % ring_spacing) / ring_spacing
        if ring_t < 0.12:
            base = np.array(PALM_BARK_LIGHT)
        else:
            base = np.array(PALM_BARK)

        for x in range(size):
            var = int(10 * math.sin(x * 0.5 + y * 0.1))
            c = np.clip(base + var, 0, 255)
            arr[y, x] = c

    noise = rng2.randint(-12, 12, (size, size, 3))
    arr = np.clip(arr.astype(int) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    return img


def _make_sky_gradient(size: int = 512, seed: int = 9) -> "Image.Image":
    """Golden-hour sky gradient from deep zenith blue to warm horizon orange."""
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    zenith  = np.array(SKY_ZENITH)
    horizon = np.array(SKY_HORIZON)

    for y in range(size):
        t = y / (size - 1)   # 0 = zenith (top), 1 = horizon (bottom)
        # use smoothstep for more realistic gradient
        t_smooth = t * t * (3 - 2 * t)
        c = (zenith * (1 - t_smooth) + horizon * t_smooth).astype(np.uint8)
        arr[y, :] = c

    # add a few soft cloud wisps
    rng2 = np.random.RandomState(seed)
    for _ in range(6):
        cx = rng2.randint(50, size - 50)
        cy = rng2.randint(size // 6, size // 2)
        w  = rng2.randint(60, 130)
        h  = rng2.randint(15, 30)
        cloud_col = np.array([240, 225, 190])
        for dy in range(-h, h):
            for dx in range(-w, w):
                if (dx / w) ** 2 + (dy / h) ** 2 < 1:
                    px, py = cx + dx, cy + dy
                    if 0 <= px < size and 0 <= py < size:
                        dist2 = (dx / w) ** 2 + (dy / h) ** 2
                        alpha = max(0.0, 1.0 - dist2) * 0.4
                        arr[py, px] = np.clip(
                            arr[py, px] * (1 - alpha) + cloud_col * alpha, 0, 255
                        ).astype(np.uint8)

    return Image.fromarray(arr, "RGB")


def _make_stone_pavement(size: int = 512, seed: int = 10) -> "Image.Image":
    """Limestone plaza pavement with irregular stone blocks."""
    rng = _rng_seed(seed)
    img = Image.new("RGB", (size, size), STONE_GREY)
    draw = ImageDraw.Draw(img)

    block_w = size // 7
    block_h = size // 10
    mortar   = 3

    for row in range(14):
        offset = (block_w // 3) if (row % 2 == 1) else 0
        y0 = row * block_h
        y1 = y0 + block_h - mortar
        for col in range(-1, 10):
            x0 = col * block_w + offset
            x1 = x0 + block_w - mortar

            var = rng.randint(-12, 12)
            c = (
                min(255, max(0, STONE_GREY[0] + var)),
                min(255, max(0, STONE_GREY[1] + var)),
                min(255, max(0, STONE_GREY[2] + var - 5)),
            )
            draw.rectangle([x0, y0, x1, y1], fill=c)
            draw.line([(x0, y0), (x1, y0)], fill=(220, 215, 205), width=1)
            draw.line([(x0, y1), (x1, y1)], fill=STONE_DARK, width=1)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return img


# ---------------------------------------------------------------------------
# Public API: TextureManager singleton
# ---------------------------------------------------------------------------
_TEXTURE_REGISTRY: dict[str, "Texture"] = {}


class TextureManager:
    """
    Singleton that lazily generates procedural textures and caches them.

    Usage::

        from engine3d.texture_manager import TextureManager
        tm = TextureManager.instance()
        tex = tm.get("sandstone_brick")
        node_path.set_texture(tex)
    """

    _singleton: "TextureManager | None" = None

    def __init__(self) -> None:
        self._cache: dict[str, "Texture"] = {}
        self._generators = {
            "sandstone_brick":  lambda: _make_sandstone_brick(512, 1),
            "lapis_glazed":     lambda: _make_lapis_glazed(512, 2),
            "mudbrick":         lambda: _make_mudbrick(512, 3),
            "wood_grain":       lambda: _make_wood_grain(256, 4),
            "wheat_field":      lambda: _make_wheat_field(512, 5),
            "water_caustics":   lambda: _make_water_caustics(256, 6),
            "marble_floor":     lambda: _make_marble_floor(512, 7),
            "palm_bark":        lambda: _make_palm_bark(256, 8),
            "sky_gradient":     lambda: _make_sky_gradient(512, 9),
            "stone_pavement":   lambda: _make_stone_pavement(512, 10),
        }

    @classmethod
    def instance(cls) -> "TextureManager":
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def get(self, name: str) -> "Texture | None":
        """Return a Panda3D Texture for *name*, generating it on first call."""
        if not _PIL_AVAILABLE:
            return None
        if not _PANDA_AVAILABLE:
            return None

        if name not in self._cache:
            if name not in self._generators:
                raise KeyError(f"Unknown texture: {name!r}")
            pil_img = self._generators[name]()
            tex = _pil_to_panda_texture(pil_img, name)
            self._cache[name] = tex
        return self._cache[name]

    def preload_all(self) -> None:
        """Pre-generate every texture (call once at startup)."""
        for name in self._generators:
            self.get(name)

    @property
    def available_names(self) -> list[str]:
        return list(self._generators.keys())

