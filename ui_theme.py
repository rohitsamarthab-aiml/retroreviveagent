"""
ui_theme.py - Design system and widgets.
"""
import math
import struct
from typing import Callable, List, Optional, Tuple
import pygame
from game_logic import GameState

class Palette:
    SAPPHIRE_DARK, SAPPHIRE_BASE, SAPPHIRE_PANEL, SAPPHIRE_GLASS = (10, 16, 28), (16, 26, 46), (15, 25, 45, 235), (12, 20, 36, 220)
    SAND_LIGHT, SAND_BASE, SAND_DARK, GOLD_BASE, GOLD_LIGHT, GOLD_PALE = (235, 218, 185), (210, 185, 145), (165, 135, 95), (212, 175, 55), (242, 210, 105), (255, 242, 185)
    PANEL_BG, PANEL_BORDER, TEXT_TITLE, TEXT_BODY, TEXT_MUTED, FOCUS_RING = (16, 26, 46), (185, 150, 75), (255, 245, 225), (235, 225, 210), (165, 175, 195), (242, 210, 105)

class FontManager:
    _cache = {}
    @classmethod
    def get_font(cls, size, bold=False):
        if (size, bold) not in cls._cache: cls._cache[(size, bold)] = pygame.font.SysFont("arial", size, bold=bold)
        return cls._cache[(size, bold)]
    @classmethod
    def header(cls, size=24): return cls.get_font(size, True)
    @classmethod
    def body(cls, size=18): return cls.get_font(size, False)
    @classmethod
    def small(cls, size=14): return cls.get_font(size, False)
    @classmethod
    def draw_text(cls, surf, text, pos, size=18, color=(255,255,255), bold=False):
        s = cls.get_font(size, bold).render(text, True, color); surf.blit(s, pos)

class SoundSynthesizer:
    @classmethod
    def init(cls): pygame.mixer.init()
    @classmethod
    def play(cls, sound_id): pass

class UIButton:
    def __init__(self, rect, text, callback, font_size=18, color_scheme="sand"):
        self.rect, self.text, self.callback, self.font_size, self.color_scheme = pygame.Rect(rect), text, callback, font_size, color_scheme
        self.is_hovered = False
    def handle_event(self, event, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            if self.callback: self.callback(); return True
        return False
    def update(self, dt): pass
    def draw(self, surf):
        col = Palette.GOLD_LIGHT if self.is_hovered else Palette.SAND_BASE
        pygame.draw.rect(surf, col, self.rect, border_radius=6)
        FontManager.draw_text(surf, self.text, (self.rect.x+10, self.rect.y+5), self.font_size, Palette.PANEL_BG, True)

class UITextInput:
    def __init__(self, rect, placeholder="", font_size=14):
        self.rect, self.text, self.placeholder, self.font_size = pygame.Rect(rect), "", placeholder, font_size
        self.active = False
    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN: self.active = self.rect.collidepoint(mouse_pos); return self.active
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE: self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN: self.active = False
            else: self.text += event.unicode
            return True
        return False
    def update(self, dt): pass
    def draw(self, surf):
        pygame.draw.rect(surf, (10, 15, 30), self.rect, border_radius=4)
        col = Palette.FOCUS_RING if self.active else Palette.PANEL_BORDER
        pygame.draw.rect(surf, col, self.rect, width=1, border_radius=4)
        txt = self.text if self.text or self.active else self.placeholder
        FontManager.draw_text(surf, txt, (self.rect.x+8, self.rect.y+8), self.font_size, Palette.TEXT_BODY)

class UIModal:
    def __init__(self, w, h, title): self.rect = pygame.Rect((1280-w)//2, (720-h)//2, w, h); self.title = title
    def draw_base(self, surf): pygame.draw.rect(surf, Palette.SAPPHIRE_PANEL, self.rect, border_radius=12)

class UIToast:
    def __init__(self, text): self.text = text; self.is_active = True
    def update(self, dt): pass
    def draw(self, surf): pass
