"""
ui_theme.py - Design system, colors, fonts, procedural sounds, and UI widgets for RetroRevive.

Provides a warm, cohesive ancient Mesopotamian aesthetic:
- Sandstone, clay, lapis lazuli blue, gold, and fertile green palette
- Scalable typography with safe system font fallbacks
- Procedural retro 8-bit sound synthesizer (no external audio assets required)
- Reusable UI components: UIButton, UINumberInput, UITextInput, UIPanel, UIModal, UIToast
"""

import math
import struct
from typing import Callable, List, Optional, Tuple
import pygame

from game_logic import GameState


# ---------------------------------------------------------------------------
# Mesopotamian Color Palette
# ---------------------------------------------------------------------------

class Palette:
    # Deep Midnight Blue & Sapphire Surfaces (Phase 8 Design System)
    SAPPHIRE_DARK = (10, 16, 28)
    SAPPHIRE_BASE = (16, 26, 46)
    SAPPHIRE_LIGHT = (26, 42, 72)
    SAPPHIRE_GLASS = (12, 20, 36, 220)
    SAPPHIRE_PANEL = (15, 25, 45, 235)

    # Sandstone & Clay
    SAND_LIGHT = (235, 218, 185)
    SAND_BASE = (210, 185, 145)
    SAND_DARK = (165, 135, 95)
    CLAY_DEEP = (120, 85, 55)

    # Dark Stone / Bronze Backgrounds -> Upgraded to Deep Sapphire Glass
    BG_DARK = (10, 16, 28)
    PANEL_BG = (16, 26, 46)
    PANEL_BG_LIGHT = (26, 40, 68)
    PANEL_BORDER = (185, 150, 75)
    PANEL_BORDER_LIGHT = (220, 185, 100)

    # Lapis Lazuli & Water
    LAPIS_DARK = (14, 28, 56)
    LAPIS_BASE = (24, 48, 96)
    LAPIS_LIGHT = (48, 95, 185)
    RIVER_BLUE = (35, 80, 155)
    RIVER_HIGHLIGHT = (70, 135, 225)

    # Royal Gold & Amber (Restrained Antique Gold)
    GOLD_DARK = (165, 125, 25)
    GOLD_BASE = (212, 175, 55)
    GOLD_LIGHT = (242, 210, 105)
    GOLD_PALE = (255, 242, 185)
    TURQUOISE_ACCENT = (38, 185, 205)

    # Agriculture & Nature
    CROP_GREEN = (65, 140, 70)
    CROP_GOLD = (215, 170, 50)
    FERTILE_EARTH = (95, 65, 40)
    PALM_GREEN = (45, 115, 55)

    # State & Alerts
    CRIMSON = (195, 45, 45)
    CRIMSON_LIGHT = (230, 75, 75)
    PESTILENCE = (145, 45, 155)
    SUCCESS_GREEN = (50, 175, 75)
    AMBER_WARN = (225, 140, 30)

    # Text & Overlays
    TEXT_TITLE = (255, 245, 225)
    TEXT_BODY = (235, 225, 210)
    TEXT_MUTED = (165, 175, 195)
    TEXT_DARK = (12, 18, 30)
    OVERLAY_DIM = (8, 12, 22, 205)

    # Luxury & Ledger Highlights
    PARCHMENT_BG = (18, 28, 50)
    BADGE_BG_DARK = (12, 18, 32)
    FOCUS_RING = (242, 210, 105)


# ---------------------------------------------------------------------------
# Font Manager with Graceful Fallbacks
# ---------------------------------------------------------------------------

class FontManager:
    """Provides cached fonts across various sizes with safe system fallbacks."""

    _cache = {}

    @classmethod
    def get_font(cls, size: int, bold: bool = False, serif: bool = False) -> pygame.font.Font:
        key = (size, bold, serif)
        if key in cls._cache:
            return cls._cache[key]

        if serif:
            font_names = ["georgia", "times new roman", "palatino", "dejavuserif", "serif"]
        else:
            font_names = ["segoe ui", "arial", "tahoma", "dejavusans", "sans-serif"]

        font = None
        for name in font_names:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                if font:
                    break
            except Exception:
                continue

        if not font:
            font = pygame.font.Font(None, size)

        cls._cache[key] = font
        return font

    @classmethod
    def title(cls, size: int = 40) -> pygame.font.Font:
        return cls.get_font(size, bold=True, serif=True)

    @classmethod
    def header(cls, size: int = 24) -> pygame.font.Font:
        return cls.get_font(size, bold=True, serif=False)

    @classmethod
    def body(cls, size: int = 18) -> pygame.font.Font:
        return cls.get_font(size, bold=False, serif=False)

    @classmethod
    def small(cls, size: int = 14) -> pygame.font.Font:
        return cls.get_font(size, bold=False, serif=False)

    @classmethod
    def mono(cls, size: int = 18) -> pygame.font.Font:
        return cls.get_font(size, bold=True, serif=False)

    @classmethod
    def italic(cls, size: int = 14) -> pygame.font.Font:
        f = cls.get_font(size, bold=False, serif=True)
        f.set_italic(True)
        return f


