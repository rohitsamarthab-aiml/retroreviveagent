"""
ui_military.py - Military system module for RetroRevive Babylonian strategy game.

Provides animated military units, formations, battle scenes, and the full
MilitaryDashboard screen for managing the ancient Babylonian army.

Visual style: Deep navy backgrounds, antique gold accents, bronze armor,
hand-drawn polygon characters — professional Mesopotamian aesthetic.
"""

import math
import random
from typing import List, Optional, Tuple

import pygame

from ui_theme import Palette, FontManager, UIButton
from game_logic import GameState


# ---------------------------------------------------------------------------
# Color Constants
# ---------------------------------------------------------------------------

NAVY      = (15, 20, 40)
GOLD      = (212, 175, 55)
GOLD_DARK = (160, 125, 30)
BRONZE    = (140, 85, 45)
BRONZE_LIGHT = (180, 120, 65)
CRIMSON   = (160, 30, 30)
CRIMSON_LIGHT = (200, 60, 60)
SKIN      = (210, 165, 110)
IRON_GREY = (110, 115, 125)
SHIELD_RED = (140, 35, 35)
DUST      = (200, 185, 145, 160)
SPARK     = (255, 230, 80)
WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)


# ---------------------------------------------------------------------------
# Soldier State Constants
# ---------------------------------------------------------------------------

IDLE    = "IDLE"
MARCH   = "MARCH"
PATROL  = "PATROL"
GUARD   = "GUARD"


# ---------------------------------------------------------------------------
# Helper drawing utilities
# ---------------------------------------------------------------------------

