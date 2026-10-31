"""
presentation.py - Retro visual effects, ASCII scenes, and animations for Hammurabi.

This module provides optional, cosmetic visual enhancements for RetroRevive:
- Animated ASCII city, ziggurat, and farmland using authentic 7-bit retro ASCII
- Color-coded resource meters (Grain, Land, Citizens)
- Fast retro harvest and rat infestation animations
- Year-to-year transition banners
- Plain-text fallback for non-TTY terminals, pipes, and automated tests.

Zero game logic or random event calculations take place here; all effects
are purely cosmetic presentations of GameState.
"""

from dataclasses import dataclass
import os
import sys
import time
from typing import Optional

from game_logic import GameState


# ANSI Color Codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Standard Foreground
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright Foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


@dataclass
class VisualConfig:
    """Controls cosmetic visual effects and animation timing."""

    enabled: bool = False
    use_color: bool = False
    frame_delay: float = 0.04  # Snappy ~25 FPS animation frames

    @classmethod
    def detect(
        cls,
        force_animate: Optional[bool] = None,
        force_color: Optional[str] = "auto",
        speed: str = "normal",
    ) -> "VisualConfig":
        """Detects terminal capabilities and creates appropriate configuration."""
        is_tty = sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False
        no_color_env = bool(os.environ.get("NO_COLOR"))
        term_env = os.environ.get("TERM", "")

        # Determine color
        if force_color == "never" or no_color_env or term_env == "dumb":
            use_color = False
        elif force_color == "always":
            use_color = True
        else:
            use_color = is_tty

        # Determine animation
        if force_animate is True:
            enabled = True
        elif force_animate is False:
            enabled = False
        else:
            enabled = is_tty

        # Delay speed
        speed_map = {"fast": 0.02, "normal": 0.04, "slow": 0.08}
        delay = speed_map.get(speed.lower(), 0.04)

        return cls(enabled=enabled, use_color=use_color, frame_delay=delay)


def colorize(text: str, color_code: str, config: VisualConfig) -> str:
    """Wraps text in ANSI color codes if color is enabled."""
    if not config.use_color:
        return text
    return f"{color_code}{text}{Colors.RESET}"


def sleep_frame(config: VisualConfig, multiplier: float = 1.0) -> None:
    """Sleeps for an animation frame if animations are enabled."""
    if config.enabled and config.frame_delay > 0:
        time.sleep(config.frame_delay * multiplier)


# ---------------------------------------------------------------------------
# ASCII City & Farmland Panorama
# ---------------------------------------------------------------------------

