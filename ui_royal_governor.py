\"\"\"
ui_royal_governor.py - Visual Royal Governor Dashboard for RetroRevive.

Provides a dedicated interactive interface for the AI Royal Governor:
- Goal delegation controls (preset goals & custom mandate input)
- Multi-tab view: Action Logs, Kingdom Intelligence, and Imperial Reports
- Real-time display of the autonomous decision cycle and reasoning
- Kingdom Comparison Dashboard (Rivals, Military, Diplomacy)
- Instant player override / revocation button
\"\"\"

from __future__ import annotations

import math
import time
from typing import Callable, List, Optional, Tuple, Dict, Any
import pygame

from game_logic import GameState
from modern_game_logic import EnhancedGameState, RivalKingdom, DiplomaticRelation
from royal_governor import ActionRecord, AgentStatus, DelegationSession, RoyalGovernor
from ui_theme import FontManager, Palette, SoundSynthesizer, UIButton, UITextInput


PRESET_GOALS = [
    (\"🛡️ Famine Defense\", \"Prevent famine, guarantee rations, and maintain grain reserves.\"),
    (\"🌾 Agrarian Prosperity\", \"Maximize agricultural planting and grow the population.\"),
    (\"⚔️ Military Superiority\", \"Recruit a strong army and prepare for regional dominance.\"),
    (\"📜 Diplomatic Peace\", \"Broker trade agreements and maintain high opinions with rivals.\"),
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
        self.current_tab = \"LOGS\" # \"LOGS\", \"INTELLIGENCE\", \"REPORTS\"

        # UI state
        self.status_message = \"Royal Governor standing by. Assign a mandate or execute step-by-step.\"
        self.last_record: Optional[ActionRecord] = None
        self.action_history: List[ActionRecord] = []
        self.is_executing = False

        # Setup Components
        self._init_buttons()
        self.custom_mandate_input = UITextInput(
            rect=(40, 480, 350, 42),
            placeholder=\"Type a custom mandate for the King...\",
            font_size=13
        )

    def _init_buttons(self) -> None:
        # Top goal presets
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
            rect=(30, 365, 350, 38),
            text=\"⏹ REVOKE DELEGATION\",
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

    def _delegate_single_turn(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            self.status_message = \"Reign has ended. No further turns can be delegated.\"
            SoundSynthesizer.play(\"warning\")
            return

        SoundSynthesizer.play(\"chime\")
        goal = self.custom_mandate_input.text or self.selected_goal
        session = self.governor.delegate(goal, turns=1)
        if session.action_history:
            self.last_record = session.action_history[-1]
            self.action_history.append(self.last_record)
            st = self.governor.current_enhanced_state.classic_state
            self.status_message = f\"Year {self.last_record.game_year} executed autonomously. Kingdom in Year {st.year}.\"

    def _delegate_all_turns(self) -> None:
        if self.governor.current_enhanced_state.classic_state.is_over:
            return
        SoundSynthesizer.play(\"victory\")
        goal = self.custom_mandate_input.text or self.selected_goal
        session = self.governor.delegate(goal, turns=self.turns_to_delegate)
        self.action_history = session.action_history
        if self.action_history:
            self.last_record = self.action_history[-1]
        self.status_message = f\"Mandate complete. Royal Governor processed {session.turns_completed} turns.\"

    def _revoke_delegation(self) -> None:
        self.governor.revoke()
        self.status_message = \"Mandate revoked. You are back in command.\"
        SoundSynthesizer.play(\"warning\")

    def _return_to_game(self) -> None:
        self.on_return()

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if self.custom_mandate_input.handle_event(event, mouse_pos): return True
        for btn in self.goal_buttons: 
            if btn.handle_event(event, mouse_pos): return True
        for btn in self.tab_buttons:
            if btn.handle_event(event, mouse_pos): return True
        if self.btn_step_turn.handle_event(event, mouse_pos): return True
        if self.btn_run_all.handle_event(event, mouse_pos): return True
        if self.btn_revoke.handle_event(event, mouse_pos): return True
        if self.btn_return.handle_event(event, mouse_pos): return True
        return False

    def update(self, dt: float) -> None:
        self.custom_mandate_input.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Background Overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((10, 20, 40, 235))
        surface.blit(overlay, (0, 0))

        # Title
        FontManager.draw_text(surface, \"ROYAL GOVERNOR COMMAND CENTER\", (30, 30), size=32, color=Palette.GOLD, bold=True)
        FontManager.draw_text(surface, f\"Intelligence Mode: {self.governor.backend_name}\", (30, 75), size=14, color=Palette.SAND)

        # Settings Panel
        pygame.draw.rect(surface, (30, 40, 60), (20, 100, 370, 520), border_radius=8)
        FontManager.draw_text(surface, \"ASSIGN IMPERIAL MANDATE\", (40, 115), size=14, color=Palette.GOLD)
        for btn in self.goal_buttons: btn.draw(surface)
        self.btn_step_turn.draw(surface)
        self.btn_run_all.draw(surface)
        self.btn_revoke.draw(surface)
        
        FontManager.draw_text(surface, \"DIRECT KING'S COMMAND\", (40, 450), size=14, color=Palette.GOLD)
        self.custom_mandate_input.draw(surface)

        # Tab Content
        panel_rect = (410, 150, 840, 540)
        pygame.draw.rect(surface, (20, 30, 50), panel_rect, border_radius=8)
        for btn in self.tab_buttons: btn.draw(surface)
        
        if self.current_tab == \"LOGS\":
            self._draw_action_logs(surface)
        elif self.current_tab == \"INTELLIGENCE\":
            self._draw_intelligence(surface)
        elif self.current_tab == \"REPORTS\":
            self._draw_reports(surface)

        self.btn_return.draw(surface)
        pygame.draw.rect(surface, (20, 30, 50), (30, 415, 350, 2), border_radius=1)

    def _draw_action_logs(self, surface: pygame.Surface) -> None:
        if not self.last_record:
            FontManager.draw_text(surface, \"No history available for this session.\", (440, 180), size=14, color=Palette.TEXT_MUTED)
            return

        FontManager.draw_text(surface, f\"YEAR {self.last_record.game_year} STRATEGIC REASONING\", (430, 170), size=18, color=Palette.GOLD)
        
        # Reasoning text (simplified wrapping)
        text = self.last_record.reasoning
        words = text.split()
        lines = []
        curr = \"\"
        for w in words:
            if len(curr) + len(w) < 80: curr += w + \" \"
            else: lines.append(curr); curr = w + \" \"
        lines.append(curr)
        
        for i, line in enumerate(lines[:12]):
            FontManager.draw_text(surface, line, (430, 210 + i * 22), size=13, color=Palette.SAND_LIGHT)

    def _draw_intelligence(self, surface: pygame.Surface) -> None:
        FontManager.draw_text(surface, \"REGIONAL POWER DYNAMICS\", (430, 170), size=18, color=Palette.GOLD)
        y = 210
        for r in self.governor.current_enhanced_state.rivals:
            pygame.draw.rect(surface, (30, 45, 70), (430, y, 800, 40), border_radius=4)
            FontManager.draw_text(surface, f\"{r.name:15} | Leader: {r.leader:15} | Army Strength: {r.military_strength:5}\", (440, y + 10), size=14, color=Palette.SAND)
            y += 50
            
        st = self.governor.current_enhanced_state.classic_state
        FontManager.draw_text(surface, f\"Babylonian Military Rating: {st.military_strength}\", (430, 480), size=16, color=Palette.GOLD)

    def _draw_reports(self, surface: pygame.Surface) -> None:
        FontManager.draw_text(surface, \"IMPERIAL STATE REPORTS\", (430, 170), size=18, color=Palette.GOLD)
        st = self.governor.current_enhanced_state.classic_state
        
        metrics = [
            (\"Treasury Gold\", str(st.treasury_gold)),
            (\"Standing Army\", str(st.soldiers) + \" Units\"),
            (\"Territory Reach\", f\"{st.territory_influence*100:.1f}%\"),
            (\"Grain Reserves\", str(st.bushels) + \" Bushels\")
        ]
        
        for i, (label, val) in enumerate(metrics):
            FontManager.draw_text(surface, label, (430, 220 + i * 35), size=15, color=Palette.SAND)
            FontManager.draw_text(surface, val, (650, 220 + i * 35), size=15, color=Palette.GOLD_LIGHT)