def _draw_soldier_at(surface: pygame.Surface, cx: int, cy: int,
                     anim: float, state: str, scale: float = 1.0,
                     facing: int = 1) -> None:
    """
    Render a single Babylonian soldier centred at (cx, cy).

    anim    – animation phase [0, 2*pi)
    state   – IDLE / MARCH / PATROL / GUARD
    scale   – size multiplier
    facing  – +1 = right, -1 = left
    """
    s = scale
    f = facing

    # ----- marching oscillations -----
    if state in (MARCH, PATROL):
        leg_l  =  math.sin(anim) * 10 * s
        leg_r  = -math.sin(anim) * 10 * s
        arm_l  = -math.sin(anim) * 8 * s
        arm_r  =  math.sin(anim) * 8 * s
        bob    =  abs(math.sin(anim)) * 2 * s
    else:
        leg_l = leg_r = 0.0
        arm_l = arm_r = 0.0
        bob   = 0.0

    # ----- body proportions -----
    head_r   = int(7 * s)
    torso_h  = int(18 * s)
    torso_w  = int(10 * s)
    leg_len  = int(14 * s)
    arm_len  = int(12 * s)
    spear_h  = int(36 * s)

    bx = cx
    by = cy - int(bob)

    # ---- spear (behind soldier when facing right) ----
    spear_x = bx + f * int(12 * s)
    spear_bot = (spear_x, by + int(8 * s))
    spear_top = (spear_x, by + int(8 * s) - spear_h)
    pygame.draw.line(surface, BRONZE, spear_bot, spear_top, max(1, int(2 * s)))
    # spear tip
    tip_pts = [
        (spear_x - int(3 * s), spear_top[1] + int(6 * s)),
        (spear_x,              spear_top[1] - int(2 * s)),
        (spear_x + int(3 * s), spear_top[1] + int(6 * s)),
    ]
    pygame.draw.polygon(surface, IRON_GREY, tip_pts)

    # ---- shield (on off-hand side) ----
    shield_x = bx - f * int(11 * s)
    shield_y = by - int(4 * s)
    shield_pts = [
        (shield_x - int(5 * s), shield_y - int(10 * s)),
        (shield_x + int(5 * s), shield_y - int(10 * s)),
        (shield_x + int(6 * s), shield_y + int(4 * s)),
        (shield_x,              shield_y + int(12 * s)),
        (shield_x - int(6 * s), shield_y + int(4 * s)),
    ]
    pygame.draw.polygon(surface, SHIELD_RED, shield_pts)
    pygame.draw.polygon(surface, BRONZE, shield_pts, max(1, int(2 * s)))
    # shield boss
    pygame.draw.circle(surface, BRONZE_LIGHT, (shield_x, shield_y), int(3 * s))

    # ---- legs ----
    hip_y = by + int(10 * s)
    foot_y = by + int(10 * s) + leg_len
    # left leg
    pygame.draw.line(surface, BRONZE,
                     (bx - int(3 * s), hip_y),
                     (bx - int(3 * s) + int(leg_l), int(foot_y + leg_l)), max(1, int(3 * s)))
    # right leg
    pygame.draw.line(surface, BRONZE,
                     (bx + int(3 * s), hip_y),
                     (bx + int(3 * s) + int(leg_r), int(foot_y + leg_r)), max(1, int(3 * s)))
    # sandals
    pygame.draw.ellipse(surface, BRONZE_LIGHT,
                        (bx - int(3 * s) + int(leg_l) - int(4 * s),
                         int(foot_y + leg_l) - int(2 * s),
                         int(8 * s), int(4 * s)))
    pygame.draw.ellipse(surface, BRONZE_LIGHT,
                        (bx + int(3 * s) + int(leg_r) - int(4 * s),
                         int(foot_y + leg_r) - int(2 * s),
                         int(8 * s), int(4 * s)))

    # ---- torso / scale armour ----
    torso_rect = pygame.Rect(bx - torso_w // 2, by - torso_h // 2, torso_w, torso_h)
    pygame.draw.rect(surface, BRONZE, torso_rect, border_radius=3)
    # scale pattern (3 rows × 2 cols)
    for row in range(3):
        for col in range(2):
            sx = torso_rect.left + col * int(5 * s) + int(1 * s)
            sy = torso_rect.top  + row * int(5 * s) + int(2 * s)
            pygame.draw.ellipse(surface, BRONZE_LIGHT, (sx, sy, int(4 * s), int(3 * s)))
    pygame.draw.rect(surface, GOLD_DARK, torso_rect, max(1, int(1 * s)), border_radius=3)

    # ---- arms ----
    shoulder_y = by - int(7 * s)
    # sword arm (forward)
    pygame.draw.line(surface, SKIN,
                     (bx + f * int(4 * s), shoulder_y),
                     (bx + f * int(4 * s) + int(arm_r * f), shoulder_y + arm_len),
                     max(1, int(3 * s)))
    # shield arm (back)
    pygame.draw.line(surface, SKIN,
                     (bx - f * int(4 * s), shoulder_y),
                     (bx - f * int(4 * s) + int(arm_l * f), shoulder_y + arm_len),
                     max(1, int(3 * s)))

    # ---- neck + head ----
    neck_y = by - int(torso_h // 2) - int(2 * s)
    pygame.draw.line(surface, SKIN, (bx, neck_y), (bx, neck_y - int(4 * s)), max(1, int(2 * s)))
    head_cy = neck_y - head_r - int(2 * s)
    pygame.draw.circle(surface, SKIN, (bx, head_cy), head_r)
    # face detail (left = negative x for face side)
    eye_x = bx + f * int(3 * s)
    eye_y = head_cy - int(1 * s)
    pygame.draw.circle(surface, BLACK, (eye_x, eye_y), max(1, int(1.5 * s)))
    # beard
    beard_pts = [
        (bx - int(4 * s), head_cy + int(3 * s)),
        (bx + int(4 * s), head_cy + int(3 * s)),
        (bx + int(3 * s), head_cy + int(8 * s)),
        (bx - int(3 * s), head_cy + int(8 * s)),
    ]
    pygame.draw.polygon(surface, (80, 50, 25), beard_pts)

    # ---- bronze helmet ----
    helm_pts = [
        (bx - head_r - int(1 * s), head_cy + int(2 * s)),
        (bx - head_r + int(1 * s), head_cy - int(4 * s)),
        (bx,                       head_cy - head_r - int(6 * s)),
        (bx + head_r - int(1 * s), head_cy - int(4 * s)),
        (bx + head_r + int(1 * s), head_cy + int(2 * s)),
    ]
    pygame.draw.polygon(surface, BRONZE, helm_pts)
    pygame.draw.polygon(surface, GOLD, helm_pts, max(1, int(1 * s)))
    # helmet crest / plume
    plume_pts = [
        (bx - int(2 * s), head_cy - head_r - int(5 * s)),
        (bx + int(2 * s), head_cy - head_r - int(5 * s)),
        (bx + int(1 * s), head_cy - head_r - int(14 * s)),
        (bx - int(1 * s), head_cy - head_r - int(14 * s)),
    ]
    pygame.draw.polygon(surface, CRIMSON, plume_pts)


# ---------------------------------------------------------------------------
# SoldierUnit
# ---------------------------------------------------------------------------

class SoldierUnit:
    """
    A single animated Babylonian soldier with full movement states.

    Attributes
    ----------
    x, y        – world position (formation anchor)
    row, col    – grid index within formation
    state       – current animation state
    """

    ANIM_SPEED = 4.0   # radians per second

    def __init__(self, x: float, y: float, row: int = 0, col: int = 0,
                 scale: float = 1.0, facing: int = 1) -> None:
        self.x = float(x)
        self.y = float(y)
        self.row = row
        self.col = col
        self.scale = scale
        self.facing = facing

        self.state: str = IDLE
        self._anim_phase: float = random.uniform(0, math.pi * 2)
        self._look_timer: float = random.uniform(1.5, 4.0)  # for PATROL look-around
        self._looking: bool = False
        self._look_elapsed: float = 0.0

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        self.state = state

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Advance animation phase based on state."""
        if self.state in (MARCH, PATROL):
            self._anim_phase += self.ANIM_SPEED * dt

        if self.state == PATROL:
            self._look_timer -= dt
            if self._look_timer <= 0 and not self._looking:
                self._looking = True
                self._look_elapsed = 0.0
                self._look_timer = random.uniform(3.0, 6.0)
            if self._looking:
                self._look_elapsed += dt
                if self._look_elapsed > 1.2:
                    self._looking = False

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        """Draw soldier at current (x, y)."""
        st = IDLE if (self._looking and self.state == PATROL) else self.state
        _draw_soldier_at(surface,
                         int(self.x), int(self.y),
                         self._anim_phase, st,
                         self.scale, self.facing)


# ---------------------------------------------------------------------------
# SoldierFormation
# ---------------------------------------------------------------------------

class SoldierFormation:
    """
    A 3×3 grid of SoldierUnit objects marching across the screen in lockstep.
    Wraps around when reaching screen edges.
    """

    MARCH_SPEED = 40.0       # pixels per second
    H_SPACING   = 38
    V_SPACING   = 52

    def __init__(self, start_x: float, start_y: float,
                 screen_width: int = 800, scale: float = 0.75,
                 facing: int = 1) -> None:
        self.screen_width = screen_width
        self.scale = scale
        self.facing = facing
        self._march_active = False
        self._wrap_margin = 120

        self.origin_x = float(start_x)
        self.origin_y = float(start_y)

        self.soldiers: List[SoldierUnit] = []
        for row in range(3):
            for col in range(3):
                ox = self.origin_x + col * self.H_SPACING * scale
                oy = self.origin_y + row * self.V_SPACING * scale
                unit = SoldierUnit(ox, oy, row, col, scale, facing)
                unit.set_state(IDLE)
                self.soldiers.append(unit)

    # ------------------------------------------------------------------
    def trigger_march(self) -> None:
        """Activate marching animation for all soldiers."""
        self._march_active = True
        for s in self.soldiers:
            s.set_state(MARCH)

    # ------------------------------------------------------------------
    def halt(self) -> None:
        self._march_active = False
        for s in self.soldiers:
            s.set_state(IDLE)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self._march_active:
            dx = self.MARCH_SPEED * self.facing * dt
            self.origin_x += dx
            # wrap around
            col_span = 2 * self.H_SPACING * self.scale
            if self.facing == 1 and self.origin_x > self.screen_width + self._wrap_margin:
                self.origin_x = -self._wrap_margin - col_span
            elif self.facing == -1 and self.origin_x < -self._wrap_margin - col_span:
                self.origin_x = self.screen_width + self._wrap_margin

        # sync soldier positions to origin
        for unit in self.soldiers:
            unit.x = self.origin_x + unit.col * self.H_SPACING * self.scale
            unit.y = self.origin_y + unit.row * self.V_SPACING * self.scale
            unit.update(dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        for unit in self.soldiers:
            unit.draw(surface)


# ---------------------------------------------------------------------------
# Clash Particle
# ---------------------------------------------------------------------------

class _ClashParticle:
    """A single spark or dust particle for battle clash effects."""

    def __init__(self, x: float, y: float, kind: str = "spark") -> None:
        self.x = x
        self.y = y
        self.kind = kind
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(30, 100)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(20, 60)
        self.life = random.uniform(0.3, 0.9)
        self.max_life = self.life
        self.size = random.uniform(2, 5) if kind == "spark" else random.uniform(5, 14)

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 120 * dt   # gravity
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = max(0, self.life / self.max_life)
        if self.kind == "spark":
            c = tuple(int(v * alpha) for v in SPARK)
            r = max(1, int(self.size * alpha))
            pygame.draw.circle(surface, c, (int(self.x), int(self.y)), r)
        else:  # dust
            c = (int(180 * alpha), int(165 * alpha), int(130 * alpha))
            r = max(1, int(self.size * alpha))
            pygame.draw.circle(surface, c, (int(self.x), int(self.y)), r)


# ---------------------------------------------------------------------------
# BattleScene
# ---------------------------------------------------------------------------

class BattleScene:
    """
    Animated battle sequence with two opposing sides of soldiers and clash FX.

    Usage
    -----
    scene = BattleScene(screen_w, screen_h)
    scene.start('victory')   # or 'retreat'

    In game loop:
        still_active = scene.update(dt)
        if still_active:
            scene.draw(surface)
    """

    DURATION       = 5.0   # seconds total
    CLASH_INTERVAL = 0.15  # seconds between particle bursts

    def __init__(self, screen_w: int, screen_h: int) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._active = False
        self._elapsed = 0.0
        self._outcome: str = "victory"
        self._particles: List[_ClashParticle] = []
        self._clash_timer = 0.0
        self._resolved = False

        mid_y = screen_h // 2 + 30
        # left side (facing right)
        self._left_units: List[SoldierUnit] = [
            SoldierUnit(screen_w // 2 - 80 - i * 38, mid_y, scale=0.9, facing=1)
            for i in range(4)
        ]
        # right side (facing left)
        self._right_units: List[SoldierUnit] = [
            SoldierUnit(screen_w // 2 + 80 + i * 38, mid_y, scale=0.9, facing=-1)
            for i in range(4)
        ]
        for u in self._left_units + self._right_units:
            u.set_state(IDLE)

    # ------------------------------------------------------------------
    def start(self, outcome: str = "victory") -> None:
        """Start the battle scene. outcome: 'victory' or 'retreat'."""
        self._active = True
        self._elapsed = 0.0
        self._outcome = outcome
        self._particles.clear()
        self._clash_timer = 0.0
        self._resolved = False
        for u in self._left_units + self._right_units:
            u.set_state(MARCH)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> bool:
        """Update scene. Returns True while active."""
        if not self._active:
            return False

        self._elapsed += dt

        # advance soldier animations
        for u in self._left_units:
            if not self._resolved:
                u.x = min(u.x + 25 * dt, self.screen_w // 2 - 35)
            u.update(dt)
        for u in self._right_units:
            if not self._resolved:
                u.x = max(u.x - 25 * dt, self.screen_w // 2 + 35)
            u.update(dt)

        # clash particles
        clash_x = self.screen_w // 2
        clash_y = self.screen_h // 2 + 10
        self._clash_timer -= dt
        if self._clash_timer <= 0 and not self._resolved:
            self._clash_timer = self.CLASH_INTERVAL
            for _ in range(random.randint(4, 9)):
                kind = random.choice(["spark", "spark", "dust"])
                self._particles.append(_ClashParticle(
                    clash_x + random.randint(-15, 15),
                    clash_y + random.randint(-15, 15),
                    kind
                ))

        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if p.alive]

        # resolution phase
        if self._elapsed >= self.DURATION * 0.6 and not self._resolved:
            self._resolved = True
            if self._outcome == "retreat":
                for u in self._left_units:
                    u.facing = -1
                    u.set_state(MARCH)
            else:
                for u in self._right_units:
                    u.facing = 1
                    u.set_state(MARCH)

        if self._elapsed >= self.DURATION:
            self._active = False
            return False

        return True

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        if not self._active:
            return

        # dim overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((8, 12, 25, 180))
        surface.blit(overlay, (0, 0))

        # banner
        font = FontManager.title(30)
        label = "⚔  BATTLE  ⚔" if not self._resolved else (
            "VICTORY!" if self._outcome == "victory" else "RETREAT!")
        color = GOLD if not self._resolved else (
            (80, 220, 80) if self._outcome == "victory" else CRIMSON_LIGHT)
        txt = font.render(label, True, color)
        surface.blit(txt, txt.get_rect(center=(self.screen_w // 2, 60)))

        # draw soldiers
        for u in self._left_units:
            u.draw(surface)
        for u in self._right_units:
            u.draw(surface)

        # draw particles
        for p in self._particles:
            p.draw(surface)


# ---------------------------------------------------------------------------
# PatrollingGuard
# ---------------------------------------------------------------------------

class PatrollingGuard:
    """
    A guard that walks back and forth along a horizontal segment of the city
    wall and periodically stops to 'look around'.
    """

    WALK_SPEED   = 30.0   # pixels/s
    STOP_CHANCE  = 0.008  # per-frame probability when moving

    def __init__(self, x_min: float, x_max: float, y: float,
                 scale: float = 0.85) -> None:
        self.x_min = float(x_min)
        self.x_max = float(x_max)
        self.y = float(y)
        self.scale = scale

        self.x = float(random.uniform(x_min, x_max))
        self.facing = random.choice([-1, 1])
        self._state = PATROL
        self._anim_phase: float = random.uniform(0, math.pi * 2)
        self._stop_timer: float = 0.0
        self._looking: bool = False

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self._looking:
            self._stop_timer -= dt
            if self._stop_timer <= 0:
                self._looking = False
                self._state = PATROL
            return

        # walk
        self.x += self.facing * self.WALK_SPEED * dt
        self._anim_phase += 4.0 * dt

        # bounce at walls
        if self.x >= self.x_max:
            self.x = self.x_max
            self.facing = -1
        elif self.x <= self.x_min:
            self.x = self.x_min
            self.facing = 1

        # random stop to look around
        if random.random() < self.STOP_CHANCE:
            self._looking = True
            self._stop_timer = random.uniform(0.8, 2.2)
            self._state = GUARD

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        st = GUARD if self._looking else PATROL
        _draw_soldier_at(surface, int(self.x), int(self.y),
                         self._anim_phase, st, self.scale, self.facing)


# ---------------------------------------------------------------------------
# MilitaryDashboard
# ---------------------------------------------------------------------------

class MilitaryDashboard:
    """
    Full-screen military management panel for the Babylonian kingdom.

    Displays animated soldier formations, statistics drawn from GameState,
    and a RETURN button.

    Parameters
    ----------
    screen_w, screen_h  – display resolution
    on_return           – callback fired when the RETURN button is clicked
    """

    def __init__(self, screen_w: int = 800, screen_h: int = 600,
                 on_return: Optional[callable] = None) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._on_return = on_return

        # Background formations (decorative)
        self._formations: List[SoldierFormation] = [
            SoldierFormation(30,  screen_h - 230, screen_w, scale=0.6, facing=1),
            SoldierFormation(screen_w - 160, screen_h - 180, screen_w, scale=0.55, facing=-1),
        ]
        for f in self._formations:
            f.trigger_march()

        # Patrolling guards along the top "wall"
        self._guards: List[PatrollingGuard] = [
            PatrollingGuard(60, screen_w // 2 - 40, 105, scale=0.7),
            PatrollingGuard(screen_w // 2 + 40, screen_w - 60, 105, scale=0.7),
        ]

        # Return button
        btn_w, btn_h = 160, 42
        self._return_btn = UIButton(
            rect=(screen_w // 2 - btn_w // 2, screen_h - 62, btn_w, btn_h),
            text="RETURN",
            callback=self._handle_return,
            font_size=17,
            primary=False,
            color_scheme="gold",
        )

        # Internal state for pulsing gold border
        self._pulse = 0.0

        # Optional live battle scene
        self._battle: Optional[BattleScene] = None

    # ------------------------------------------------------------------
    def _handle_return(self) -> None:
        if self._on_return:
            self._on_return()

    # ------------------------------------------------------------------
    def trigger_battle(self, outcome: str = "victory") -> None:
        """Spawn an overlay battle scene."""
        if self._battle is None:
            self._battle = BattleScene(self.screen_w, self.screen_h)
        self._battle.start(outcome)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Advance all animations."""
        self._pulse += dt * 2.0

        for f in self._formations:
            f.update(dt)

        for g in self._guards:
            g.update(dt)

        if self._battle is not None:
            still_active = self._battle.update(dt)
            if not still_active:
                self._battle = None

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process pygame event. Returns True if consumed."""
        mouse_pos = pygame.mouse.get_pos()
        consumed = self._return_btn.handle_event(event, mouse_pos)
        return consumed

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface,
             state: Optional[GameState] = None,
             time_elapsed: float = 0.0) -> None:
        """
        Render the complete military dashboard.

        Parameters
        ----------
        surface      – pygame display surface
        state        – current GameState (may be None)
        time_elapsed – seconds since screen was opened (for animations)
        """
        # ---- background ----
        surface.fill(NAVY)
        self._draw_background_pattern(surface)

        # ---- city wall strip ----
        wall_color = (55, 45, 30)
        pygame.draw.rect(surface, wall_color,
                         (0, 88, self.screen_w, 30))
        pygame.draw.rect(surface, (80, 65, 45),
                         (0, 88, self.screen_w, 4))
        # battlements
        for mx in range(0, self.screen_w, 28):
            pygame.draw.rect(surface, wall_color, (mx, 72, 16, 18))
            pygame.draw.rect(surface, (80, 65, 45), (mx, 72, 16, 2))

        # ---- patrolling guards ----
        for g in self._guards:
            g.draw(surface)

        # ---- background formations ----
        for f in self._formations:
            f.draw(surface)

        # ---- gold border (pulsing) ----
        pulse_alpha = int(180 + 75 * math.sin(self._pulse))
        border_col = (
            min(255, GOLD[0] + 20),
            min(255, int(GOLD[1] * (0.85 + 0.15 * math.sin(self._pulse)))),
            min(255, GOLD[2])
        )
        pygame.draw.rect(surface, border_col,
                         (8, 8, self.screen_w - 16, self.screen_h - 16), 3, border_radius=6)

        # ---- header panel ----
        self._draw_header(surface)

        # ---- stats panel ----
        self._draw_stats_panel(surface, state)

        # ---- 3×3 soldier showcase ----
        self._draw_soldier_showcase(surface, time_elapsed)

        # ---- return button ----
        self._return_btn.draw(surface)

        # ---- battle scene overlay (if active) ----
        if self._battle is not None:
            self._battle.draw(surface)

    # ------------------------------------------------------------------
    def _draw_background_pattern(self, surface: pygame.Surface) -> None:
        """Subtle geometric tile pattern on the background."""
        tile = 40
        pat_color = (20, 28, 52)
        for gy in range(0, self.screen_h, tile):
            for gx in range(0, self.screen_w, tile):
                if (gx // tile + gy // tile) % 2 == 0:
                    pygame.draw.rect(surface, pat_color, (gx, gy, tile, tile))
        # horizontal dividers
        for ly in [120, self.screen_h - 80]:
            pygame.draw.line(surface, GOLD_DARK, (16, ly), (self.screen_w - 16, ly), 1)

    # ------------------------------------------------------------------
    def _draw_header(self, surface: pygame.Surface) -> None:
        """Render the MILITARY COMMAND header bar."""
        hdr_rect = pygame.Rect(16, 16, self.screen_w - 32, 52)
        pygame.draw.rect(surface, (18, 28, 58), hdr_rect, border_radius=4)
        pygame.draw.rect(surface, GOLD, hdr_rect, 2, border_radius=4)

        font = FontManager.title(30)
        txt = font.render("MILITARY COMMAND", True, GOLD)
        surface.blit(txt, txt.get_rect(center=hdr_rect.center))

        # decorative sword symbols
        for sx in [hdr_rect.left + 20, hdr_rect.right - 20]:
            pygame.draw.line(surface, GOLD, (sx, hdr_rect.top + 10), (sx, hdr_rect.bottom - 10), 2)
            pygame.draw.line(surface, GOLD, (sx - 6, hdr_rect.centery), (sx + 6, hdr_rect.centery), 2)

    # ------------------------------------------------------------------
    def _draw_stats_panel(self, surface: pygame.Surface,
                          state: Optional[GameState]) -> None:
        """Render the stats panel on the right side."""
        panel_x = self.screen_w - 210
        panel_y = 130
        panel_w = 195
        panel_h = 290

        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(surface, (14, 22, 44), panel_rect, border_radius=5)
        pygame.draw.rect(surface, GOLD_DARK, panel_rect, 2, border_radius=5)

        # panel title
        font_hdr = FontManager.header(15)
        title_surf = font_hdr.render("COMMAND REPORT", True, GOLD)
        surface.blit(title_surf, title_surf.get_rect(
            centerx=panel_rect.centerx, top=panel_rect.top + 10))

        pygame.draw.line(surface, GOLD_DARK,
                         (panel_x + 10, panel_y + 32),
                         (panel_x + panel_w - 10, panel_y + 32), 1)

        if state is not None:
            army_size     = max(0, state.population // 10)
            defense_rating = min(100, army_size * 2 + state.acres // 50)
            patrol_routes = min(8, army_size // 5 + 1)
            threat_level  = max(0, 50 - defense_rating // 2 + state.starved_this_year)
        else:
            army_size = defense_rating = patrol_routes = threat_level = 0

        stats = [
            ("Army Size",      f"{army_size} soldiers",    GOLD),
            ("Defense Rating", f"{defense_rating}/100",    (80, 210, 80) if defense_rating >= 50 else CRIMSON_LIGHT),
            ("Patrol Routes",  f"{patrol_routes} active",  Palette.TURQUOISE_ACCENT),
            ("Threat Level",   f"{threat_level}%",         CRIMSON_LIGHT if threat_level > 40 else (80, 200, 100)),
            ("Year",           f"{state.year if state else '-'}",  Palette.TEXT_MUTED),
            ("Population",     f"{state.population if state else '-'}",  Palette.TEXT_MUTED),
        ]

        font_lbl = FontManager.small(13)
        font_val = FontManager.header(14)
        row_y = panel_y + 44
        for label, value, val_color in stats:
            lbl_surf = font_lbl.render(label, True, Palette.TEXT_MUTED)
            surface.blit(lbl_surf, (panel_x + 12, row_y))
            val_surf = font_val.render(value, True, val_color)
            surface.blit(val_surf, (panel_x + 12, row_y + 14))
            row_y += 40
            if row_y > panel_y + panel_h - 20:
                break

    # ------------------------------------------------------------------
    def _draw_soldier_showcase(self, surface: pygame.Surface,
                               time_elapsed: float) -> None:
        """Render a 3×3 grid of animated individual soldiers as a showcase."""
        showcase_x = 30
        showcase_y = 135
        cell_w = 72
        cell_h = 78

        # panel background
        bg_rect = pygame.Rect(showcase_x - 10, showcase_y - 10,
                              cell_w * 3 + 20, cell_h * 3 + 30)
        pygame.draw.rect(surface, (12, 18, 40), bg_rect, border_radius=5)
        pygame.draw.rect(surface, GOLD_DARK, bg_rect, 1, border_radius=5)

        # label
        font_lbl = FontManager.header(13)
        lbl = font_lbl.render("GARRISON", True, GOLD)
        surface.blit(lbl, lbl.get_rect(
            centerx=bg_rect.centerx, top=bg_rect.bottom + 4))

        for row in range(3):
            for col in range(3):
                cx = showcase_x + col * cell_w + cell_w // 2
                cy = showcase_y + row * cell_h + cell_h // 2 + 12
                # stagger phase per unit
                phase = time_elapsed * 4.0 + (row * 3 + col) * 0.7
                _draw_soldier_at(surface, cx, cy, phase, MARCH, scale=0.72, facing=1)

        # threat bar below showcase
        self._draw_threat_bar(surface, showcase_x - 10, bg_rect.bottom + 24,
                              bg_rect.width)

    # ------------------------------------------------------------------
    def _draw_threat_bar(self, surface: pygame.Surface,
                         x: int, y: int, width: int) -> None:
        """A decorative status bar showing patrol status."""
        bar_rect = pygame.Rect(x, y, width, 22)
        pygame.draw.rect(surface, (18, 24, 50), bar_rect, border_radius=3)
        pygame.draw.rect(surface, GOLD_DARK, bar_rect, 1, border_radius=3)

        fill_frac = 0.5 + 0.25 * math.sin(self._pulse * 0.5)
        fill_w = int((width - 4) * fill_frac)
        fill_col = (int(80 + 80 * fill_frac), int(200 - 100 * fill_frac), 60)
        if fill_w > 0:
            pygame.draw.rect(surface, fill_col,
                             (x + 2, y + 3, fill_w, 16), border_radius=2)

        font = FontManager.small(12)
        txt = font.render("PATROL STATUS", True, Palette.TEXT_MUTED)
        surface.blit(txt, txt.get_rect(center=bar_rect.center))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "SoldierUnit",
    "SoldierFormation",
    "BattleScene",
    "MilitaryDashboard",
    "PatrollingGuard",
    "IDLE", "MARCH", "PATROL", "GUARD",
]
