"""Unit tests for utils/models.py — written before implementation per TDD."""

import pytest

from utils.models import CardStats, Flashcard, SessionStats


class TestFlashcard:
    def test_required_fields_set_correctly(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        assert card.front == "EC2"
        assert card.back == "Amazon Elastic Compute Cloud"

    def test_optional_fields_default_to_empty_string(self):
        card = Flashcard(front="S3", back="Simple Storage Service")
        assert card.id == ""
        assert card.category == ""
        assert card.description == ""

    def test_optional_fields_can_be_set(self):
        card = Flashcard(
            front="EC2",
            back="Amazon Elastic Compute Cloud",
            id="ec2",
            category="Compute",
            description="Virtual server hosting",
        )
        assert card.id == "ec2"
        assert card.category == "Compute"
        assert card.description == "Virtual server hosting"


class TestCardStats:
    def test_attempts_and_correct_default_to_zero(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        stats = CardStats(card=card)
        assert stats.attempts == 0
        assert stats.correct == 0

    def test_misses_is_zero_when_no_attempts(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        stats = CardStats(card=card)
        assert stats.misses == 0

    def test_misses_equals_attempts_minus_correct(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        stats = CardStats(card=card, attempts=5, correct=3)
        assert stats.misses == 2

    def test_misses_zero_when_all_correct(self):
        card = Flashcard(front="S3", back="Simple Storage Service")
        stats = CardStats(card=card, attempts=4, correct=4)
        assert stats.misses == 0

    def test_card_reference_is_preserved(self):
        card = Flashcard(front="Lambda", back="Serverless compute")
        stats = CardStats(card=card)
        assert stats.card is card


class TestSessionStats:
    def test_defaults_to_zero_totals_and_empty_stats(self):
        session = SessionStats()
        assert session.total_attempts == 0
        assert session.total_correct == 0
        assert session.card_stats == {}

    def test_accuracy_is_zero_when_no_attempts(self):
        session = SessionStats()
        assert session.accuracy == 0.0

    def test_accuracy_100_when_all_correct(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        cs = CardStats(card=card, attempts=3, correct=3)
        session = SessionStats(card_stats={"EC2": cs})
        assert session.accuracy == 100.0

    def test_accuracy_calculated_correctly(self):
        card = Flashcard(front="S3", back="Simple Storage Service")
        cs = CardStats(card=card, attempts=4, correct=1)
        session = SessionStats(card_stats={"S3": cs})
        assert session.accuracy == pytest.approx(25.0)

    def test_missed_cards_empty_when_all_correct(self):
        card = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        cs = CardStats(card=card, attempts=2, correct=2)
        session = SessionStats(card_stats={"EC2": cs})
        assert session.missed_cards == []

    def test_missed_cards_returns_cards_with_at_least_one_miss(self):
        card_a = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        card_b = Flashcard(front="S3", back="Simple Storage Service")
        cs_a = CardStats(card=card_a, attempts=3, correct=3)
        cs_b = CardStats(card=card_b, attempts=2, correct=1)
        session = SessionStats(card_stats={"EC2": cs_a, "S3": cs_b})
        assert session.missed_cards == [card_b]

    def test_missed_cards_returns_all_missed(self):
        card_a = Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")
        card_b = Flashcard(front="S3", back="Simple Storage Service")
        cs_a = CardStats(card=card_a, attempts=1, correct=0)
        cs_b = CardStats(card=card_b, attempts=1, correct=0)
        session = SessionStats(card_stats={"EC2": cs_a, "S3": cs_b})
        assert set(c.front for c in session.missed_cards) == {"EC2", "S3"}

    def test_total_attempts_derived_from_card_stats(self):
        card_a = Flashcard(front="EC2", back="Elastic Compute Cloud")
        card_b = Flashcard(front="S3", back="Simple Storage")
        cs_a = CardStats(card=card_a, attempts=3, correct=2)
        cs_b = CardStats(card=card_b, attempts=2, correct=1)
        session = SessionStats(card_stats={"EC2": cs_a, "S3": cs_b})
        assert session.total_attempts == 5

    def test_total_correct_derived_from_card_stats(self):
        card_a = Flashcard(front="EC2", back="Elastic Compute Cloud")
        card_b = Flashcard(front="S3", back="Simple Storage")
        cs_a = CardStats(card=card_a, attempts=3, correct=2)
        cs_b = CardStats(card=card_b, attempts=2, correct=1)
        session = SessionStats(card_stats={"EC2": cs_a, "S3": cs_b})
        assert session.total_correct == 3


class TestSessionStatsRecordAttempt:
    def test_record_attempt_creates_card_stats_entry(self):
        session = SessionStats()
        card = Flashcard(front="EC2", back="Elastic Compute Cloud")
        session.record_attempt(card, True)
        assert "EC2" in session.card_stats

    def test_record_correct_attempt_increments_attempts_and_correct(self):
        session = SessionStats()
        card = Flashcard(front="EC2", back="Elastic Compute Cloud")
        session.record_attempt(card, True)
        assert session.total_attempts == 1
        assert session.total_correct == 1

    def test_record_incorrect_attempt_increments_attempts_only(self):
        session = SessionStats()
        card = Flashcard(front="EC2", back="Elastic Compute Cloud")
        session.record_attempt(card, False)
        assert session.total_attempts == 1
        assert session.total_correct == 0

    def test_record_multiple_attempts_accumulates(self):
        session = SessionStats()
        card = Flashcard(front="EC2", back="Elastic Compute Cloud")
        session.record_attempt(card, True)
        session.record_attempt(card, False)
        session.record_attempt(card, True)
        assert session.card_stats["EC2"].attempts == 3
        assert session.card_stats["EC2"].correct == 2

    def test_totals_always_consistent_with_card_stats(self):
        session = SessionStats()
        card_a = Flashcard(front="EC2", back="Elastic Compute Cloud")
        card_b = Flashcard(front="S3", back="Simple Storage")
        session.record_attempt(card_a, True)
        session.record_attempt(card_b, False)
        session.record_attempt(card_a, True)
        total_from_cards = sum(cs.attempts for cs in session.card_stats.values())
        correct_from_cards = sum(cs.correct for cs in session.card_stats.values())
        assert session.total_attempts == total_from_cards
        assert session.total_correct == correct_from_cards
