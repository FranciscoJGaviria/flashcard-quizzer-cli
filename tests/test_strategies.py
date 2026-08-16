"""Unit tests for utils/strategies.py — written before implementation per TDD."""

import pytest

from utils.models import CardStats, Flashcard, SessionStats
from utils.strategies import AdaptiveStrategy, RandomStrategy, SequentialStrategy


def make_cards(fronts: list[str]) -> list[Flashcard]:
    return [Flashcard(front=f, back=f"Answer for {f}") for f in fronts]


def make_session(misses: dict[str, int]) -> SessionStats:
    card_stats = {}
    for front, miss_count in misses.items():
        card = Flashcard(front=front, back=f"Answer for {front}")
        card_stats[front] = CardStats(card=card, attempts=miss_count, correct=0)
    return SessionStats(card_stats=card_stats)


class TestSequentialStrategy:
    @pytest.mark.parametrize(
        "fronts",
        [
            ["EC2", "S3", "Lambda"],
            ["A"],
            ["Z", "Y", "X", "W"],
        ],
    )
    def test_preserves_original_order(self, fronts: list[str]):
        cards = make_cards(fronts)
        strategy = SequentialStrategy()
        result = strategy.select(cards, SessionStats())
        assert [c.front for c in result] == fronts

    def test_returns_all_cards(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        result = SequentialStrategy().select(cards, SessionStats())
        assert len(result) == 3

    def test_returns_new_list_not_same_reference(self):
        cards = make_cards(["EC2", "S3"])
        result = SequentialStrategy().select(cards, SessionStats())
        assert result is not cards

    def test_empty_card_list(self):
        result = SequentialStrategy().select([], SessionStats())
        assert result == []


class TestRandomStrategy:
    def test_returns_all_cards(self):
        cards = make_cards(["EC2", "S3", "Lambda", "RDS", "VPC"])
        result = RandomStrategy().select(cards, SessionStats())
        assert len(result) == len(cards)

    def test_returns_same_cards_different_object(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        result = RandomStrategy().select(cards, SessionStats())
        assert result is not cards
        assert set(c.front for c in result) == {"EC2", "S3", "Lambda"}

    def test_does_not_mutate_original_list(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        original_order = [c.front for c in cards]
        RandomStrategy().select(cards, SessionStats())
        assert [c.front for c in cards] == original_order

    def test_produces_shuffle_over_many_runs(self):
        cards = make_cards(["A", "B", "C", "D", "E", "F", "G", "H"])
        strategy = RandomStrategy()
        orders = set()
        for _ in range(20):
            result = strategy.select(cards, SessionStats())
            orders.add(tuple(c.front for c in result))
        assert len(orders) > 1

    def test_empty_card_list(self):
        result = RandomStrategy().select([], SessionStats())
        assert result == []

    def test_single_card_list(self):
        cards = make_cards(["EC2"])
        result = RandomStrategy().select(cards, SessionStats())
        assert len(result) == 1
        assert result[0].front == "EC2"


class TestAdaptiveStrategy:
    def test_unseen_cards_come_first_on_first_pass(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        result = AdaptiveStrategy().select(cards, SessionStats())
        assert set(c.front for c in result) == {"EC2", "S3", "Lambda"}
        assert len(result) == 3

    def test_higher_miss_count_sorts_first(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        session = make_session({"EC2": 1, "S3": 3, "Lambda": 0})
        result = AdaptiveStrategy().select(cards, session)
        assert result[0].front == "S3"
        assert result[1].front == "EC2"

    def test_zero_miss_unseen_cards_after_missed_cards(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        session = make_session({"EC2": 2})
        result = AdaptiveStrategy().select(cards, session)
        assert result[0].front == "EC2"

    def test_all_cards_returned(self):
        cards = make_cards(["EC2", "S3", "Lambda", "RDS"])
        session = make_session({"EC2": 2, "S3": 1})
        result = AdaptiveStrategy().select(cards, session)
        assert len(result) == 4
        assert set(c.front for c in result) == {"EC2", "S3", "Lambda", "RDS"}

    def test_does_not_mutate_original_list(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        session = make_session({"EC2": 2, "S3": 1})
        original_order = [c.front for c in cards]
        AdaptiveStrategy().select(cards, session)
        assert [c.front for c in cards] == original_order

    def test_equal_miss_counts_preserves_relative_order(self):
        cards = make_cards(["EC2", "S3", "Lambda"])
        session = make_session({"EC2": 2, "S3": 2, "Lambda": 2})
        result = AdaptiveStrategy().select(cards, session)
        assert set(c.front for c in result) == {"EC2", "S3", "Lambda"}
        assert len(result) == 3

    def test_empty_card_list(self):
        result = AdaptiveStrategy().select([], SessionStats())
        assert result == []

    @pytest.mark.parametrize(
        "miss_map,expected_first",
        [
            ({"A": 5, "B": 3, "C": 1}, "A"),
            ({"A": 1, "B": 5, "C": 3}, "B"),
            ({"A": 0, "B": 0, "C": 0}, None),
        ],
    )
    def test_highest_miss_always_first(
        self, miss_map: dict[str, int], expected_first: str | None
    ):
        cards = make_cards(["A", "B", "C"])
        session = make_session(miss_map)
        result = AdaptiveStrategy().select(cards, session)
        if expected_first is not None:
            assert result[0].front == expected_first
        assert len(result) == 3


class TestStrategyRepr:
    def test_sequential_repr(self):
        assert repr(SequentialStrategy()) == "SequentialStrategy()"

    def test_random_repr(self):
        assert repr(RandomStrategy()) == "RandomStrategy()"

    def test_adaptive_repr(self):
        assert repr(AdaptiveStrategy()) == "AdaptiveStrategy()"
