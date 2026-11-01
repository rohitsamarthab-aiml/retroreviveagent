"""
retrorevive.py - Graphical Game Library and Hub for RetroRevive.

The central entry point for discovering and playing classic computer games.
Provides game catalog cards, category filters, real-time search, detail modals,
and seamless launch / return routing for Hammurabi and 23 Matches.
"""

import sys
from typing import Callable, List, Optional, Tuple

import pygame

from auth_manager import AuthManager
from game_registry import CATALOG, GameCategory, GameMetadata, GameRegistry, GameStatus
from games import matches_app
from ui_auth import AuthModal
from ui_pygame import BASE_HEIGHT, BASE_WIDTH, GameApp
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton


class LibraryCard:
    """Interactive visual card for a retro game in the library."""

    def __init__(self, rect: Tuple[int, int, int, int], metadata: GameMetadata, on_play: Callable[[], None], on_details: Callable[[], None]) -> None:
        self.rect = pygame.Rect(rect)
        self.meta = metadata
        self.on_play = on_play
        self.on_details = on_details
        self.is_hovered = False
        self.is_selected = False

        # Action buttons
        btn_w = (self.rect.width - 36) // 2
        btn_y = self.rect.bottom - 54

        if self.meta.is_playable:
            self.btn_play = UIButton((self.rect.x + 14, btn_y, btn_w, 38), "PLAY NOW", self.on_play, primary=True, font_size=14)
        else:
            self.btn_play = UIButton((self.rect.x + 14, btn_y, btn_w, 38), "SOON", None, font_size=14, color_scheme="sand")
            self.btn_play.is_enabled = False

        self.btn_details = UIButton((self.rect.x + 22 + btn_w, btn_y, btn_w, 38), "DETAILS", self.on_details, font_size=14, color_scheme="lapis")

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        if self.btn_play.handle_event(event, mouse_pos):
            return True
        if self.btn_details.handle_event(event, mouse_pos):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            self.on_details()
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        # Card Background
        bg_col = (48, 38, 30) if (self.is_hovered or self.is_selected) else Palette.PANEL_BG
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=12)

        # Border
        border_col = Palette.GOLD_LIGHT if self.is_selected else (Palette.GOLD_BASE if self.is_hovered else Palette.PANEL_BORDER)
        width = 3 if (self.is_selected or self.is_hovered) else 1
        pygame.draw.rect(surface, border_col, self.rect, width=width, border_radius=12)

        # Status Badge Pill
        badge_x = self.rect.x + 16
        badge_y = self.rect.y + 14
        if self.meta.is_playable:
            pill_rect = pygame.Rect(badge_x, badge_y, 115, 24)
            pygame.draw.rect(surface, (25, 75, 40), pill_rect, border_radius=12)
            pygame.draw.rect(surface, Palette.SUCCESS_GREEN, pill_rect, width=1, border_radius=12)
            badge_txt = FontManager.small(11).render("● PLAYABLE", True, Palette.SUCCESS_GREEN)
            surface.blit(badge_txt, (badge_x + 14, badge_y + 5))
        else:
            pill_rect = pygame.Rect(badge_x, badge_y, 125, 24)
            pygame.draw.rect(surface, (60, 45, 30), pill_rect, border_radius=12)
            pygame.draw.rect(surface, Palette.SAND_DARK, pill_rect, width=1, border_radius=12)
            badge_txt = FontManager.small(11).render("○ COMING SOON", True, Palette.SAND_LIGHT)
            surface.blit(badge_txt, (badge_x + 10, badge_y + 5))

        # Year and Category tag
        tag_str = f"{self.meta.year} • {self.meta.category_display}"
        tag_surf = FontManager.small(12).render(tag_str, True, Palette.TEXT_MUTED)
        surface.blit(tag_surf, (self.rect.right - tag_surf.get_width() - 16, badge_y + 5))

        # Game Title
        title_surf = FontManager.header(20).render(self.meta.title, True, Palette.GOLD_PALE)
        surface.blit(title_surf, (self.rect.x + 16, self.rect.y + 48))

        # Subtitle
        sub_surf = FontManager.small(12).render(self.meta.subtitle, True, Palette.SAND_LIGHT)
        surface.blit(sub_surf, (self.rect.x + 16, self.rect.y + 74))

        # Divider
        pygame.draw.line(surface, Palette.PANEL_BORDER, (self.rect.x + 16, self.rect.y + 96), (self.rect.right - 16, self.rect.y + 96), 1)

        # Description text (wrapped up to 4 lines)
        desc_words = self.meta.description.split()
        lines: List[str] = []
        curr_line = ""
        font = FontManager.small(12)
        for w in desc_words:
            test = curr_line + (" " if curr_line else "") + w
            if font.size(test)[0] < self.rect.width - 32:
                curr_line = test
            else:
                lines.append(curr_line)
                curr_line = w
                if len(lines) >= 4:
                    break
        if curr_line and len(lines) < 4:
            lines.append(curr_line)

        dy = self.rect.y + 106
        for line in lines:
            txt_surf = font.render(line, True, Palette.TEXT_BODY)
            surface.blit(txt_surf, (self.rect.x + 16, dy))
            dy += 18

        # Buttons
        self.btn_play.draw(surface)
        self.btn_details.draw(surface)


