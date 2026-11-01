"""
ui_royal_governor.py - Visual Royal Governor Dashboard with direct interaction.
"""
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
    ("🛡️ Famine Defense", "Prevent famine and maintain grain reserves."),
    ("🌾 Agrarian Prosperity", "Maximize planting and grow population."),
    ("⚔️ Military Superiority", "Recruit army and prepare for dominance."),
    ("📜 Diplomatic Peace", "Broker trade and maintain alliances."),
]

class RoyalGovernorDashboard:
    def __init__(self, governor, on_return, screen_w=1280, screen_h=720):
        self.governor, self.on_return, self.screen_w, self.screen_h = governor, on_return, screen_w, screen_h
        self.selected_goal, self.turns_to_delegate, self.current_tab = PRESET_GOALS[0][1], 3, "LOGS"
        self.status_message, self.last_record, self.action_history = "Standing by.", None, []
        self._init_buttons()
        self.custom_mandate_input = UITextInput(rect=(40, 460, 350, 40), placeholder="Type custom mandate...")
    def _init_buttons(self):
        self.goal_buttons = [UIButton((30+(i%2)*180, 110+(i//2)*44, 172, 38), label, lambda idx=i: self._select_goal(idx), 12) for i, (label, _) in enumerate(PRESET_GOALS)]
        self.btn_step = UIButton((30, 260, 350, 42), "▶ DELEGATE 1 TURN", self._delegate_single_turn, 13)
        self.tab_buttons = [UIButton((420, 110, 120, 35), "LOGS", lambda: self._set_tab("LOGS"), 11), UIButton((550, 110, 140, 35), "INTEL", lambda: self._set_tab("INTELLIGENCE"), 11), UIButton((700, 110, 130, 35), "REPORTS", lambda: self._set_tab("REPORTS"), 11)]
        self.btn_return = UIButton((30, 660, 350, 38), "↩ RETURN", self.on_return, 13)
    def _select_goal(self, idx): self.selected_goal = PRESET_GOALS[idx][1]
    def _set_tab(self, tab): self.current_tab = tab
    def _delegate_single_turn(self):
        goal = self.custom_mandate_input.text or self.selected_goal
        session = self.governor.delegate(goal, 1)
        if session.action_history: self.last_record = session.action_history[-1]; self.action_history.append(self.last_record)
    def handle_event(self, event, mouse_pos):
        if self.custom_mandate_input.handle_event(event, mouse_pos): return True
        for b in self.goal_buttons + [self.btn_step, self.btn_return] + self.tab_buttons:
            if b.handle_event(event, mouse_pos): return True
        return False
    def update(self, dt): self.custom_mandate_input.update(dt)
    def draw(self, surf):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA); overlay.fill((10, 20, 40, 230)); surf.blit(overlay, (0, 0))
        FontManager.draw_text(surf, "ROYAL GOVERNOR COMMAND CENTER", (30, 30), 32, Palette.GOLD, True)
        pygame.draw.rect(surf, (30, 40, 60), (20, 100, 370, 520), border_radius=8)
        for b in self.goal_buttons + [self.btn_step, self.btn_return] + self.tab_buttons: b.draw(surf)
        self.custom_mandate_input.draw(surf)
        if self.current_tab == "LOGS": self._draw_logs(surf)
        elif self.current_tab == "INTELLIGENCE": self._draw_intel(surf)
        elif self.current_tab == "REPORTS": self._draw_reports(surf)
    def _draw_logs(self, surf):
        if self.last_record: FontManager.draw_text(surf, f"REASONING: {self.last_record.reasoning[:100]}...", (430, 170), 16, Palette.GOLD)
    def _draw_intel(self, surf):
        y = 200
        for r in self.governor.current_enhanced_state.rivals:
            FontManager.draw_text(surf, f"{r.name}: {r.personality} | Power: {r.military_strength}", (430, y), 14, Palette.SAND)
            y += 40
    def _draw_reports(self, surf):
        st = self.governor.current_enhanced_state.classic_state
        FontManager.draw_text(surf, f"Treasury: {st.treasury_gold} | Soldiers: {st.soldiers}", (430, 170), 16, Palette.GOLD)