def render_city_scene(state: GameState, config: VisualConfig) -> str:
    """
    Renders an ASCII landscape depicting the ancient city-state of Sumeria,
    with a ziggurat, palm grove, Euphrates river, farmland, and grain silos.
    Uses 100% portable 7-bit ASCII characters compatible with all encodings.
    """
    # Farmland density (1 to 10 stalks)
    wheat_count = min(10, max(1, state.acres // 150))
    wheat_line = " " + "| " * wheat_count

    # Silo fullness meter (out of 10 blocks)
    silo_pct = min(10, max(0, state.bushels // 350))
    silo_bar = "#" * silo_pct + "-" * (10 - silo_pct)

    # Population density indicator
    pop_icons = min(10, max(1, state.population // 15))
    pop_bar = "o " * pop_icons

    gold = Colors.BRIGHT_YELLOW
    green = Colors.BRIGHT_GREEN
    cyan = Colors.BRIGHT_CYAN
    blue = Colors.BRIGHT_BLUE

    c_city = colorize("ANCIENT SUMERIA", Colors.BOLD + Colors.BRIGHT_WHITE, config)
    c_zigg = colorize(r"      _/\_          ", gold, config)
    c_zig2 = colorize(r"    _/____\_        ", gold, config)
    c_zig3 = colorize(r"  _/________\_      ", gold, config)
    c_zig4 = colorize(" [=== TEMPLE ===]   ", gold, config)

    silos_text = colorize(f"SILOS:    [{silo_bar}] {state.bushels} bu", gold, config)
    pop_text = colorize(f"CITIZENS: {pop_bar}({state.population})", cyan, config)
    farm_text = colorize(f"FARMLAND: {state.acres} acres", green, config)
    river_text = colorize("EUPHRATES: ~~~~~ ~^~^~ ~~~~~", blue, config)
    fields_lbl = colorize("FIELDS:", green, config)
    fields_val = colorize(wheat_line, green, config)

    border_top = "+-- " + c_city + " " + "-" * (58 - 19) + "+"
    border_bot = "+" + "-" * 62 + "+"

    lines = [
        border_top,
        f"| {c_zigg} {silos_text:<47} |",
        f"| {c_zig2} {pop_text:<47} |",
        f"| {c_zig3} {farm_text:<47} |",
        f"| {c_zig4} {river_text:<47} |",
        f"|  {fields_lbl}{fields_val:<54} |",
        border_bot,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Visual Year Transitions & Status Badges
# ---------------------------------------------------------------------------

def print_year_transition(year: int, config: VisualConfig) -> None:
    """Displays a retro banner introducing the new governing year."""
    if not config.enabled:
        return

    banner_text = f"SUMERIA CHRONICLE: YEAR {year} OF HAMURABI'S REIGN"
    c_banner = colorize(banner_text, Colors.BOLD + Colors.BRIGHT_YELLOW, config)
    border = "=" * (len(banner_text) + 6)

    print()
    print(colorize(f"+{border}+", Colors.YELLOW, config))
    print(colorize(f"|   {c_banner}   |", Colors.YELLOW, config))
    print(colorize(f"+{border}+", Colors.YELLOW, config))
    sleep_frame(config, 2.0)


def print_resource_dashboard(state: GameState, config: VisualConfig) -> None:
    """Displays a compact color-coded resource status dashboard."""
    if not config.use_color and not config.enabled:
        return

    c_pop = colorize(f"Citizens: {state.population}", Colors.BRIGHT_CYAN, config)
    c_acres = colorize(f"Land: {state.acres} ac", Colors.BRIGHT_GREEN, config)
    c_grain = colorize(f"Store: {state.bushels} bu", Colors.BRIGHT_YELLOW, config)
    c_price = colorize(f"Price: {state.land_price} bu/ac", Colors.BRIGHT_MAGENTA, config)

    print(f"[{c_pop}]  [{c_acres}]  [{c_grain}]  [{c_price}]\n")


# ---------------------------------------------------------------------------
# Animated Event Sequences (Harvest, Rats, Plague)
# ---------------------------------------------------------------------------

def animate_harvest(
    planted_acres: int,
    yield_per_acre: int,
    total_harvest: int,
    config: VisualConfig,
) -> None:
    """Displays a short retro animation of the wheat harvest."""
    if not config.enabled or planted_acres <= 0:
        return

    gold = Colors.BRIGHT_YELLOW
    green = Colors.BRIGHT_GREEN

    frames = [
        f"  {colorize('* Reapers gathering across', green, config)} {planted_acres} {colorize('acres...', green, config)}",
        f"  {colorize('* Threshing grain...', gold, config)} {colorize(f'Yield: {yield_per_acre} bu/acre!', Colors.BOLD + gold, config)}",
        f"  {colorize('* Bountiful harvest:', gold, config)} {colorize(f'+{total_harvest} bushels', Colors.BOLD + Colors.BRIGHT_GREEN, config)} {colorize('delivered to granaries!', gold, config)}",
    ]

    for frame in frames:
        print(frame)
        sleep_frame(config, 1.5)


def animate_rats(
    rats_ate: int,
    config: VisualConfig,
) -> None:
    """Displays a quick retro animation when rats raid grain silos."""
    if not config.enabled or rats_ate <= 0:
        return

    red = Colors.BRIGHT_RED

    frames = [
        colorize("  ..:..:.. (___)o~  Scurrying sounds in the silos!", red, config),
        colorize("  ..:..:.. (___)o~  (___)o~  Rats are running wild through the grain!", red, config),
        colorize(f"  [SILOS RAIDED] Rats devoured {rats_ate} bushels of grain!", Colors.BOLD + red, config),
    ]

    for frame in frames:
        print(frame)
        sleep_frame(config, 1.5)


def animate_plague(config: VisualConfig) -> None:
    """Displays a dramatic pestilence alert when plague strikes."""
    if not config.enabled:
        return

    red = Colors.BOLD + Colors.BRIGHT_RED
    banner = [
        colorize("  *** A HORRIBLE PLAGUE STRUCK! ***", red, config),
        colorize("  Pestilence sweeps through the streets of Sumeria! Half the people died.", Colors.RED, config),
    ]
    for line in banner:
        print(line)
        sleep_frame(config, 2.0)


def print_evaluation_banner(tier: int, config: VisualConfig) -> None:
    """Displays an ASCII celebration or defeat banner matching the final rating tier."""
    if not config.enabled and not config.use_color:
        return

    if tier == 4:
        # Fantastic
        title = colorize("*** TRIUMPH OF SUMERIA -- GOLDEN AGE ***", Colors.BOLD + Colors.BRIGHT_GREEN, config)
        print(f"\n{title}\n")
    elif tier == 1:
        # Impeached / Fink
        title = colorize("*** IMPEACHED AND DECLARED NATIONAL FINK ***", Colors.BOLD + Colors.BRIGHT_RED, config)
        print(f"\n{title}\n")
    elif tier == 2:
        # Tyrant / Nero
        title = colorize("*** HEAVY-HANDED RULE OF NERO & IVAN IV ***", Colors.BOLD + Colors.RED, config)
        print(f"\n{title}\n")
    elif tier == 3:
        # Mediocre
        title = colorize("*** MEDIOCRE SURVIVAL -- ASSASSINATION RISK ***", Colors.BOLD + Colors.YELLOW, config)
        print(f"\n{title}\n")
