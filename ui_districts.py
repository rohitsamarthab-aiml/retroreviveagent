"""
ui_districts.py - Interactive Kingdom Districts & World Navigation for RetroRevive.

Provides 7 inspectable Babylonian civilization districts:
1. Royal Palace - Issue decrees, review annual reports, audience with Grand Vizier
2. Granary Silos - Grain reserves, rat vermin losses, food rationing
3. Agricultural Lands - Sowing acres, crop yields, labor capacity
4. Marketplace - Land prices, buying/selling land, treasury balance
5. City Gates - Population, immigration from Mesopotamia, defense
6. Temple District - Ziggurat ceremonies, sky atmosphere, divine blessings
7. Royal Archives - 10-year chronicles, legal code stele, historical records

Features smooth camera panning, interactive world pins with pulse animations,
and context-sensitive gameplay linkages.
"""

import math
from typing import Callable, Dict, List, Optional, Tuple
import pygame

from game_logic import GameState
from ui_theme import FontManager, Palette, SoundSynthesizer


class District:
    """Represents an interactive Babylonian kingdom location."""

    def __init__(
        self,
        district_id: str,
        name: str,
        subtitle: str,
        icon: str,
        world_x: int,
        world_y: int,
        camera_target: Tuple[int, int],
        description: str,
        hotkey: str,
    ) -> None:
        self.district_id = district_id
        self.name = name
        self.subtitle = subtitle
        self.icon = icon
        self.world_x = world_x
        self.world_y = world_y
        self.camera_target = camera_target
        self.description = description
        self.hotkey = hotkey

    def get_status(self, state: Optional[GameState]) -> List[Tuple[str, str, Tuple[int, int, int]]]:
        """Returns key-value status lines and alert color based on current simulation state."""
        if not state:
            return [("Status", "Awaiting Royal Reign", Palette.SAND_LIGHT)]

        if self.district_id == "palace":
            cond = "PROSPEROUS" if (state.starved_this_year == 0 and state.harvest_yield >= 3) else (
                "CRITICAL FAMINE" if state.starved_this_year > 0 else "STABLE"
            )
            col = Palette.SUCCESS_GREEN if cond == "PROSPEROUS" else (Palette.CRIMSON_LIGHT if cond == "CRITICAL FAMINE" else Palette.GOLD_LIGHT)
            return [
                ("Condition", cond, col),
                ("Year of Rule", f"{state.year} of 10", Palette.TEXT_TITLE),
                ("Annual Starvation", f"{state.starved_this_year} citizens", Palette.CRIMSON_LIGHT if state.starved_this_year > 0 else Palette.SUCCESS_GREEN),
            ]

        elif self.district_id == "granary":
            rat_col = Palette.CRIMSON_LIGHT if state.rats_ate > 0 else Palette.TEXT_MUTED
            return [
                ("Grain Reserves", f"{state.bushels:,} bushels", Palette.GOLD_LIGHT),
                ("Vermin Losses", f"-{state.rats_ate:,} bu eaten", rat_col),
                ("Silo Capacity", "Secure Mudbrick Vaults", Palette.SAND_LIGHT),
            ]

        elif self.district_id == "farmland":
            y_col = Palette.SUCCESS_GREEN if state.harvest_yield >= 4 else (Palette.CRIMSON_LIGHT if state.harvest_yield <= 1 else Palette.GOLD_LIGHT)
            return [
                ("Last Yield", f"{state.harvest_yield} bu/acre", y_col),
                ("Total Estate", f"{state.acres:,} acres", Palette.TEXT_TITLE),
                ("Labor Ceiling", f"{state.population * 10:,} acres max", Palette.SAND_LIGHT),
            ]

        elif self.district_id == "market":
            p_rating = "BARGAIN" if state.land_price <= 18 else ("EXPENSIVE" if state.land_price >= 24 else "FAIR")
            p_col = Palette.SUCCESS_GREEN if p_rating == "BARGAIN" else (Palette.AMBER_WARN if p_rating == "EXPENSIVE" else Palette.GOLD_LIGHT)
            return [
                ("Land Price", f"{state.land_price} bu/acre", p_col),
                ("Market Trend", p_rating, p_col),
                ("Affordable Land", f"{state.bushels // max(1, state.land_price):,} acres", Palette.TEXT_TITLE),
            ]

        elif self.district_id == "gates":
            return [
                ("Population", f"{state.population:,} citizens", Palette.TEXT_TITLE),
                ("New Arrivals", f"+{state.immigrants_this_year} newcomers", Palette.SUCCESS_GREEN),
                ("Gate Order", "Guards at Post", Palette.SAND_LIGHT),
            ]

        elif self.district_id == "temple":
            plague_str = "PLAGUE BLESSINGS SOUGHT" if state.plague_struck else "FAVORED BY SHAMASH"
            p_col = Palette.CRIMSON_LIGHT if state.plague_struck else Palette.GOLD_LIGHT
            return [
                ("Sanctuary", "Etemenanki High Altar", Palette.GOLD_PALE),
                ("Omen", plague_str, p_col),
                ("Brazier Fires", "Burning Sacred Embers", Palette.SAND_LIGHT),
            ]

        elif self.district_id == "archives":
            return [
                ("Royal Codices", "Laws of Hammurabi", Palette.GOLD_LIGHT),
                ("Chronicle Years", f"{state.year - 1} recorded", Palette.TEXT_TITLE),
                ("Historical Scribe", "Tablet Baked in Clay", Palette.SAND_LIGHT),
            ]

        return []