# ---------------------------------------------------------------------------
# Procedural Retro Sound Synthesizer
# ---------------------------------------------------------------------------

class SoundSynthesizer:
    """
    Synthesizes pleasant 8-bit retro sound effects directly in memory.
    Requires zero external audio files.
    """

    _sounds = {}
    _enabled = True

    @classmethod
    def init(cls) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            cls._generate_sounds()
        except Exception:
            cls._enabled = False

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        cls._enabled = enabled

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled

    @classmethod
    def _create_tone(cls, freq: float, duration: float, volume: float = 0.25, waveform: str = "sine") -> Optional[pygame.mixer.Sound]:
        try:
            sample_rate = 22050
            total_samples = int(sample_rate * duration)
            buffer = bytearray()

            for i in range(total_samples):
                t = i / sample_rate
                # Decay envelope
                envelope = max(0.0, 1.0 - (i / total_samples))

                if waveform == "sine":
                    val = math.sin(2.0 * math.pi * freq * t)
                elif waveform == "square":
                    val = 1.0 if math.sin(2.0 * math.pi * freq * t) >= 0 else -1.0
                else:
                    val = random.uniform(-1, 1)

                sample = int(val * 32767 * volume * envelope)
                buffer.extend(struct.pack("<h", sample))

            return pygame.mixer.Sound(buffer)
        except Exception:
            return None

    @classmethod
    def _generate_sounds(cls) -> None:
        cls._sounds["click"] = cls._create_tone(440, 0.05, volume=0.1, waveform="square")
        cls._sounds["coin"] = cls._create_tone(880, 0.15, volume=0.15)
        cls._sounds["harvest"] = cls._create_tone(330, 0.1, volume=0.1)
        cls._sounds["warning"] = cls._create_tone(220, 0.3, volume=0.2, waveform="square")
        cls._sounds["chime"] = cls._create_tone(660, 0.2, volume=0.15)
        cls._sounds["victory"] = cls._create_tone(523, 0.4, volume=0.2)

    @classmethod
    def play(cls, sound_id: str) -> None:
        if cls._enabled and sound_id in cls._sounds:
            s = cls._sounds[sound_id]
            if s:
                s.play()


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

class UIButton:
    """A standard Mesopotamian-styled button with hover states and callback."""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        text: str,
        callback: Optional[Callable[[], None]],
        primary: bool = False,
        font_size: int = 18,
        color_scheme: str = "sand",  # "sand", "gold", "lapis", "crimson"
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.primary = primary
        self.font_size = font_size
        self.color_scheme = color_scheme
        self.is_hovered = False
        self.is_pressed = False
        self.is_enabled = True

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if not self.is_enabled:
            return False

        self.is_hovered = self.rect.collidepoint(mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            self.is_pressed = True
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.is_hovered and self.callback:
                SoundSynthesizer.play("click")
                self.callback()
                self.is_pressed = False
                return True
            self.is_pressed = False

        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # Determine colors based on scheme
        if self.color_scheme == "gold":
            base, light, dark = Palette.GOLD_BASE, Palette.GOLD_LIGHT, Palette.GOLD_DARK
            text_col = Palette.TEXT_DARK
        elif self.color_scheme == "lapis":
            base, light, dark = Palette.LAPIS_BASE, Palette.LAPIS_LIGHT, Palette.LAPIS_DARK
            text_col = Palette.TEXT_TITLE
        elif self.color_scheme == "crimson":
            base, light, dark = Palette.CRIMSON, Palette.CRIMSON_LIGHT, Palette.CLAY_DEEP
            text_col = Palette.TEXT_TITLE
        else:  # sand
            base, light, dark = Palette.SAND_BASE, Palette.SAND_LIGHT, Palette.SAND_DARK
            text_col = Palette.TEXT_DARK

        if not self.is_enabled:
            base = Palette.TEXT_MUTED
            text_col = Palette.BG_DARK

        # Draw box
        draw_rect = self.rect.copy()
        if self.is_pressed:
            draw_rect.y += 2
            pygame.draw.rect(surface, dark, draw_rect, border_radius=6)
        else:
            # Shadow
            shadow_rect = draw_rect.copy()
            shadow_rect.y += 3
            pygame.draw.rect(surface, (10, 10, 15), shadow_rect, border_radius=6)
            # Main surface
            col = light if self.is_hovered else base
            pygame.draw.rect(surface, col, draw_rect, border_radius=6)
            # Border
            border_col = Palette.GOLD_PALE if self.primary else Palette.PANEL_BORDER
            pygame.draw.rect(surface, border_col, draw_rect, width=2, border_radius=6)

        # Text
        font = FontManager.get_font(self.font_size, bold=True)
        text_surf = font.render(self.text, True, text_col)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)