class RetroReviveHub:
    """Main graphical platform application controller."""

    def __init__(
        self,
        start_fullscreen: bool = False,
        auth: Optional[AuthManager] = None,
        show_auth_modal: bool = False,
    ) -> None:
        pygame.init()
        SoundSynthesizer.init()

        self.auth = auth or AuthManager()
        self.auth_modal: Optional[AuthModal] = None
        if show_auth_modal:
            self._open_auth_modal()

        self.registry = GameRegistry()
        self.screen_width = BASE_WIDTH
        self.screen_height = BASE_HEIGHT

        flags = pygame.RESIZABLE
        if start_fullscreen:
            flags |= pygame.FULLSCREEN
        self.window = pygame.display.set_mode((self.screen_width, self.screen_height), flags)
        pygame.display.set_caption("RetroRevive — Classic Computer Games Platform")

        self.canvas = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.clock = pygame.time.Clock()
        self.is_running = True

        # Navigation & Filtering
        self.current_category = GameCategory.ALL
        self.search_query: str = ""
        self.is_search_active: bool = False
        self.selected_card_index: int = 0
        self.selected_game_for_modal: Optional[GameMetadata] = None

        # Active sub-game controller (delegates events/updates/drawing)
        self.active_subapp: Optional[object] = None

        # Build UI Elements
        self._init_category_buttons()
        self._init_header_buttons()
        self._refresh_game_cards()

    def _init_header_buttons(self) -> None:
        uname = self.auth.get_current_username()
        self.btn_auth = UIButton((BASE_WIDTH - 490, 16, 235, 36), f"SOVEREIGN: {uname[:12]}", self._open_auth_modal, font_size=13, color_scheme="gold")
        self.btn_audio = UIButton((BASE_WIDTH - 240, 16, 105, 36), "AUDIO: ON", self._toggle_audio, color_scheme="gold", font_size=13)
        self.btn_quit = UIButton((BASE_WIDTH - 120, 16, 90, 36), "QUIT", self.quit, color_scheme="crimson", font_size=13)

        # Modal buttons
        self.btn_modal_launch = UIButton((BASE_WIDTH // 2 - 270, 565, 160, 44), "LAUNCH GAME", self._launch_modal_game, primary=True)
        self.btn_modal_governor = UIButton((BASE_WIDTH // 2 - 90, 565, 180, 44), "⚖ ROYAL GOVERNOR", self._launch_modal_governor, color_scheme="gold")
        self.btn_modal_close = UIButton((BASE_WIDTH // 2 + 110, 565, 160, 44), "BACK", self._close_modal, color_scheme="sand")

    def _open_auth_modal(self) -> None:
        prof = self.auth.get_current_profile()
        initial_mode = "PROFILE" if (prof and not prof.is_guest) else "LOGIN"
        self.auth_modal = AuthModal(self.auth, on_success=self._on_auth_success, initial_mode=initial_mode)

    def _on_auth_success(self) -> None:
        uname = self.auth.get_current_username()
        if hasattr(self, "btn_auth"):
            self.btn_auth.text = f"SOVEREIGN: {uname[:12]}"

    def _init_category_buttons(self) -> None:
        categories = [
            (GameCategory.ALL, "ALL GAMES (5)"),
            (GameCategory.STRATEGY_SIMULATION, "STRATEGY (3)"),
            (GameCategory.PUZZLE_LOGIC, "PUZZLE / NIM (1)"),
            (GameCategory.ADVENTURE_SPACE, "SPACE (1)"),
        ]
        self.cat_buttons: List[Tuple[GameCategory, UIButton]] = []
        bw = 180
        start_x = 40
        y = 120

        for i, (cat, label) in enumerate(categories):
            btn = UIButton((start_x + i * (bw + 12), y, bw, 36), label, lambda c=cat: self._set_category(c), font_size=13, color_scheme="sand")
            self.cat_buttons.append((cat, btn))

    def _set_category(self, cat: GameCategory) -> None:
        self.current_category = cat
        self._refresh_game_cards()
        SoundSynthesizer.play("click")

    def _toggle_audio(self) -> None:
        enabled = not SoundSynthesizer._enabled
        SoundSynthesizer.set_enabled(enabled)
        self.btn_audio.text = "AUDIO: ON" if enabled else "AUDIO: OFF"

    def _refresh_game_cards(self) -> None:
        """Filters catalog games based on category and search text, then builds cards."""
        # 1. Filter by category
        if self.current_category == GameCategory.ALL:
            games = self.registry.list_all()
        else:
            games = self.registry.filter_by_category(self.current_category)

        # 2. Search query filter
        if self.search_query.strip():
            q = self.search_query.strip().lower()
            games = [g for g in games if (q in g.title.lower() or q in g.subtitle.lower() or q in g.author.lower() or any(q in t.lower() for t in g.tags))]

        self.cards: List[LibraryCard] = []
        if not games:
            return

        card_w = 360
        card_h = 240
        start_x = 40
        start_y = 180
        cols = 3

        for i, g in enumerate(games):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_w + 30)
            y = start_y + row * (card_h + 25)
            card = LibraryCard(
                (x, y, card_w, card_h),
                g,
                on_play=lambda meta=g: self.launch_game(meta.game_id),
                on_details=lambda meta=g: self._open_details(meta),
            )
            self.cards.append(card)

        # Clamp selection index
        self.selected_card_index = min(max(0, self.selected_card_index), max(0, len(self.cards) - 1))
        if self.cards:
            self.cards[self.selected_card_index].is_selected = True

    def _open_details(self, meta: GameMetadata) -> None:
        self.selected_game_for_modal = meta
        SoundSynthesizer.play("click")

    def _close_modal(self) -> None:
        self.selected_game_for_modal = None
        SoundSynthesizer.play("click")

    def _launch_modal_game(self) -> None:
        if self.selected_game_for_modal and self.selected_game_for_modal.is_playable:
            gid = self.selected_game_for_modal.game_id
            self.selected_game_for_modal = None
            self.launch_game(gid)

    def _launch_modal_governor(self) -> None:
        if self.selected_game_for_modal and self.selected_game_for_modal.game_id == "hammurabi":
            self.selected_game_for_modal = None
            self.launch_game("hammurabi", screen="governor")

    def launch_game(self, game_id: str, screen: Optional[str] = None) -> None:
        """Launches the selected game subapp cleanly using the shared display window."""
        SoundSynthesizer.play("fanfare")

        if game_id == "hammurabi":
            self.active_subapp = GameApp(
                shared_window=self.window,
                on_exit_to_library=self._return_to_hub,
                auth=self.auth,
            )
            if screen == "governor":
                self.active_subapp._open_governor_screen()
        elif game_id == "23_matches":
            self.active_subapp = matches_app.MatchesApp(
                shared_window=self.window,
                on_exit_to_library=self._return_to_hub,
            )
        else:
            # Non-playable or unknown
            return

    def _return_to_hub(self) -> None:
        """Callback invoked by game subapps when the player returns to the library."""
        self.active_subapp = None
        pygame.display.set_caption("RetroRevive — Classic Computer Games Platform")
        if hasattr(self, "btn_auth"):
            self.btn_auth.text = f"SOVEREIGN: {self.auth.get_current_username()[:12]}"
        self._refresh_game_cards()
        SoundSynthesizer.play("click")

    def quit(self) -> None:
        self.is_running = False

    def handle_event(self, event: pygame.event.Event) -> None:
        # If a game subapp is actively running, delegate all events to it!
        if self.active_subapp is not None:
            self.active_subapp.handle_event(event)
            return

        canvas_mouse = self._screen_to_canvas(pygame.mouse.get_pos())

        # Auth Modal Event Handling (Top Priority)
        if getattr(self, "auth_modal", None) and self.auth_modal.is_open:
            if self.auth_modal.handle_event(event, canvas_mouse):
                return

        if event.type == pygame.QUIT:
            self.is_running = False
            return

        if event.type == pygame.VIDEORESIZE:
            self.screen_width = event.w
            self.screen_height = event.h
            self.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            return

        # Modal Event Handling
        if self.selected_game_for_modal is not None:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._close_modal()
                    return
                elif event.key == pygame.K_RETURN:
                    self._launch_modal_game()
                    return
            if self.selected_game_for_modal.is_playable and self.btn_modal_launch.handle_event(event, canvas_mouse):
                return
            if self.selected_game_for_modal.game_id == "hammurabi" and hasattr(self, "btn_modal_governor") and self.btn_modal_governor.handle_event(event, canvas_mouse):
                return
            if self.btn_modal_close.handle_event(event, canvas_mouse):
                return
            return

        # Header buttons
        if hasattr(self, "btn_auth") and self.btn_auth.handle_event(event, canvas_mouse):
            return
        if self.btn_audio.handle_event(event, canvas_mouse):
            return
        if self.btn_quit.handle_event(event, canvas_mouse):
            return

        # Category buttons
        for cat, btn in self.cat_buttons:
            if btn.handle_event(event, canvas_mouse):
                return

        # Search bar click
        search_rect = pygame.Rect(BASE_WIDTH - 360, 120, 320, 36)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_search_active = search_rect.collidepoint(canvas_mouse)

        # Search text input
        if self.is_search_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.search_query = self.search_query[:-1]
                self._refresh_game_cards()
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.is_search_active = False
            elif event.unicode and event.unicode.isprintable():
                self.search_query += event.unicode
                self._refresh_game_cards()
            return

        # Game Card Clicks
        for card in self.cards:
            if card.handle_event(event, canvas_mouse):
                return

        # Keyboard Navigation Shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1):
                self.launch_game("hammurabi")
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.launch_game("23_matches")
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.launch_game("hammurabi", screen="governor")
            elif event.key == pygame.K_s:
                self.is_search_active = True
            elif event.key == pygame.K_LEFT:
                if self.cards:
                    self.selected_card_index = (self.selected_card_index - 1) % len(self.cards)
                    for i, c in enumerate(self.cards):
                        c.is_selected = (i == self.selected_card_index)
            elif event.key == pygame.K_RIGHT:
                if self.cards:
                    self.selected_card_index = (self.selected_card_index + 1) % len(self.cards)
                    for i, c in enumerate(self.cards):
                        c.is_selected = (i == self.selected_card_index)
            elif event.key == pygame.K_d:
                if self.cards and 0 <= self.selected_card_index < len(self.cards):
                    self._open_details(self.cards[self.selected_card_index].meta)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.cards and 0 <= self.selected_card_index < len(self.cards):
                    card = self.cards[self.selected_card_index]
                    if card.meta.is_playable:
                        self.launch_game(card.meta.game_id)
                    else:
                        self._open_details(card.meta)
            elif event.key == pygame.K_ESCAPE:
                if self.search_query:
                    self.search_query = ""
                    self._refresh_game_cards()
                else:
                    self.quit()

    def update(self, dt: float) -> None:
        if self.active_subapp is not None:
            self.active_subapp.update(dt)
            return

    def draw(self) -> None:
        # If subapp active, delegate drawing directly!
        if self.active_subapp is not None:
            self.active_subapp.draw()
            return

        # 1. Background
        self.canvas.fill(Palette.BG_DARK)

        # Subtle gold Mesopotamian / arcade top stripe
        pygame.draw.rect(self.canvas, Palette.GOLD_DARK, (0, 0, BASE_WIDTH, 4))

        # 2. Top Header Bar
        header_rect = pygame.Rect(0, 4, BASE_WIDTH, 90)
        pygame.draw.rect(self.canvas, Palette.PANEL_BG, header_rect)
        pygame.draw.line(self.canvas, Palette.GOLD_BASE, (0, 94), (BASE_WIDTH, 94), 2)

        # Platform Title & Tagline
        title_surf = FontManager.title(32).render("RETROREVIVE", True, Palette.GOLD_PALE)
        sub_surf = FontManager.header(16).render("CLASSIC COMPUTER GAMES PLATFORM", True, Palette.SAND_LIGHT)
        build_badge = FontManager.small(12).render("Confluence Buildathon 2026 — Track: Resurrections", True, Palette.TEXT_MUTED)

        self.canvas.blit(title_surf, (40, 16))
        self.canvas.blit(sub_surf, (40, 56))
        self.canvas.blit(build_badge, (360, 58))

        # Header action buttons
        if hasattr(self, "btn_auth"):
            self.btn_auth.draw(self.canvas)
        self.btn_audio.draw(self.canvas)
        self.btn_quit.draw(self.canvas)

        # 3. Category Buttons
        for cat, btn in self.cat_buttons:
            btn.primary = (cat == self.current_category)
            btn.draw(self.canvas)

        # 4. Search Bar
        search_rect = pygame.Rect(BASE_WIDTH - 360, 120, 320, 36)
        s_bg = (50, 40, 32) if self.is_search_active else (32, 26, 20)
        pygame.draw.rect(self.canvas, s_bg, search_rect, border_radius=8)
        s_border = Palette.GOLD_LIGHT if self.is_search_active else Palette.PANEL_BORDER
        pygame.draw.rect(self.canvas, s_border, search_rect, width=1, border_radius=8)

        # Search placeholder or text
        if self.search_query:
            query_surf = FontManager.body(15).render(self.search_query, True, Palette.TEXT_TITLE)
        else:
            query_surf = FontManager.small(13).render("Search games [S]...", True, Palette.TEXT_MUTED)
        self.canvas.blit(query_surf, (search_rect.x + 12, search_rect.y + 9))

        # 5. Game Cards
        if self.cards:
            for card in self.cards:
                card.draw(self.canvas)
        else:
            no_games = FontManager.header(20).render("No games match the current filter or search.", True, Palette.TEXT_MUTED)
            self.canvas.blit(no_games, no_games.get_rect(center=(BASE_WIDTH // 2, 340)))

        # 6. Bottom Navigation Bar / Shortcuts
        bot_rect = pygame.Rect(0, BASE_HEIGHT - 38, BASE_WIDTH, 38)
        pygame.draw.rect(self.canvas, (18, 14, 12), bot_rect)
        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (0, BASE_HEIGHT - 38), (BASE_WIDTH, BASE_HEIGHT - 38), 1)

        shortcuts = "[1] Hammurabi  |  [2] 23 Matches  |  [3] AI Royal Governor  |  [←/→] Select Card  |  [Enter] Play  |  [D] Details  |  [Esc] Quit"
        sc_surf = FontManager.small(12).render(shortcuts, True, Palette.TEXT_MUTED)
        self.canvas.blit(sc_surf, sc_surf.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT - 19)))

        # 7. Game Details Modal
        if self.selected_game_for_modal is not None:
            self._draw_details_modal()

        # 8. Auth Modal (Login / Register / Profile)
        if getattr(self, "auth_modal", None) and self.auth_modal.is_open:
            self.auth_modal.draw(self.canvas)

        # 9. Scale canvas to window
        self._present()

    def _draw_details_modal(self) -> None:
        g = self.selected_game_for_modal
        if not g:
            return

        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 6, 220))
        self.canvas.blit(overlay, (0, 0))

        pw, ph = 780, 560
        px = (BASE_WIDTH - pw) // 2
        py = (BASE_HEIGHT - ph) // 2
        p_rect = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(self.canvas, Palette.PANEL_BG, p_rect, border_radius=14)
        pygame.draw.rect(self.canvas, Palette.GOLD_LIGHT, p_rect, width=2, border_radius=14)

        # Header Title
        title_surf = FontManager.title(28).render(g.title, True, Palette.GOLD_PALE)
        self.canvas.blit(title_surf, (px + 36, py + 28))

        sub_surf = FontManager.body(16).render(g.subtitle, True, Palette.SAND_LIGHT)
        self.canvas.blit(sub_surf, (px + 36, py + 66))

        # Divider
        pygame.draw.line(self.canvas, Palette.PANEL_BORDER, (px + 36, py + 95), (px + pw - 36, py + 95), 1)

        # Metadata Details
        meta_items = [
            ("Historical Origin:", f"{g.author} ({g.year})"),
            ("Publisher:", g.original_publisher),
            ("Source Book:", g.book_source),
            ("Genre & Category:", f"{g.category_display} (Status: {g.status.value})"),
            ("Available Modes:", " • ".join(g.modes)),
        ]

        curr_y = py + 108
        for label, val in meta_items:
            l_surf = FontManager.header(14).render(label, True, Palette.GOLD_BASE)
            v_surf = FontManager.body(14).render(val, True, Palette.TEXT_BODY)
            self.canvas.blit(l_surf, (px + 36, curr_y))
            self.canvas.blit(v_surf, (px + 200, curr_y))
            curr_y += 24

        # Rules Overview
        curr_y += 8
        r_title = FontManager.header(15).render("RULES & MECHANICS OVERVIEW:", True, Palette.GOLD_BASE)
        self.canvas.blit(r_title, (px + 36, curr_y))
        curr_y += 22

        r_words = g.rules_summary.split()
        r_line = ""
        for w in r_words:
            test = r_line + (" " if r_line else "") + w
            if FontManager.small(13).size(test)[0] < pw - 72:
                r_line = test
            else:
                self.canvas.blit(FontManager.small(13).render(r_line, True, Palette.SAND_LIGHT), (px + 36, curr_y))
                curr_y += 18
                r_line = w
        if r_line:
            self.canvas.blit(FontManager.small(13).render(r_line, True, Palette.SAND_LIGHT), (px + 36, curr_y))
            curr_y += 22

        # Historical Provenance
        curr_y += 6
        p_title = FontManager.header(15).render("HISTORICAL PROVENANCE & FIDELITY:", True, Palette.GOLD_BASE)
        self.canvas.blit(p_title, (px + 36, curr_y))
        curr_y += 22

        p_words = g.historical_provenance.split()
        p_line = ""
        for w in p_words:
            test = p_line + (" " if p_line else "") + w
            if FontManager.small(13).size(test)[0] < pw - 72:
                p_line = test
            else:
                self.canvas.blit(FontManager.small(13).render(p_line, True, Palette.TEXT_MUTED), (px + 36, curr_y))
                curr_y += 18
                p_line = w
        if p_line:
            self.canvas.blit(FontManager.small(13).render(p_line, True, Palette.TEXT_MUTED), (px + 36, curr_y))

        # Launch / Close buttons
        if g.is_playable:
            self.btn_modal_launch.is_enabled = True
            self.btn_modal_launch.draw(self.canvas)
            if g.game_id == "hammurabi" and hasattr(self, "btn_modal_governor"):
                self.btn_modal_governor.draw(self.canvas)
        else:
            self.btn_modal_launch.is_enabled = False

        self.btn_modal_close.draw(self.canvas)

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
    hub = RetroReviveHub(start_fullscreen=start_fullscreen)
    hub.run()
    pygame.quit()


if __name__ == "__main__":
    main()
