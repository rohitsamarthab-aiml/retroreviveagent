\"\"\"
ui_royal_governor.py - Visual Royal Governor Dashboard for RetroRevive.
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
    def __init__(self, governor, on_return, screen_w=1280, screen_h=720):
        self.governor = governor
        self.on_return = on_return
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.selected_goal_idx = 0
        self.selected_goal = PRESET_GOALS[0][1]
        self.turns_to_delegate = 3
        self.current_tab = \"LOGS\"

        self.status_message = \"Royal Governor standing by. Assign a mandate or execute step-by-step.\"
        self.last_record = None
        self.action_history = []
        
        self._init_buttons()
        self.custom_mandate_input = UITextInput(rect=(40, 480, 350, 42), placeholder=\"Type a custom mandate...\", font_size=13)

    def _init_buttons(self) -> None:
        self.goal_buttons = [UIButton((30 + (i % 2) * 180, 110 + (i // 2) * 44, 172, 38), label, lambda idx=i: self._select_goal(idx), 12) for i, (label, _) in enumerate(PRESET_GOALS)]
        
        self.btn_minus = UIButton((230, 215, 36, 32), \"-\", self._dec_turns, 16)
        self.btn_plus = UIButton((340, 215, 36, 32), \"+\", self._inc_turns, 16)

        self.btn_step = UIButton((30, 260, 350, 42), \"▶ DELEGATE 1 TURN\", self._delegate_single_turn, 13)
        self.btn_run = UIButton((30, 310, 350, 42), \"⏩ DELEGATE ALL TURNS\", self._delegate_all_turns, 13)
        
        self.tab_buttons = [
            UIButton(rect=(420, 110, 120, 35), text=\"LOGS\", callback=lambda: self._set_tab(\"LOGS\"), font_size=11),
            UIButton(rect=(550, 110, 140, 35), text=\"INTELLIGENCE\", callback=lambda: self._set_tab(\"INTELLIGENCE\"), font_size=11),
            UIButton(rect=(700, 110, 130, 35), text=\"REPORTS\", callback=lambda: self._set_tab(\"REPORTS\"), font_size=11),
        ]

        self.btn_revoke = UIButton((30, 365, 350, 38), \"⏹ REVOKE DELEGATION\", self._revoke, 12)
        self.btn_return = UIButton((30, 660, 350, 38), \"↩ RETURN\", self.on_return, 13)

    def _inc_turns(self): self.turns_to_delegate = min(10, self.turns_to_delegate + 1)
    def _dec_turns(self): self.turns_to_delegate = max(1, self.turns_to_delegate - 1)
    def _select_goal(self, idx): self.selected_goal_idx = idx; self.selected_goal = PRESET_GOALS[idx][1]
    def _set_tab(self, tab): self.current_tab = tab
    def _revoke(self): self.governor.revoke(); self.status_message = \"Mandate revoked.\"
    
    def _delegate_single_turn(self):
        goal = self.custom_mandate_input.text or self.selected_goal
        session = self.governor.delegate(goal, 1)
        if session.action_history: self.last_record = session.action_history[-1]; self.action_history.append(self.last_record)

    def _delegate_all_turns(self):
        goal = self.custom_mandate_input.text or self.selected_goal
        session = self.governor.delegate(goal, self.turns_to_delegate)
        if session.action_history: self.last_record = session.action_history[-1]; self.action_history = session.action_history

    def handle_event(self, event, mouse_pos) -> bool:
        if self.custom_mandate_input.handle_event(event, mouse_pos): return True
        for b in self.goal_buttons + [self.btn_minus, self.btn_plus, self.btn_step, self.btn_run, self.btn_revoke, self.btn_return] + self.tab_buttons:
            if b.handle_event(event, mouse_pos): return True
        return False

    def update(self, dt): self.custom_mandate_input.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA); overlay.fill((10, 20, 40, 235)); surface.blit(overlay, (0, 0))
        FontManager.draw_text(surface, \"ROYAL GOVERNOR COMMAND CENTER\", (30, 30), 32, Palette.GOLD, True)
        
        pygame.draw.rect(surface, (30, 40, 60), (20, 100, 370, 520), border_radius=8)
        FontManager.draw_text(surface, \"ASSIGN IMPERIAL MANDATE\", (40, 115), 14, Palette.GOLD)
        for b in self.goal_buttons: b.draw(surface)
        
        FontManager.draw_text(surface, \"DURATION (YEARS)\", (40, 222), 14, Palette.SAND)
        pygame.draw.rect(surface, (10, 20, 35), (275, 215, 60, 32), border_radius=4)
        FontManager.draw_text(surface, str(self.turns_to_delegate), (295, 222), 18, Palette.GOLD)
        self.btn_minus.draw(surface); self.btn_plus.draw(surface); self.btn_step.draw(surface); self.btn_run.draw(surface); self.btn_revoke.draw(surface); self.btn_return.draw(surface)
        
        FontManager.draw_text(surface, \"DIRECT COMMAND\", (40, 450), 14, Palette.GOLD); self.custom_mandate_input.draw(surface)

        panel_rect = (410, 150, 840, 540)
        pygame.draw.rect(surface, (20, 30, 50), panel_rect, border_radius=8)
        for b in self.tab_buttons: b.draw(surface)
        
        if self.current_tab == \"LOGS\": self._draw_logs(surface)
        elif self.current_tab == \"INTELLIGENCE\": self._draw_intel(surface)
        elif self.current_tab == \"REPORTS\": self._draw_reports(surface)

    def _draw_logs(self, surface):
        if not self.last_record: return
        FontManager.draw_text(surface, f\"YEAR {self.last_record.game_year} STRATEGIC REASONING\", (430, 170), 18, Palette.GOLD)
        FontManager.draw_text(surface, self.last_record.reasoning[:100] + \"...\", (430, 210), 13, Palette.SAND_LIGHT)

    def _draw_intel(self, surface):
        FontManager.draw_text(surface, \"REGIONAL POWER DYNAMICS\", (430, 170), 18, Palette.GOLD)
        y = 210
        for r in self.governor.current_enhanced_state.rivals:
            pygame.draw.rect(surface, (30, 45, 70), (430, y, 800, 40), border_radius=4)
            FontManager.draw_text(surface, f\"{r.name:15} | Army Strength: {r.military_strength:5}\", (440, y + 10), 14, Palette.SAND)
            y += 50

    def _draw_reports(self, surface):
        FontManager.draw_text(surface, \"IMPERIAL STATE REPORTS\", (430, 170), 18, Palette.GOLD)
        st = self.governor.current_enhanced_state.classic_state
        metrics = [(\"Treasury\", str(st.treasury_gold)), (\"Army\", str(st.soldiers)), (\"Grain\", str(st.bushels))]
        for i, (l, v) in enumerate(metrics):
            FontManager.draw_text(surface, l, (430, 220 + i * 35), 15, Palette.SAND)
            FontManager.draw_text(surface, v, (650, 220 + i * 35), 15, Palette.GOLD_LIGHT)