class DistrictManager:
    """Manages Babylonian districts, pins, camera transitions, and interaction."""

    def __init__(self) -> None:
        self.districts: List[District] = [
            District(
                district_id="palace",
                name="Royal Palace",
                subtitle="Throne Room & Decrees",
                icon="PALACE",
                world_x=640,
                world_y=310,
                camera_target=(640, 310),
                description="The seat of King Hammurabi. Issue annual proclamations and review ministerial reports.",
                hotkey="1",
            ),
            District(
                district_id="granary",
                name="Granary Silos",
                subtitle="Food Reserves & Storage",
                icon="GRANARY",
                world_x=280,
                world_y=420,
                camera_target=(320, 420),
                description="Mud-brick grain vaults along the riverbank. Monitor grain stock and rat infestations.",
                hotkey="2",
            ),
            District(
                district_id="farmland",
                name="Farmland District",
                subtitle="Plains & Irrigation",
                icon="FARMLAND",
                world_x=980,
                world_y=510,
                camera_target=(940, 500),
                description="Fertile Euphrates silt fields. Order sowing and inspect crop cultivation and labor.",
                hotkey="3",
            ),
            District(
                district_id="market",
                name="Marketplace",
                subtitle="Bazaar & Land Deeds",
                icon="MARKET",
                world_x=490,
                world_y=480,
                camera_target=(500, 470),
                description="Bustling waterfront market where land deeds are bartered for bushels of grain.",
                hotkey="4",
            ),
            District(
                district_id="gates",
                name="Ishtar Gates",
                subtitle="City Fortifications & Entry",
                icon="GATES",
                world_x=1120,
                world_y=390,
                camera_target=(1080, 400),
                description="Glazed blue lapis-brick gateway through which travellers, merchants, and newcomers enter.",
                hotkey="5",
            ),
            District(
                district_id="temple",
                name="Temple District",
                subtitle="Ziggurat Summit & Omens",
                icon="TEMPLE",
                world_x=835,
                world_y=140,
                camera_target=(835, 180),
                description="The monumental stepped Ziggurat. Sacred braziers burn in honor of Shamash and Marduk.",
                hotkey="6",
            ),
            District(
                district_id="archives",
                name="Royal Archives",
                subtitle="Scribe Stele & Chronicle",
                icon="ARCHIVES",
                world_x=530,
                world_y=320,
                camera_target=(550, 320),
                description="The cuneiform library preserving year-by-year chronicles and the royal code.",
                hotkey="7",
            ),
        ]

        self.district_by_id: Dict[str, District] = {d.district_id: d for d in self.districts}
        self.selected_district: Optional[District] = None
        self.hovered_district: Optional[District] = None

        # Camera Lerp System
        self.camera_x: float = 0.0
        self.camera_y: float = 0.0
        self.target_camera_x: float = 0.0
        self.target_camera_y: float = 0.0

        # Animation Pulse
        self.pulse_timer: float = 0.0

        # Dock Tab Rectangles for Hit Detection
        self.dock_rects: Dict[str, pygame.Rect] = {}

    def select_district(self, district_id: Optional[str]) -> None:
        """Selects a district and initiates smooth camera focus."""
        if not district_id:
            self.selected_district = None
            self.target_camera_x = 0.0
            self.target_camera_y = 0.0
            return

        if district_id in self.district_by_id:
            self.selected_district = self.district_by_id[district_id]
            tx, ty = self.selected_district.camera_target
            # Subtle pan offset
            self.target_camera_x = (640 - tx) * 0.12
            self.target_camera_y = (360 - ty) * 0.12
            SoundSynthesizer.play("click")

    def update(self, dt: float) -> None:
        """Updates camera lerp and pulse timer."""
        self.pulse_timer += dt * 3.0
        lerp_speed = 6.0 * dt
        self.camera_x += (self.target_camera_x - self.camera_x) * lerp_speed
        self.camera_y += (self.target_camera_y - self.camera_y) * lerp_speed

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """Handles mouse interactions with district dock tabs and world pins."""
        # 1. Dock tab clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for dist_id, rect in self.dock_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.select_district(dist_id if self.selected_district != self.district_by_id[dist_id] else None)
                    return dist_id

            # 2. World Pin clicks
            for dist in self.districts:
                pin_rect = pygame.Rect(dist.world_x - 18, dist.world_y - 18, 36, 36)
                if pin_rect.collidepoint(mouse_pos):
                    self.select_district(dist.district_id if self.selected_district != dist else None)
                    return dist.district_id

        # Update hover state
        self.hovered_district = None
        for dist in self.districts:
            pin_rect = pygame.Rect(dist.world_x - 18, dist.world_y - 18, 36, 36)
            if pin_rect.collidepoint(mouse_pos):
                self.hovered_district = dist
                break

        if not self.hovered_district:
            for dist_id, rect in self.dock_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.hovered_district = self.district_by_id[dist_id]
                    break

        return None

    def draw_world_pins(self, surface: pygame.Surface, state: Optional[GameState], mouse_pos: Tuple[int, int]) -> None:
        """Draws glowing antique-gold pins over kingdom districts with living pulses."""
        pulse = math.sin(self.pulse_timer) * 3

        for dist in self.districts:
            is_sel = (self.selected_district == dist)
            is_hov = (self.hovered_district == dist)

            px = dist.world_x
            py = dist.world_y

            # Outer glowing pulse ring
            ring_r = int(14 + (6 if is_hov or is_sel else pulse))
            glow_col = Palette.GOLD_LIGHT if (is_sel or is_hov) else (212, 175, 55, 120)

            # Draw subtle glow disk
            glow_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (242, 210, 105, 50 if is_sel else 25), (ring_r + 2, ring_r + 2), ring_r)
            surface.blit(glow_surf, (px - ring_r - 2, py - ring_r - 2))

            # Main medallion pin (Sapphire Dark with Gold Border)
            pin_bg = Palette.SAPPHIRE_LIGHT if is_hov else Palette.SAPPHIRE_DARK
            border_col = Palette.GOLD_PALE if is_sel else Palette.GOLD_BASE
            pygame.draw.circle(surface, pin_bg, (px, py), 12)
            pygame.draw.circle(surface, border_col, (px, py), 12, width=2)

            # Center golden dot
            pygame.draw.circle(surface, Palette.GOLD_LIGHT, (px, py), 4)

            # Hotkey / Icon tag above pin
            tag_surf = FontManager.mono(10).render(dist.hotkey, True, Palette.GOLD_PALE if is_sel else Palette.TEXT_TITLE)
            surface.blit(tag_surf, (px - tag_surf.get_width() // 2, py - 24))

        # Draw inspection tooltip card if hovered or selected
        target = self.hovered_district or self.selected_district
        if target:
            self._draw_district_card(surface, target, state)

    def _draw_district_card(self, surface: pygame.Surface, dist: District, state: Optional[GameState]) -> None:
        """Draws a premium sapphire glass inspector card for the district."""
        card_w = 260
        card_h = 138

        # Position neatly near the pin without overflowing screen bounds
        cx = dist.world_x + 22
        cy = dist.world_y - card_h // 2
        if cx + card_w > 1260:
            cx = dist.world_x - card_w - 22
        if cy < 70:
            cy = 70
        if cy + card_h > 560:
            cy = 560 - card_h

        # Sapphire Glass Backdrop
        glass = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        glass.fill(Palette.SAPPHIRE_PANEL)
        surface.blit(glass, (cx, cy))
        pygame.draw.rect(surface, Palette.GOLD_BASE, (cx, cy, card_w, card_h), width=2, border_radius=8)

        # Header Bar
        hdr_rect = pygame.Rect(cx, cy, card_w, 28)
        pygame.draw.rect(surface, Palette.SAPPHIRE_BASE, hdr_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, Palette.GOLD_DARK, (cx, cy + 28), (cx + card_w, cy + 28), 1)

        title_surf = FontManager.header(13).render(dist.name.upper(), True, Palette.GOLD_PALE)
        surface.blit(title_surf, (cx + 10, cy + 6))

        key_surf = FontManager.mono(11).render(f"[{dist.hotkey}]", True, Palette.GOLD_LIGHT)
        surface.blit(key_surf, (cx + card_w - key_surf.get_width() - 8, cy + 7))

        # Status Metrics
        metrics = dist.get_status(state)
        my = cy + 34
        for k, v, col in metrics[:3]:
            k_s = FontManager.small(11).render(f"{k}:", True, Palette.TEXT_MUTED)
            v_s = FontManager.small(11).render(v, True, col)
            surface.blit(k_s, (cx + 10, my))
            surface.blit(v_s, (cx + 96, my))
            my += 18

        # Short Historical Description
        desc_s = FontManager.italic(10).render(dist.subtitle, True, Palette.SAND_LIGHT)
        surface.blit(desc_s, (cx + 10, cy + card_h - 22))

    def draw_district_dock(self, surface: pygame.Surface, active_id: Optional[str]) -> None:
        """Renders the sleek bottom navigation dock with all 7 kingdom district tabs."""
        dock_w = 840
        dock_h = 38
        dx = (1280 - dock_w) // 2
        dy = 672

        # Sapphire glass dock background
        dock_surf = pygame.Surface((dock_w, dock_h), pygame.SRCALPHA)
        dock_surf.fill((10, 16, 28, 235))
        surface.blit(dock_surf, (dx, dy))
        pygame.draw.rect(surface, Palette.GOLD_BASE, (dx, dy, dock_w, dock_h), width=1, border_radius=6)

        tab_w = (dock_w - 16) // len(self.districts)
        self.dock_rects.clear()

        for i, dist in enumerate(self.districts):
            tx = dx + 8 + i * tab_w
            tab_rect = pygame.Rect(tx, dy + 4, tab_w - 4, dock_h - 8)
            self.dock_rects[dist.district_id] = tab_rect

            is_active = (active_id == dist.district_id or (self.selected_district and self.selected_district.district_id == dist.district_id))
            is_hover = (self.hovered_district == dist)

            if is_active:
                bg_col = Palette.LAPIS_BASE
                border_col = Palette.GOLD_LIGHT
                text_col = Palette.GOLD_PALE
            elif is_hover:
                bg_col = Palette.SAPPHIRE_LIGHT
                border_col = Palette.GOLD_BASE
                text_col = Palette.TEXT_TITLE
            else:
                bg_col = (16, 24, 40)
                border_col = (45, 65, 95)
                text_col = Palette.TEXT_MUTED

            pygame.draw.rect(surface, bg_col, tab_rect, border_radius=4)
            pygame.draw.rect(surface, border_col, tab_rect, width=1, border_radius=4)

            # Label with hotkey
            lbl = f"{dist.hotkey}. {dist.name.split()[0]}"
            t_s = FontManager.small(11).render(lbl, True, text_col)
            surface.blit(t_s, t_s.get_rect(center=tab_rect.center))
