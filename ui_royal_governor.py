"""
ui_royal_governor.py — Advanced Royal Governor Dashboard for RetroRevive.

Provides a dedicated interactive interface for the AI Royal Governor:
- Goal delegation controls (5 preset mandates, custom text input, & turn duration stepper)
- Multi-tab command center:
    1. OVERVIEW: Real-time kingdom resources, before/after deltas, food security meters
    2. INTELLIGENCE: Rival kingdoms (Elam, Assyria, Ur of Sumer), scouting intel, diplomacy status
    3. COGNITIVE LOG: ReAct Observe-Recall-Think-Plan-Act-Verify cycle, reasoning, tool calls
    4. CHRONICLE: Longitudinal history, harvest trends, rat damage, immigration records
- Real-time player override / instant control revocation
- 100% standardized in English
"""

from __future__ import annotations

import math
import time
from typing import Callable, List, Optional, Tuple
import pygame

from game_logic import GameState
from modern_game_logic import EnhancedGameState
from royal_governor import ActionRecord, AgentStatus, DelegationSession, RoyalGovernor
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton, UITextInput


PRESET_GOALS = [
    ("🛡️ Famine Defense", "Prevent famine, guarantee rations for all citizens, and maintain grain reserves."),
    ("🌾 Agrarian Prosperity", "Maximize agricultural planting, balance grain reserves, and grow the population."),
    ("🏛️ Imperial Expansion", "Acquire fertile land whenever market prices are cheap while maintaining zero starvation."),
    ("⚔️ Military Dominance", "Expand army garrison, build fortifications, scout rivals, and establish regional deterrence."),
    ("🤝 Hegemony & Trade", "Form trade agreements, negotiate alliances, and balance diplomacy across Mesopotamia."),
]


