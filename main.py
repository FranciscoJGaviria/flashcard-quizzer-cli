"""Entry point for the CLI Flashcard Quizzer application.

Usage:
    python main.py [--file PATH] [--mode {sequential,random,adaptive}]

Wires together FlashcardLoader, a CardSelectionStrategy, QuizEngine,
and Display, then launches the quiz loop.
"""

import argparse
import sys
from typing import Dict, List, Optional, Type

from utils.display import Display
from utils.engine import QuizEngine
from utils.loader import FlashcardLoader, FlashcardLoadError
from utils.models import SessionStats
from utils.strategies import (
    AdaptiveStrategy,
    CardSelectionStrategy,
    RandomStrategy,
    SequentialStrategy,
)

DEFAULT_DATA_FILE = "data/aws_services.json"

STRATEGIES: Dict[str, Type[CardSelectionStrategy]] = {
    "sequential": SequentialStrategy,
    "random": RandomStrategy,
    "adaptive": AdaptiveStrategy,
}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list to parse. Defaults to sys.argv when None.

    Returns:
        Parsed namespace with ``file`` and ``mode`` attributes.
    """
    parser = argparse.ArgumentParser(
        description="CLI Flashcard Quizzer — memorize service acronyms."
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_DATA_FILE,
        help=f"Path to flashcard JSON file (default: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--mode",
        choices=list(STRATEGIES),
        default="sequential",
        help=(
            "Quiz mode: sequential | random | adaptive (default: sequential). "
            "Answers are matched case-insensitively with leading/trailing "
            "whitespace stripped."
        ),
    )
    return parser.parse_args(argv)


def build_strategy(mode: str) -> CardSelectionStrategy:
    """Instantiate the correct CardSelectionStrategy for *mode*.

    Args:
        mode: One of ``"sequential"``, ``"random"``, or ``"adaptive"``.

    Returns:
        A concrete CardSelectionStrategy instance.

    Raises:
        ValueError: If *mode* is not a recognised strategy key.
    """
    if mode not in STRATEGIES:
        raise ValueError(f"Unknown mode {mode!r}. Valid modes: {list(STRATEGIES)}")
    return STRATEGIES[mode]()


def main(argv: Optional[List[str]] = None) -> int:
    """Application entry point.

    Parses CLI arguments, loads cards, wires dependencies, and runs the quiz.
    Supports interactive multi-round sessions until the user decides to exit.
    Handles KeyboardInterrupt (Ctrl+C) with a clean exit message.

    Args:
        argv: Optional argument list (used for testing). Defaults to sys.argv.

    Returns:
        Exit code: 0 on success, 1 on error, 130 on keyboard interrupt.
    """
    args = parse_args(argv)
    display = Display()

    try:
        cards = FlashcardLoader().load(args.file)
    except FlashcardLoadError as exc:
        display.show_error(str(exc))
        return 1

    if not cards:
        display.show_error(f"No cards found in {args.file}.")
        return 1

    strategy = build_strategy(args.mode)
    display.show_info(f"Loaded {len(cards)} card(s) — mode: {args.mode}")

    last_stats: Optional[SessionStats] = None
    engine = QuizEngine(cards, strategy, display)
    try:
        while True:
            last_stats = engine.run(previous_stats=last_stats)
            if not display.ask_continue():
                break
    except KeyboardInterrupt:
        print("\n\n[Quiz interrupted. Goodbye!]")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
