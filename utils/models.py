"""Data models for the CLI Flashcard Quizzer application."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Flashcard:
    """Represents a single flashcard with a front (prompt) and back (answer).

    Args:
        front: The prompt shown to the user. Required.
        back: The expected answer. Required.
        id: Optional unique identifier for the card.
        category: Optional grouping category.
        description: Optional extended description.
    """

    front: str
    back: str
    id: str = ""
    category: str = ""
    description: str = ""


@dataclass
class CardStats:
    """Tracks attempt statistics for a single flashcard.

    Args:
        card: The flashcard this stat record belongs to.
        attempts: Total number of times the card was shown.
        correct: Number of times the answer was correct.
    """

    card: Flashcard
    attempts: int = 0
    correct: int = 0

    @property
    def misses(self) -> int:
        """Number of incorrect attempts.

        Returns:
            Difference between total attempts and correct answers.
        """
        return self.attempts - self.correct


@dataclass
class SessionStats:
    """Aggregated statistics for a complete quiz session.

    Totals are derived from per-card statistics to guarantee a single
    source of truth — ``total_attempts`` and ``total_correct`` are
    computed properties rather than stored fields.

    Args:
        card_stats: Mapping of card front text to its CardStats instance.
    """

    card_stats: Dict[str, CardStats] = field(default_factory=dict)

    @property
    def total_attempts(self) -> int:
        """Total answers submitted across all cards.

        Returns:
            Sum of attempts across all CardStats entries.
        """
        return sum(cs.attempts for cs in self.card_stats.values())

    @property
    def total_correct(self) -> int:
        """Total correct answers across all cards.

        Returns:
            Sum of correct across all CardStats entries.
        """
        return sum(cs.correct for cs in self.card_stats.values())

    @property
    def accuracy(self) -> float:
        """Percentage of correct answers over total attempts.

        Returns:
            Float between 0.0 and 100.0, or 0.0 if no attempts recorded.
        """
        if self.total_attempts == 0:
            return 0.0
        return (self.total_correct / self.total_attempts) * 100.0

    @property
    def missed_cards(self) -> List[Flashcard]:
        """All cards that were answered incorrectly at least once.

        Returns:
            List of Flashcard instances with at least one miss.
        """
        return [cs.card for cs in self.card_stats.values() if cs.misses > 0]

    def record_attempt(self, card: Flashcard, is_correct: bool) -> None:
        """Record one answer attempt for *card* and update per-card stats.

        Creates a new CardStats entry for *card* on first encounter.
        All aggregate totals (total_attempts, total_correct) are derived
        from card_stats, so they remain consistent automatically.

        Args:
            card: The flashcard that was just attempted.
            is_correct: Whether the user's answer was correct.
        """
        if card.front not in self.card_stats:
            self.card_stats[card.front] = CardStats(card=card)
        cs = self.card_stats[card.front]
        cs.attempts += 1
        if is_correct:
            cs.correct += 1
