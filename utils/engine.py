"""Quiz engine for the CLI Flashcard Quizzer application."""

from typing import TYPE_CHECKING, List, Optional

from utils.models import Flashcard, SessionStats
from utils.strategies import CardSelectionStrategy

if TYPE_CHECKING:
    from utils.display import DisplayProtocol


class QuizEngine:
    """Orchestrates the quiz loop without performing any I/O directly.

    Accepts a card deck, a selection strategy, and a display dependency.
    All terminal interaction is delegated to the DisplayProtocol instance
    so this class remains fully testable with mocks.

    Args:
        cards: The full deck of flashcards for the session.
        strategy: A CardSelectionStrategy that orders the cards.
        display: Any object satisfying DisplayProtocol for I/O.
    """

    def __init__(
        self,
        cards: List[Flashcard],
        strategy: CardSelectionStrategy,
        display: "DisplayProtocol",
    ) -> None:
        self._cards = cards
        self._strategy = strategy
        self._display = display

    def run(self) -> SessionStats:
        """Execute the quiz loop and return aggregated session statistics.

        For each card in strategy order:
            1. Show the card front via display.
            2. Read user input via display (``None`` signals EOF — loop ends).
            3. Evaluate the answer (case-insensitive, stripped).
            4. Show feedback via display.
            5. Record the attempt on SessionStats.

        The summary is shown in a ``finally`` block so it is displayed even
        when the user interrupts the session with ``Ctrl+C``. This guarantees
        partial-session metrics are never silently discarded.

        Returns:
            A SessionStats instance with per-card and aggregate results.
        """
        stats = SessionStats()
        ordered = self._strategy.select(self._cards, stats)

        interrupted = False
        try:
            for card in ordered:
                self._display.show_prompt(card.front)
                raw: Optional[str] = self._display.get_input()
                if raw is None:
                    break
                is_correct = self._evaluate_answer(raw, card.back)
                self._display.show_feedback(is_correct, card.back)
                stats.record_attempt(card, is_correct)
        except KeyboardInterrupt:
            interrupted = True
        finally:
            self._display.show_summary(stats)

        if interrupted:
            raise KeyboardInterrupt

        return stats

    @staticmethod
    def _evaluate_answer(raw: str, expected: str) -> bool:
        """Compare user input against the expected answer.

        Comparison is case-insensitive and strips leading/trailing whitespace
        from both sides so minor formatting differences are ignored. This
        normalisation is communicated to the user via ``show_feedback``
        docstring and the ``--help`` text.

        Args:
            raw: The raw string entered by the user.
            expected: The correct answer from the flashcard back.

        Returns:
            True if the normalised strings match, False otherwise.
        """
        return raw.strip().lower() == expected.strip().lower()
