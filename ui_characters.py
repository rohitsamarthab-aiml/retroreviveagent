"""
ui_characters.py - Procedural Character Rendering & Animation for RetroRevive.

Features:
- Royal King Hammurabi: Monumental Mesopotamian monarch with layered Babylonian horned crown,
  braided royal beard with gold rings, embroidered tunic, royal purple robe, and the golden
  Rod and Ring of Justice. Procedural idle breathing, blinking, and sceptre glimmer.
- Royal Advisor Portrait: Animated Sumerian scribe/vizier with expressive moods (Normal, Alarmed, Joyous).
- Living World Entities:
  * Farmers with sickles reaping wheat in the fields
  * Merchants with wooden grain carts and pack donkeys
  * Palace Guards with bronze helmets, spears, and shields patrolling battlements
  * River Boats with billowing sails navigating the Euphrates
  * Citizens with varied Mesopotamian attire walking the riverbanks
"""

import math
import os
import random
from typing import Any, Dict, List, Optional, Tuple
import pygame

from ui_theme import Palette


def make_circular_portrait(image: pygame.Surface, size: int) -> pygame.Surface:
    """Creates a smooth anti-aliased circular cropped portrait."""
    scaled = pygame.transform.smoothscale(image, (size, size))
    masked = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(masked, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    masked.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return masked


class RoyalHammurabi:
    """
    Renders an impressive, historically grounded animated character of King Hammurabi.
    Includes breathing physics, subtle head movements, blinking, robe sway, and sceptre shine.
    """

    def __init__(self, scale: float = 1.0) -> None:
        self.scale = scale
        self.time = 0.0
        self.blink_timer = random.uniform(2.0, 5.0)
        self.is_blinking = False
        self.sceptre_gleam = 0.0

        # Photorealistic King Hammurabi Portrait Asset
        self.portrait_img: Optional[pygame.Surface] = None
        self._cached_portraits: Dict[int, pygame.Surface] = {}
        p_path = os.path.join(os.path.dirname(__file__), "assets", "hammurabi_portrait.jpg")
        if os.path.exists(p_path):
            try:
                self.portrait_img = pygame.image.load(p_path)
            except Exception:
                self.portrait_img = None

    def update(self, dt: float) -> None:
        self.time += dt
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            if not self.is_blinking:
                self.is_blinking = True
                self.blink_timer = 0.15  # blink duration
            else:
                self.is_blinking = False
                self.blink_timer = random.uniform(3.0, 6.0)

        # Sceptre gleam pulse
        self.sceptre_gleam = (math.sin(self.time * 3.0) + 1.0) * 0.5

    def draw_bust(self, surface: pygame.Surface, center_x: int, center_y: int, size: int = 160) -> None:
        """
        Draws a detailed royal portrait/bust of King Hammurabi for dialogues,
        menus, and royal decrees.
        """
        if self.portrait_img is not None:
            # Idle breathing bob
            breath = int(math.sin(self.time * 2.0) * 2.5)
            cy = center_y + breath

            # Outer ornate royal medallion frame
            medallion_s = size
            inner_s = size - 14
            if inner_s not in self._cached_portraits:
                self._cached_portraits[inner_s] = make_circular_portrait(self.portrait_img, inner_s)
            p_surf = self._cached_portraits[inner_s]

            # 1. Dark obsidian background disc
            pygame.draw.circle(surface, (18, 14, 12), (center_x, cy), medallion_s // 2)

            # 2. Photorealistic King Hammurabi portrait
            p_rect = p_surf.get_rect(center=(center_x, cy))
            surface.blit(p_surf, p_rect)

            # 3. Concentric Royal Gold Rings with filigree
            pygame.draw.circle(surface, Palette.GOLD_LIGHT, (center_x, cy), medallion_s // 2, width=3)
            pygame.draw.circle(surface, (36, 28, 20), (center_x, cy), medallion_s // 2 - 3, width=2)
            pygame.draw.circle(surface, Palette.GOLD_BASE, (center_x, cy), medallion_s // 2 - 5, width=1)

            # 4. Lapis Lazuli corner jewels at cardinal points
            radius = medallion_s // 2 - 1
            for angle in [0, 90, 180, 270]:
                rad = math.radians(angle)
                jx = int(center_x + math.cos(rad) * radius)
                jy = int(cy + math.sin(rad) * radius)
                pygame.draw.circle(surface, Palette.GOLD_LIGHT, (jx, jy), 5)
                pygame.draw.circle(surface, (40, 180, 200), (jx, jy), 3)

            # 5. Sceptre gleam pulse running across the upper tiara rim
            if self.sceptre_gleam > 0.4:
                glint_alpha = int((self.sceptre_gleam - 0.4) * 255 / 0.6)
                glint_surf = pygame.Surface((28, 28), pygame.SRCALPHA)
                pygame.draw.circle(glint_surf, (255, 255, 220, glint_alpha), (14, 14), 12)
                pygame.draw.circle(glint_surf, (255, 255, 255, glint_alpha), (14, 14), 5)
                surface.blit(glint_surf, (center_x + radius // 2 - 14, cy - radius + 10 - 14))
        else:
            self._draw_procedural_bust(surface, center_x, center_y, size)

    def _draw_procedural_bust(self, surface: pygame.Surface, center_x: int, center_y: int, size: int = 160) -> None:
        """Procedural fallback bust."""
        breath = math.sin(self.time * 2.0) * 2.5
        head_tilt = math.sin(self.time * 1.2) * 1.5

        # Create localized surface for clean scaling and alpha blending
        bust_w, bust_h = size, int(size * 1.2)
        s = pygame.Surface((bust_w, bust_h), pygame.SRCALPHA)
        cx = bust_w // 2
        cy = bust_h // 2 + int(breath * 0.5)

        # --- 1. Royal Mantle / Robe (Shoulders & Chest) ---
        # Deep royal purple with antique gold embroidery
        shoulder_poly = [
            (cx - int(bust_w * 0.45), cy + int(bust_h * 0.42)),
            (cx - int(bust_w * 0.35), cy + int(bust_h * 0.15)),
            (cx - int(bust_w * 0.18), cy + int(bust_h * 0.08)),
            (cx + int(bust_w * 0.18), cy + int(bust_h * 0.08)),
            (cx + int(bust_w * 0.35), cy + int(bust_h * 0.15)),
            (cx + int(bust_w * 0.45), cy + int(bust_h * 0.42)),
            (cx, cy + int(bust_h * 0.48)),
        ]
        pygame.draw.polygon(s, (65, 25, 80), shoulder_poly)  # Tyrian royal purple
        pygame.draw.polygon(s, Palette.GOLD_DARK, shoulder_poly, width=3)

        # Gold ceremonial sash / shawl draped diagonally
        sash_poly = [
            (cx - int(bust_w * 0.35), cy + int(bust_h * 0.15)),
            (cx - int(bust_w * 0.15), cy + int(bust_h * 0.10)),
            (cx + int(bust_w * 0.28), cy + int(bust_h * 0.42)),
            (cx + int(bust_w * 0.12), cy + int(bust_h * 0.44)),
        ]
        pygame.draw.polygon(s, Palette.GOLD_BASE, sash_poly)
        pygame.draw.polygon(s, Palette.GOLD_LIGHT, sash_poly, width=2)

        # Royal gold breastplate medallion with turquoise inlay
        med_y = cy + int(bust_h * 0.20)
        pygame.draw.circle(s, Palette.GOLD_LIGHT, (cx, med_y), int(bust_w * 0.10))
        pygame.draw.circle(s, (30, 140, 160), (cx, med_y), int(bust_w * 0.06))  # Lapis/turquoise
        pygame.draw.circle(s, Palette.GOLD_PALE, (cx, med_y), int(bust_w * 0.03))

        # --- 2. Neck & Head ---
        neck_y = cy + int(bust_h * 0.02)
        pygame.draw.rect(s, (215, 175, 135), (cx - 16, neck_y - 10, 32, 26))

        # Head base (olive-tan ancient Mesopotamian complexion)
        head_cx = cx + int(head_tilt)
        head_cy = cy - int(bust_h * 0.12)
        pygame.draw.ellipse(s, (225, 185, 145), (head_cx - 24, head_cy - 30, 48, 58))

        # --- 3. Facial Features & Royal Beard ---
        # Regal dark eyes
        eye_y = head_cy - 8
        if not self.is_blinking:
            # Sclera
            pygame.draw.ellipse(s, (245, 240, 230), (head_cx - 17, eye_y - 4, 11, 7))
            pygame.draw.ellipse(s, (245, 240, 230), (head_cx + 6, eye_y - 4, 11, 7))
            # Dark iris & pupil
            pygame.draw.circle(s, (25, 18, 14), (head_cx - 12, eye_y - 1), 3)
            pygame.draw.circle(s, (25, 18, 14), (head_cx + 11, eye_y - 1), 3)
            # Catchlight
            pygame.draw.circle(s, (255, 255, 255), (head_cx - 13, eye_y - 2), 1)
            pygame.draw.circle(s, (255, 255, 255), (head_cx + 10, eye_y - 2), 1)
        else:
            # Closed eyelids
            pygame.draw.line(s, (70, 50, 40), (head_cx - 17, eye_y), (head_cx - 6, eye_y), 2)
            pygame.draw.line(s, (70, 50, 40), (head_cx + 6, eye_y), (head_cx + 17, eye_y), 2)

        # Strong arched eyebrows
        pygame.draw.arc(s, (25, 18, 14), (head_cx - 20, eye_y - 12, 16, 10), 0.2, 2.9, width=3)
        pygame.draw.arc(s, (25, 18, 14), (head_cx + 4, eye_y - 12, 16, 10), 0.2, 2.9, width=3)

        # Aquiline Babylonian nose
        pygame.draw.line(s, (195, 155, 120), (head_cx, eye_y - 5), (head_cx - 2, eye_y + 12), 2)
        pygame.draw.line(s, (180, 140, 105), (head_cx - 2, eye_y + 12), (head_cx + 3, eye_y + 12), 2)

        # Authentic Babylonian stylized braided square beard with golden rings
        beard_y = eye_y + 14
        beard_poly = [
            (head_cx - 20, beard_y),
            (head_cx + 20, beard_y),
            (head_cx + 16, beard_y + 44),
            (head_cx - 16, beard_y + 44),
        ]
        pygame.draw.polygon(s, (20, 15, 12), beard_poly)

        # Intricate curls and horizontal rows
        for row in range(beard_y + 6, beard_y + 42, 7):
            pygame.draw.line(s, (45, 35, 28), (head_cx - 15, row), (head_cx + 15, row), 1)

        # Golden beard rings / beads (classic royal insignia)
        pygame.draw.rect(s, Palette.GOLD_LIGHT, (head_cx - 10, beard_y + 22, 20, 3), border_radius=1)
        pygame.draw.rect(s, Palette.GOLD_LIGHT, (head_cx - 8, beard_y + 36, 16, 3), border_radius=1)

        # Mustache
        mustache_poly = [
            (head_cx - 14, eye_y + 11),
            (head_cx, eye_y + 8),
            (head_cx + 14, eye_y + 11),
            (head_cx, eye_y + 14),
        ]
        pygame.draw.polygon(s, (20, 15, 12), mustache_poly)

        # --- 4. The Royal Mesopotamian Crown / Tiara ---
        # Conical royal headdress with golden bull horns & feathers
        tiara_y = head_cy - 48
        tiara_poly = [
            (head_cx - 26, tiara_y + 24),
            (head_cx - 20, tiara_y),
            (head_cx + 20, tiara_y),
            (head_cx + 26, tiara_y + 24),
        ]
        pygame.draw.polygon(s, (240, 235, 220), tiara_poly)  # Fine bleached linen/felt
        pygame.draw.polygon(s, Palette.GOLD_BASE, tiara_poly, width=3)

        # Golden Horns of Divinity (Symbol of Mesopotamian Supreme Rule)
        pygame.draw.arc(s, Palette.GOLD_LIGHT, (head_cx - 36, tiara_y + 4, 30, 24), 1.0, 3.14, width=4)
        pygame.draw.arc(s, Palette.GOLD_LIGHT, (head_cx + 6, tiara_y + 4, 30, 24), 0.0, 2.14, width=4)

        # Golden Crown Finial and Sunburst on top
        pygame.draw.circle(s, Palette.GOLD_PALE, (head_cx, tiara_y), 5)
        gleam_alpha = int(120 + self.sceptre_gleam * 135)
        glow_s = pygame.Surface((18, 18), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (255, 230, 120, gleam_alpha), (9, 9), 8)
        s.blit(glow_s, (head_cx - 9, tiara_y - 9))

        # --- 5. The Golden Rod & Ring of Justice (Held in Hand) ---
        rod_x = cx + int(bust_w * 0.36)
        rod_top_y = cy - int(bust_h * 0.15)
        rod_bot_y = cy + int(bust_h * 0.42)
        # Sceptre staff
        pygame.draw.line(s, Palette.GOLD_BASE, (rod_x, rod_top_y), (rod_x, rod_bot_y), 4)
        pygame.draw.line(s, Palette.GOLD_LIGHT, (rod_x - 1, rod_top_y), (rod_x - 1, rod_bot_y), 2)
        # Sacred Ring of Justice at top
        ring_y = rod_top_y - 10
        pygame.draw.circle(s, Palette.GOLD_LIGHT, (rod_x, ring_y), 9, width=3)
        pygame.draw.circle(s, (40, 180, 200), (rod_x, ring_y), 4)  # Lapis lazuli jewel core
        if self.sceptre_gleam > 0.6:
            # Dynamic glint
            pygame.draw.line(s, (255, 255, 255), (rod_x - 6, ring_y), (rod_x + 6, ring_y), 2)
            pygame.draw.line(s, (255, 255, 255), (rod_x, ring_y - 6), (rod_x, ring_y + 6), 2)

        # Royal Hand clasping rod
        hand_y = cy + int(bust_h * 0.16)
        pygame.draw.ellipse(s, (215, 175, 135), (rod_x - 8, hand_y, 16, 18))
        pygame.draw.rect(s, Palette.GOLD_LIGHT, (rod_x - 6, hand_y + 4, 12, 4), border_radius=1)  # Signet ring

        # Blit centered onto target surface
        dest_rect = s.get_rect(center=(center_x, center_y))
        surface.blit(s, dest_rect)


class RoyalAdvisorPortrait:
    """
    Renders the Royal Vizier / High Scribe advisor with expressive mood states.
    Moods: 'normal', 'alarmed' (famine/plague/rats), 'celebratory' (bumper/harvest).
    """

    def __init__(self) -> None:
        self.time = 0.0
        self.portrait_img: Optional[pygame.Surface] = None
        self._cached_portraits: Dict[int, pygame.Surface] = {}
        v_path = os.path.join(os.path.dirname(__file__), "assets", "vizier_portrait.jpg")
        if os.path.exists(v_path):
            try:
                self.portrait_img = pygame.image.load(v_path)
            except Exception:
                self.portrait_img = None

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(
        self,
        surface: pygame.Surface,
        target: Any = None,
        y: Optional[int] = None,
        size: int = 120,
        mood: str = "normal",
        center_x: Optional[int] = None,
        center_y: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Draws the advisor medallion portrait into given rect or at (x, y)."""
        if self.portrait_img is not None:
            target_x = target if isinstance(target, (int, float)) else center_x
            target_y = y if y is not None else center_y

            if isinstance(target, pygame.Rect):
                w, h = target.width, target.height
                cx, cy = target.centerx, target.centery
            elif target_x is not None and target_y is not None:
                w = h = size
                cx, cy = int(target_x), int(target_y)
            else:
                w = h = size
                cx, cy = w // 2, h // 2

            # Idle breathing bob
            bob = int(math.sin(self.time * 2.4) * 1.5)
            cy += bob

            inner_s = min(w, h) - 8
            if inner_s not in self._cached_portraits:
                self._cached_portraits[inner_s] = make_circular_portrait(self.portrait_img, inner_s)
            p_surf = self._cached_portraits[inner_s]

            # Border color based on mood
            border_col = (
                Palette.CRIMSON_LIGHT if mood == "alarmed"
                else Palette.GOLD_LIGHT if mood == "celebratory"
                else Palette.GOLD_BASE
            )

            # Dark obsidian background disc
            pygame.draw.circle(surface, (18, 14, 12), (cx, cy), min(w, h) // 2)

            # Blit photorealistic Vizier portrait
            p_rect = p_surf.get_rect(center=(cx, cy))
            surface.blit(p_surf, p_rect)

            # Outer and inner gold/mood rings
            pygame.draw.circle(surface, border_col, (cx, cy), min(w, h) // 2, width=3)
            pygame.draw.circle(surface, Palette.PANEL_BORDER, (cx, cy), min(w, h) // 2 - 3, width=1)
        else:
            self._draw_procedural(surface, target, y, size, mood, center_x, center_y, **kwargs)

    def _draw_procedural(
        self,
        surface: pygame.Surface,
        target: Any = None,
        y: Optional[int] = None,
        size: int = 120,
        mood: str = "normal",
        center_x: Optional[int] = None,
        center_y: Optional[int] = None,
        **kwargs: Any,
    ) -> None:

        target_x = target if isinstance(target, (int, float)) else center_x
        target_y = y if y is not None else center_y

        if isinstance(target, pygame.Rect):
            dest_rect = target
            w, h = target.width, target.height
        elif target_x is not None and target_y is not None:
            w = h = size
            dest_rect = pygame.Rect(int(target_x - w // 2), int(target_y - h // 2), w, h)
        else:
            w = h = size
            dest_rect = pygame.Rect(0, 0, w, h)

        s = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2

        # Outer ornate frame
        border_col = (
            Palette.CRIMSON_LIGHT if mood == "alarmed"
            else Palette.GOLD_LIGHT if mood == "celebratory"
            else Palette.GOLD_BASE
        )
        pygame.draw.circle(s, (22, 18, 14), (cx, cy), cx - 2)
        pygame.draw.circle(s, border_col, (cx, cy), cx - 2, width=3)
        pygame.draw.circle(s, Palette.PANEL_BORDER, (cx, cy), cx - 6, width=1)

        # Advisor Head & Shoulders
        bob = math.sin(self.time * 2.5) * 1.5
        head_cy = cy - 4 + int(bob)

        # Robe
        robe_col = (40, 70, 95) if mood != "alarmed" else (90, 40, 35)
        pygame.draw.polygon(s, robe_col, [(cx - 28, cy + 28), (cx + 28, cy + 28), (cx + 18, cy + 10), (cx - 18, cy + 10)])

        # Head
        pygame.draw.circle(s, (225, 185, 145), (cx, head_cy), 16)

        # Headdress / turban
        pygame.draw.arc(s, (240, 230, 210), (cx - 17, head_cy - 18, 34, 20), 0.1, 3.04, width=5)
        pygame.draw.circle(s, border_col, (cx, head_cy - 14), 3)

        # Eyes
        if mood == "alarmed":
            # Wide stressed eyes
            pygame.draw.circle(s, (255, 255, 255), (cx - 6, head_cy - 2), 4)
            pygame.draw.circle(s, (255, 255, 255), (cx + 6, head_cy - 2), 4)
            pygame.draw.circle(s, (25, 18, 14), (cx - 6, head_cy - 2), 2)
            pygame.draw.circle(s, (25, 18, 14), (cx + 6, head_cy - 2), 2)
            # Worried brows
            pygame.draw.line(s, (25, 18, 14), (cx - 10, head_cy - 7), (cx - 3, head_cy - 5), 2)
            pygame.draw.line(s, (25, 18, 14), (cx + 10, head_cy - 7), (cx + 3, head_cy - 5), 2)
        else:
            # Calm respectful eyes
            pygame.draw.line(s, (25, 18, 14), (cx - 9, head_cy - 2), (cx - 3, head_cy - 2), 2)
            pygame.draw.line(s, (25, 18, 14), (cx + 3, head_cy - 2), (cx + 9, head_cy - 2), 2)

        # Neat trimmed beard
        beard_pts = [(cx - 11, head_cy + 5), (cx + 11, head_cy + 5), (cx + 6, head_cy + 22), (cx - 6, head_cy + 22)]
        pygame.draw.polygon(s, (35, 28, 22), beard_pts)

        # Clay tablet with cuneiform in hand
        tab_rect = pygame.Rect(cx + 8, cy + 6, 14, 18)
        pygame.draw.rect(s, (190, 150, 110), tab_rect, border_radius=2)
        pygame.draw.rect(s, (140, 100, 70), tab_rect, width=1, border_radius=2)
        for ty in range(tab_rect.y + 4, tab_rect.bottom - 2, 4):
            pygame.draw.line(s, (120, 80, 50), (tab_rect.x + 3, ty), (tab_rect.right - 3, ty), 1)

        surface.blit(s, dest_rect)


class FarmerWorker:
    """Animated procedural farmer harvesting crops in the Babylonian fields."""

    def __init__(self, x: float, y: float, work_rate: float = 1.0) -> None:
        self.x = x
        self.y = y
        self.work_rate = work_rate
        self.time = random.uniform(0.0, 6.28)
        self.carrying_sheaf = random.choice([True, False])

    def update(self, dt: float) -> None:
        self.time += dt * self.work_rate

    def draw(self, surface: pygame.Surface) -> None:
        # Reaping sickle swing cycle
        swing = math.sin(self.time * 3.0)
        bend_y = int(abs(swing) * 3)

        base_x = int(self.x)
        base_y = int(self.y)

        # Shadow
        pygame.draw.ellipse(surface, (20, 16, 12, 100), (base_x - 8, base_y + 4, 16, 6))

        # Legs (linen kilt)
        pygame.draw.line(surface, (160, 125, 85), (base_x - 3, base_y - 4), (base_x - 4, base_y + 6), 2)
        pygame.draw.line(surface, (160, 125, 85), (base_x + 3, base_y - 4), (base_x + 4, base_y + 6), 2)

        # Body (peasant linen tunic)
        tunic_poly = [
            (base_x - 5, base_y - 14 + bend_y),
            (base_x + 5, base_y - 14 + bend_y),
            (base_x + 6, base_y - 2),
            (base_x - 6, base_y - 2),
        ]
        pygame.draw.polygon(surface, (210, 195, 170), tunic_poly)

        # Head
        head_y = base_y - 18 + bend_y
        pygame.draw.circle(surface, (215, 175, 135), (base_x, head_y), 4)
        # Straw sun-hat / headband
        pygame.draw.line(surface, (180, 150, 70), (base_x - 5, head_y - 3), (base_x + 5, head_y - 3), 2)

        # Arms & Curved Bronze Sickle
        sickle_angle = swing * 0.8
        hand_x = base_x + int(math.cos(sickle_angle) * 8)
        hand_y = base_y - 8 + int(math.sin(sickle_angle) * 6) + bend_y
        pygame.draw.line(surface, (200, 160, 120), (base_x, base_y - 10 + bend_y), (hand_x, hand_y), 2)

        # Curved bronze blade
        pygame.draw.arc(surface, Palette.GOLD_LIGHT, (hand_x - 3, hand_y - 5, 8, 8), 0.5, 3.14, width=2)

        # Sheaf of golden wheat in other arm
        if self.carrying_sheaf:
            sheaf_x = base_x - 7
            sheaf_y = base_y - 12 + bend_y
            pygame.draw.line(surface, Palette.CROP_GOLD, (sheaf_x, sheaf_y + 8), (sheaf_x - 3, sheaf_y - 4), 3)
            pygame.draw.line(surface, Palette.GOLD_LIGHT, (sheaf_x, sheaf_y + 8), (sheaf_x + 3, sheaf_y - 4), 3)


class MerchantCart:
    """Animated merchant guiding a grain cart along the royal highway."""

    def __init__(self, x: float, y: float, speed: float = 18.0) -> None:
        self.x = x
        self.y = y
        self.speed = speed
        self.wheel_angle = 0.0

    def update(self, dt: float) -> None:
        self.x += self.speed * dt
        self.wheel_angle += self.speed * 0.15 * dt
        if self.x > 1320:
            self.x = -160

    def draw(self, surface: pygame.Surface) -> None:
        cx = int(self.x)
        cy = int(self.y)

        # Ground shadow
        pygame.draw.ellipse(surface, (25, 20, 16, 90), (cx - 24, cy + 8, 70, 10))

        # 1. Pack Donkey / Ox
        beast_x = cx + 28
        # Donkey body
        pygame.draw.ellipse(surface, (150, 120, 95), (beast_x - 14, cy - 8, 28, 16))
        # Head & long ears
        pygame.draw.ellipse(surface, (140, 110, 85), (beast_x + 10, cy - 18, 14, 18))
        pygame.draw.line(surface, (120, 90, 70), (beast_x + 16, cy - 18), (beast_x + 20, cy - 26), 2)
        # Legs
        leg_stride = math.sin(self.wheel_angle * 4.0) * 3
        pygame.draw.line(surface, (120, 90, 70), (beast_x - 8, cy + 4), (beast_x - 8 + int(leg_stride), cy + 14), 2)
        pygame.draw.line(surface, (120, 90, 70), (beast_x + 6, cy + 4), (beast_x + 6 - int(leg_stride), cy + 14), 2)

        # 2. Wooden Cart Body
        cart_w, cart_h = 32, 16
        pygame.draw.rect(surface, (120, 80, 45), (cx - 16, cy - 12, cart_w, cart_h), border_radius=2)
        pygame.draw.rect(surface, (75, 50, 25), (cx - 16, cy - 12, cart_w, cart_h), width=2, border_radius=2)

        # Sacks of Sumerian grain piled high in cart
        pygame.draw.circle(surface, (220, 200, 160), (cx - 8, cy - 14), 7)
        pygame.draw.circle(surface, (210, 190, 150), (cx + 4, cy - 16), 8)
        pygame.draw.circle(surface, (230, 210, 170), (cx - 2, cy - 20), 6)

        # Cart Spoked Wheel
        wheel_r = 9
        wx, wy = cx, cy + 4
        pygame.draw.circle(surface, (70, 45, 25), (wx, wy), wheel_r, width=3)
        pygame.draw.circle(surface, Palette.GOLD_DARK, (wx, wy), 2)
        # Spokes
        for spk in [0.0, 1.05, 2.09]:
            angle = self.wheel_angle + spk
            spk_x = int(math.cos(angle) * (wheel_r - 2))
            spk_y = int(math.sin(angle) * (wheel_r - 2))
            pygame.draw.line(surface, (70, 45, 25), (wx - spk_x, wy - spk_y), (wx + spk_x, wy + spk_y), 1)

        # Harness leading to donkey
        pygame.draw.line(surface, (60, 40, 25), (cx + 16, cy - 4), (beast_x - 10, cy), 2)


class PalaceGuard:
    """Royal Babylonian sentinel with spear and shield stationed at palace gates."""

    def __init__(self, x: float, y: float, facing: int = 1) -> None:
        self.x = x
        self.y = y
        self.facing = facing
        self.time = random.uniform(0.0, 6.28)

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self, surface: pygame.Surface) -> None:
        bx = int(self.x)
        by = int(self.y)
        f = self.facing

        # Breathing
        breath = math.sin(self.time * 2.0) * 1.5

        # Spear (tall ceremonial spear held upright)
        spear_x = bx + f * 9
        spear_top_y = by - 44
        spear_bot_y = by + 12
        pygame.draw.line(surface, (80, 55, 35), (spear_x, spear_top_y), (spear_x, spear_bot_y), 2)
        # Bronze leaf-shaped spearhead
        spearhead_poly = [
            (spear_x, spear_top_y - 10),
            (spear_x - 3, spear_top_y),
            (spear_x + 3, spear_top_y),
        ]
        pygame.draw.polygon(surface, Palette.GOLD_LIGHT, spearhead_poly)

        # Body (scale bronze armor over tunic)
        armor_poly = [
            (bx - 6, by - 16 + int(breath)),
            (bx + 6, by - 16 + int(breath)),
            (bx + 7, by + 2),
            (bx - 7, by + 2),
        ]
        pygame.draw.polygon(surface, (140, 85, 45), armor_poly)  # Bronze scale armor
        pygame.draw.polygon(surface, Palette.GOLD_BASE, armor_poly, width=1)

        # Conical Babylonian bronze helmet
        head_y = by - 22 + int(breath)
        pygame.draw.circle(surface, (215, 175, 135), (bx, head_y), 5)
        helmet_poly = [
            (bx - 6, head_y),
            (bx, head_y - 11),
            (bx + 6, head_y),
        ]
        pygame.draw.polygon(surface, Palette.GOLD_BASE, helmet_poly)
        pygame.draw.circle(surface, Palette.GOLD_LIGHT, (bx, head_y - 11), 2)

        # Round bronze shield held on off-hand
        shield_x = bx - f * 5
        shield_y = by - 6 + int(breath)
        pygame.draw.circle(surface, Palette.GOLD_BASE, (shield_x, shield_y), 9)
        pygame.draw.circle(surface, Palette.LAPIS_BASE, (shield_x, shield_y), 6)
        pygame.draw.circle(surface, Palette.GOLD_LIGHT, (shield_x, shield_y), 2)


class RiverBoat:
    """Mesopotamian reed boat / wooden trade barge sailing gracefully along the Euphrates."""

    def __init__(self, x: float, y: float, speed: float = 14.0) -> None:
        self.x = x
        self.y = y
        self.speed = speed
        self.time = random.uniform(0.0, 6.28)

    def update(self, dt: float) -> None:
        self.x += self.speed * dt
        self.time += dt
        if self.x > 1360:
            self.x = -140

    def draw(self, surface: pygame.Surface) -> None:
        # Gentle buoyant water bobbing
        bob = math.sin(self.time * 2.8) * 3.0
        bx = int(self.x)
        by = int(self.y + bob)

        # Water ripple / wake
        pygame.draw.ellipse(surface, (180, 225, 240, 110), (bx - 28, by + 5, 56, 6))

        # Crescent-shaped reed/wooden hull (ancient Mesopotamian guffa / trade boat)
        hull_poly = [
            (bx - 26, by - 6),
            (bx - 20, by + 6),
            (bx + 20, by + 6),
            (bx + 26, by - 6),
            (bx + 12, by + 2),
            (bx - 12, by + 2),
        ]
        pygame.draw.polygon(surface, (140, 100, 60), hull_poly)
        pygame.draw.polygon(surface, (95, 65, 35), hull_poly, width=2)

        # Timber Mast
        mast_h = 32
        pygame.draw.line(surface, (90, 60, 35), (bx, by + 2), (bx, by - mast_h), 2)

        # Square linen sail billowing in river wind
        sail_billow = math.sin(self.time * 3.5) * 4.0
        sail_poly = [
            (bx, by - mast_h + 3),
            (bx + 16 + int(sail_billow), by - mast_h + 6),
            (bx + 16 + int(sail_billow), by - 8),
            (bx, by - 12),
        ]
        pygame.draw.polygon(surface, (245, 238, 220), sail_poly)
        # Red Babylonian decorative stripe on sail
        pygame.draw.line(surface, (180, 45, 45), (bx + 8, by - mast_h + 5), (bx + 8, by - 10), 2)

        # Boatman / Oarsman
        pygame.draw.circle(surface, (215, 175, 135), (bx - 14, by - 6), 3)
        # Oar dipping into river
        oar_angle = math.sin(self.time * 2.8) * 0.4
        oar_end_x = bx - 14 + int(math.cos(1.2 + oar_angle) * 18)
        oar_end_y = by - 4 + int(math.sin(1.2 + oar_angle) * 18)
        pygame.draw.line(surface, (100, 70, 40), (bx - 14, by - 4), (oar_end_x, oar_end_y), 2)
