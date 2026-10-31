"""
ui_royal_governor.py - Visual Royal Governor Dashboard for RetroRevive.

Provides a dedicated interactive interface for the AI Royal Governor:
- Goal delegation controls (preset goals & turn duration stepper)
- Real-time display of the autonomous decision cycle:
    1. Observe (real game engine state & disaster checks)
    2. Reason & Plan (LLM or rule-based cognitive steps)
    3. Tool Calls (actual authoritative game-engine calls)
    4. Act & Execute (advance turn)
    5. Verify & Delta (before/after resource proof)
- Turn-by-turn delegation history
- Instant player override / revocation button
"""

from __future__ import annotations

import math
import time
from typing import Callable, List, Optional, Tuple
import pygame

from game_logic import GameState
from modern_game_logic import EnhancedGameState
from royal_governor import ActionRecord, AgentStatus, DelegationSession, RoyalGovernor
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton


PRESET_GOALS = [
    ("🛡️ Famine Defense", "Prevent famine, guarantee rations for all citizens, and maintain grain reserves."),
    ("🌾 Agrarian Prosperity", "Maximize agricultural planting, balance grain reserves, and grow the population."),
    ("🏛️ Imperial Expansion", "Acquire fertile land whenever market prices are cheap while maintaining zero starvation."),
    ("💰 Granary Stockpile", "Conserve grain, protect against rodent infestation, and build a multi-year food buffer."),
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

        # UI state
        self.status_message = "Royal Governor standing by. Assign a mandate or execute step-by-step."
        self.last_record: Optional[ActionRecord] = None
        self.action_history: List[ActionRecord] = []
        self.is_executing = False

        # Setup Buttons
        self._init_buttons()

    def _init_buttons(self) -> None:
        # Top goal presets (Left column top)
        self.goal_buttons = []
        for i, (label, _) in enumerate(PRESET_GOALS):
            btn = UIButton(
                rect=(30 + (i % 2) * 180, 110 + (i // 2) * 44, 172, 38),
                text=label,
                callback=lambda idx=i: self._select_goal(idx),
                font_size=12,
                color_scheme="gold" if i == self.selected_goal_idx else "sand",
            )
            self.goal_buttons.append(btn)

        # Turns stepper
        self.btn_turns_minus = UIButton(
            rect=(180, 215, 36, 32),
            text="-",
            callback=self._decrement_turns,
            font_size=16,
            color_scheme="sand",
        )
        self.btn_turns_plus = UIButton(
            rect=(340, 215, 36, 32),
            text="+",
            callback=self._increment_turns,
            font_size=16,
            color_scheme="sand",
        )

        # Execution controls
        self.btn_step_turn = UIButton(
            rect=(30, 260, 350, 42),
            text="▶ DELEGATE 1 TURN (REASON & ACT)",
            callback=self._delegate_single_turn,
            font_size=13,
            primary=True,
            color_scheme="gold",
        )

        self.btn_run_all = UIButton(
            rect=(30, 310, 350, 42),
            text=f"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS",
            callback=self._delegate_all_turns,
            font_size=13,
            color_scheme="lapis",
        )

        self.btn_revoke = UIButton(
            rect=(30, 360, 350, 38),
            text="⏹ REVOKE DELEGATION (TAKE CONTROL)",
            callback=self._revoke_delegation,
            font_size=12,
            color_scheme="crimson",
        )

        self.btn_return = UIButton(
            rect=(30, 660, 350, 38),
            text="↩ RETURN TO KINGDOM COMMAND",
            callback=self._return_to_game,
            font_size=13,
            color_scheme="sand",
        )

    def _select_goal(self, idx: int) -> None:
        self.selected_goal_idx = idx
        self.selected_goal = PRESET_GOALS[idx][1]
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

    def _delegate_single_turn(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = "Reign has ended. No further turns can be delegated."
            SoundSynthesizer.play("warning")
            return

        SoundSynthesizer.play("chime")
        session = self.governor.delegate(self.selected_goal, turns=1)
        if session.action_history:
            self.last_record = session.action_history[-1]
            self.action_history.append(self.last_record)
            st = self.governor.current_enhanced_state.classic_state
            self.status_message = f"Year {self.last_record.game_year} executed autonomously. Kingdom in Year {st.year}."
            if self.last_record.verification_ok:
                SoundSynthesizer.play("coin")
            else:
                SoundSynthesizer.play("warning")

    def _delegate_all_turns(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = "Reign has ended. No further turns can be delegated."
            SoundSynthesizer.play("warning")
            return

        SoundSynthesizer.play("gong")
        turns = self.turns_to_delegate
        session = self.governor.delegate(self.selected_goal, turns=turns)
        for rec in session.action_history:
            if rec not in self.action_history:
                self.action_history.append(rec)
        if session.action_history:
            self.last_record = session.action_history[-1]
            st = self.governor.current_enhanced_state.classic_state
            self.status_message = (
                f"Delegation completed: {session.turns_completed} turns executed. "
                f"Now Year {st.year} of 10."
            )
            SoundSynthesizer.play("harvest")

    def _revoke_delegation(self) -> None:
        self.governor.revoke()
        self.status_message = "Delegation revoked by player. Sovereign Hammurabi has taken manual command."
        SoundSynthesizer.play("warning")

    def _return_to_game(self) -> None:
        SoundSynthesizer.play("click")
        self.on_return()

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> None:
        for btn in self.goal_buttons:
            btn.handle_event(event, mouse_pos)
        self.btn_turns_minus.handle_event(event, mouse_pos)
        self.btn_turns_plus.handle_event(event, mouse_pos)
        self.btn_step_turn.handle_event(event, mouse_pos)
        self.btn_run_all.handle_event(event, mouse_pos)
        self.btn_revoke.handle_event(event, mouse_pos)
        self.btn_return.handle_event(event, mouse_pos)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                self._return_to_game()
            elif event.key == pygame.K_SPACE:
                self._delegate_single_turn()
            elif event.key == pygame.K_r:
                self._revoke_delegation()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf: pygame.Surface) -> None:
        # Deep sapphire backdrop
        surf.fill(Palette.BG_DARK)

        # Draw decorative grid / subtle backdrop lines
        for y in range(0, self.screen_h, 40):
            pygame.draw.line(surf, (15, 22, 38), (0, y), (self.screen_w, y), 1)

        # Header bar
        self._draw_header(surf)

        # 3-Column Layout:
        # Col 1: Delegation Mandate & Real Game Engine Observation (x=20 to 390)
        self._draw_col1_mandate(surf)

        # Col 2: Cognitive Reasoning & Authoritative Tool Sequence (x=410 to 830)
        self._draw_col2_reasoning(surf)

        # Col 3: Resource Deltas & Action History (x=850 to 1260)
        self._draw_col3_deltas(surf)

        # Footer toast status
        self._draw_footer(surf)

    def _draw_header(self, surf: pygame.Surface) -> None:
        # Header banner box
        hdr_rect = pygame.Rect(20, 15, self.screen_w - 40, 54)
        pygame.draw.rect(surf, Palette.PANEL_BG, hdr_rect, border_radius=6)
        pygame.draw.rect(surf, Palette.GOLD_BASE, hdr_rect, width=2, border_radius=6)

        font_title = FontManager.get_font(20, bold=True, serif=True)
        title_s = font_title.render("⚖ ROYAL GOVERNOR — AUTONOMOUS SOVEREIGN AGENT", True, Palette.GOLD_LIGHT)
        surf.blit(title_s, (36, 28))

        # Backend Badge (Honest Architecture Label)
        backend = self.governor.backend_name
        if backend == "GEMINI_LLM":
            badge_text = "● BACKEND: GOOGLE GEMINI 1.5 FLASH (TOOL-CALLING LLM)"
            badge_color = Palette.SUCCESS_GREEN
        else:
            badge_text = "● BACKEND: DETERMINISTIC RULE PLANNER (AUTHORITATIVE ENGINE)"
            badge_color = Palette.GOLD_BASE

        font_badge = FontManager.get_font(12, bold=True)
        badge_s = font_badge.render(badge_text, True, badge_color)
        surf.blit(badge_s, (self.screen_w - badge_s.get_width() - 40, 25))

        st = self.governor.current_enhanced_state.classic_state
        status_s = font_badge.render(f"YEAR {st.year} OF 10 | AGENT STATUS: {self.governor.status.value}", True, Palette.TEXT_MUTED)
        surf.blit(status_s, (self.screen_w - status_s.get_width() - 40, 43))

    def _draw_col1_mandate(self, surf: pygame.Surface) -> None:
        # Panel 1A: Delegation Mandate
        p1 = pygame.Rect(20, 78, 370, 330)
        pygame.draw.rect(surf, Palette.PANEL_BG, p1, border_radius=6)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, p1, width=1, border_radius=6)

        font_sec = FontManager.get_font(14, bold=True)
        font_sm = FontManager.get_font(11)

        lbl = font_sec.render("1. ASSIGN DELEGATION MANDATE", True, Palette.GOLD_PALE)
        surf.blit(lbl, (32, 88))

        # Goal buttons
        for btn in self.goal_buttons:
            btn.draw(surf)

        # Goal description text
        desc_rect = pygame.Rect(32, 160, 346, 46)
        pygame.draw.rect(surf, (12, 18, 32), desc_rect, border_radius=4)
        words = self.selected_goal.split(" ")
        line1 = " ".join(words[:6])
        line2 = " ".join(words[6:])
        s1 = font_sm.render(line1, True, Palette.TEXT_BODY)
        s2 = font_sm.render(line2, True, Palette.TEXT_MUTED)
        surf.blit(s1, (38, 165))
        surf.blit(s2, (38, 182))

        # Turns selector label
        lbl_turns = font_sm.render(f"Delegation Limit: {self.turns_to_delegate} Years", True, Palette.GOLD_LIGHT)
        surf.blit(lbl_turns, (32, 222))
        self.btn_turns_minus.draw(surf)
        turns_val_s = font_sec.render(f"{self.turns_to_delegate}", True, Palette.TEXT_TITLE)
        surf.blit(turns_val_s, (250, 220))
        self.btn_turns_plus.draw(surf)

        # Control buttons
        self.btn_step_turn.draw(surf)
        self.btn_run_all.draw(surf)
        self.btn_revoke.draw(surf)

        # Panel 1B: Real Game State Observations
        p2 = pygame.Rect(20, 418, 370, 230)
        pygame.draw.rect(surf, Palette.PANEL_BG, p2, border_radius=6)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, p2, width=1, border_radius=6)

        lbl2 = font_sec.render("2. REAL GAME-STATE OBSERVATIONS", True, Palette.GOLD_PALE)
        surf.blit(lbl2, (32, 428))

        st = self.governor.current_enhanced_state.classic_state
        metrics = [
            ("Current Year:", f"Year {st.year} of 10"),
            ("Living Citizens:", f"{st.population:,} people"),
            ("Grain in Silos:", f"{st.bushels:,} bushels"),
            ("Kingdom Land:", f"{st.acres:,} acres"),
            ("Land Market Price:", f"{st.land_price} bu / acre"),
            ("Last Harvest Yield:", f"{st.harvest_yield} bu / acre"),
            ("Rats Loss (Last Turn):", f"{st.rats_ate:,} bushels"),
            ("Food Security:", f"{st.bushels / max(1, st.population * 20):.2f} years of food"),
        ]

        for i, (k, v) in enumerate(metrics):
            y_pos = 452 + i * 21
            sk = font_sm.render(k, True, Palette.TEXT_MUTED)
            sv = font_sm.render(v, True, Palette.TEXT_TITLE)
            surf.blit(sk, (32, y_pos))
            surf.blit(sv, (220, y_pos))

        self.btn_return.draw(surf)

    def _draw_col2_reasoning(self, surf: pygame.Surface) -> None:
        p = pygame.Rect(405, 78, 430, 570)
        pygame.draw.rect(surf, Palette.PANEL_BG, p, border_radius=6)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, p, width=1, border_radius=6)

        font_sec = FontManager.get_font(14, bold=True)
        font_sm = FontManager.get_font(11)
        font_mono = FontManager.get_font(11)

        lbl = font_sec.render("3. REASONING & AUTHORITATIVE TOOL CALLS", True, Palette.GOLD_PALE)
        surf.blit(lbl, (420, 88))

        if self.last_record is None:
            prompt_rect = pygame.Rect(420, 115, 400, 515)
            pygame.draw.rect(surf, (12, 18, 32), prompt_rect, border_radius=4)
            msg1 = font_sm.render("No autonomous turns executed yet in this session.", True, Palette.TEXT_MUTED)
            msg2 = font_sm.render("Click [▶ DELEGATE 1 TURN] to observe the complete cycle:", True, Palette.GOLD_LIGHT)
            steps = [
                "1. Observe real game engine state & inspect threats",
                "2. Reason about resource constraints against the mandate",
                "3. Call calculate_grain_requirements() & manage_land()",
                "4. Validate proposed decrees through game rules",
                "5. Advance turn authoritative engine (step_enhanced_year)",
                "6. Verify real outcome & calculate resource deltas",
            ]
            surf.blit(msg1, (435, 140))
            surf.blit(msg2, (435, 170))
            for i, step in enumerate(steps):
                ss = font_sm.render(step, True, Palette.TEXT_BODY)
                surf.blit(ss, (445, 205 + i * 26))
            return

        rec = self.last_record

        # 1. Goal banner
        goal_s = font_sm.render(f"Mandate: {rec.goal[:45]}...", True, Palette.GOLD_LIGHT)
        surf.blit(goal_s, (420, 115))

        # 2. Reasoning Box
        box_r = pygame.Rect(420, 135, 400, 140)
        pygame.draw.rect(surf, (12, 18, 30), box_r, border_radius=4)
        pygame.draw.rect(surf, Palette.LAPIS_BASE, box_r, width=1, border_radius=4)

        box_hdr = font_sm.render("AI Cognitive Reasoning:", True, Palette.GOLD_PALE)
        surf.blit(box_hdr, (428, 140))

        lines = rec.reasoning.split("\n")
        y_text = 158
        for line in lines[:6]:
            if line.strip():
                ls = font_sm.render(line[:54], True, Palette.TEXT_BODY)
                surf.blit(ls, (428, y_text))
                y_text += 18

        # 3. Tool Calls Sequence Box
        tool_hdr = font_sec.render("Game Engine Tool Executions:", True, Palette.GOLD_PALE)
        surf.blit(tool_hdr, (420, 285))

        tool_box = pygame.Rect(420, 308, 400, 130)
        pygame.draw.rect(surf, (10, 15, 26), tool_box, border_radius=4)
        pygame.draw.rect(surf, (40, 60, 90), tool_box, width=1, border_radius=4)

        for i, tool_name in enumerate(rec.tool_calls):
            y_t = 316 + i * 20
            t_s = font_mono.render(f"[{i+1}] {tool_name}() -> AUTHORITATIVE OK", True, Palette.TURQUOISE_ACCENT)
            surf.blit(t_s, (428, y_t))

        # 4. Planned & Validated Decrees
        dec_hdr = font_sec.render("Executed Decrees (Validated):", True, Palette.GOLD_PALE)
        surf.blit(dec_hdr, (420, 448))

        dec_box = pygame.Rect(420, 470, 400, 85)
        pygame.draw.rect(surf, (12, 18, 30), dec_box, border_radius=4)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, dec_box, width=1, border_radius=4)

        p_act = rec.planned_actions
        d_lines = [
            f"• FEED CITIZENS:  {p_act.get('feed_bushels', 0):,} bushels ({p_act.get('feed_bushels', 0)//20} fed)",
            f"• CULTIVATE SEED: {p_act.get('plant_acres', 0):,} acres ({p_act.get('plant_acres', 0)//2} bu seed)",
            f"• LAND PURCHASE:  {p_act.get('buy_acres', 0):,} acres (Cost: {p_act.get('buy_acres', 0) * rec.game_year} bu)",
            f"• LAND SALE:      {p_act.get('sell_acres', 0):,} acres",
        ]
        for i, dl in enumerate(d_lines):
            ds = font_sm.render(dl, True, Palette.TEXT_TITLE)
            surf.blit(ds, (428, 477 + i * 18))

        # Replan alert if triggered
        if rec.replanned:
            rep_s = font_sm.render(f"⚠️ REPLANNED: {rec.replan_reason[:45]}", True, Palette.CRIMSON_LIGHT)
            surf.blit(rep_s, (420, 562))

    def _draw_col3_deltas(self, surf: pygame.Surface) -> None:
        p = pygame.Rect(850, 78, 410, 570)
        pygame.draw.rect(surf, Palette.PANEL_BG, p, border_radius=6)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, p, width=1, border_radius=6)

        font_sec = FontManager.get_font(14, bold=True)
        font_sm = FontManager.get_font(11)
        font_badge = FontManager.get_font(12, bold=True)

        lbl = font_sec.render("4. VERIFICATION & RESOURCE DELTAS", True, Palette.GOLD_PALE)
        surf.blit(lbl, (865, 88))

        if self.last_record is None:
            empty_r = pygame.Rect(865, 115, 380, 515)
            pygame.draw.rect(surf, (12, 18, 32), empty_r, border_radius=4)
            s_empty = font_sm.render("Awaiting first delegated turn execution...", True, Palette.TEXT_MUTED)
            surf.blit(s_empty, (880, 140))
            return

        rec = self.last_record

        # Verification Banner
        ver_col = Palette.SUCCESS_GREEN if rec.verification_ok else Palette.CRIMSON
        ver_r = pygame.Rect(865, 115, 380, 36)
        pygame.draw.rect(surf, ver_col, ver_r, border_radius=4)
        ver_label = "✅ GOAL VERIFIED: SUCCESS" if rec.verification_ok else "⚠️ GOAL VERIFIED: PARTIAL / ATTENTION"
        v_s = font_badge.render(ver_label, True, Palette.TEXT_DARK)
        surf.blit(v_s, (875, 124))

        v_detail = font_sm.render(rec.verification[:54], True, Palette.TEXT_TITLE)
        surf.blit(v_detail, (865, 156))

        # Before / After Resource Proof Table
        tbl_hdr = font_sec.render("Before / After Resource Proof:", True, Palette.GOLD_PALE)
        surf.blit(tbl_hdr, (865, 180))

        tbl_r = pygame.Rect(865, 202, 380, 115)
        pygame.draw.rect(surf, (12, 18, 30), tbl_r, border_radius=4)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, tbl_r, width=1, border_radius=4)

        cols = ["Resource", "Before", "After", "Delta"]
        x_offsets = [875, 960, 1040, 1130]
        for x, c in zip(x_offsets, cols):
            cs = font_sm.render(c, True, Palette.GOLD_LIGHT)
            surf.blit(cs, (x, 208))

        pygame.draw.line(surf, Palette.PANEL_BORDER, (865, 226), (1245, 226), 1)

        rows = [
            ("Population", rec.before_resources["population"], rec.after_resources["population"], rec.resource_deltas["population"]),
            ("Grain (bu)", rec.before_resources["bushels"], rec.after_resources["bushels"], rec.resource_deltas["bushels"]),
            ("Land (ac)", rec.before_resources["acres"], rec.after_resources["acres"], rec.resource_deltas["acres"]),
        ]

        for i, (name, bef, aft, dlt) in enumerate(rows):
            y_r = 234 + i * 24
            d_str = f"+{dlt:,}" if dlt > 0 else f"{dlt:,}"
            d_col = Palette.SUCCESS_GREEN if dlt > 0 else (Palette.CRIMSON_LIGHT if dlt < 0 else Palette.TEXT_MUTED)

            surf.blit(font_sm.render(name, True, Palette.TEXT_BODY), (x_offsets[0], y_r))
            surf.blit(font_sm.render(f"{bef:,}", True, Palette.TEXT_MUTED), (x_offsets[1], y_r))
            surf.blit(font_sm.render(f"{aft:,}", True, Palette.TEXT_TITLE), (x_offsets[2], y_r))
            surf.blit(font_sm.render(d_str, True, d_col), (x_offsets[3], y_r))

        # Event Consequences
        ev = rec.execution_result.get("events", {})
        ev_lines = [
            f"• Harvest Yield:    {ev.get('harvest_yield', 0)} bu/ac (Total: {ev.get('total_harvested', 0):,} bu)",
            f"• Grain Eaten by Rats: {ev.get('grain_eaten_by_rats', 0):,} bu",
            f"• Immigrants Arrived:  +{ev.get('immigrants_arrived', 0):,} newcomers",
            f"• Starvation Deaths:   {ev.get('starved_this_year', 0):,} citizens",
        ]
        for i, el in enumerate(ev_lines):
            surf.blit(font_sm.render(el, True, Palette.TEXT_BODY), (865, 328 + i * 19))

        # Turn History Log (Bottom)
        hist_hdr = font_sec.render(f"Delegation Chronicle ({len(self.action_history)} Turns):", True, Palette.GOLD_PALE)
        surf.blit(hist_hdr, (865, 415))

        hist_box = pygame.Rect(865, 436, 380, 200)
        pygame.draw.rect(surf, (10, 15, 26), hist_box, border_radius=4)
        pygame.draw.rect(surf, (40, 60, 90), hist_box, width=1, border_radius=4)

        for i, item in enumerate(self.action_history[-7:]):
            y_h = 444 + i * 26
            act = item.planned_actions
            h_str = (
                f"Y{item.game_year}: Feed={act.get('feed_bushels', 0):,} Plant={act.get('plant_acres', 0):,} "
                f"-> Pop:{item.after_resources['population']} Grain:{item.after_resources['bushels']:,}"
            )
            surf.blit(font_sm.render(h_str, True, Palette.TEXT_BODY), (875, y_h))

    def _draw_footer(self, surf: pygame.Surface) -> None:
        ftr_rect = pygame.Rect(20, 656, self.screen_w - 40, 48)
        pygame.draw.rect(surf, (12, 18, 30), ftr_rect, border_radius=4)
        pygame.draw.rect(surf, Palette.PANEL_BORDER, ftr_rect, width=1, border_radius=4)

        font_sm = FontManager.get_font(12)
        s_msg = font_sm.render(f"STATUS: {self.status_message}", True, Palette.GOLD_PALE)
        surf.blit(s_msg, (400, 672))

        font_hint = FontManager.get_font(11)
        h_msg = font_hint.render("[Space] Delegate 1 Turn | [R] Revoke Control | [Esc] Kingdom Menu", True, Palette.TEXT_MUTED)
        surf.blit(h_msg, (self.screen_w - h_msg.get_width() - 40, 672))
