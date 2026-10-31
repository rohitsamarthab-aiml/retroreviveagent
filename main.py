"""
main.py - Interactive command-line interface for Hammurabi (1978 Edition).

This module manages user interaction, terminal formatting, safe input handling,
and runs the game loop while delegating simulation calculations to game_logic.py
and cosmetic retro visual presentation to presentation.py.
"""

import argparse
import sys
from typing import Optional

from game_logic import (
    DefaultRNG,
    GameState,
    RandomProvider,
    TurnDecisions,
    evaluate_term,
    init_game,
    step_year,
    validate_buy_land,
    validate_feed_people,
    validate_plant_seed,
    validate_sell_land,
)
from presentation import (
    Colors,
    VisualConfig,
    animate_harvest,
    animate_plague,
    animate_rats,
    colorize,
    print_evaluation_banner,
    print_resource_dashboard,
    print_year_transition,
    render_city_scene,
)


def safe_prompt_int(prompt_text: str) -> Optional[int]:
    """
    Safely reads an integer from stdin.
    - If input cannot be converted to int, prints historical '?REDO FROM START'
      and re-prompts without crashing or modifying game state.
    - Handles EOF (Ctrl+D / Ctrl+Z) cleanly by returning None.
    """
    while True:
        try:
            raw = input(prompt_text).strip()
            if not raw:
                print("?REDO FROM START")
                continue
            return int(raw)
        except ValueError:
            print("?REDO FROM START")
        except (EOFError, KeyboardInterrupt):
            print("\nSO LONG FOR NOW.")
            return None


def print_historical_header(visual_config: Optional[VisualConfig] = None) -> None:
    """Prints the authentic Creative Computing 1978 game banner."""
    config = visual_config or VisualConfig()
    title = colorize("HAMURABI", Colors.BOLD + Colors.BRIGHT_YELLOW, config)
    subtitle = colorize(
        "CREATIVE COMPUTING  MORRISTOWN, NEW JERSEY", Colors.CYAN, config
    )

    print(" " * 32 + title)
    print(" " * 15 + subtitle)
    print("\n\n")
    print("TRY YOUR HAND AT GOVERNING ANCIENT SUMERIA")
    print("FOR A TEN-YEAR TERM OF OFFICE.\n")


def print_year_report(
    state: GameState,
    visual_config: Optional[VisualConfig] = None,
) -> None:
    """Displays the annual status report matching lines 215-260."""
    config = visual_config or VisualConfig()

    print("\n\nHAMURABI:  I BEG TO REPORT TO YOU,")
    print(
        f"IN YEAR {state.year}, {state.starved_this_year} PEOPLE STARVED, "
        f"{state.immigrants_this_year} CAME TO THE CITY,"
    )
    if state.plague_struck:
        print("A HORRIBLE PLAGUE STRUCK!  HALF THE PEOPLE DIED.")
    print(f"POPULATION IS NOW {state.population}")
    print(f"THE CITY NOW OWNS {state.acres} ACRES.")
    print(f"YOU HARVESTED {state.harvest_yield} BUSHELS PER ACRE.")
    print(f"THE RATS ATE {state.rats_ate} BUSHELS.")
    print(f"YOU NOW HAVE {state.bushels} BUSHELS IN STORE.\n")

    if config.enabled or config.use_color:
        print_resource_dashboard(state, config)


def print_farewell_beeps(play_audio: bool = True) -> None:
    """Prints 10 ASCII bell characters (CHR$(7)) and farewell message."""
    print()
    if play_audio:
        for _ in range(10):
            sys.stdout.write("\a")
        sys.stdout.flush()
    print("SO LONG FOR NOW.\n")