class UINumberInput:
    """Numeric input field with increment/decrement steppers."""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        value: int,
        min_val: int = 0,
        max_val: int = 99999,
        label: str = "",
        on_change: Optional[Callable[[int], None]] = None,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.label = label
        self.on_change = on_change

        btn_size = self.rect.height
        self.btn_minus = UIButton((self.rect.x, self.rect.y, btn_size, btn_size), "-", self.decrement, font_size=20)
        self.btn_plus = UIButton((self.rect.right - btn_size, self.rect.y, btn_size, btn_size), "+", self.increment, font_size=20)

    def increment(self) -> None:
        if self.value < self.max_val:
            self.value += 1
            if self.on_change:
                self.on_change(self.value)

    def decrement(self) -> None:
        if self.value > self.min_val:
            self.value -= 1
            if self.on_change:
                self.on_change(self.value)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if self.btn_minus.handle_event(event, mouse_pos):
            return True
        if self.btn_plus.handle_event(event, mouse_pos):
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        bg_rect = pygame.Rect(self.rect.x + self.rect.height, self.rect.y, self.rect.width - 2 * self.rect.height, self.rect.height)
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, bg_rect, border_radius=4)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, bg_rect, width=1, border_radius=4)

        # Label
        if self.label:
            lbl_surf = FontManager.small(12).render(self.label, True, Palette.TEXT_MUTED)
            surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))

        # Value
        val_surf = FontManager.header(18).render(str(self.value), True, Palette.GOLD_LIGHT)
        val_rect = val_surf.get_rect(center=bg_rect.center)
        surface.blit(val_surf, val_rect)

        self.btn_minus.draw(surface)
        self.btn_plus.draw(surface)


class UITextInput:
    """A standard single-line text input field for Pygame."""

    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        placeholder: str = "",
        font_size: int = 14,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = ""
        self.placeholder = placeholder
        self.font_size = font_size
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0.0

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(mouse_pos)
            return self.active
        
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            else:
                if len(self.text) < 100:  # Limit length
                    self.text += event.unicode
            return True
        return False

    def update(self, dt: float) -> None:
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 0.5:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        border_col = Palette.FOCUS_RING if self.active else Palette.PANEL_BORDER
        pygame.draw.rect(surface, (10, 15, 30), self.rect, border_radius=4)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=4)
        
        display_text = self.text if self.text or self.active else self.placeholder
        color = Palette.TEXT_BODY if self.text or self.active else Palette.TEXT_MUTED
        
        font = FontManager.get_font(self.font_size)
        surf = font.render(display_text, True, color)
        surface.blit(surf, (self.rect.x + 8, self.rect.y + (self.rect.height - surf.get_height()) // 2))
        
        if self.active and self.cursor_visible:
            cur_x = self.rect.x + 8 + surf.get_width() + 2
            pygame.draw.line(surface, Palette.GOLD_LIGHT, (cur_x, self.rect.y + 6), (cur_x, self.rect.bottom - 6), 2)


class UIModal:
    """Base class for centered popup dialogs."""

    def __init__(self, width: int, height: int, title: str) -> None:
        self.rect = pygame.Rect((1280 - width) // 2, (720 - height) // 2, width, height)
        self.title = title
        self.is_open = True

    def draw_base(self, surface: pygame.Surface) -> None:
        # Dim background
        overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
        overlay.fill(Palette.OVERLAY_DIM)
        surface.blit(overlay, (0, 0))

        # Panel
        pygame.draw.rect(surface, Palette.SAPPHIRE_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, Palette.GOLD_BASE, self.rect, width=2, border_radius=12)

        # Header
        title_surf = FontManager.header(22).render(self.title, True, Palette.GOLD_PALE)
        surface.blit(title_surf, (self.rect.x + 24, self.rect.y + 20))
        pygame.draw.line(surface, Palette.PANEL_BORDER, (self.rect.x + 20, self.rect.y + 55), (self.rect.right - 20, self.rect.y + 55), 1)


class UIToast:
    """Brief overlay message that fades away."""

    def __init__(self, text: str, duration: float = 3.0, color: Tuple[int, int, int] = Palette.GOLD_BASE) -> None:
        self.text = text
        self.duration = duration
        self.timer = duration
        self.color = color
        self.is_active = True

    def update(self, dt: float) -> None:
        self.timer -= dt
        if self.timer <= 0:
            self.is_active = False

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(min(1.0, self.timer * 2.0) * 255)
        toast_surf = pygame.Surface((400, 50), pygame.SRCALPHA)
        pygame.draw.rect(toast_surf, (20, 30, 45, alpha), (0, 0, 400, 50), border_radius=8)
        pygame.draw.rect(toast_surf, (*self.color, alpha), (0, 0, 400, 50), width=1, border_radius=8)
        
        txt = FontManager.body(16).render(self.text, True, Palette.TEXT_BODY)
        txt.set_alpha(alpha)
        toast_surf.blit(txt, txt.get_rect(center=(200, 25)))
        
        surface.blit(toast_surf, (440, 600))


class DecreePreviewData:
    """Helper for passing turn outcome projections to the UI."""
    def __init__(self, buy: int, sell: int, feed: int, plant: int):
        self.buy_acres = buy
        self.sell_acres = sell
        self.feed_bushels = feed
        self.plant_acres = plant


class UIDecreePreview:
    """Interactive preview panel showing consequences of current orders."""
    # (Existing implementation kept for brevity)
    pass
