"""
launcher_menu.py — Cinematic main launcher for RetroRevive: Hammurabi's Living Empire.

Displays a beautiful ancient Babylonian themed launcher window with:
  - Full-screen procedurally-drawn Babylon cityscape backdrop
  - Animated golden particles / dust motes
  - Lapis Ishtar Gate entrance motif
  - Royal title typography
  - Mode selection buttons (3D Kingdom, Classic 2D, Watch Cinematic)
  - Looping animated golden border
  - King Hammurabi silhouette
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Pygame import guard
# ---------------------------------------------------------------------------
try:
    import pygame
    import pygame.gfxdraw
    _PYGAME_OK = True
except ImportError:
    _PYGAME_OK = False


# ---------------------------------------------------------------------------
# Colour palette matching reference images
# ---------------------------------------------------------------------------
DEEP_NAVY       = ( 15,  20,  42)
ROYAL_NAVY      = ( 20,  35,  80)
LAPIS_DEEP      = ( 18,  52, 115)
LAPIS_BRIGHT    = ( 45,  90, 180)
GOLD            = (235, 198,  71)
GOLD_DARK       = (180, 140,  30)
GOLD_PALE       = (250, 230, 160)
SANDSTONE       = (209, 178, 133)
SANDSTONE_DARK  = (160, 130,  90)
SANDSTONE_LIGHT = (235, 210, 165)
WHITE           = (255, 255, 255)
BLACK           = (  0,   0,   0)
SKY_GOLD        = (235, 170,  70)
SKY_BLUE        = ( 80, 130, 200)
DUST_ORANGE     = (220, 160,  80)

SCREEN_W = 1280
SCREEN_H = 720


# ---------------------------------------------------------------------------
# Helper drawing functions
# ---------------------------------------------------------------------------

def _lerp_col(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _draw_gradient_rect(surf, rect, c1, c2, vertical=True):
    """Fill rect with a gradient from c1 to c2."""
    x, y, w, h = rect
    if vertical:
        for i in range(h):
            t = i / max(1, h - 1)
            pygame.draw.line(surf, _lerp_col(c1, c2, t), (x, y + i), (x + w, y + i))
    else:
        for i in range(w):
            t = i / max(1, w - 1)
            pygame.draw.line(surf, _lerp_col(c1, c2, t), (x + i, y), (x + i, y + h))


def _draw_ziggurat(surf, cx, cy, scale=1.0, col=SANDSTONE, dark=SANDSTONE_DARK):
    """Draw a simplified Ziggurat silhouette."""
    tiers = 7
    tier_w_base = int(120 * scale)
    tier_h = int(18 * scale)
    for i in range(tiers):
        w = tier_w_base - i * int(14 * scale)
        h = tier_h
        x = cx - w // 2
        y = cy - (i + 1) * h
        pygame.draw.rect(surf, col, (x, y, w, h))
        pygame.draw.rect(surf, dark, (x, y, w, 2))   # shadow top edge
    # shrine on top
    shrine_w = int(20 * scale)
    shrine_h = int(25 * scale)
    pygame.draw.rect(surf, _lerp_col(col, (255, 255, 255), 0.15),
                     (cx - shrine_w // 2, cy - tiers * tier_h - shrine_h, shrine_w, shrine_h))


def _draw_city_wall(surf, x, y, length, height, col=SANDSTONE, dark=SANDSTONE_DARK):
    """Draw a section of crenellated city wall."""
    pygame.draw.rect(surf, col, (x, y, length, height))
    # crenellations
    merlon_w = 18
    gap_w    = 12
    mx = x
    while mx < x + length:
        pygame.draw.rect(surf, col, (mx, y - 16, merlon_w, 16))
        mx += merlon_w + gap_w


def _draw_ishtar_gate_silhouette(surf, cx, bottom_y, scale=1.0):
    """Draw Ishtar Gate arch silhouette in lapis + gold."""
    gate_w = int(160 * scale)
    gate_h = int(220 * scale)
    tower_w = int(55 * scale)
    tower_h = int(250 * scale)

    # Left tower
    pygame.draw.rect(surf, LAPIS_DEEP,
                     (cx - gate_w // 2 - tower_w, bottom_y - tower_h, tower_w, tower_h))
    # Right tower
    pygame.draw.rect(surf, LAPIS_DEEP,
                     (cx + gate_w // 2, bottom_y - tower_h, tower_w, tower_h))
    # Gate body
    pygame.draw.rect(surf, LAPIS_BRIGHT,
                     (cx - gate_w // 2, bottom_y - gate_h, gate_w, gate_h))

    # Arch
    arch_r = gate_w // 2 - 8
    arch_cx = cx
    arch_cy = bottom_y - gate_h + arch_r + 10
    pygame.draw.circle(surf, DEEP_NAVY, (arch_cx, arch_cy), arch_r)   # arch opening

    # Gold animal relief strips
    strip_y = bottom_y - gate_h + int(50 * scale)
    while strip_y < bottom_y - int(20 * scale):
        pygame.draw.rect(surf, GOLD_DARK,
                         (cx - gate_w // 2, strip_y, gate_w, max(2, int(4 * scale))))
        strip_y += int(28 * scale)

    # Crenellations on towers
    for tx in [cx - gate_w // 2 - tower_w, cx + gate_w // 2]:
        for mx in range(tx, tx + tower_w, 10):
            pygame.draw.rect(surf, LAPIS_BRIGHT, (mx, bottom_y - tower_h - 14, 7, 14))

    # Gold top border
    pygame.draw.rect(surf, GOLD,
                     (cx - gate_w // 2 - tower_w, bottom_y - tower_h - 6,
                      gate_w + tower_w * 2, 6))


def _draw_palm_silhouette(surf, x, y, height=80):
    """Draw a simple palm tree silhouette."""
    # trunk
    pygame.draw.line(surf, SANDSTONE_DARK,
                     (x, y), (x + height // 10, y - height), 4)
    # fronds (lines from top)
    top_x = x + height // 10
    top_y = y - height
    for angle_deg in range(-80, 100, 20):
        angle_r = math.radians(angle_deg - 90)
        frond_l = height * 0.45
        ex = int(top_x + frond_l * math.cos(angle_r))
        ey = int(top_y + frond_l * math.sin(angle_r) * 0.8)
        pygame.draw.line(surf, (40, 90, 25), (top_x, top_y), (ex, ey), 2)


def _draw_people_silhouettes(surf, y_ground):
    """Draw tiny human silhouettes walking near the Ishtar Gate."""
    positions = [150, 220, 310, 390, 440, 550, 620, 720, 800, 900, 1050, 1150]
    rng = random.Random(7)
    for x in positions:
        h = rng.randint(20, 32)
        col = _lerp_col(SANDSTONE_DARK, (80, 50, 20), rng.random())
        # body
        pygame.draw.line(surf, col, (x, y_ground), (x, y_ground - h), 2)
        # head
        pygame.draw.circle(surf, col, (x, y_ground - h - 4), 4)
        # arms
        arm_y = y_ground - int(h * 0.65)
        pygame.draw.line(surf, col, (x - 5, arm_y), (x + 5, arm_y + 3), 2)


def _draw_dust_particles(surf, particles):
    """Draw floating dust motes / golden particles."""
    for p in particles:
        alpha_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
        alpha = int(p["alpha"])
        pygame.draw.circle(alpha_surf, (*GOLD, alpha), (2, 2), 2)
        surf.blit(alpha_surf, (int(p["x"]), int(p["y"])))


def _make_particles(n=120):
    rng = random.Random(42)
    return [
        {
            "x": rng.uniform(0, SCREEN_W),
            "y": rng.uniform(0, SCREEN_H),
            "vx": rng.uniform(-0.3, 0.3),
            "vy": rng.uniform(-0.8, -0.2),
            "alpha": rng.uniform(60, 200),
            "life": rng.uniform(0, 6.28),
        }
        for _ in range(n)
    ]


def _update_particles(particles, dt):
    for p in particles:
        p["x"]  += p["vx"] + 0.3 * math.sin(p["life"] * 1.3)
        p["y"]  += p["vy"]
        p["life"] += dt
        p["alpha"] = 120 + 80 * math.sin(p["life"] * 2.0)
        if p["y"] < -10:
            p["y"] = SCREEN_H + 5
            p["x"] = random.uniform(0, SCREEN_W)


# ---------------------------------------------------------------------------
# Procedural backdrop (Babylon skyline)
# ---------------------------------------------------------------------------

def _draw_babylon_backdrop(surf: "pygame.Surface") -> None:
    """Draw a rich Babylon city backdrop onto surf."""

    # === Sky gradient (golden hour) ===
    _draw_gradient_rect(surf, (0, 0, SCREEN_W, SCREEN_H // 2 + 80),
                        SKY_BLUE, SKY_GOLD)

    # === Ground plane ===
    _draw_gradient_rect(surf, (0, SCREEN_H // 2 + 80, SCREEN_W, SCREEN_H // 2 - 80),
                        _lerp_col(SANDSTONE, SKY_GOLD, 0.4),
                        SANDSTONE_DARK)

    # === Euphrates river strip ===
    river_y = SCREEN_H - 180
    river_h = 45
    _draw_gradient_rect(surf, (0, river_y, SCREEN_W, river_h),
                        (60, 130, 195), (40, 100, 160))
    # Caustic shimmer
    for rx in range(0, SCREEN_W, 25):
        alpha_s = pygame.Surface((22, 3), pygame.SRCALPHA)
        alpha_s.fill((200, 235, 255, 60))
        surf.blit(alpha_s, (rx, river_y + 8 + int(6 * math.sin(rx * 0.1))))

    # === Background city (distant buildings) ===
    ground_y = SCREEN_H - 195
    rng = random.Random(99)
    for i in range(30):
        bx = rng.randint(0, SCREEN_W - 30)
        bh = rng.randint(20, 80)
        bw = rng.randint(18, 50)
        col = _lerp_col(SANDSTONE_DARK, SANDSTONE, rng.random() * 0.5)
        pygame.draw.rect(surf, col, (bx, ground_y - bh, bw, bh))

    # === City walls (left and right) ===
    _draw_city_wall(surf, 0, ground_y - 55, 200, 55)
    _draw_city_wall(surf, SCREEN_W - 200, ground_y - 55, 200, 55)

    # === Ziggurat (distant, centre-right) ===
    _draw_ziggurat(surf, SCREEN_W * 3 // 4, ground_y, scale=1.1)

    # === Ishtar Gate (centre, foreground) ===
    _draw_ishtar_gate_silhouette(surf, SCREEN_W // 2, ground_y + 30, scale=1.0)

    # === Palm trees ===
    palm_positions = [80, 160, 240, SCREEN_W - 80, SCREEN_W - 160, SCREEN_W - 240,
                      SCREEN_W // 4, SCREEN_W * 3 // 4 - 50]
    for px in palm_positions:
        h = random.Random(px).randint(65, 95)
        _draw_palm_silhouette(surf, px, ground_y, h)

    # === People silhouettes near gate ===
    _draw_people_silhouettes(surf, ground_y + 28)

    # === Atmospheric dust haze ===
    haze = pygame.Surface((SCREEN_W, 80), pygame.SRCALPHA)
    haze.fill((220, 180, 100, 28))
    surf.blit(haze, (0, ground_y - 10))

    # === Foreground dark gradient ===
    _draw_gradient_rect(surf, (0, SCREEN_H - 80, SCREEN_W, 80),
                        DEEP_NAVY, BLACK)


# ---------------------------------------------------------------------------
# Button class
# ---------------------------------------------------------------------------

class _Button:
    BORDER_W = 3

    def __init__(
        self, label: str, rect: tuple,
        icon: str = "",
        color_bg = LAPIS_DEEP,
        color_border = GOLD,
        color_text = GOLD_PALE,
        font_size: int = 22,
    ):
        self.label  = label
        self.rect   = pygame.Rect(rect)
        self.icon   = icon
        self.bg     = color_bg
        self.border = color_border
        self.text_c = color_text
        self.font_size = font_size
        self._hovered  = False
        self._anim_t   = 0.0

    def update(self, dt: float, mouse_pos: tuple) -> None:
        self._hovered = self.rect.collidepoint(mouse_pos)
        self._anim_t  = (self._anim_t + dt * 3) % (2 * math.pi)

    def draw(self, surf: "pygame.Surface", font: "pygame.font.Font") -> None:
        col  = _lerp_col(self.bg, LAPIS_BRIGHT, 0.45 if self._hovered else 0.0)
        border_col = _lerp_col(self.border, GOLD_PALE, 0.5 if self._hovered else 0.0)
        glow_alpha = int(40 + 30 * math.sin(self._anim_t)) if self._hovered else 20

        # Glow
        glow = pygame.Surface((self.rect.w + 16, self.rect.h + 16), pygame.SRCALPHA)
        glow.fill((*GOLD, glow_alpha))
        surf.blit(glow, (self.rect.x - 8, self.rect.y - 8))

        # Background
        pygame.draw.rect(surf, col, self.rect, border_radius=6)
        pygame.draw.rect(surf, border_col, self.rect, self.BORDER_W, border_radius=6)

        # Gold inner accent line
        inner = self.rect.inflate(-self.BORDER_W * 3, -self.BORDER_W * 3)
        pygame.draw.rect(surf, _lerp_col(self.border, col, 0.7),
                         inner, 1, border_radius=4)

        # Label
        lbl = f"{self.icon}  {self.label}" if self.icon else self.label
        txt_surf = font.render(lbl, True, self.text_c)
        surf.blit(txt_surf, txt_surf.get_rect(center=self.rect.center))

    def is_clicked(self, event: "pygame.event.Event") -> bool:
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


# ---------------------------------------------------------------------------
# LauncherMenu
# ---------------------------------------------------------------------------

class LauncherMenu:
    """
    Full-screen launcher menu for RetroRevive: Hammurabi's Living Empire.

    Returns one of: 'play', 'cinematic', 'quit'
    """

    def __init__(self) -> None:
        if not _PYGAME_OK:
            raise RuntimeError("pygame not available")

        pygame.init()
        pygame.display.set_caption("RetroRevive — Hammurabi: The Living Empire")
        self._screen = pygame.display.set_mode(
            (SCREEN_W, SCREEN_H), pygame.NOFRAME | pygame.RESIZABLE
        )
        self._clock  = pygame.time.Clock()

        # Fonts
        self._font_title  = self._load_font(58)
        self._font_sub    = self._load_font(22)
        self._font_btn    = self._load_font(22)
        self._font_tiny   = self._load_font(14)

        # Pre-render backdrop
        self._backdrop = pygame.Surface((SCREEN_W, SCREEN_H))
        _draw_babylon_backdrop(self._backdrop)

        # Particles
        self._particles = _make_particles(150)

        # Animated border phase
        self._border_t  = 0.0
        self._title_y   = -80.0   # slide-in from top
        self._btn_alpha = 0.0

        # Buttons
        btn_cx = SCREEN_W // 2
        btn_w  = 360
        btn_h  = 48
        gap    = 12
        start_y = 360

        self._buttons = [
            _Button("Rule the Kingdom",        (btn_cx - btn_w // 2, start_y, btn_w, btn_h),
                    icon="👑", color_bg=ROYAL_NAVY),
            _Button("AI Royal Governor",       (btn_cx - btn_w // 2, start_y + btn_h + gap, btn_w, btn_h),
                    icon="⚖", color_bg=(25, 45, 80)),
            _Button("Watch Cinematic Intro",   (btn_cx - btn_w // 2, start_y + 2 * (btn_h + gap), btn_w, btn_h),
                    icon="🎬", color_bg=(55, 25, 15)),
            _Button("Military Command",        (btn_cx - btn_w // 2, start_y + 3 * (btn_h + gap), btn_w, btn_h),
                    icon="⚔", color_bg=(45, 20, 20)),
            _Button("Agricultural Ministry",   (btn_cx - btn_w // 2, start_y + 4 * (btn_h + gap), btn_w, btn_h),
                    icon="🌾", color_bg=(20, 45, 20)),
            _Button("Quit",                    (btn_cx - btn_w // 2, start_y + 5 * (btn_h + gap), btn_w, btn_h // 2 + 4),
                    icon="✕", color_bg=(40, 15, 15), color_border=SANDSTONE_DARK,
                    color_text=SANDSTONE, font_size=16),
        ]
        self._action_map = {
            self._buttons[0]: "play",
            self._buttons[1]: "governor",
            self._buttons[2]: "cinematic",
            self._buttons[3]: "military",
            self._buttons[4]: "agriculture",
            self._buttons[5]: "quit",
        }

    @staticmethod
    def _load_font(size: int) -> "pygame.font.Font":
        """Try to load a system serif font; fall back to default."""
        candidates = [
            "Palatino Linotype", "Times New Roman", "Georgia",
            "Book Antiqua", "Garamond", "serif",
        ]
        for name in candidates:
            try:
                f = pygame.font.SysFont(name, size, bold=False)
                return f
            except Exception:
                pass
        return pygame.font.Font(None, size)

    def _draw_animated_border(self, surf: "pygame.Surface") -> None:
        """Draw an animated golden border with corner ornaments."""
        margin = 18
        r = pygame.Rect(margin, margin, SCREEN_W - 2 * margin, SCREEN_H - 2 * margin)
        pulse = 0.75 + 0.25 * math.sin(self._border_t * 2.5)
        col   = (int(GOLD[0] * pulse), int(GOLD[1] * pulse), int(GOLD[2] * pulse))
        pygame.draw.rect(surf, col, r, 2, border_radius=4)
        # Inner border
        r2 = r.inflate(-8, -8)
        pygame.draw.rect(surf, GOLD_DARK, r2, 1, border_radius=3)

        # Corner ornaments (simple diamond shape)
        corners = [r.topleft, r.topright, r.bottomleft, r.bottomright]
        offsets = [(6, 6), (-6, 6), (6, -6), (-6, -6)]
        for (cx_, cy_), (ox, oy) in zip(corners, offsets):
            diamond = [
                (cx_ + ox, cy_),
                (cx_, cy_ + oy),
                (cx_ + ox * 2, cy_ + oy),
                (cx_ + ox, cy_ + oy * 2),
            ]
            pygame.draw.polygon(surf, GOLD, [(cx_ + ox, cy_), (cx_, cy_ + oy),
                                              (cx_ + ox * 2, cy_ + oy),
                                              (cx_ + ox, cy_ + oy * 2)])

    def _draw_title_block(self, surf: "pygame.Surface") -> None:
        """Render the cinematic title with subtitle."""
        ty = int(self._title_y)

        # Gold top ornament
        mid = SCREEN_W // 2
        pygame.draw.line(surf, GOLD, (mid - 220, ty - 20), (mid + 220, ty - 20), 1)
        pygame.draw.polygon(surf, GOLD, [(mid, ty - 30), (mid - 8, ty - 20), (mid + 8, ty - 20)])

        # Main title — split into two lines for the cinematic feel
        t1 = self._font_title.render("HAMMURABI", True, GOLD)
        t2 = self._font_title.render("The Living Empire", True, GOLD_PALE)
        surf.blit(t1, t1.get_rect(centerx=mid, top=ty))
        surf.blit(t2, t2.get_rect(centerx=mid, top=ty + 62))

        # Subtitle
        sub_col = _lerp_col(SANDSTONE, GOLD, 0.6)
        sub = self._font_sub.render(
            "RetroRevive  •  Ancient Babylonian Kingdom Strategy", True, sub_col
        )
        surf.blit(sub, sub.get_rect(centerx=mid, top=ty + 135))

        # Decorative line
        pygame.draw.line(surf, GOLD_DARK, (mid - 260, ty + 162), (mid + 260, ty + 162), 1)

    def _draw_bottom_info(self, surf: "pygame.Surface") -> None:
        """Show keybinding hint and version at bottom."""
        info = "Press ESC to quit  |  Arrow keys to navigate  |  Enter to confirm"
        txt = self._font_tiny.render(info, True, _lerp_col(SANDSTONE_DARK, GOLD, 0.3))
        surf.blit(txt, txt.get_rect(centerx=SCREEN_W // 2, bottom=SCREEN_H - 26))

        ver = self._font_tiny.render("v3.0  feature/3d-babylon-empire", True, SANDSTONE_DARK)
        surf.blit(ver, (SCREEN_W - ver.get_width() - 28, SCREEN_H - 28))

    def _animate_intro(self, dt: float) -> None:
        """Animate title sliding down + buttons fading in."""
        target_y = 185.0
        if self._title_y < target_y:
            self._title_y += min((target_y - self._title_y) * 4 * dt + 60 * dt, target_y - self._title_y + 0.5)
            self._title_y = min(self._title_y, target_y)

        target_alpha = 255.0
        self._btn_alpha = min(target_alpha, self._btn_alpha + 180 * dt)

    def run(self) -> str:
        """Run the launcher event loop. Returns one of: 'play', 'cinematic', 'military', 'agriculture', 'quit'."""
        running = True
        result  = "quit"

        while running:
            dt = self._clock.tick(60) / 1000.0
            self._border_t += dt
            self._animate_intro(dt)

            # --- Events ---
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        result = "play"
                        running = False

                for btn in self._buttons:
                    if btn.is_clicked(event):
                        result = self._action_map[btn]
                        running = False

            for btn in self._buttons:
                btn.update(dt, mouse_pos)

            _update_particles(self._particles, dt)

            # --- Draw ---
            self._screen.blit(self._backdrop, (0, 0))
            _draw_dust_particles(self._screen, self._particles)

            # Translucent dark overlay over lower half for readability
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((5, 8, 25, 175))
            self._screen.blit(overlay, (0, SCREEN_H // 3))

            self._draw_animated_border(self._screen)
            self._draw_title_block(self._screen)

            # Buttons with fade-in
            btn_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            for btn in self._buttons:
                btn.draw(btn_surf, self._font_btn)
            btn_surf.set_alpha(int(self._btn_alpha))
            self._screen.blit(btn_surf, (0, 0))

            self._draw_bottom_info(self._screen)
            pygame.display.flip()

        pygame.quit()
        return result


# ---------------------------------------------------------------------------
# Standalone launcher entry point
# ---------------------------------------------------------------------------

def launch() -> None:
    """Open the launcher menu, then launch the chosen mode."""
    if not _PYGAME_OK:
        print("pygame-ce not available. Run: pip install pygame-ce")
        sys.exit(1)

    menu = LauncherMenu()
    choice = menu.run()

    root   = Path(__file__).parent
    venv_py = root / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        python = str(venv_py)
    else:
        python = sys.executable

    if choice == "play":
        subprocess.Popen([python, str(root / "main.py")])
    elif choice == "governor":
        subprocess.Popen([python, str(root / "main.py"), "--screen", "governor"])
    elif choice == "cinematic":
        # Play the AI cinematic video if available
        video_path = Path(
            r"C:\Users\rohit\.gemini\antigravity\brain\6f39ef59-d107-4ba7-b334-74f65f2f80f8"
            r"\.user_uploaded\media_1793461843017_d5e8c805.mp4"
        )
        if video_path.exists():
            os.startfile(str(video_path))
        else:
            subprocess.Popen([python, str(root / "main.py"), "--cinematic"])
    elif choice == "military":
        subprocess.Popen([python, str(root / "main.py"), "--screen", "military"])
    elif choice == "agriculture":
        subprocess.Popen([python, str(root / "main.py"), "--screen", "agriculture"])
    elif choice == "quit":
        pass


if __name__ == "__main__":
    launch()

