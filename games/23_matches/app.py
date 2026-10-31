"""
games/23_matches/app.py - Graphical Pygame interface for 23 Matches (1978 Edition).

Features an interactive matchstick board, animated burns and selection,
dynamic AI response timing, historical instructions, and library integration.
"""

import math
import random
import sys
import time
from typing import Callable, List, Optional, Tuple

import pygame

from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton, UIModal
from .engine import (
    MatchesGameState,
    get_computer_move,
    init_game,
    make_move,
    validate_move,
)

BASE_WIDTH = 1280
BASE_HEIGHT = 720


class VisualMatch:
    """Represents a single matchstick on the wooden board."""

    def __init__(self, index: int, x: int, y: int, width: int = 14, height: int = 150) -> None:
        self.index = index
        self.base_x = x
        self.base_y = y
        self.width = width
        self.height = height
        self.is_taken = False
        self.is_hovered = False
        self.is_selected = False
        self.burn_progress = 0.0  # 0.0 (fresh) to 1.0 (burned away)
        self.tilt = (random.random() - 0.5) * 4  # subtle natural wood tilt

    @property
    def rect(self) -> pygame.Rect:
        # If hovered or selected, match lifts up by 16px
        lift = 16 if (self.is_hovered or self.is_selected) and not self.is_taken else 0
        return pygame.Rect(self.base_x, self.base_y - lift, self.width, self.height)

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect

        if self.is_taken:
            # Ghost outline of taken match
            pygame.draw.rect(surface, (45, 38, 30), r, border_radius=3)
            return

        # Wooden stick body (gradient light birch to darker wood)
        wood_color = Palette.GOLD_PALE if (self.is_hovered or self.is_selected) else (210, 180, 140)
        shadow_rect = pygame.Rect(r.x + 3, r.y + 3, r.width, r.height)
        pygame.draw.rect(surface, (15, 12, 10, 120), shadow_rect, border_radius=3)
        pygame.draw.rect(surface, wood_color, r, border_radius=3)

        # Matchstick sulfur head (red / sulfur amber)
        head_h = 24
        head_rect = pygame.Rect(r.x - 2, r.y - 4, r.width + 4, head_h)
        head_color = Palette.CRIMSON_LIGHT if self.is_hovered else Palette.CRIMSON
        pygame.draw.ellipse(surface, head_color, head_rect)

        # Sulfur tip highlight
        tip_rect = pygame.Rect(r.x + 1, r.y - 3, r.width - 2, 8)
        pygame.draw.ellipse(surface, Palette.GOLD_LIGHT, tip_rect)

        # Hover spark particle
        if self.is_hovered or self.is_selected:
            glow_surf = pygame.Surface((r.width + 24, head_h + 24), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 200, 50, 60), (glow_surf.get_width() // 2, glow_surf.get_height() // 2), 16)
            surface.blit(glow_surf, (r.centerx - glow_surf.get_width() // 2, r.y - 12))


class MatchesApp:
    """Pygame application for 23 Matches."""

    def __init__(
        self,
        start_fullscreen: bool = False,
        on_exit_to_library: Optional[Callable[[], None]] = None,
        shared_window: Optional[pygame.Surface] = None,
        ai_mode: str = "CLASSIC_1978",
    ) -> None:
        pygame.init()
        SoundSynthesizer.init()

        self.on_exit_to_library = on_exit_to_library
        self.screen_width = BASE_WIDTH
        self.screen_height = BASE_HEIGHT

        if shared_window is not None:
            self.window = shared_window
        else:
            flags = pygame.RESIZABLE
            if start_fullscreen:
                flags |= pygame.FULLSCREEN
            self.window = pygame.display.set_mode((self.screen_width, self.screen_height), flags)

        pygame.display.set_caption("RetroRevive: 23 Matches (1978)")
        self.canvas = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True

        # State
        self.ai_mode = ai_mode
        self.state: MatchesGameState = init_game(initial_matches=23, first_player="HUMAN", ai_mode=self.ai_mode)
        self.status_message = "Your turn! Choose 1, 2, or 3 matches to remove."
        self.ai_timer: float = 0.0  # timer for computer move pause
        self.ai_pending: bool = False
        self.toast_message: Optional[str] = None
        self.toast_timer: float = 0.0

        # Matchstick objects
        self.matches: List[VisualMatch] = []
        self._init_matches()

        # UI Buttons
        self._init_buttons()

        # Rules Modal
        self.show_rules_modal = False

    def _init_matches(self) -> None:
        """Arranges 23 visual matchsticks centered across the board."""
        self.matches.clear()
        total = self.state.matches_remaining
        spacing = 44
        total_width = total * spacing
        start_x = (BASE_WIDTH - total_width) // 2
        y = 260

        for i in range(total):
            x = start_x + i * spacing
            self.matches.append(VisualMatch(index=i, x=x, y=y))

    def _init_buttons(self) -> None:
        """Initializes action and navigation buttons."""
        # Top Header Bar Buttons
        self.btn_back = UIButton((30, 20, 160, 40), "← LIBRARY", self._on_back_clicked, color_scheme="sand", font_size=15)
        self.btn_rules = UIButton((205, 20, 140, 40), "HOW TO PLAY", self._toggle_rules, color_scheme="lapis", font_size=15)
        self.btn_mode = UIButton(
            (BASE_WIDTH - 280, 20, 250, 40),
            f"AI: {self._mode_label()}",
            self._toggle_ai_mode,
            color_scheme="gold",
            font_size=15,
        )

        # Move Selection Action Buttons
        btn_y = 520
        bw = 200
        gap = 30
        total_bw = 3 * bw + 2 * gap
        bx = (BASE_WIDTH - total_bw) // 2

        self.btn_take_1 = UIButton((bx, btn_y, bw, 52), "TAKE 1 MATCH [1]", lambda: self._on_human_move(1), primary=True)
        self.btn_take_2 = UIButton((bx + bw + gap, btn_y, bw, 52), "TAKE 2 MATCHES [2]", lambda: self._on_human_move(2), primary=True)
        self.btn_take_3 = UIButton((bx + (bw + gap) * 2, btn_y, bw, 52), "TAKE 3 MATCHES [3]", lambda: self._on_human_move(3), primary=True)

        # Game Over Buttons
        self.btn_play_again = UIButton((BASE_WIDTH // 2 - 210, 490, 200, 50), "PLAY AGAIN", self._restart_game, primary=True)
        self.btn_over_library = UIButton((BASE_WIDTH // 2 + 10, 490, 200, 50), "BACK TO LIBRARY", self._on_back_clicked, color_scheme="sand")

        # Modal close
        self.btn_modal_close = UIButton((BASE_WIDTH // 2 - 80, 560, 160, 42), "CLOSE", self._toggle_rules, color_scheme="gold")

    def _mode_label(self) -> str:
        return "1978 ALBRECHT" if self.ai_mode == "CLASSIC_1978" else "MASTER MIND"

    def _toggle_ai_mode(self) -> None:
        self.ai_mode = "OPTIMAL" if self.ai_mode == "CLASSIC_1978" else "CLASSIC_1978"
        self.btn_mode.text = f"AI: {self._mode_label()}"
        self._restart_game()
        self.show_toast(f"AI switched to {self._mode_label()}")

    def _toggle_rules(self) -> None:
        self.show_rules_modal = not self.show_rules_modal

    def _restart_game(self) -> None:
        self.state = init_game(initial_matches=23, first_player="HUMAN", ai_mode=self.ai_mode)
        self._init_matches()
        self.status_message = "New game! Your turn: choose 1, 2, or 3 matches."
        self.ai_pending = False
        self.ai_timer = 0.0

    def _on_back_clicked(self) -> None:
        if self.on_exit_to_library:
            self.on_exit_to_library()
        else:
            self.is_running = False

    def show_toast(self, msg: str) -> None:
        self.toast_message = msg
        self.toast_timer = 2.5

    def _on_human_move(self, take: int) -> None:
        if self.state.game_over or self.state.current_player != "HUMAN" or self.ai_pending:
            return

        ok, err = validate_move(self.state, take)
        if not ok:
            SoundSynthesizer.play("warning")
            self.show_toast(err or "Invalid move")
            return

        SoundSynthesizer.play("click")
        self.state = make_move(self.state, take)
        self._sync_visual_matches()

        if self.state.game_over:
            SoundSynthesizer.play("fanfare" if self.state.winner == "HUMAN" else "warning")
            return

        # Prepare computer turn with a natural visual thinking pause
        self.status_message = f"You took {take} match{'es' if take > 1 else ''}. Computer is thinking..."
        self.ai_pending = True
        self.ai_timer = 0.65

    def _execute_computer_turn(self) -> None:
        if self.state.game_over or self.state.current_player != "COMPUTER":
            return

        comp_take = get_computer_move(self.state)
        self.state = make_move(self.state, comp_take)
        self._sync_visual_matches()
        SoundSynthesizer.play("harvest")

        if self.state.game_over:
            SoundSynthesizer.play("fanfare" if self.state.winner == "HUMAN" else "warning")
        else:
            self.status_message = f"Computer removed {comp_take} match{'es' if comp_take > 1 else ''}. Your turn!"

        self.ai_pending = False

    def _sync_visual_matches(self) -> None:
        rem = self.state.matches_remaining
        for i, m in enumerate(self.matches):
            m.is_taken = (i >= rem)

    def handle_event(self, event: pygame.event.Event) -> None:
        canvas_mouse = self._screen_to_canvas(pygame.mouse.get_pos())

        if event.type == pygame.QUIT:
            self.is_running = False
            return

        if event.type == pygame.VIDEORESIZE:
            self.screen_width = event.w
            self.screen_height = event.h
            self.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            return

        # Modal dismissal
        if self.show_rules_modal:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.show_rules_modal = False
                return
            self.btn_modal_close.handle_event(event, canvas_mouse)
            return

        # Header buttons
        if self.btn_back.handle_event(event, canvas_mouse):
            return
        if self.btn_rules.handle_event(event, canvas_mouse):
            return
        if self.btn_mode.handle_event(event, canvas_mouse):
            return

        # Game over screen buttons
        if self.state.game_over:
            if self.btn_play_again.handle_event(event, canvas_mouse):
                return
            if self.btn_over_library.handle_event(event, canvas_mouse):
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                    self._restart_game()
                elif event.key == pygame.K_ESCAPE:
                    self._on_back_clicked()
            return

        # Move buttons
        rem = self.state.matches_remaining
        if rem >= 1 and self.btn_take_1.handle_event(event, canvas_mouse):
            return
        if rem >= 2 and self.btn_take_2.handle_event(event, canvas_mouse):
            return
        if rem >= 3 and self.btn_take_3.handle_event(event, canvas_mouse):
            return

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self._on_human_move(1)
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self._on_human_move(2)
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self._on_human_move(3)
            elif event.key == pygame.K_ESCAPE:
                self._on_back_clicked()

        # Mouse hover on matches
        for m in self.matches:
            if not m.is_taken:
                m.is_hovered = m.rect.collidepoint(canvas_mouse)

    def update(self, dt: float) -> None:
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast_message = None

        if self.ai_pending:
            self.ai_timer -= dt
            if self.ai_timer <= 0:
                self._execute_computer_turn()

    def draw(self) -> None:
        # 1. Warm tavern table background (rich wood grain & brass border)
        self.canvas.fill((28, 22, 18))

        # Wooden table felt / inset panel
        inset_rect = pygame.Rect(30, 80, BASE_WIDTH - 60, BASE_HEIGHT - 110)
        pygame.draw.rect(self.canvas, (40, 32, 26), inset_rect, border_radius=16)
        pygame.draw.rect(self.canvas, Palette.GOLD_BASE, inset_rect, width=2, border_radius=16)

        # 2. Header Bar
        header_rect = pygame.Rect(0, 0, BASE_WIDTH, 75)
        pygame.draw.rect(self.canvas, Palette.PANEL_BG, header_rect)
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (0, 75), (BASE_WIDTH, 75), 2)

        # Header Title
        title_surf = FontManager.header(24).render("23 MATCHES", True, Palette.GOLD_PALE)
        sub_surf = FontManager.small(12).render("1978 Bob Albrecht / David H. Ahl — Nim Subtraction Strategy", True, Palette.TEXT_MUTED)
        self.canvas.blit(title_surf, (BASE_WIDTH // 2 - title_surf.get_width() // 2, 14))
        self.canvas.blit(sub_surf, (BASE_WIDTH // 2 - sub_surf.get_width() // 2, 44))

        self.btn_back.draw(self.canvas)
        self.btn_rules.draw(self.canvas)
        self.btn_mode.draw(self.canvas)

        # 3. Matches Counter & Status Banner
        rem = self.state.matches_remaining
        count_str = f"{rem} MATCH{'ES' if rem != 1 else ''} REMAINING"
        count_color = Palette.GOLD_PALE if rem > 5 else (Palette.AMBER_WARN if rem > 1 else Palette.CRIMSON_LIGHT)
        count_surf = FontManager.title(36).render(count_str, True, count_color)
        self.canvas.blit(count_surf, count_surf.get_rect(center=(BASE_WIDTH // 2, 130)))

        # Status / Turn Announcement
        status_color = Palette.SUCCESS_GREEN if self.state.current_player == "HUMAN" else Palette.LAPIS_LIGHT
        status_surf = FontManager.body(18).render(self.status_message, True, status_color)
        self.canvas.blit(status_surf, status_surf.get_rect(center=(BASE_WIDTH // 2, 180)))

        # 4. Render Matchsticks
        for m in self.matches:
            m.draw(self.canvas)

        # Table Divider line
        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (60, 480), (BASE_WIDTH - 60, 480), 1)

        # 5. Move Action Buttons (Enabled dynamically based on remaining matches)
        if not self.state.game_over:
            self.btn_take_1.is_enabled = (rem >= 1 and not self.ai_pending)
            self.btn_take_2.is_enabled = (rem >= 2 and not self.ai_pending)
            self.btn_take_3.is_enabled = (rem >= 3 and not self.ai_pending)

            self.btn_take_1.draw(self.canvas)
            self.btn_take_2.draw(self.canvas)
            self.btn_take_3.draw(self.canvas)

            # Shortcut hints
            hint = FontManager.small(13).render(
                "Press [1], [2], or [3] on keyboard  |  [Esc] Back to Library", True, Palette.TEXT_MUTED
            )
            self.canvas.blit(hint, hint.get_rect(center=(BASE_WIDTH // 2, 620)))

        # 6. Game Over Modal Overlay
        if self.state.game_over:
            self._draw_game_over()

        # 7. Rules Modal
        if self.show_rules_modal:
            self._draw_rules_modal()

        # 8. Toast Alert
        if self.toast_message:
            self._draw_toast()

        # 9. Canvas blit to window
        self._present()

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 6, 210))
        self.canvas.blit(overlay, (0, 0))

        pw, ph = 640, 360
        px = (BASE_WIDTH - pw) // 2
        py = (BASE_HEIGHT - ph) // 2
        p_rect = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(self.canvas, Palette.PANEL_BG, p_rect, border_radius=12)
        border_col = Palette.GOLD_LIGHT if self.state.winner == "HUMAN" else Palette.CRIMSON
        pygame.draw.rect(self.canvas, border_col, p_rect, width=2, border_radius=12)

        # Banner Title
        if self.state.winner == "HUMAN":
            h_text = "VICTORY!"
            h_color = Palette.GOLD_PALE
            sub_text = "The computer was forced to take the final match!"
            detail = "You have mastered the ancient mathematics of Nim."
        else:
            h_text = "DEFEAT!"
            h_color = Palette.CRIMSON_LIGHT
            sub_text = "You were forced to take the very last match!"
            detail = "Remember: try to always leave your opponent with a multiple of 4 plus 1!"

        h_surf = FontManager.title(40).render(h_text, True, h_color)
        sub_surf = FontManager.body(18).render(sub_text, True, Palette.SAND_LIGHT)
        det_surf = FontManager.small(14).render(detail, True, Palette.TEXT_MUTED)

        self.canvas.blit(h_surf, h_surf.get_rect(center=(BASE_WIDTH // 2, py + 60)))
        self.canvas.blit(sub_surf, sub_surf.get_rect(center=(BASE_WIDTH // 2, py + 120)))
        self.canvas.blit(det_surf, det_surf.get_rect(center=(BASE_WIDTH // 2, py + 160)))

        self.btn_play_again.draw(self.canvas)
        self.btn_over_library.draw(self.canvas)

    def _draw_rules_modal(self) -> None:
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 6, 225))
        self.canvas.blit(overlay, (0, 0))

        pw, ph = 760, 520
        px = (BASE_WIDTH - pw) // 2
        py = (BASE_HEIGHT - ph) // 2
        p_rect = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(self.canvas, Palette.PANEL_BG, p_rect, border_radius=12)
        pygame.draw.rect(self.canvas, Palette.GOLD_LIGHT, p_rect, width=2, border_radius=12)

        title = FontManager.header(24).render("HOW TO PLAY: 23 MATCHES (1978)", True, Palette.GOLD_PALE)
        self.canvas.blit(title, title.get_rect(center=(BASE_WIDTH // 2, py + 40)))

        lines = [
            ("THE OBJECTIVE:", Palette.GOLD_BASE, True),
            ("Avoid being forced to pick up the very last matchstick on the table.", Palette.SAND_LIGHT, False),
            ("", Palette.TEXT_MUTED, False),
            ("THE RULES:", Palette.GOLD_BASE, True),
            ("• The game starts with exactly 23 matches on the table.", Palette.SAND_LIGHT, False),
            ("• You and the computer take turns alternating moves.", Palette.SAND_LIGHT, False),
            ("• On each turn, you may take 1, 2, or 3 matches.", Palette.SAND_LIGHT, False),
            ("• You cannot take more matches than remain on the table.", Palette.SAND_LIGHT, False),
            ("• Whichever player takes the final match loses the game!", Palette.CRIMSON_LIGHT, False),
            ("", Palette.TEXT_MUTED, False),
            ("THE SECRET MATHEMATICAL STRATEGY:", Palette.GOLD_BASE, True),
            ("Aim to leave your opponent with 21, 17, 13, 9, 5, or 1 match (a multiple of 4 plus 1).", Palette.SUCCESS_GREEN, False),
            ("Bob Albrecht's 1978 AI plays '4 - your move' — see if you can outsmart it!", Palette.TEXT_MUTED, False),
        ]

        curr_y = py + 85
        for text, col, is_bold in lines:
            if text:
                font = FontManager.body(16) if not is_bold else FontManager.header(17)
                s = font.render(text, True, col)
                self.canvas.blit(s, (px + 40, curr_y))
            curr_y += 24

        self.btn_modal_close.draw(self.canvas)

    def _draw_toast(self) -> None:
        if not self.toast_message:
            return
        surf = FontManager.body(16).render(self.toast_message, True, Palette.TEXT_TITLE)
        tw = surf.get_width() + 40
        th = 44
        tx = (BASE_WIDTH - tw) // 2
        ty = BASE_HEIGHT - 70
        pygame.draw.rect(self.canvas, (40, 20, 20), (tx, ty, tw, th), border_radius=8)
        pygame.draw.rect(self.canvas, Palette.CRIMSON_LIGHT, (tx, ty, tw, th), width=2, border_radius=8)
        self.canvas.blit(surf, (tx + 20, ty + 12))

    def _screen_to_canvas(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        win_w, win_h = self.screen_width, self.screen_height
        scale = min(win_w / BASE_WIDTH, win_h / BASE_HEIGHT)
        scaled_w = int(BASE_WIDTH * scale)
        scaled_h = int(BASE_HEIGHT * scale)
        offset_x = (win_w - scaled_w) // 2
        offset_y = (win_h - scaled_h) // 2

        cx = int((pos[0] - offset_x) / scale)
        cy = int((pos[1] - offset_y) / scale)
        return max(0, min(BASE_WIDTH, cx)), max(0, min(BASE_HEIGHT, cy))

    def _present(self) -> None:
        win_w, win_h = self.screen_width, self.screen_height
        scale = min(win_w / BASE_WIDTH, win_h / BASE_HEIGHT)
        scaled_w = int(BASE_WIDTH * scale)
        scaled_h = int(BASE_HEIGHT * scale)
        offset_x = (win_w - scaled_w) // 2
        offset_y = (win_h - scaled_h) // 2

        scaled_canvas = pygame.transform.smoothscale(self.canvas, (scaled_w, scaled_h))
        self.window.fill((0, 0, 0))
        self.window.blit(scaled_canvas, (offset_x, offset_y))
        pygame.display.flip()

    def run(self) -> None:
        while self.is_running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


def main() -> None:
    start_fullscreen = "--fullscreen" in sys.argv
    app = MatchesApp(start_fullscreen=start_fullscreen)
    app.run()
    pygame.quit()


if __name__ == "__main__":
    main()
