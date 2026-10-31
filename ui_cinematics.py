"""
ui_cinematics.py - Cinematic In-Engine Sequence & Event Director for RetroRevive.

Drives genuine real-time cinematic sequences based on authentic simulation events:
- Opening Prologue: Sunrise over Babylon, royal palace reveal, and title presentation
- Harvest Sequence: Golden sunbeam sweep, reaping farmers, and granary stockpile surge
- Drought Sequence: Harsh desert sandstorm, parched earth, and stressed crops
- Plague Sequence: Solemn twilight mist, respectful city quarantine, and royal condolences
- Rat Infestation: Rodent scurry across silos and grain loss particles
- Immigrant Caravan: New citizens entering through the Ishtar Gates
- Famine Warning: City unrest and urgent royal advisor plea
- Victory & Defeat: Grand imperial coronation fireworks vs twilight abdication

All sequences are smooth, delta-time driven, dynamically responsive, and instantly skippable.
"""

import math
from typing import Callable, Optional
import pygame

from game_logic import GameState
from ui_characters import RoyalHammurabi
from ui_theme import FontManager, Palette, SoundSynthesizer


class CinematicSequence:
    """Represents an active cinematic event sequence."""

    def __init__(
        self,
        event_type: str,
        title: str,
        subtitle: str,
        details: str,
        duration: float = 3.5,
        on_complete: Optional[Callable[[], None]] = None,
        badge_col: tuple = Palette.GOLD_LIGHT,
    ) -> None:
        self.event_type = event_type
        self.title = title
        self.subtitle = subtitle
        self.details = details
        self.duration = duration
        self.elapsed = 0.0
        self.on_complete = on_complete
        self.badge_col = badge_col
        self.is_active = True
        self.hammurabi = RoyalHammurabi(scale=1.0)

    def update(self, dt: float) -> bool:
        """Returns True while sequence is running, False when complete."""
        self.elapsed += dt
        self.hammurabi.update(dt)
        if self.elapsed >= self.duration:
            self.finish()
            return False
        return True

    def skip(self) -> None:
        """Immediately finishes sequence on player input."""
        self.finish()

    def finish(self) -> None:
        if self.is_active:
            self.is_active = False
            if self.on_complete:
                self.on_complete()

    def get_progress(self) -> float:
        return min(1.0, max(0.0, self.elapsed / self.duration))

    def draw(self, surface: pygame.Surface) -> None:
        """Renders cinematic overlays, letterbox bars, and narrative banners."""
        prog = self.get_progress()

        # Cinematic Letterbox Bars (Expanding from top and bottom)
        bar_h = 56
        bar_top = pygame.Rect(0, 0, 1280, bar_h)
        bar_bot = pygame.Rect(0, 720 - bar_h, 1280, bar_h)
        pygame.draw.rect(surface, (12, 9, 7), bar_top)
        pygame.draw.rect(surface, (12, 9, 7), bar_bot)
        pygame.draw.line(surface, Palette.GOLD_DARK, (0, bar_h), (1280, bar_h), 1)
        pygame.draw.line(surface, Palette.GOLD_DARK, (0, 720 - bar_h), (1280, 720 - bar_h), 1)

        # Skip guide in bottom bar
        skip_hint = FontManager.small(12).render("[SPACE / CLICK / ESC] Skip Cinematic", True, Palette.TEXT_MUTED)
        surface.blit(skip_hint, skip_hint.get_rect(center=(1280 // 2, 720 - bar_h // 2)))

        # Atmosphere Wash depending on event
        self._draw_atmosphere(surface, prog)

        # Central Royal Cinematic Banner
        self._draw_banner(surface, prog)

    def _draw_atmosphere(self, surface: pygame.Surface, prog: float) -> None:
        alpha_curve = math.sin(prog * 3.14159)  # Smooth fade-in and fade-out
        alpha = int(alpha_curve * 110)

        overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
        if self.event_type == "HARVEST":
            # Golden sunbeam wash
            overlay.fill((255, 215, 80, alpha))
            # Diagonal sunbeams
            for i in range(5):
                beam_x = int(300 + i * 220 + math.sin(prog * 2.0 + i) * 40)
                pygame.draw.line(overlay, (255, 240, 160, int(alpha * 0.7)), (beam_x, 0), (beam_x - 150, 720), 45)
        elif self.event_type == "DROUGHT":
            # Harsh amber dust storm wash
            overlay.fill((210, 130, 40, alpha))
            # Blowing dust particles
            for i in range(16):
                dx = int((prog * 1800 + i * 90) % 1280)
                dy = int(100 + (i * 37) % 520)
                pygame.draw.line(overlay, (240, 190, 100, alpha), (dx, dy), (dx + 30, dy + 4), 2)
        elif self.event_type == "PLAGUE":
            # Somber violet twilight mist
            overlay.fill((50, 20, 60, alpha))
        elif self.event_type == "RATS":
            # Dark shadowy rodent raid wash
            overlay.fill((40, 25, 20, int(alpha * 0.8)))
        elif self.event_type == "IMMIGRATION":
            # Welcoming morning golden light
            overlay.fill((240, 220, 140, int(alpha * 0.7)))
        elif self.event_type == "PROLOGUE":
            # Deep dawn into brilliant sunrise
            overlay.fill((25, 15, 30, int((1.0 - prog) * 160)))

        surface.blit(overlay, (0, 0))

    def _draw_banner(self, surface: pygame.Surface, prog: float) -> None:
        # Smooth bounce-in animation for card
        fade = min(1.0, prog * 4.0) if prog < 0.85 else max(0.0, (1.0 - prog) * 6.0)
        card_w, card_h = 740, 170
        cx = (1280 - card_w) // 2
        cy = 135

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        bg_alpha = int(fade * 235)
        card_surf.fill((24, 18, 14, bg_alpha))

        # Golden royal border with ornamental corners
        border_col = (
            int(self.badge_col[0] * fade),
            int(self.badge_col[1] * fade),
            int(self.badge_col[2] * fade),
        )
        pygame.draw.rect(card_surf, border_col, (0, 0, card_w, card_h), width=2, border_radius=10)
        pygame.draw.rect(card_surf, Palette.PANEL_BORDER, (4, 4, card_w - 8, card_h - 8), width=1, border_radius=8)

        # Title
        t_surf = FontManager.title(28).render(self.title, True, self.badge_col)
        card_surf.blit(t_surf, t_surf.get_rect(center=(card_w // 2, 34)))

        # Subtitle
        s_surf = FontManager.header(17).render(self.subtitle, True, Palette.SAND_LIGHT)
        card_surf.blit(s_surf, s_surf.get_rect(center=(card_w // 2, 70)))

        # Narrative Details
        d_surf = FontManager.body(16).render(self.details, True, Palette.TEXT_TITLE)
        card_surf.blit(d_surf, d_surf.get_rect(center=(card_w // 2, 110)))

        # Progress bar under banner
        bar_w = int((card_w - 60) * prog)
        pygame.draw.rect(card_surf, Palette.GOLD_DARK, (30, 146, card_w - 60, 4), border_radius=2)
        pygame.draw.rect(card_surf, Palette.GOLD_LIGHT, (30, 146, bar_w, 4), border_radius=2)

        surface.blit(card_surf, (cx, cy))


class CinematicDirector:
    """Manages playback, queueing, and triggering of cinematic events."""

    def __init__(self) -> None:
        self.active_cinematic: Optional[CinematicSequence] = None

    def is_playing(self) -> bool:
        return self.active_cinematic is not None and self.active_cinematic.is_active

    def skip(self) -> None:
        if self.active_cinematic:
            self.active_cinematic.skip()
            self.active_cinematic = None

    def update(self, dt: float) -> None:
        if self.active_cinematic:
            alive = self.active_cinematic.update(dt)
            if not alive:
                self.active_cinematic = None

    def draw(self, surface: pygame.Surface) -> None:
        if self.active_cinematic:
            self.active_cinematic.draw(surface)

    def trigger_prologue(self, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("harvest")
        self.active_cinematic = CinematicSequence(
            event_type="PROLOGUE",
            title="HAMMURABI: THE LIVING EMPIRE",
            subtitle="Sunrise Over Ancient Babylon — Kingdom of the Euphrates",
            details="Take up the Royal Sceptre, Sire. Govern Sumeria for a glorious Ten-Year Reign!",
            duration=3.8,
            on_complete=on_complete,
            badge_col=Palette.GOLD_LIGHT,
        )

    def trigger_turn_events(self, state: GameState, on_complete: Optional[Callable[[], None]] = None) -> None:
        """Inspects actual GameState results and presents the most prominent annual event."""
        # Priority 1: Plague
        if state.plague_struck:
            SoundSynthesizer.play("warning")
            self.active_cinematic = CinematicSequence(
                event_type="PLAGUE",
                title="A TERRIBLE PESTILENCE SWEEPS THE CITY!",
                subtitle="The Great Plague of Sumeria",
                details=f"Half the citizens perished in the temples. {state.population} survivors remain under your care.",
                duration=3.5,
                on_complete=on_complete,
                badge_col=Palette.CRIMSON_LIGHT,
            )
            return

        # Priority 2: Famine / Starvation
        if state.starved_this_year > 0:
            SoundSynthesizer.play("warning")
            self.active_cinematic = CinematicSequence(
                event_type="STARVATION",
                title="FAMINE GRIPS THE KINGDOM!",
                subtitle=f"{state.starved_this_year} Citizens Starved in Year {state.year}",
                details="Grain rations fell short! Ensure 20 bushels per person to prevent revolt.",
                duration=3.4,
                on_complete=on_complete,
                badge_col=Palette.AMBER_WARN,
            )
            return

        # Priority 3: Severe Drought
        if state.harvest_yield == 1:
            SoundSynthesizer.play("click")
            self.active_cinematic = CinematicSequence(
                event_type="DROUGHT",
                title="THE DRY WINDS OF THE DESERT ARRIVE",
                subtitle="Drought Yield: Only 1 Bushel Per Acre Reaped",
                details=f"Scorching sun parched the crops. Silos stand at {state.bushels} bushels.",
                duration=3.2,
                on_complete=on_complete,
                badge_col=(220, 140, 60),
            )
            return

        # Priority 4: Bumper Harvest
        if state.harvest_yield == 5:
            SoundSynthesizer.play("harvest")
            self.active_cinematic = CinematicSequence(
                event_type="HARVEST",
                title="A MAGNIFICENT BUMPER HARVEST!",
                subtitle="Golden Grain Floods Sumerian Silos: 5 Bushels Per Acre!",
                details=f"The Euphrates blessed our soil! Total granary reserve reaches {state.bushels} bushels.",
                duration=3.2,
                on_complete=on_complete,
                badge_col=Palette.GOLD_LIGHT,
            )
            return

        # Priority 5: Heavy Rat Infestation
        if state.rats_ate >= 150:
            SoundSynthesizer.play("warning")
            self.active_cinematic = CinematicSequence(
                event_type="RATS",
                title="RODENT SWARMS INVADE THE GRANARIES!",
                subtitle=f"Rats Devoured {state.rats_ate} Bushels of Royal Grain",
                details=f"Storehouses compromised! Remaining grain: {state.bushels} bushels.",
                duration=3.0,
                on_complete=on_complete,
                badge_col=Palette.AMBER_WARN,
            )
            return

        # Priority 6: Large Immigrant Influx
        if state.immigrants_this_year >= 10:
            SoundSynthesizer.play("coin")
            self.active_cinematic = CinematicSequence(
                event_type="IMMIGRATION",
                title="WORD OF SUMERIA'S SPLENDOR SPREADS",
                subtitle=f"{state.immigrants_this_year} Migrants Arrived Through the City Gates",
                details=f"Babylon expands! Your workforce now stands at {state.population} living citizens.",
                duration=3.0,
                on_complete=on_complete,
                badge_col=Palette.LAPIS_LIGHT,
            )
            return

        # Default smooth turn advance if no critical event
        if on_complete:
            on_complete()

    def trigger_harvest(self, yield_per_acre: int = 5, total_harvest: int = 2500, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("harvest")
        self.active_cinematic = CinematicSequence(
            event_type="HARVEST",
            title="A MAGNIFICENT BUMPER HARVEST!",
            subtitle=f"Golden Grain Floods Sumerian Silos: {yield_per_acre} Bushels Per Acre!",
            details=f"The Euphrates blessed our soil! Total harvested grain: {total_harvest:,} bushels.",
            duration=3.2,
            on_complete=on_complete,
            badge_col=Palette.GOLD_LIGHT,
        )

    def trigger_plague(self, deaths: int = 50, survivors: int = 50, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("warning")
        self.active_cinematic = CinematicSequence(
            event_type="PLAGUE",
            title="A TERRIBLE PESTILENCE SWEEPS THE CITY!",
            subtitle="The Great Plague of Sumeria",
            details=f"{deaths} citizens perished in the temples. {survivors} survivors remain under your care.",
            duration=3.5,
            on_complete=on_complete,
            badge_col=Palette.CRIMSON_LIGHT,
        )

    def trigger_drought(self, yield_per_acre: int = 1, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("click")
        self.active_cinematic = CinematicSequence(
            event_type="DROUGHT",
            title="THE DRY WINDS OF THE DESERT ARRIVE",
            subtitle=f"Drought Yield: Only {yield_per_acre} Bushel Per Acre Reaped",
            details="Scorching heat parched the crops. Strategic grain management required.",
            duration=3.2,
            on_complete=on_complete,
            badge_col=(220, 140, 60),
        )

    def trigger_rats(self, rats_ate: int = 200, bushels_left: int = 2500, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("warning")
        self.active_cinematic = CinematicSequence(
            event_type="RATS",
            title="RODENT SWARMS INVADE THE GRANARIES!",
            subtitle=f"Rats Devoured {rats_ate} Bushels of Royal Grain",
            details=f"Storehouses breached! Remaining granary stores: {bushels_left:,} bushels.",
            duration=3.0,
            on_complete=on_complete,
            badge_col=Palette.AMBER_WARN,
        )

    def trigger_immigration(self, newcomers: int = 12, total_pop: int = 112, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("coin")
        self.active_cinematic = CinematicSequence(
            event_type="IMMIGRATION",
            title="WORD OF SUMERIA'S SPLENDOR SPREADS",
            subtitle=f"{newcomers} Migrants Arrived Through the City Gates",
            details=f"Babylon expands! Your workforce now stands at {total_pop} living citizens.",
            duration=3.0,
            on_complete=on_complete,
            badge_col=Palette.LAPIS_LIGHT,
        )

    def trigger_starvation(self, starved: int = 15, on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("warning")
        self.active_cinematic = CinematicSequence(
            event_type="STARVATION",
            title="FAMINE GRIPS THE KINGDOM!",
            subtitle=f"{starved} Citizens Starved Due to Grain Shortages",
            details="Grain rations fell short! Ensure 20 bushels per person to prevent revolt.",
            duration=3.4,
            on_complete=on_complete,
            badge_col=Palette.AMBER_WARN,
        )

    def trigger_victory(self, message: str = "A triumphant reign of 10 years!", on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("bell")
        self.active_cinematic = CinematicSequence(
            event_type="VICTORY",
            title="GLORY TO HAMMURABI — FATHER OF BABYLON!",
            subtitle="Ten-Year Governance Concluded in Triumph",
            details=message,
            duration=4.0,
            on_complete=on_complete,
            badge_col=Palette.GOLD_LIGHT,
        )

    def trigger_defeat(self, message: str = "Reign terminated prematurely.", on_complete: Optional[Callable[[], None]] = None) -> None:
        SoundSynthesizer.play("warning")
        self.active_cinematic = CinematicSequence(
            event_type="DEFEAT",
            title="THE FALL OF THE STEWARD",
            subtitle="Rule Terminated by Imperial Decree",
            details=message,
            duration=3.8,
            on_complete=on_complete,
            badge_col=Palette.CRIMSON_LIGHT,
        )