def play_game(
    rng: Optional[RandomProvider] = None,
    strict_historical: bool = True,
    play_audio: bool = True,
    visual_config: Optional[VisualConfig] = None,
) -> int:
    """
    Runs an interactive game session to completion.
    Returns 0 on clean completion or exit.
    """
    config = visual_config or VisualConfig()
    print_historical_header(config)

    state = init_game(rng=rng, strict_historical=strict_historical)

    while not state.is_over:
        # Visual transition banner & City Scene
        if config.enabled:
            print_year_transition(state.year, config)
            print(render_city_scene(state, config))

        # Step 1: Print annual report
        print_year_report(state, config)

        # Step 2: Land Trading Phase
        price_text = colorize(
            f"{state.land_price}", Colors.BOLD + Colors.BRIGHT_MAGENTA, config
        )
        print(f"LAND IS TRADING AT {price_text} BUSHELS PER ACRE.")

        buy_acres = 0
        sell_acres = 0

        # Sub-phase: Buy Land
        while True:
            val = safe_prompt_int("HOW MANY ACRES DO YOU WISH TO BUY? ")
            if val is None:
                return 0
            buy_res = validate_buy_land(state, val)
            if buy_res.is_fatal:
                print(f"\n{buy_res.message}")
                print_farewell_beeps(play_audio)
                return 0
            if not buy_res.is_valid:
                print(buy_res.message)
                continue
            buy_acres = val
            break

        # Sub-phase: Sell Land (only if player bought 0 acres, line 330)
        if buy_acres == 0:
            while True:
                val = safe_prompt_int("HOW MANY ACRES DO YOU WISH TO SELL? ")
                if val is None:
                    return 0
                sell_res = validate_sell_land(
                    state, val, strict_historical=strict_historical
                )
                if sell_res.is_fatal:
                    print(f"\n{sell_res.message}")
                    print_farewell_beeps(play_audio)
                    return 0
                if not sell_res.is_valid:
                    print(sell_res.message)
                    continue
                sell_acres = val
                break

        # Step 3: Feeding Phase
        print()
        # Calculate available grain store after land transactions
        if buy_acres > 0:
            grain_after_land = state.bushels - buy_acres * state.land_price
        else:
            grain_after_land = state.bushels + sell_acres * state.land_price

        # Temporary state view for feed validation
        temp_state_for_feed = GameState(
            year=state.year,
            population=state.population,
            bushels=grain_after_land,
            acres=state.acres + buy_acres - sell_acres,
            land_price=state.land_price,
            starved_this_year=state.starved_this_year,
            starved_total=state.starved_total,
            starved_pct_avg=state.starved_pct_avg,
            immigrants_this_year=state.immigrants_this_year,
            harvest_yield=state.harvest_yield,
            rats_ate=state.rats_ate,
            plague_struck=state.plague_struck,
            plague_next_year=state.plague_next_year,
            is_over=False,
        )

        feed_bushels = 0
        while True:
            val = safe_prompt_int(
                "HOW MANY BUSHELS DO YOU WISH TO FEED YOUR PEOPLE? "
            )
            if val is None:
                return 0
            feed_res = validate_feed_people(temp_state_for_feed, val)
            if feed_res.is_fatal:
                print(f"\n{feed_res.message}")
                print_farewell_beeps(play_audio)
                return 0
            if not feed_res.is_valid:
                print(feed_res.message)
                continue
            feed_bushels = val
            break

        # Step 4: Planting Phase
        print()
        grain_after_feed = grain_after_land - feed_bushels
        plant_acres = 0
        while True:
            val = safe_prompt_int(
                "HOW MANY ACRES DO YOU WISH TO PLANT WITH SEED? "
            )
            if val is None:
                return 0
            plant_res = validate_plant_seed(
                temp_state_for_feed,
                val,
                available_grain=grain_after_feed,
                strict_historical=strict_historical,
            )
            if plant_res.is_fatal:
                print(f"\n{plant_res.message}")
                print_farewell_beeps(play_audio)
                return 0
            if not plant_res.is_valid:
                print(plant_res.message)
                continue
            plant_acres = val
            break

        # Step 5: Advance simulation
        decisions = TurnDecisions(
            buy_acres=buy_acres,
            sell_acres=sell_acres,
            feed_bushels=feed_bushels,
            plant_acres=plant_acres,
        )
        state = step_year(
            state,
            decisions,
            rng=rng,
            strict_historical=strict_historical,
        )

        # Trigger visual event animations if enabled
        if config.enabled:
            print()
            if plant_acres > 0:
                animate_harvest(
                    plant_acres,
                    state.harvest_yield,
                    plant_acres * state.harvest_yield,
                    config,
                )
            if state.rats_ate > 0:
                animate_rats(state.rats_ate, config)
            if state.plague_struck:
                animate_plague(config)

        # Check in-term impeachment
        if state.is_over and state.game_over_reason == "IMPEACHED":
            print(f"\nYOU STARVED {state.starved_this_year} PEOPLE IN ONE YEAR!!!")
            print("DUE TO THIS EXTREME MISMANAGEMENT YOU HAVE NOT ONLY")
            print("BEEN IMPEACHED AND THROWN OUT OF OFFICE BUT YOU HAVE")
            print("ALSO BEEN DECLARED NATIONAL FINK!!!!")
            print_evaluation_banner(1, config)
            print_farewell_beeps(play_audio)
            return 0

    # Step 6: Final Term Evaluation (Year 11 reached)
    if state.year == 11 and state.game_over_reason == "COMPLETED":
        # Print year 10 final report
        if config.enabled:
            print_year_transition(10, config)
            print(render_city_scene(state, config))
        print_year_report(state, config)

        eval_res = evaluate_term(state, rng=rng)
        print(f"IN YOUR 10-YEAR TERM OF OFFICE, {eval_res.avg_starved_pct:.0f} PERCENT OF THE")
        print("POPULATION STARVED PER YEAR ON THE AVERAGE, I.E. A TOTAL OF")
        print(f"{eval_res.total_starved} PEOPLE DIED!!")
        print("YOU STARTED WITH 10 ACRES PER PERSON AND ENDED WITH")
        print(f"{eval_res.acres_per_person:.2f} ACRES PER PERSON.\n")
        print(eval_res.message)
        print_evaluation_banner(eval_res.tier, config)
        print_farewell_beeps(play_audio)

    return 0


