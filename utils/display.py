"""CLI rendering for the Flashcard Quizzer application."""

import re
import sys
from typing import Optional, Protocol, runtime_checkable

from utils.models import SessionStats

_SUMMARY_WIDTH = 40
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _sanitise(text: str) -> str:
    """Strip ANSI escape sequences from *text* before printing.

    Prevents crafted card content from manipulating terminal state
    (screen clear, colour spoofing, cursor repositioning, etc.).

    Args:
        text: Raw string that may contain ANSI escape codes.

    Returns:
        The string with all ANSI CSI sequences removed.
    """
    return _ANSI_ESCAPE.sub("", text)


def _safe_print(text: str) -> None:
    """Print *text*, replacing unencodable characters instead of crashing.

    On legacy terminals (e.g. Windows ``cmd.exe`` with a non-UTF-8 codepage)
    characters such as ``✓`` and ``✗`` may not be representable. Using
    ``errors="replace"`` ensures the application never raises
    ``UnicodeEncodeError`` in those environments.

    Args:
        text: The string to write to stdout.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        print(
            text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            )
        )


@runtime_checkable
class DisplayProtocol(Protocol):
    """Structural interface that any display implementation must satisfy.

    QuizEngine depends on this protocol rather than the concrete Display
    class, fulfilling the Dependency Inversion Principle. Any object that
    implements all five methods is a valid display — no subclassing required.
    """

    def show_prompt(self, front: str) -> None:
        """Show the card front to the user."""
        ...

    def get_input(self) -> Optional[str]:
        """Read and return the user's answer, or None on EOF."""
        ...

    def show_feedback(self, is_correct: bool, correct_answer: str) -> None:
        """Show whether the answer was correct and reveal the expected answer."""
        ...

    def show_summary(self, stats: SessionStats) -> None:
        """Show the end-of-session summary."""
        ...

    def show_error(self, message: str) -> None:
        """Show a user-friendly error message."""
        ...

    def ask_continue(self, prompt: str = "Play another round? (y/n): ") -> bool:
        """Prompt the user to continue the quiz session."""
        ...


class Display:
    """Handles all terminal I/O: prompts, feedback, summary table, and errors.

    This class is the single point of contact for stdout/stdin so that
    QuizEngine remains fully testable without capturing real terminal output.
    Implements DisplayProtocol structurally.

    Security notes:
        - All card text is sanitised through ``_sanitise()`` before printing
          to strip ANSI escape sequences that could manipulate terminal state.
        - Output is printed via ``_safe_print()`` which handles
          ``UnicodeEncodeError`` on legacy terminals without crashing.
    """

    def show_prompt(self, front: str) -> None:
        """Print the card front to the terminal.

        Card text is sanitised to remove ANSI escape sequences before display.

        Args:
            front: The prompt side of the flashcard to display.
        """
        _safe_print(f"\nCard: {_sanitise(front)}")

    def get_input(self) -> Optional[str]:
        """Read and return the user's answer from stdin.

        Returns ``None`` if stdin is closed (``EOFError``). The quiz engine
        treats ``None`` as a signal to stop the quiz loop immediately, so no
        cards are silently marked incorrect when input is exhausted.

        Returns:
            The raw string entered by the user, or ``None`` on EOF.
        """
        try:
            return input("Your answer: ")
        except EOFError:
            return None

    def show_feedback(self, is_correct: bool, correct_answer: str) -> None:
        """Print feedback after an answer attempt.

        Correct-answer text is sanitised before display.
        Answer matching is case-insensitive and strips leading/trailing
        whitespace; this normalisation is applied transparently so users
        are not penalised for minor formatting differences.

        Args:
            is_correct: True if the user's answer was correct.
            correct_answer: The expected answer, shown on incorrect attempts.
        """
        if is_correct:
            _safe_print("✓ Correct!")
        else:
            _safe_print(
                f"✗ Incorrect. The correct answer is: {_sanitise(correct_answer)}"
            )

    def show_summary(self, stats: SessionStats) -> None:
        """Print the end-of-session summary table.

        Displays total questions attempted, accuracy percentage, and a list
        of any terms the user missed at least once. Card fronts are sanitised
        before display.

        Args:
            stats: The completed SessionStats from the quiz engine.
        """
        _safe_print("\n" + "=" * _SUMMARY_WIDTH)
        _safe_print("         SESSION SUMMARY")
        _safe_print("=" * _SUMMARY_WIDTH)
        _safe_print(f"  Total Questions : {stats.total_attempts}")
        _safe_print(f"  Correct         : {stats.total_correct}")
        _safe_print(f"  Accuracy        : {stats.accuracy:.0f}%")
        _safe_print("-" * _SUMMARY_WIDTH)

        missed = stats.missed_cards
        if missed:
            _safe_print("  Missed Terms:")
            for card in missed:
                _safe_print(f"    - {_sanitise(card.front)}")
        else:
            _safe_print("  Missed Terms    : None")

        _safe_print("=" * _SUMMARY_WIDTH)

    def show_info(self, message: str) -> None:
        """Print an informational banner message.

        Args:
            message: The information to display.
        """
        _safe_print(f"\n{message}\n")

    def show_error(self, message: str) -> None:
        """Print a user-friendly error message.

        Args:
            message: The error description to display.
        """
        _safe_print(f"Error: {message}")

    def ask_continue(self, prompt: str = "Play another round? (y/n): ") -> bool:
        """Prompt the user to decide whether to continue the quiz.

        Args:
            prompt: Question displayed to the user. Defaults to
                ``"Play another round? (y/n): "``.

        Returns:
            True if user entered 'y' or 'yes' (case-insensitive, whitespace
            stripped), False otherwise or on EOF.
        """
        try:
            raw = input(prompt)
            return raw.strip().lower() in ("y", "yes")
        except EOFError:
            return False
