"""Card selection strategies for the CLI Flashcard Quizzer application."""

import random
from abc import ABC, abstractmethod
from typing import List

from utils.models import Flashcard, SessionStats


class CardSelectionStrategy(ABC):
    """Abstract base class for card ordering algorithms.

    Concrete subclasses implement different quiz modes by defining
    how the ordered card list is produced for each session.
    """

    @abstractmethod
    def select(self, cards: List[Flashcard], stats: SessionStats) -> List[Flashcard]:
        """Return an ordered list of cards for this quiz session.

        Args:
            cards: The full deck of flashcards to select from.
            stats: Current session statistics used by adaptive strategies.

        Returns:
            A new list of Flashcard objects in the desired presentation order.
        """


class SequentialStrategy(CardSelectionStrategy):
    """Returns cards in their original index order (1 to N)."""

    def __repr__(self) -> str:
        return "SequentialStrategy()"

    def select(self, cards: List[Flashcard], stats: SessionStats) -> List[Flashcard]:
        """Return a copy of cards preserving original order.

        Args:
            cards: The full deck of flashcards.
            stats: Unused; present for interface compliance.

        Returns:
            A new list with cards in their original order.
        """
        return list(cards)


class RandomStrategy(CardSelectionStrategy):
    """Returns a shuffled copy of the deck."""

    def __repr__(self) -> str:
        return "RandomStrategy()"

    def select(self, cards: List[Flashcard], stats: SessionStats) -> List[Flashcard]:
        """Return a shuffled copy of cards without mutating the original.

        Args:
            cards: The full deck of flashcards.
            stats: Unused; present for interface compliance.

        Returns:
            A new list with cards in a random order.
        """
        shuffled = list(cards)
        random.shuffle(shuffled)
        return shuffled


class AdaptiveStrategy(CardSelectionStrategy):
    """Prioritises cards the user has previously missed.

    Sort order:
        1. Cards with the highest miss count appear first (DESC).
        2. Unseen cards (not in stats) or zero-miss cards appear last,
           preserving their relative original order.

    Note:
        Ties in miss count preserve insertion order because Python's
        ``sorted()`` is guaranteed to be stable (PEP 3109 / Timsort).
    """

    def __repr__(self) -> str:
        return "AdaptiveStrategy()"

    def select(self, cards: List[Flashcard], stats: SessionStats) -> List[Flashcard]:
        """Return cards sorted by miss count descending.

        Cards with no recorded stats are treated as having zero misses and
        appear after all cards with at least one miss, in their original
        relative order (guaranteed by Python's stable sort).

        Args:
            cards: The full deck of flashcards.
            stats: Session statistics used to look up per-card miss counts.

        Returns:
            A new list with highest-miss cards first.
        """

        def miss_count(card: Flashcard) -> int:
            card_stat = stats.card_stats.get(card.front)
            return card_stat.misses if card_stat is not None else 0

        return sorted(cards, key=miss_count, reverse=True)
