"""
ui_royal_governor.py - Visual Royal Governor Dashboard for RetroRevive.

Provides a dedicated interactive interface for the AI Royal Governor:
- Goal delegation controls (preset goals & turn duration stepper)
- Real-time display of the autonomous decision cycle
- Kingdom Comparison Dashboard (Rivals, Military, Diplomacy)
- Detailed Economic, Military, and Diplomacy reports
- Turn-by-turn delegation history
- Instant player override / revocation button
"""

from __future__ import annotations

import math
import time
from typing import Callable, List, Optional, Tuple, Dict, Any
import pygame

from game_logic import GameState
from modern_game_logic import EnhancedGameState, RivalKingdom, DiplomaticRelation
from royal_governor import ActionRecord, AgentStatus, DelegationSession, RoyalGovernor
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton


PRESET_GOALS = [
    (\"🛡️ Famine Defense\", \"Prevent famine, guarantee rations for all citizens, and maintain grain reserves.\"),
    (\"🌾 Agrarian Prosperity\", \"Maximize agricultural planting, balance grain reserves, and grow the population.\"),
    (\"⚔️ Military Superiority\", \"Recruit a strong army, build fortifications, and prepare for regional dominance.\"),
    (\"📜 Diplomatic Peace\", \"Broker trade agreements and maintain high opinions with all rival kingdoms.\"),
]


class RoyalGovernorDashboard:
    \"\"\"Interactive Pygame dashboard for delegating kingdom management to the Royal Governor.\"\"\"

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
        self.current_tab = \"LOGS\" # \"LOGS\", \"INTELLIGENCE\", \"ECONOMY\"

        # UI state
        self.status_message = \"Royal Governor standing by. Assign a mandate or execute step-by-step.\"
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
                color_scheme=\"gold\" if i == self.selected_goal_idx else \"sand\",
            )
            self.goal_buttons.append(btn)

        # Turns stepper
        self.btn_turns_minus = UIButton(
            rect=(180, 215, 36, 32),
            text=\"-\",
            callback=self._decrement_turns,
            font_size=16,
            color_scheme=\"sand\",
        )
        self.btn_turns_plus = UIButton(
            rect=(340, 215, 36, 32),
            text=\"+\",
            callback=self._increment_turns,
            font_size=16,
            color_scheme=\"sand\",
        )

        # Execution controls
        self.btn_step_turn = UIButton(
            rect=(30, 260, 350, 42),
            text=\"▶ DELEGATE 1 TURN (REASON & ACT)\",
            callback=self._delegate_single_turn,
            font_size=13,
            primary=True,
            color_scheme=\"gold\",
        )

        self.btn_run_all = UIButton(
            rect=(30, 310, 350, 42),
            text=f\"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS\",
            callback=self._delegate_all_turns,
            font_size=13,
            color_scheme=\"lapis\",
        )
        
        # Tab Controls
        self.tab_buttons = [
            UIButton(rect=(420, 110, 120, 35), text=\"ACTION LOG\", callback=lambda: self._set_tab(\"LOGS\"), font_size=11, color_scheme=\"sand\"),
            UIButton(rect=(550, 110, 140, 35), text=\"INTELLIGENCE\", callback=lambda: self._set_tab(\"INTELLIGENCE\"), font_size=11, color_scheme=\"sand\"),
            UIButton(rect=(700, 110, 130, 35), text=\"REPORTS\", callback=lambda: self._set_tab(\"REPORTS\"), font_size=11, color_scheme=\"sand\"),
        ]

        self.btn_revoke = UIButton(
            rect=(30, 360, 350, 38),
            text=\"⏹ REVOKE DELEGATION (TAKE CONTROL)\",
            callback=self._revoke_delegation,
            font_size=12,
            color_scheme=\"crimson\",
        )

        self.btn_return = UIButton(
            rect=(30, 660, 350, 38),
            text=\"↩ RETURN TO KINGDOM COMMAND\",
            callback=self._return_to_game,
            font_size=13,
            color_scheme=\"sand\",
        )

    def _set_tab(self, tab_name: str) -> None:
        self.current_tab = tab_name
        SoundSynthesizer.play(\"click\")

    def _select_goal(self, idx: int) -> None:
        self.selected_goal_idx = idx
        self.selected_goal = PRESET_GOALS[idx][1]
        for i, btn in enumerate(self.goal_buttons):
            btn.color_scheme = \"gold\" if i == idx else \"sand\"
        SoundSynthesizer.play(\"click\")

    def _increment_turns(self) -> None:
        if self.turns_to_delegate < 10:
            self.turns_to_delegate += 1
            self.btn_run_all.text = f\"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS\"
            SoundSynthesizer.play(\"click\")

    def _decrement_turns(self) -> None:
        if self.turns_to_delegate > 1:
            self.turns_to_delegate -= 1
            self.btn_run_all.text = f\"⏩ DELEGATE ALL {self.turns_to_delegate} TURNS\"
            SoundSynthesizer.play(\"click\")

    def _delegate_single_turn(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = \"Reign has ended. No further turns can be delegated.\"
            SoundSynthesizer.play(\"warning\")
            return

        SoundSynthesizer.play(\"chime\")
        session = self.governor.delegate(self.selected_goal, turns=1)
        if session.action_history:
            self.last_record = session.action_history[-1]
            self.action_history.append(self.last_record)
            st = self.governor.current_enhanced_state.classic_state
            self.status_message = f\"Year {self.last_record.game_year} executed autonomously. Kingdom in Year {st.year}.\"

    def _delegate_all_turns(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            return
        SoundSynthesizer.play(\"victory\")
        session = self.governor.delegate(self.selected_goal, turns=self.turns_to_delegate)
        self.action_history = session.action_history
        if self.action_history:
            self.last_record = self.action_history[-1]
        self.status_message = f\"Mandate complete. Royal Governor processed {session.turns_completed} turns.\"

    def _revoke_delegation(self) -> None:
        self.governor.revoke()
        self.status_message = \"Mandate revoked. You are back in full command of Babylon.\"
        SoundSynthesizer.play(\"warning\")

    def _return_to_game(self) -> None:
        self.on_return()

    def update(self, dt: float) -> None:
        for btn in self.goal_buttons: btn.update(dt)
        self.btn_turns_minus.update(dt)
        self.btn_turns_plus.update(dt)
        self.btn_step_turn.update(dt)
        self.btn_run_all.update(dt)
        self.btn_revoke.update(dt)
        self.btn_return.update(dt)
        for btn in self.tab_buttons: btn.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Background Overlay (Sapphire Glass)
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((10, 20, 40, 230))
        surface.blit(overlay, (0, 0))

        # Title
        FontManager.draw_text(surface, \"ROYAL GOVERNOR COMMAND CENTER\", (30, 30), size=32, color=Palette.GOLD, bold=True)
        FontManager.draw_text(surface, f\"Backend: {self.governor.backend_name}\", (30, 70), size=14, color=Palette.SAND)

        # --- Left Panel: Mandate Settings ---
        self._draw_settings_panel(surface)

        # --- Right Panel: Dynamic Content ---
        if self.current_tab == \"LOGS\":
            self._draw_action_logs(surface)
        elif self.current_tab == \"INTELLIGENCE\":
            self._draw_intelligence_dashboard(surface)
        elif self.current_tab == \"REPORTS\":
            self._draw_reports_dashboard(surface)

        # Global Status Bar
        pygame.draw.rect(surface, (20, 30, 50), (30, 410, 350, 40), border_radius=4)
        FontManager.draw_text(surface, self.status_message, (40, 422), size=11, color=Palette.SAND)

    def _draw_settings_panel(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (30, 40, 60), (20, 100, 370, 300), border_radius=8)
        FontManager.draw_text(surface, \"ASSIGN IMPERIAL MANDATE\", (40, 115), size=14, color=Palette.GOLD)
        for btn in self.goal_buttons: btn.draw(surface)
        
        FontManager.draw_text(surface, \"DURATION (YEARS)\", (40, 222), size=14, color=Palette.SAND)
        pygame.draw.rect(surface, (10, 20, 35), (230, 215, 100, 32), border_radius=4)
        FontManager.draw_text(surface, str(self.turns_to_delegate), (270, 222), size=18, color=Palette.GOLD)
        self.btn_turns_minus.draw(surface)
        self.btn_turns_plus.draw(surface)

        self.btn_step_turn.draw(surface)
        self.btn_run_all.draw(surface)
        self.btn_revoke.draw(surface)
        self.btn_return.draw(surface)

    def _draw_action_logs(self, surface: pygame.Surface) -> None:
        panel_rect = (410, 150, 840, 540)
        pygame.draw.rect(surface, (20, 30, 50), panel_rect, border_radius=8)
        
        for btn in self.tab_buttons: btn.draw(surface)
        
        if not self.last_record:
            FontManager.draw_text(surface, \"No history available for this session.\", (440, 180), size=14, color=Palette.GREY)
            return

        # Latest Reasoning
        FontManager.draw_text(surface, f\"YEAR {self.last_record.game_year} STRATEGIC REASONING\", (430, 170), size=16, color=Palette.GOLD)
        
        # Split text into lines
        lines = self._wrap_text(self.last_record.reasoning, 85)
        for i, line in enumerate(lines[:12]):
            FontManager.draw_text(surface, line, (430, 210 + i * 22), size=13, color=Palette.SAND)

        # Result Summary
        pygame.draw.line(surface, (40, 50, 70), (430, 480), (1220, 480))
        FontManager.draw_text(surface, \"RESOURCE DELTAS\", (430, 495), size=14, color=Palette.GOLD)
        
        x_off = 430
        for res, delta in self.last_record.resource_deltas.items():
            color = (50, 220, 100) if delta >= 0 else (220, 50, 80)
            sign = \"+\" if delta >= 0 else \"\"
            FontManager.draw_text(surface, f\"{res.upper()}: {sign}{delta}\", (x_off, 525), size=13, color=color)
            x_off += 160

    def _draw_intelligence_dashboard(self, surface: pygame.Surface) -> None:
        panel_rect = (410, 150, 840, 540)
        pygame.draw.rect(surface, (20, 30, 50), panel_rect, border_radius=8)
        for btn in self.tab_buttons: btn.draw(surface)
        
        FontManager.draw_text(surface, \"REGIONAL POWER DYNAMICS & RIVAL KINGDOMS\", (430, 170), size=18, color=Palette.GOLD)
        
        headers = [\"Kingdom\", \"Leader\", \"Personality\", \"Opinion\", \"Status\", \"Power\"]
        x_cols = [430, 560, 680, 820, 930, 1050]
        
        for i, h in enumerate(headers):
            FontManager.draw_text(surface, h, (x_cols[i], 210), size=12, color=Palette.GREY)
            
        y_off = 245
        for rival in self.governor.current_enhanced_state.rivals:
            rel = next((d for d in self.governor.current_enhanced_state.diplomacy if d.rival_id == rival.id), None)
            
            FontManager.draw_text(surface, rival.name, (x_cols[0], y_off), size=14, color=Palette.SAND)
            FontManager.draw_text(surface, rival.leader, (x_cols[1], y_off), size=14, color=Palette.SAND)
            FontManager.draw_text(surface, rival.personality, (x_cols[2], y_off), size=14, color=Palette.SAND)
            FontManager.draw_text(surface, f\"{rel.opinion}%\", (x_cols[3], y_off), size=14, color=Palette.SAND)
            
            status_color = (220, 50, 80) if rel.status in (\"WAR\", \"HOSTILE\") else (50, 220, 100) if rel.status == \"ALLY\" else Palette.SAND
            FontManager.draw_text(surface, rel.status, (x_cols[4], y_off), size=14, color=status_color)
            
            power = \"HIGH\" if rival.military_strength > 200 else \"MEDIUM\" if rival.military_strength > 100 else \"LOW\"
            FontManager.draw_text(surface, power, (x_cols[5], y_off), size=14, color=Palette.GOLD)
            
            y_off += 45
            pygame.draw.line(surface, (30, 40, 60), (430, y_off - 10), (1220, y_off - 10))

        # Military Comparison
        st = self.governor.current_enhanced_state.classic_state
        FontManager.draw_text(surface, \"MILITARY READINESS\", (430, 480), size=16, color=Palette.GOLD)
        FontManager.draw_text(surface, f\"Babylonian Army: {st.soldiers} soldiers (Strength: {st.military_strength})\", (430, 510), size=14, color=Palette.SAND)
        
        total_rival_str = sum(r.military_strength for r in self.governor.current_enhanced_state.rivals)
        avg_rival_str = total_rival_str / len(self.governor.current_enhanced_state.rivals)
        
        risk = \"SUPERIOR\" if st.military_strength > avg_rival_str * 1.2 else \"MATCHED\" if st.military_strength > avg_rival_str * 0.8 else \"VULNERABLE\"
        FontManager.draw_text(surface, f\"Strategic Assessment: {risk}\", (430, 540), size=14, color=Palette.GOLD if risk == \"SUPERIOR\" else (220, 50, 80))

    def _draw_reports_dashboard(self, surface: pygame.Surface) -> None:
        panel_rect = (410, 150, 840, 540)
        pygame.draw.rect(surface, (20, 30, 50), panel_rect, border_radius=8)
        for btn in self.tab_buttons: btn.draw(surface)
        
        st = self.governor.current_enhanced_state.classic_state
        
        # Economic Report
        FontManager.draw_text(surface, \"ECONOMIC & TREASURY REPORT\", (430, 170), size=18, color=Palette.GOLD)
        eco_data = [
            (\"Grain Reserves\", f\"{st.bushels} Bushels\"),
            (\"Land Holdings\", f\"{st.acres} Acres\"),
            (\"Land Market Price\", f\"{st.land_price} Bu/Acre\"),
            (\"Imperial Treasury\", f\"{st.treasury_gold} Gold\"),
            (\"Territory Influence\", f\"{st.territory_influence*100:.1f}%\"),
        ]
        for i, (label, val) in enumerate(eco_data):
            FontManager.draw_text(surface, label, (430, 220 + i * 35), size=14, color=Palette.GREY)
            FontManager.draw_text(surface, val, (650, 220 + i * 35), size=14, color=Palette.SAND)

        # Historical Success Rate
        pygame.draw.line(surface, (40, 50, 70), (430, 420), (1220, 420))
        FontManager.draw_text(surface, \"HISTORICAL MEMORY ANALYSIS\", (430, 440), size=16, color=Palette.GOLD)
        
        chronicle = self.governor.current_enhanced_state.chronicle
        if chronicle:
            avg_yield = sum(e.yield_rate for e in chronicle) / len(chronicle)
            FontManager.draw_text(surface, f\"Avg Harvest Yield: {avg_yield:.1f} bu/acre\", (430, 475), size=14, color=Palette.SAND)
            total_immigrants = sum(e.immigrants for e in chronicle)
            FontManager.draw_text(surface, f\"Total Immigrants During Reign: {total_immigrants}\", (430, 505), size=14, color=Palette.SAND)
        else:
            FontManager.draw_text(surface, \"Analyzing kingdom history...\", (430, 475), size=14, color=Palette.GREY)

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        words = text.split()
        lines = []
        current_line = []
        current_len = 0
        for word in words:
            if current_len + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_len += len(word) + 1
            else:
                lines.append(\" \".join(current_line))
                current_line = [word]
                current_len = len(word)
        if current_line:
            lines.append(\" \".join(current_line))
        return lines