class RoyalGovernorDashboard:
    """Interactive Pygame dashboard for delegating kingdom management to the Royal Governor."""

    def __init__(
        self,
        governor: RoyalGovernor,
        on_return: Callable[[], None],
        screen_w: int = 1280,
        screen_h: int = 720,
    ) -> None:
        self.governor = governor
        self.on_return = on_return
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Delegation settings
        self.selected_goal_idx = 0
        self.selected_goal = PRESET_GOALS[0][1]
        self.turns_to_delegate = 3
        self.current_tab = "OVERVIEW"  # "OVERVIEW", "INTELLIGENCE", "COGNITIVE LOG", "CHRONICLE"

        # UI state
        self.status_message = "Royal Governor standing by. Assign a mandate or execute step-by-step."
        self.last_record: Optional[ActionRecord] = None
        self.action_history: List[ActionRecord] = []
        self.is_executing = False

        # Custom mandate text input
        self.custom_mandate_input = UITextInput(
            rect=(30, 205, 350, 36),
            placeholder="Type custom mandate or select above...",
            font_size=12,
        )

        # Setup Buttons
        self._init_buttons()

    def _init_buttons(self) -> None:
        # Top goal presets (Left column top)
        self.goal_buttons = []
        for i, (label, _) in enumerate(PRESET_GOALS):
            btn = UIButton(
                rect=(30 + (i % 2) * 180, 85 + (i // 2) * 38, 172, 34),
                text=label,
                callback=lambda idx=i: self._select_goal(idx),
                font_size=11,
                color_scheme="gold" if i == self.selected_goal_idx else "sand",
            )
            self.goal_buttons.append(btn)

        # Turns stepper
        self.btn_turns_minus = UIButton(
            rect=(180, 250, 36, 32),
            text="-",
            callback=self._decrement_turns,
            font_size=16,
            color_scheme="sand",
        )
        self.btn_turns_plus = UIButton(
            rect=(340, 250, 36, 32),
            text="+",
            callback=self._increment_turns,
            font_size=16,
            color_scheme="sand",
        )

        # Execution controls
        self.btn_step_turn = UIButton(
            rect=(30, 290, 350, 38),
            text="▶ STEP 1 TURN (REASON & ACT)",
            callback=self._delegate_single_turn,
            font_size=12,
            primary=True,
            color_scheme="gold",
        )

        self.btn_run_all = UIButton(
            rect=(30, 335, 350, 38),
            text=f"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS",
            callback=self._delegate_all_turns,
            font_size=12,
            color_scheme="lapis",
        )

        self.btn_revoke = UIButton(
            rect=(30, 380, 350, 36),
            text="⏹ REVOKE DELEGATION (TAKE CONTROL)",
            callback=self._revoke_delegation,
            font_size=11,
            color_scheme="crimson",
        )

        self.btn_return = UIButton(
            rect=(30, 665, 350, 36),
            text="↩ RETURN TO KINGDOM COMMAND",
            callback=self._return_to_game,
            font_size=12,
            color_scheme="sand",
        )

        # Tab navigation buttons
        tab_names = ["OVERVIEW", "INTELLIGENCE", "COGNITIVE LOG", "CHRONICLE"]
        self.tab_buttons = []
        for i, tname in enumerate(tab_names):
            t_btn = UIButton(
                rect=(420 + i * 205, 75, 195, 34),
                text=tname,
                callback=lambda t=tname: self._set_tab(t),
                font_size=11,
                color_scheme="gold" if tname == self.current_tab else "sand",
            )
            self.tab_buttons.append(t_btn)

    def _set_tab(self, tab: str) -> None:
        self.current_tab = tab
        for btn in self.tab_buttons:
            btn.color_scheme = "gold" if btn.text == tab else "sand"
        SoundSynthesizer.play("click")

    def _select_goal(self, idx: int) -> None:
        self.selected_goal_idx = idx
        self.selected_goal = PRESET_GOALS[idx][1]
        self.custom_mandate_input.text = ""
        for i, btn in enumerate(self.goal_buttons):
            btn.color_scheme = "gold" if i == idx else "sand"
        SoundSynthesizer.play("click")

    def _increment_turns(self) -> None:
        if self.turns_to_delegate < 10:
            self.turns_to_delegate += 1
            self.btn_run_all.text = f"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS"
            SoundSynthesizer.play("click")

    def _decrement_turns(self) -> None:
        if self.turns_to_delegate > 1:
            self.turns_to_delegate -= 1
            self.btn_run_all.text = f"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS"
            SoundSynthesizer.play("click")

    def _get_active_mandate(self) -> str:
        if self.custom_mandate_input.text.strip():
            return self.custom_mandate_input.text.strip()
        return self.selected_goal

    def _delegate_single_turn(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = "Reign has ended. No further turns can be delegated."
            return

        mandate = self._get_active_mandate()
        self.status_message = f"Royal Governor executing Turn {self.governor.current_enhanced_state.classic_state.year}..."
        session = self.governor.delegate(goal=mandate, turns=1)
        if session.action_history:
            self.last_record = session.action_history[-1]
            self.action_history.extend(session.action_history)
        self.status_message = f"Turn {self.last_record.game_year if self.last_record else 1} completed by {self.governor.backend_name}."
        SoundSynthesizer.play("action")

    def _delegate_all_turns(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = "Reign has ended. No further turns can be delegated."
            return

        mandate = self._get_active_mandate()
        self.status_message = f"Royal Governor running {self.turns_to_delegate} turns autonomously..."
        session = self.governor.delegate(goal=mandate, turns=self.turns_to_delegate)
        if session.action_history:
            self.last_record = session.action_history[-1]
            self.action_history.extend(session.action_history)
        self.status_message = f"Delegation of {session.turns_completed} turns finished."
        SoundSynthesizer.play("level_up")

    def _revoke_delegation(self) -> None:
        self.governor.revoke()
        self.status_message = "Control REVOKED. King Hammurabi resumes immediate manual rule."
        SoundSynthesizer.play("alert")

    def _return_to_game(self) -> None:
        SoundSynthesizer.play("click")
        self.on_return()

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        # Custom mandate text input
        self.custom_mandate_input.handle_event(event, mouse_pos)

        # Tab buttons
        for btn in self.tab_buttons:
            if btn.handle_event(event, mouse_pos):
                return

        # Goal buttons
        for btn in self.goal_buttons:
            if btn.handle_event(event, mouse_pos):
                return

        # Turns steppers
        if self.btn_turns_minus.handle_event(event, mouse_pos):
            return
        if self.btn_turns_plus.handle_event(event, mouse_pos):
            return

        # Actions
        if self.btn_step_turn.handle_event(event, mouse_pos):
            return
        if self.btn_run_all.handle_event(event, mouse_pos):
            return
        if self.btn_revoke.handle_event(event, mouse_pos):
            return
        if self.btn_return.handle_event(event, mouse_pos):
            return

    def update(self, dt: float) -> None:
        for btn in self.goal_buttons:
            if hasattr(btn, "update"):
                btn.update(dt)
        for btn in self.tab_buttons:
            if hasattr(btn, "update"):
                btn.update(dt)
        for b in [
            self.btn_turns_minus,
            self.btn_turns_plus,
            self.btn_step_turn,
            self.btn_run_all,
            self.btn_revoke,
            self.btn_return,
        ]:
            if hasattr(b, "update"):
                b.update(dt)
        if hasattr(self, "custom_mandate_input") and hasattr(self.custom_mandate_input, "update"):
            self.custom_mandate_input.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(Palette.SAPPHIRE_DARK)

        # Header Banner
        pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, (0, 0, self.screen_w, 65))
        pygame.draw.line(surface, Palette.PANEL_BORDER, (0, 65), (self.screen_w, 65), 1)

        title_surf = FontManager.title(22).render("AI ROYAL GOVERNOR — AUTONOMOUS COMMAND DASHBOARD", True, Palette.GOLD_METALLIC)
        surface.blit(title_surf, (30, 18))

        backend_text = f"Backend: {self.governor.backend_name}"
        b_surf = FontManager.small(12).render(backend_text, True, Palette.TEXT_MUTED)
        surface.blit(b_surf, (self.screen_w - b_surf.get_width() - 30, 24))

        # Left Column Panel (Delegation & Mandates)
        pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, (20, 75, 370, 630), border_radius=8)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (20, 75, 370, 630), width=1, border_radius=8)

        # Mandates title
        lbl = FontManager.bold(13).render("SELECT OR TYPE ROYAL MANDATE:", True, Palette.GOLD_METALLIC)
        surface.blit(lbl, (30, 80))

        # Draw Goal Buttons
        for btn in self.goal_buttons:
            btn.draw(surface)

        # Custom mandate input
        self.custom_mandate_input.draw(surface)

        # Duration Stepper
        lbl_dur = FontManager.regular(12).render("DELEGATION DURATION:", True, Palette.TEXT_TITLE)
        surface.blit(lbl_dur, (30, 258))

        self.btn_turns_minus.draw(surface)
        turns_surf = FontManager.bold(14).render(f"{self.turns_to_delegate} YRS", True, Palette.GOLD_METALLIC)
        surface.blit(turns_surf, (240, 256))
        self.btn_turns_plus.draw(surface)

        # Action Buttons
        self.btn_step_turn.draw(surface)
        self.btn_run_all.draw(surface)
        self.btn_revoke.draw(surface)
        self.btn_return.draw(surface)

        # Status Message Box
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (30, 430, 350, 100), border_radius=6)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (30, 430, 350, 100), width=1, border_radius=6)
        s_title = FontManager.bold(11).render("GOVERNOR DISPATCH:", True, Palette.TEXT_MUTED)
        surface.blit(s_title, (40, 438))
        self._draw_multiline_text(surface, self.status_message, (40, 458), 330, 12, Palette.TEXT_BODY)

        # Draw Tabs
        for btn in self.tab_buttons:
            btn.draw(surface)

        # Main Display Area (Right panel)
        content_rect = pygame.Rect(410, 115, 840, 590)
        pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, content_rect, border_radius=8)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, content_rect, width=1, border_radius=8)

        if self.current_tab == "OVERVIEW":
            self._draw_overview_tab(surface, content_rect)
        elif self.current_tab == "INTELLIGENCE":
            self._draw_intelligence_tab(surface, content_rect)
        elif self.current_tab == "COGNITIVE LOG":
            self._draw_cognitive_log_tab(surface, content_rect)
        elif self.current_tab == "CHRONICLE":
            self._draw_chronicle_tab(surface, content_rect)

    def _draw_overview_tab(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        st = self.governor.current_enhanced_state.classic_state

        # Title
        t = FontManager.bold(16).render("LIVE KINGDOM STATUS & FOOD SECURITY", True, Palette.GOLD_METALLIC)
        surface.blit(t, (rect.x + 20, rect.y + 15))

        # Metrics cards
        metrics = [
            ("Current Year", f"Year {st.year} / 10", Palette.GOLD_METALLIC),
            ("Population", f"{st.population} citizens", Palette.TEXT_TITLE),
            ("Grain in Silos", f"{st.bushels} bushels", Palette.GOLD_METALLIC),
            ("Land Owned", f"{st.acres} acres", Palette.TEXT_TITLE),
            ("Land Price", f"{st.land_price} bu/acre", Palette.TEXT_BODY),
            ("Royal Treasury", f"{getattr(st, 'treasury_gold', 0)} gold", Palette.GOLD_METALLIC),
            ("Royal Guard", f"{getattr(st, 'soldiers', 0)} soldiers", Palette.TEXT_TITLE),
            ("Military Power", f"{getattr(st, 'military_strength', 0)} rating", Palette.CRIMSON_LIGHT),
        ]

        for i, (title, val, col) in enumerate(metrics):
            rx = rect.x + 20 + (i % 4) * 195
            ry = rect.y + 50 + (i // 4) * 65
            pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rx, ry, 185, 55), border_radius=6)
            pygame.draw.rect(surface, Palette.PANEL_BORDER, (rx, ry, 185, 55), width=1, border_radius=6)
            surface.blit(FontManager.small(11).render(title, True, Palette.TEXT_MUTED), (rx + 10, ry + 8))
            surface.blit(FontManager.bold(14).render(val, True, col), (rx + 10, ry + 26))

        # Before & After Deltas Table
        ty = rect.y + 195
        surface.blit(FontManager.bold(14).render("PREVIOUS TURN RESOURCE DELTAS & VERIFICATION", True, Palette.GOLD_METALLIC), (rect.x + 20, ty))

        if self.last_record:
            rec = self.last_record
            table_y = ty + 30
            pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, table_y, 800, 140), border_radius=6)
            pygame.draw.rect(surface, Palette.PANEL_BORDER, (rect.x + 20, table_y, 800, 140), width=1, border_radius=6)

            headers = ["Resource", "Before Turn", "Decreed Orders", "After Turn", "Delta"]
            for h_idx, h in enumerate(headers):
                surface.blit(FontManager.bold(12).render(h, True, Palette.TEXT_MUTED), (rect.x + 40 + h_idx * 155, table_y + 12))

            rows = [
                ("Grain Bushels", f"{rec.before_resources.get('bushels', 0)}", f"Feed: {rec.planned_actions.get('feed_bushels', 0)}", f"{rec.after_resources.get('bushels', 0)}", f"{rec.resource_deltas.get('bushels', 0):+d}"),
                ("Farmland Acres", f"{rec.before_resources.get('acres', 0)}", f"Plant: {rec.planned_actions.get('plant_acres', 0)}", f"{rec.after_resources.get('acres', 0)}", f"{rec.resource_deltas.get('acres', 0):+d}"),
                ("Citizens", f"{rec.before_resources.get('population', 0)}", f"Starved: {rec.execution_result.get('events', {}).get('starved_this_year', 0)}", f"{rec.after_resources.get('population', 0)}", f"{rec.resource_deltas.get('population', 0):+d}"),
                ("Soldiers", f"{rec.before_resources.get('soldiers', 0)}", f"Recruit: {rec.planned_actions.get('recruit_soldiers', 0)}", f"{rec.after_resources.get('soldiers', 0)}", f"{rec.resource_deltas.get('soldiers', 0):+d}"),
            ]

            for r_idx, r in enumerate(rows):
                ry = table_y + 38 + r_idx * 24
                for c_idx, val in enumerate(r):
                    col = Palette.SUCCESS_GREEN if "+" in val and c_idx == 4 else (Palette.CRIMSON_LIGHT if "-" in val and c_idx == 4 else Palette.TEXT_BODY)
                    surface.blit(FontManager.regular(12).render(val, True, col), (rect.x + 40 + c_idx * 155, ry))

            # Verification badge
            v_badge = "VERIFIED SAFE" if rec.verification_ok else "VERIFICATION WARNING"
            v_col = Palette.SUCCESS_GREEN if rec.verification_ok else Palette.CRIMSON_LIGHT
            surface.blit(FontManager.bold(12).render(f"STATUS: {v_badge}", True, v_col), (rect.x + 20, table_y + 155))
            surface.blit(FontManager.regular(12).render(rec.verification, True, Palette.TEXT_BODY), (rect.x + 200, table_y + 155))
        else:
            surface.blit(FontManager.regular(12).render("No autonomous turn has run yet this session. Assign mandate to begin.", True, Palette.TEXT_MUTED), (rect.x + 20, ty + 40))

    def _draw_intelligence_tab(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        t = FontManager.bold(16).render("REGIONAL INTELLIGENCE & RIVAL KINGDOMS", True, Palette.GOLD_METALLIC)
        surface.blit(t, (rect.x + 20, rect.y + 15))

        rivals = getattr(self.governor.current_enhanced_state, "rivals", []) or []
        diplomacy = getattr(self.governor.current_enhanced_state, "diplomacy", []) or []

        for idx, rival in enumerate(rivals):
            ry = rect.y + 50 + idx * 165
            pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, ry, 800, 150), border_radius=6)
            pygame.draw.rect(surface, Palette.PANEL_BORDER, (rect.x + 20, ry, 800, 150), width=1, border_radius=6)

            rel = next((d for d in diplomacy if d.rival_id == rival.id), None)
            status_str = rel.status if rel else "NEUTRAL"
            opinion_val = rel.opinion if rel else 50

            # Title
            surface.blit(FontManager.bold(15).render(f"{rival.name.upper()} — Ruler: {rival.leader}", True, Palette.GOLD_METALLIC), (rect.x + 35, ry + 12))
            surface.blit(FontManager.small(11).render(f"Personality: {rival.personality}", True, Palette.TEXT_MUTED), (rect.x + 400, ry + 15))

            # Details
            details = [
                f"Population: {rival.population} citizens",
                f"Farmland: {rival.acres} acres",
                f"Grain Reserves: {rival.bushels} bushels",
                f"Royal Treasury: {rival.treasury} gold",
                f"Soldiers Garrison: {rival.soldiers} troops",
                f"Military Power: {rival.military_strength} combat rating",
            ]

            for d_idx, d_txt in enumerate(details):
                col = d_idx % 2
                row = d_idx // 2
                surface.blit(FontManager.regular(12).render(d_txt, True, Palette.TEXT_BODY), (rect.x + 35 + col * 260, ry + 42 + row * 22))

            # Diplomatic status pill
            pill_col = Palette.SUCCESS_GREEN if status_str in ("TRADE", "ALLY") else (Palette.CRIMSON_LIGHT if status_str in ("HOSTILE", "WAR") else Palette.TEXT_TITLE)
            pygame.draw.rect(surface, Palette.SAPPHIRE_LIGHT, (rect.x + 580, ry + 40, 210, 80), border_radius=6)
            surface.blit(FontManager.bold(12).render("DIPLOMATIC STANDING:", True, Palette.TEXT_MUTED), (rect.x + 595, ry + 50))
            surface.blit(FontManager.bold(14).render(status_str, True, pill_col), (rect.x + 595, ry + 70))
            surface.blit(FontManager.regular(11).render(f"Opinion Index: {opinion_val}/100", True, Palette.TEXT_BODY), (rect.x + 595, ry + 95))

    def _draw_cognitive_log_tab(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        t = FontManager.bold(16).render("GOVERNOR REASONING & TOOL EXECUTION LOG", True, Palette.GOLD_METALLIC)
        surface.blit(t, (rect.x + 20, rect.y + 15))

        if not self.last_record:
            surface.blit(FontManager.regular(12).render("No autonomous turn has run yet. Assign a mandate to review reasoning.", True, Palette.TEXT_MUTED), (rect.x + 20, rect.y + 55))
            return

        rec = self.last_record

        # Observation Box
        y = rect.y + 45
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, y, 800, 120), border_radius=6)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (rect.x + 20, y, 800, 120), width=1, border_radius=6)
        surface.blit(FontManager.bold(12).render("1. OBSERVE & STRATEGIC MEMORY:", True, Palette.GOLD_METALLIC), (rect.x + 30, y + 8))

        obs_text = (
            f"Mandate: {rec.goal}\n"
            f"Famine Threat: {rec.disaster_check.get('famine', {}).get('level')} — {rec.disaster_check.get('famine', {}).get('detail')}\n"
            f"Tool Execution Pipeline: {' -> '.join(rec.tool_calls)}"
        )
        self._draw_multiline_text(surface, obs_text, (rect.x + 30, y + 28), 770, 12, Palette.TEXT_BODY)

        # Reasoning Box
        y += 135
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, y, 800, 240), border_radius=6)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (rect.x + 20, y, 800, 240), width=1, border_radius=6)
        surface.blit(FontManager.bold(12).render(f"2. COGNITIVE REASONING ({rec.backend_used}):", True, Palette.GOLD_METALLIC), (rect.x + 30, y + 8))
        self._draw_multiline_text(surface, rec.reasoning, (rect.x + 30, y + 30), 770, 12, Palette.TEXT_BODY)

        # Verification Box
        y += 255
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, y, 800, 110), border_radius=6)
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (rect.x + 20, y, 800, 110), width=1, border_radius=6)
        surface.blit(FontManager.bold(12).render("3. OUTCOME VERIFICATION & RESOURCE DELTAS:", True, Palette.GOLD_METALLIC), (rect.x + 30, y + 8))
        v_text = f"{rec.verification}\nReplan Status: {'Auto-Replanned to avoid constraint violation' if rec.replanned else 'Passed first-pass validation'}"
        self._draw_multiline_text(surface, v_text, (rect.x + 30, y + 30), 770, 12, Palette.TEXT_BODY)

    def _draw_chronicle_tab(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        t = FontManager.bold(16).render("CHRONICLE OF BABYLON — HISTORICAL TRENDS", True, Palette.GOLD_METALLIC)
        surface.blit(t, (rect.x + 20, rect.y + 15))

        chronicle = getattr(self.governor.current_enhanced_state, "chronicle", []) or []
        if not chronicle:
            surface.blit(FontManager.regular(12).render("The chronicle begins in Year 1. Advance turns to record history.", True, Palette.TEXT_MUTED), (rect.x + 20, rect.y + 55))
            return

        headers = ["Year", "Population", "Starved", "Immigrants", "Harvest Yield", "Rats Ate", "Bushels", "Acres"]
        table_y = rect.y + 50
        pygame.draw.rect(surface, Palette.SAPPHIRE_DARK, (rect.x + 20, table_y, 800, 35), border_radius=4)
        for h_idx, h in enumerate(headers):
            surface.blit(FontManager.bold(12).render(h, True, Palette.GOLD_METALLIC), (rect.x + 30 + h_idx * 95, table_y + 10))

        for idx, entry in enumerate(chronicle[-12:]):
            row_y = table_y + 40 + idx * 32
            vals = [
                f"Year {entry.year}",
                f"{entry.population_end}",
                f"{entry.starved}",
                f"+{entry.immigrants}",
                f"{entry.yield_rate} bu/ac",
                f"{entry.rats_ate} bu",
                f"{entry.bushels}",
                f"{entry.acres}",
            ]
            for c_idx, val in enumerate(vals):
                col = Palette.CRIMSON_LIGHT if c_idx == 2 and entry.starved > 0 else Palette.TEXT_BODY
                surface.blit(FontManager.regular(12).render(val, True, col), (rect.x + 30 + c_idx * 95, row_y + 8))

    def _draw_multiline_text(
        self,
        surface: pygame.Surface,
        text: str,
        pos: Tuple[int, int],
        max_width: int,
        font_size: int,
        color: Tuple[int, int, int],
    ) -> None:
        font = FontManager.regular(font_size)
        x, y = pos
        line_height = font.get_height() + 3

        for paragraph in text.split("\n"):
            words = paragraph.split(" ")
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    surface.blit(font.render(current_line, True, color), (x, y))
                    y += line_height
                    current_line = word
            if current_line:
                surface.blit(font.render(current_line, True, color), (x, y))
                y += line_height