def main() -> None:
    """Universal entry point for RetroRevive platform, graphical games, and CLI fallbacks."""
    parser = argparse.ArgumentParser(
        description="RetroRevive — Classic Computer Games Platform (Buildathon 2026)"
    )
    # Mode and launcher flags
    parser.add_argument(
        "--cli", "--no-pygame",
        dest="force_cli",
        action="store_true",
        help="Force zero-dependency standard library terminal interface",
    )
    parser.add_argument(
        "--hammurabi",
        action="store_true",
        help="Launch Hammurabi directly",
    )
    parser.add_argument(
        "--matches",
        action="store_true",
        help="Launch 23 Matches directly",
    )
    parser.add_argument(
        "--screen",
        choices=["main", "gameplay", "governor", "military", "agriculture", "video_creator"],
        default=None,
        help="Launch directly into a specific ministry or dashboard",
    )
    parser.add_argument(
        "--governor",
        action="store_true",
        help="Launch directly into the AI Royal Governor autonomous agent",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch desktop interface in fullscreen mode",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Prompt for sovereign login / registration on application startup",
    )
    parser.add_argument(
        "--guest",
        action="store_true",
        help="Start directly as Guest Sovereign without initial authentication prompt",
    )
    # Historical Hammurabi CLI options
    parser.add_argument(
        "--relaxed",
        action="store_true",
        help="Use modernized/relaxed constraints (D <= 10*P and Q <= A) instead of strict historical '<'",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for reproducible random generation",
    )
    parser.add_argument(
        "--no-sound",
        action="store_true",
        help="Disable terminal bell sound effect at game exit",
    )
    parser.add_argument(
        "--animate",
        dest="animate",
        action="store_true",
        default=None,
        help="Force enable animated ASCII city scenes and transitions",
    )
    parser.add_argument(
        "--no-animate",
        dest="animate",
        action="store_false",
        help="Disable ASCII animations and transitions (classic terminal mode)",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Control ANSI terminal colors (default: auto)",
    )
    parser.add_argument(
        "--speed",
        choices=["fast", "normal", "slow"],
        default="normal",
        help="Animation speed (default: normal)",
    )
    args = parser.parse_args()

    # Determine if CLI execution was explicitly requested or terminal flags provided
    cli_flags_present = (
        args.force_cli
        or args.relaxed
        or (args.seed is not None and not args.fullscreen)
        or (args.animate is False)
        or args.color != "auto"
        or args.speed != "normal"
    )

    # 1. Try launching Pygame Graphical Interface unless CLI is forced
    if not cli_flags_present:
        try:
            import pygame  # noqa: F401
            show_auth = not args.guest
            if args.matches:
                from games import matches_app
                app = matches_app.MatchesApp(start_fullscreen=args.fullscreen)
                app.run()
                return
            elif args.hammurabi or args.governor or args.screen:
                from ui_pygame import GameApp
                app = GameApp(start_fullscreen=args.fullscreen, show_auth_modal=show_auth)
                if args.governor or args.screen == "governor":
                    app._open_governor_screen()
                elif args.screen == "military":
                    app._open_military_screen()
                elif args.screen == "agriculture":
                    app._open_agriculture_screen()
                elif args.screen == "video_creator":
                    app._open_video_creator_screen()
                app.run()
                return
            else:
                # Default: Launch RetroRevive Game Library Hub
                import retrorevive
                hub = retrorevive.RetroReviveHub(start_fullscreen=args.fullscreen, show_auth_modal=show_auth)
                hub.run()
                return
        except ImportError:
            # Fallback smoothly to CLI if Pygame is not installed
            pass

    # 2. Terminal CLI Execution
    if args.matches:
        from games import matches_engine
        matches_engine.play_cli()
        return

    # Standard Hammurabi Terminal CLI
    rng = DefaultRNG(seed=args.seed) if args.seed is not None else None
    strict_historical = not args.relaxed
    play_audio = not args.no_sound

    visual_config = VisualConfig.detect(
        force_animate=args.animate,
        force_color=args.color,
        speed=args.speed,
    )

    sys.exit(
        play_game(
            rng=rng,
            strict_historical=strict_historical,
            play_audio=play_audio,
            visual_config=visual_config,
        )
    )


if __name__ == "__main__":
    main()
