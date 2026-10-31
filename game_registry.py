"""
game_registry.py - Central Game Registry for RetroRevive.

Provides a unified catalog of retro computer games supported by the platform,
including metadata, category filtering, search capabilities, and launcher entry points.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class GameStatus(str, Enum):
    PLAYABLE = "PLAYABLE"
    COMING_SOON = "COMING_SOON"


class GameCategory(str, Enum):
    ALL = "ALL"
    STRATEGY_SIMULATION = "STRATEGY_SIMULATION"
    PUZZLE_LOGIC = "PUZZLE_LOGIC"
    ADVENTURE_SPACE = "ADVENTURE_SPACE"


@dataclass
class GameMetadata:
    """Stores metadata and launch configuration for a retro game."""
    game_id: str
    title: str
    subtitle: str
    year: int
    author: str
    original_publisher: str
    category: GameCategory
    category_display: str
    status: GameStatus
    modes: List[str]
    description: str
    rules_summary: str
    historical_provenance: str
    book_source: str
    tags: List[str] = field(default_factory=list)
    launch_callable: Optional[Callable[..., Any]] = None

    @property
    def is_playable(self) -> bool:
        return self.status == GameStatus.PLAYABLE


# Master game definitions
CATALOG: Dict[str, GameMetadata] = {
    "hammurabi": GameMetadata(
        game_id="hammurabi",
        title="HAMMURABI",
        subtitle="The Ancient Sumerian Kingdom Simulation",
        year=1978,
        author="Doug Dyment (1968), David H. Ahl (1973/1978)",
        original_publisher="Creative Computing (Morristown, NJ)",
        category=GameCategory.STRATEGY_SIMULATION,
        category_display="Strategy & Simulation",
        status=GameStatus.PLAYABLE,
        modes=["Classic 1978 Mode", "Enhanced Mode (Advisors & Scenarios)"],
        description=(
            "Rule ancient Sumeria for a 10-year term of office. Allocate grain between "
            "feeding your citizens, planting seed for the next harvest, and trading land "
            "while managing rat plagues, droughts, and population growth."
        ),
        rules_summary=(
            "Each citizen needs 20 bushels to survive. 1 acre requires 1 bushel of seed "
            "and 1 citizen can tend up to 10 acres. Land trades between 17 and 26 bushels/acre. "
            "Starving over 45% in any year triggers immediate impeachment."
        ),
        historical_provenance=(
            "Derived from Doug Dyment's The Sumer Game (FOCAL, 1968). Ported to DEC BASIC "
            "by David H. Ahl in 101 BASIC Computer Games (1973) and published in BASIC Computer "
            "Games (1978). RetroRevive preserves the exact 1978 Microsoft BASIC mechanics."
        ),
        book_source="BASIC Computer Games: Microcomputer Edition (1978), pp. 78-79.",
        tags=["Simulation", "Resource Management", "Classic 1978", "Historical"],
    ),
    "23_matches": GameMetadata(
        game_id="23_matches",
        title="23 MATCHES",
        subtitle="The Classic Mathematical Nim Subtraction Game",
        year=1978,
        author="Bob Albrecht (1973), David H. Ahl (1978)",
        original_publisher="People's Computer Company / Creative Computing",
        category=GameCategory.PUZZLE_LOGIC,
        category_display="Puzzle & Logic",
        status=GameStatus.PLAYABLE,
        modes=["Classic 1978 Mode (Albrecht AI)", "Master Mode (Optimal Modular AI)"],
        description=(
            "The timeless strategy game of 23 matchsticks. You and the computer take turns "
            "removing 1, 2, or 3 matches from the table. The player forced to take the "
            "very last match loses! Can you discover the mathematical winning strategy?"
        ),
        rules_summary=(
            "23 matches start on the table. Each turn, take 1, 2, or 3 matches. "
            "You cannot take more matches than remain on the table. The player who takes "
            "the last match loses the game (Misère Nim rules)."
        ),
        historical_provenance=(
            "Authored by Bob Albrecht at the People's Computer Company to teach modular "
            "arithmetic and strategic thinking. Published in 101 BASIC Computer Games (1973) "
            "and republished in BASIC Computer Games (1978) as game #93."
        ),
        book_source="BASIC Computer Games: Microcomputer Edition (1978), pp. 177-178.",
        tags=["Puzzle", "Nim", "Mathematical", "Turn-Based", "Misère"],
    ),
    "lunar_lander": GameMetadata(
        game_id="lunar_lander",
        title="LUNAR LANDER",
        subtitle="Apollo 11 Lunar Module Descent Simulator",
        year=1973,
        author="Jim Storer (1969), David H. Ahl (1973)",
        original_publisher="DEC / Creative Computing",
        category=GameCategory.STRATEGY_SIMULATION,
        category_display="Strategy & Simulation",
        status=GameStatus.COMING_SOON,
        modes=["Standard Physics (1973)", "Enhanced Radar HUD"],
        description=(
            "Pilot the Apollo lunar excursion module safely to the moon's surface. Manage your "
            "fuel burn rate against lunar gravity to touch down at under 5 ft/sec."
        ),
        rules_summary=(
            "Burn fuel every second to counteract gravity. Soft landing achieved below 5 mph. "
            "High descent rates result in impact and crater creation."
        ),
        historical_provenance="Created in 1969 by Lexington High School student Jim Storer; published in 101 BASIC Computer Games (1973).",
        book_source="BASIC Computer Games (1978), pp. 106-108.",
        tags=["Space", "Physics", "Apollo", "Coming Soon"],
    ),
    "super_star_trek": GameMetadata(
        game_id="super_star_trek",
        title="SUPER STAR TREK",
        subtitle="Tactical Deep Space Command Simulation",
        year=1974,
        author="Mike Mayfield (1971), David H. Ahl & Bob Leedom (1974)",
        original_publisher="Creative Computing",
        category=GameCategory.ADVENTURE_SPACE,
        category_display="Adventure & Space",
        status=GameStatus.COMING_SOON,
        modes=["Classic Sector Grid", "Tactical Sensor Array"],
        description=(
            "Command the USS Enterprise across an 8x8 quadrant galaxy. Hunt Klingon warships, "
            "manage photon torpedoes, shields, and dock at starbases before stardates expire."
        ),
        rules_summary=(
            "Navigate through 64 quadrants. Balance energy between shields, phasers, and warp engines. "
            "Neutralize all Klingon battlecruisers before time runs out."
        ),
        historical_provenance="Originated on SDS Sigma 7 by Mike Mayfield in 1971; expanded into Super Star Trek by David H. Ahl and Bob Leedom in 1974.",
        book_source="BASIC Computer Games (1978), pp. 157-163.",
        tags=["Sci-Fi", "Tactical", "Grid Command", "Coming Soon"],
    ),
    "oregon_trail": GameMetadata(
        game_id="oregon_trail",
        title="THE OREGON TRAIL",
        subtitle="The Great 1848 Pioneer Frontier Journey",
        year=1971,
        author="Don Rawitsch, Bill Heinemann, Paul Dillenberger (1971)",
        original_publisher="MECC (Minnesota Educational Computing Consortium)",
        category=GameCategory.STRATEGY_SIMULATION,
        category_display="Strategy & Simulation",
        status=GameStatus.COMING_SOON,
        modes=["1848 Historic Trail", "Trail Guide Companion"],
        description=(
            "Lead a covered wagon party of pioneers from Independence, Missouri to Oregon's "
            "Willamette Valley. Hunt for food, ford treacherous rivers, and brave harsh weather."
        ),
        rules_summary=(
            "Manage oxen, food, clothing, ammunition, and medical supplies over 2,000 miles. "
            "Survive river crossings, bandits, and cholera."
        ),
        historical_provenance="Created in 1971 by student teachers in Minneapolis to teach 8th-grade history; published in Creative Computing in 1978.",
        book_source="Creative Computing Magazine (May/June 1978).",
        tags=["History", "Survival", "Pioneers", "Coming Soon"],
    ),
}


class GameRegistry:
    """Manages the catalog of retro games and provides filtering and lookup methods."""

    def __init__(self, catalog: Optional[Dict[str, GameMetadata]] = None) -> None:
        self._catalog: Dict[str, GameMetadata] = dict(catalog if catalog is not None else CATALOG)

    def register(self, metadata: GameMetadata) -> None:
        """Registers or replaces a game in the catalog."""
        self._catalog[metadata.game_id] = metadata

    def get(self, game_id: str) -> Optional[GameMetadata]:
        """Returns game metadata for a given game ID, or None if not found."""
        return self._catalog.get(game_id)

    def list_all(self) -> List[GameMetadata]:
        """Returns all registered games in catalog order."""
        return list(self._catalog.values())

    def list_playable(self) -> List[GameMetadata]:
        """Returns only currently playable games."""
        return [g for g in self._catalog.values() if g.is_playable]

    def filter_by_category(self, category: GameCategory) -> List[GameMetadata]:
        """Filters games by category enum. Returns all if category is ALL."""
        if category == GameCategory.ALL:
            return self.list_all()
        return [g for g in self._catalog.values() if g.category == category]

    def search(self, query: str) -> List[GameMetadata]:
        """
        Searches game titles, subtitles, tags, and authors by substring (case-insensitive).
        Empty query returns all games.
        """
        q = query.strip().lower()
        if not q:
            return self.list_all()
        results: List[GameMetadata] = []
        for g in self._catalog.values():
            if (
                q in g.title.lower()
                or q in g.subtitle.lower()
                or q in g.author.lower()
                or q in g.category_display.lower()
                or any(q in tag.lower() for tag in g.tags)
            ):
                results.append(g)
        return results


# Global singleton instance for convenient import
REGISTRY = GameRegistry()
