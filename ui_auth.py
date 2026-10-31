"""
ui_auth.py - Graphical Authentication, Profile, and Save Slot Dialogs for RetroRevive.

Provides:
- Login modal with username and masked password (with Show/Hide toggle)
- Registration modal with password confirmation and validation
- Instant One-Click "Play as Guest" ruler mode
- Player Profile viewer with career achievements
- Multi-slot save game manager (Slots 1, 2, 3)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
import pygame

from auth_manager import AuthManager, UserProfile
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton


class AuthModal:
    """Semi-transparent sapphire glass modal managing Login, Registration, Profile, and Save Slots."""

    def __init__(
        self,
        auth: AuthManager,
        on_success: Optional[Callable[[], None]] = None,
        initial_mode: str = "LOGIN",  # "LOGIN", "REGISTER", "PROFILE", "SAVES"
    ) -> None:
        self.auth = auth
        self.on_success = on_success
        self.mode = initial_mode
        self.is_open = True

        self.width = 680
        self.height = 460
        self.rect = pygame.Rect((1280 - self.width) // 2, (720 - self.height) // 2, self.width, self.height)

        # Form fields
        self.username_buffer = ""
        self.password_buffer = ""
        self.confirm_password_buffer = ""
        self.show_password = False
        self.focused_field = "username"  # "username", "password", "confirm"
        self.error_message: Optional[str] = None
        self.success_message: Optional[str] = None

        # Multi-slot saves state
        self.save_mode_action = "SAVE"  # "SAVE" or "LOAD"
        self.current_state_getter: Optional[Callable[[], Optional[dict]]] = None
        self.on_load_state: Optional[Callable[[dict], None]] = None

        # Cached slot infos
        self.slot_infos: List[Dict[str, Any]] = []
        self._refresh_slots()

        # Build Interactive Buttons
        self._rebuild_buttons()

    def _refresh_slots(self) -> None:
        self.slot_infos = self.auth.list_save_slots()

    def set_save_context(
        self,
        action: str,
        state_getter: Optional[Callable[[], Optional[dict]]] = None,
        on_load: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """Configures the dialog for Save/Load slot management."""
        self.save_mode_action = action
        self.current_state_getter = state_getter
        self.on_load_state = on_load
        self.mode = "SAVES"
        self.error_message = None
        self.success_message = None
        self._refresh_slots()
        self._rebuild_buttons()

    def _rebuild_buttons(self) -> None:
        self.buttons: List[UIButton] = []
        bx = self.rect.x
        by = self.rect.y
        bw = self.rect.width
        bh = self.rect.height

        # Close button (top right)
        self.btn_close = UIButton((bx + bw - 44, by + 12, 32, 30), "X", self.close, font_size=14, color_scheme="crimson")

        if self.mode == "LOGIN":
            self.buttons = [
                UIButton((bx + 60, by + 340, 160, 44), "SIGN IN", self._submit_login, font_size=15, primary=True),
                UIButton((bx + 240, by + 340, 180, 44), "PLAY AS GUEST", self._submit_guest, font_size=15, color_scheme="gold"),
                UIButton((bx + 440, by + 340, 180, 44), "NEW ACCOUNT", lambda: self.switch_mode("REGISTER"), font_size=14),
            ]
        elif self.mode == "REGISTER":
            self.buttons = [
                UIButton((bx + 120, by + 360, 200, 44), "CREATE ACCOUNT", self._submit_register, font_size=15, primary=True),
                UIButton((bx + 360, by + 360, 200, 44), "BACK TO LOGIN", lambda: self.switch_mode("LOGIN"), font_size=14),
            ]
        elif self.mode == "PROFILE":
            self.buttons = [
                UIButton((bx + 120, by + 360, 200, 44), "SWITCH USER / LOGOUT", self._submit_logout, font_size=14, color_scheme="crimson"),
                UIButton((bx + 360, by + 360, 200, 44), "CLOSE PROFILE", self.close, font_size=15, primary=True),
            ]
        elif self.mode == "SAVES":
            # Slot action buttons are built per-slot in draw
            self.buttons = [
                UIButton((bx + (bw - 180) // 2, by + bh - 55, 180, 40), "CLOSE", self.close, font_size=15),
            ]

    def switch_mode(self, new_mode: str) -> None:
        self.mode = new_mode
        self.error_message = None
        self.success_message = None
        self._refresh_slots()
        self._rebuild_buttons()
        SoundSynthesizer.play("click")

    def close(self) -> None:
        self.is_open = False
        SoundSynthesizer.play("click")

    def _submit_login(self) -> None:
        ok, err = self.auth.login(self.username_buffer, self.password_buffer)
        if ok:
            self.success_message = f"Welcome, Sire {self.auth.get_current_username()}!"
            SoundSynthesizer.play("harvest")
            if self.on_success:
                self.on_success()
            self.close()
        else:
            self.error_message = err
            SoundSynthesizer.play("warning")

    def _submit_guest(self) -> None:
        self.auth.login_as_guest()
        self.success_message = "Entered reign as Guest Sovereign."
        SoundSynthesizer.play("harvest")
        if self.on_success:
            self.on_success()
        self.close()

    def _submit_register(self) -> None:
        if self.password_buffer != self.confirm_password_buffer:
            self.error_message = "Passwords do not match."
            SoundSynthesizer.play("warning")
            return
        ok, err = self.auth.register(self.username_buffer, self.password_buffer, self.confirm_password_buffer)
        if ok:
            self.success_message = "Account created! Signed in as sovereign."
            SoundSynthesizer.play("coin")
            if self.on_success:
                self.on_success()
            self.close()
        else:
            self.error_message = err
            SoundSynthesizer.play("warning")

    def _submit_logout(self) -> None:
        self.auth.logout()
        self.switch_mode("LOGIN")
        SoundSynthesizer.play("click")

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if not self.is_open:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True
            elif event.key == pygame.K_TAB:
                if self.mode == "LOGIN":
                    self.focused_field = "password" if self.focused_field == "username" else "username"
                elif self.mode == "REGISTER":
                    order = ["username", "password", "confirm"]
                    idx = (order.index(self.focused_field) + 1) % len(order)
                    self.focused_field = order[idx]
                return True
            elif event.key == pygame.K_RETURN:
                if self.mode == "LOGIN":
                    self._submit_login()
                elif self.mode == "REGISTER":
                    self._submit_register()
                return True

            # Typing into active buffer
            if self.mode in ("LOGIN", "REGISTER"):
                if event.key == pygame.K_BACKSPACE:
                    if self.focused_field == "username":
                        self.username_buffer = self.username_buffer[:-1]
                    elif self.focused_field == "password":
                        self.password_buffer = self.password_buffer[:-1]
                    elif self.focused_field == "confirm":
                        self.confirm_password_buffer = self.confirm_password_buffer[:-1]
                    self.error_message = None
                    return True
                elif event.unicode and len(event.unicode) == 1 and event.unicode.isprintable():
                    if self.focused_field == "username" and len(self.username_buffer) < 20:
                        self.username_buffer += event.unicode
                    elif self.focused_field == "password" and len(self.password_buffer) < 32:
                        self.password_buffer += event.unicode
                    elif self.focused_field == "confirm" and len(self.confirm_password_buffer) < 32:
                        self.confirm_password_buffer += event.unicode
                    self.error_message = None
                    return True

        # Mouse clicks on form fields
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            bx, by = self.rect.x, self.rect.y
            # Username input box
            if pygame.Rect(bx + 180, by + 120, 360, 38).collidepoint(mouse_pos):
                self.focused_field = "username"
                return True
            # Password input box
            if pygame.Rect(bx + 180, by + 180, 360, 38).collidepoint(mouse_pos):
                self.focused_field = "password"
                return True
            # Confirm password box
            if self.mode == "REGISTER" and pygame.Rect(bx + 180, by + 240, 360, 38).collidepoint(mouse_pos):
                self.focused_field = "confirm"
                return True
            # Toggle show password button
            if pygame.Rect(bx + 550, by + 180, 60, 38).collidepoint(mouse_pos):
                self.show_password = not self.show_password
                SoundSynthesizer.play("click")
                return True

            # Saves Slot interactions
            if self.mode == "SAVES":
                for slot_idx in (1, 2, 3):
                    slot_y = by + 90 + (slot_idx - 1) * 85
                    action_rect = pygame.Rect(bx + 520, slot_y + 16, 110, 38)
                    if action_rect.collidepoint(mouse_pos):
                        self._handle_slot_action(slot_idx)
                        return True
                    # Delete slot button
                    del_rect = pygame.Rect(bx + 460, slot_y + 16, 48, 38)
                    if del_rect.collidepoint(mouse_pos):
                        self.auth.delete_slot(slot_idx)
                        self._refresh_slots()
                        SoundSynthesizer.play("click")
                        return True

        if self.btn_close.handle_event(event, mouse_pos):
            return True

        for btn in self.buttons:
            if btn.handle_event(event, mouse_pos):
                return True

        return True  # Consume all events while modal is open

    def _handle_slot_action(self, slot_idx: int) -> None:
        if self.save_mode_action == "SAVE":
            if self.current_state_getter:
                state_dict = self.current_state_getter()
                if state_dict:
                    ok = self.auth.save_slot(slot_idx, state_dict)
                    if ok:
                        self.success_message = f"Game saved to Slot {slot_idx}!"
                        SoundSynthesizer.play("coin")
                        self._refresh_slots()
                    else:
                        self.error_message = f"Failed to save to Slot {slot_idx}."
        elif self.save_mode_action == "LOAD":
            loaded = self.auth.load_slot(slot_idx)
            if loaded:
                if self.on_load_state:
                    self.on_load_state(loaded)
                self.success_message = f"Resumed from Slot {slot_idx}!"
                SoundSynthesizer.play("harvest")
                self.close()
            else:
                self.error_message = f"Slot {slot_idx} is empty."
                SoundSynthesizer.play("warning")

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_open:
            return

        # Dim backdrop
        dim = pygame.Surface((1280, 720), pygame.SRCALPHA)
        dim.fill((8, 12, 22, 215))
        surface.blit(dim, (0, 0))

        # Main Sapphire Glass Window
        pygame.draw.rect(surface, Palette.SAPPHIRE_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, Palette.GOLD_BASE, self.rect, width=2, border_radius=12)

        # Header Bar
        hdr_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 56)
        pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, hdr_rect, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(surface, Palette.GOLD_DARK, (self.rect.x, self.rect.y + 56), (self.rect.right, self.rect.y + 56), 2)

        titles = {
            "LOGIN": "SOVEREIGN ACCESS & IDENTITY",
            "REGISTER": "ENTHRONE NEW RULER",
            "PROFILE": f"ROYAL PROFILE: {self.auth.get_current_username()}",
            "SAVES": f"{'SAVE EMPIRE' if self.save_mode_action == 'SAVE' else 'RESTORE EMPIRE'} — ROYAL RECORDS",
        }
        title_surf = FontManager.header(20).render(titles.get(self.mode, "HAMMURABI"), True, Palette.GOLD_PALE)
        surface.blit(title_surf, (self.rect.x + 28, self.rect.y + 16))

        self.btn_close.draw(surface)

        # Draw content according to mode
        if self.mode == "LOGIN":
            self._draw_login(surface)
        elif self.mode == "REGISTER":
            self._draw_register(surface)
        elif self.mode == "PROFILE":
            self._draw_profile(surface)
        elif self.mode == "SAVES":
            self._draw_saves(surface)

        for btn in self.buttons:
            btn.draw(surface)

    def _draw_login(self, surface: pygame.Surface) -> None:
        bx, by = self.rect.x, self.rect.y

        # Subtitle
        sub_s = FontManager.small(12).render("Sign in with your Babylonian local profile or enter as Guest.", True, Palette.TEXT_MUTED)
        surface.blit(sub_s, (bx + 60, by + 76))

        # 1. Username
        u_lbl = FontManager.header(14).render("Ruler Name:", True, Palette.TEXT_TITLE)
        surface.blit(u_lbl, (bx + 60, by + 128))
        u_box = pygame.Rect(bx + 180, by + 120, 360, 38)
        self._draw_input_box(surface, u_box, self.username_buffer, self.focused_field == "username", is_password=False)

        # 2. Password
        p_lbl = FontManager.header(14).render("Secret Seal:", True, Palette.TEXT_TITLE)
        surface.blit(p_lbl, (bx + 60, by + 188))
        p_box = pygame.Rect(bx + 180, by + 180, 360, 38)
        self._draw_input_box(surface, p_box, self.password_buffer, self.focused_field == "password", is_password=not self.show_password)

        # Show/Hide Password Button
        eye_box = pygame.Rect(bx + 550, by + 180, 60, 38)
        pygame.draw.rect(surface, Palette.SAPPHIRE_LIGHT, eye_box, border_radius=5)
        pygame.draw.rect(surface, Palette.GOLD_DARK, eye_box, width=1, border_radius=5)
        eye_text = "HIDE" if self.show_password else "SHOW"
        eye_s = FontManager.small(11).render(eye_text, True, Palette.GOLD_PALE)
        surface.blit(eye_s, eye_s.get_rect(center=eye_box.center))

        # Status / Error banner
        self._draw_messages(surface, by + 265)

    def _draw_register(self, surface: pygame.Surface) -> None:
        bx, by = self.rect.x, self.rect.y

        sub_s = FontManager.small(12).render("Register a secure sovereign profile with PBKDF2 salt hashing.", True, Palette.TEXT_MUTED)
        surface.blit(sub_s, (bx + 60, by + 76))

        # Username
        u_lbl = FontManager.header(14).render("Ruler Name:", True, Palette.TEXT_TITLE)
        surface.blit(u_lbl, (bx + 60, by + 128))
        u_box = pygame.Rect(bx + 180, by + 120, 360, 38)
        self._draw_input_box(surface, u_box, self.username_buffer, self.focused_field == "username", is_password=False)

        # Password
        p_lbl = FontManager.header(14).render("Secret Seal:", True, Palette.TEXT_TITLE)
        surface.blit(p_lbl, (bx + 60, by + 188))
        p_box = pygame.Rect(bx + 180, by + 180, 360, 38)
        self._draw_input_box(surface, p_box, self.password_buffer, self.focused_field == "password", is_password=not self.show_password)

        # Show/Hide Password Button
        eye_box = pygame.Rect(bx + 550, by + 180, 60, 38)
        pygame.draw.rect(surface, Palette.SAPPHIRE_LIGHT, eye_box, border_radius=5)
        pygame.draw.rect(surface, Palette.GOLD_DARK, eye_box, width=1, border_radius=5)
        eye_text = "HIDE" if self.show_password else "SHOW"
        eye_s = FontManager.small(11).render(eye_text, True, Palette.GOLD_PALE)
        surface.blit(eye_s, eye_s.get_rect(center=eye_box.center))

        # Confirm
        c_lbl = FontManager.header(14).render("Confirm Seal:", True, Palette.TEXT_TITLE)
        surface.blit(c_lbl, (bx + 60, by + 248))
        c_box = pygame.Rect(bx + 180, by + 240, 360, 38)
        self._draw_input_box(surface, c_box, self.confirm_password_buffer, self.focused_field == "confirm", is_password=not self.show_password)

        self._draw_messages(surface, by + 305)

    def _draw_profile(self, surface: pygame.Surface) -> None:
        bx, by = self.rect.x, self.rect.y
        profile = self.auth.get_current_profile()

        # Stats grid
        stats = [
            ("Ruler Identity", profile.display_name if profile else "Guest"),
            ("Status", "Guest Sovereign" if (profile and profile.is_guest) else "Registered Sovereign"),
            ("Reigns Attempted", str(profile.games_played if profile else 0)),
            ("Triumphs & Victories", str(profile.victories if profile else 0)),
            ("Highest Evaluation", profile.best_score_title if profile else "Unrecorded"),
            ("Achievements", f"{len(profile.achievements)} unlocked" if profile else "None"),
            ("Crowned Since", profile.created_at[:10] if (profile and profile.created_at) else "Present"),
        ]

        py_cur = by + 85
        for k, v in stats:
            k_s = FontManager.header(14).render(f"{k}:", True, Palette.GOLD_LIGHT)
            v_s = FontManager.body(15).render(v, True, Palette.TEXT_TITLE)
            surface.blit(k_s, (bx + 80, py_cur))
            surface.blit(v_s, (bx + 300, py_cur))
            py_cur += 34

    def _draw_saves(self, surface: pygame.Surface) -> None:
        bx, by = self.rect.x, self.rect.y
        sub = "Select a royal parchment slot to preserve or resume your empire."
        sub_s = FontManager.small(12).render(sub, True, Palette.TEXT_MUTED)
        surface.blit(sub_s, (bx + 50, by + 68))

        slot_dict = {item["slot_id"]: item for item in self.slot_infos if isinstance(item, dict) and item.get("exists")}

        for slot_idx in (1, 2, 3):
            slot_y = by + 95 + (slot_idx - 1) * 90
            card_rect = pygame.Rect(bx + 40, slot_y, self.width - 80, 80)
            pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, card_rect, border_radius=8)
            pygame.draw.rect(surface, Palette.GOLD_DARK, card_rect, width=1, border_radius=8)

            info = slot_dict.get(slot_idx)
            if info:
                s_title = FontManager.header(15).render(f"SLOT {slot_idx}: {info.get('mode', 'CLASSIC')} MODE", True, Palette.GOLD_PALE)
                surface.blit(s_title, (bx + 56, slot_y + 12))
                meta_str = f"Year {info.get('year', 1)} of 10  |  Pop: {info.get('population', 100)}  |  Grain: {info.get('bushels', 2800)} bu  |  Land: {info.get('acres', 1000)} ac"
                m_surf = FontManager.small(12).render(meta_str, True, Palette.TEXT_BODY)
                surface.blit(m_surf, (bx + 56, slot_y + 36))
                time_s = FontManager.small(10).render(f"Saved: {info.get('saved_at', 'Unknown')}", True, Palette.TEXT_MUTED)
                surface.blit(time_s, (bx + 56, slot_y + 56))

                # Delete button
                del_rect = pygame.Rect(bx + 460, slot_y + 20, 48, 38)
                pygame.draw.rect(surface, (70, 25, 25), del_rect, border_radius=5)
                pygame.draw.rect(surface, Palette.CRIMSON_LIGHT, del_rect, width=1, border_radius=5)
                d_s = FontManager.small(11).render("DEL", True, Palette.CRIMSON_LIGHT)
                surface.blit(d_s, d_s.get_rect(center=del_rect.center))
            else:
                s_title = FontManager.header(15).render(f"SLOT {slot_idx}: [EMPTY SCROLL]", True, Palette.TEXT_MUTED)
                surface.blit(s_title, (bx + 56, slot_y + 28))

            # Action button: SAVE or LOAD
            act_rect = pygame.Rect(bx + 520, slot_y + 20, 100, 38)
            act_col = Palette.GOLD_BASE if self.save_mode_action == "SAVE" else Palette.LAPIS_BASE
            pygame.draw.rect(surface, act_col, act_rect, border_radius=5)
            pygame.draw.rect(surface, Palette.GOLD_LIGHT, act_rect, width=1, border_radius=5)
            act_lbl = "SAVE" if self.save_mode_action == "SAVE" else "LOAD"
            act_s = FontManager.header(13).render(act_lbl, True, Palette.TEXT_DARK if self.save_mode_action == "SAVE" else Palette.TEXT_TITLE)
            surface.blit(act_s, act_s.get_rect(center=act_rect.center))

        self._draw_messages(surface, by + 375)

    def _draw_input_box(self, surface: pygame.Surface, rect: pygame.Rect, text: str, is_focused: bool, is_password: bool) -> None:
        bg_col = Palette.SAPPHIRE_DARK if is_focused else (12, 18, 30)
        border_col = Palette.GOLD_LIGHT if is_focused else Palette.PANEL_BORDER
        pygame.draw.rect(surface, bg_col, rect, border_radius=6)
        pygame.draw.rect(surface, border_col, rect, width=2 if is_focused else 1, border_radius=6)

        display_text = ("•" * len(text)) if is_password else text
        txt_surf = FontManager.mono(16).render(display_text, True, Palette.TEXT_TITLE)
        surface.blit(txt_surf, (rect.x + 10, rect.centery - txt_surf.get_height() // 2))

        # Blinking typing cursor
        if is_focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = rect.x + 10 + txt_surf.get_width() + 2
            pygame.draw.line(surface, Palette.GOLD_LIGHT, (cx, rect.y + 8), (cx, rect.bottom - 8), 2)

    def _draw_messages(self, surface: pygame.Surface, y: int) -> None:
        bx = self.rect.x
        if self.error_message:
            e_s = FontManager.small(12).render(f"[!] {self.error_message}", True, Palette.CRIMSON_LIGHT)
            surface.blit(e_s, (bx + 80, y))
        elif self.success_message:
            s_s = FontManager.small(12).render(f"[✓] {self.success_message}", True, Palette.SUCCESS_GREEN)
            surface.blit(s_s, (bx + 80, y))
