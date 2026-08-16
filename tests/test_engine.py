"""Unit tests for utils/engine.py — written before implementation per TDD."""

from unittest.mock import MagicMock

import pytest

from utils.engine import QuizEngine
from utils.models import Flashcard, SessionStats
from utils.strategies import SequentialStrategy


def make_display(answers: list[str]) -> MagicMock:
    display = MagicMock()
    display.get_input.side_effect = answers
    return display


def make_cards(pairs: list[tuple[str, str]]) -> list[Flashcard]:
    return [Flashcard(front=f, back=b) for f, b in pairs]


class TestQuizEngineStats:
    def test_correct_answer_increments_total_correct(self):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display(["amazon elastic compute cloud"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 1

    def test_correct_answer_increments_total_attempts(self):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display(["amazon elastic compute cloud"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_attempts == 1

    def test_incorrect_answer_does_not_increment_correct(self):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display(["wrong answer"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 0
        assert stats.total_attempts == 1

    def test_multiple_cards_all_correct(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["elastic compute cloud", "simple storage"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 2
        assert stats.total_attempts == 2

    def test_mixed_correct_and_incorrect(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["elastic compute cloud", "wrong"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 1
        assert stats.total_attempts == 2

    def test_returns_session_stats_instance(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        result = QuizEngine(cards, SequentialStrategy(), display).run()
        assert isinstance(result, SessionStats)


class TestQuizEngineAnswerEvaluation:
    @pytest.mark.parametrize(
        "user_input",
        [
            "Amazon Elastic Compute Cloud",
            "amazon elastic compute cloud",
            "AMAZON ELASTIC COMPUTE CLOUD",
            "Amazon ELASTIC compute Cloud",
        ],
    )
    def test_answer_comparison_is_case_insensitive(self, user_input: str):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display([user_input])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 1

    def test_whitespace_stripped_from_input(self):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display(["  amazon elastic compute cloud  "])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_correct == 1

    def test_wrong_answer_counted_as_miss(self):
        cards = make_cards([("EC2", "Amazon Elastic Compute Cloud")])
        display = make_display(["nope"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert "EC2" in stats.card_stats
        assert stats.card_stats["EC2"].misses == 1


class TestQuizEngineCardStats:
    def test_card_stats_populated_for_each_card(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["elastic compute cloud", "simple storage"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert "EC2" in stats.card_stats
        assert "S3" in stats.card_stats

    def test_correct_card_stat_attempts_and_correct(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        cs = stats.card_stats["EC2"]
        assert cs.attempts == 1
        assert cs.correct == 1

    def test_incorrect_card_stat_attempts_and_correct(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["wrong"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        cs = stats.card_stats["EC2"]
        assert cs.attempts == 1
        assert cs.correct == 0

    def test_missed_cards_list_contains_wrong_answers(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["wrong", "simple storage"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        missed_fronts = [c.front for c in stats.missed_cards]
        assert "EC2" in missed_fronts
        assert "S3" not in missed_fronts


class TestQuizEngineDisplayInteractions:
    def test_show_prompt_called_for_each_card(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["elastic compute cloud", "simple storage"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        assert display.show_prompt.call_count == 2

    def test_show_prompt_called_with_card_front(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        display.show_prompt.assert_called_once_with("EC2")

    def test_show_feedback_called_for_each_card(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud"), ("S3", "Simple Storage")])
        display = make_display(["elastic compute cloud", "wrong"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        assert display.show_feedback.call_count == 2

    def test_show_feedback_correct_flag_true_on_correct(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        args = display.show_feedback.call_args
        assert args[0][0] is True

    def test_show_feedback_correct_flag_false_on_wrong(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["wrong"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        args = display.show_feedback.call_args
        assert args[0][0] is False

    def test_show_feedback_passes_correct_answer(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["wrong"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        args = display.show_feedback.call_args
        assert args[0][1] == "Elastic Compute Cloud"

    def test_show_summary_called_once_at_end(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        assert display.show_summary.call_count == 1

    def test_show_summary_receives_session_stats(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud"])
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        display.show_summary.assert_called_once_with(stats)


class TestQuizEngineEdgeCases:
    def test_empty_card_list_returns_empty_stats(self):
        display = MagicMock()
        stats = QuizEngine([], SequentialStrategy(), display).run()
        assert stats.total_attempts == 0
        assert stats.total_correct == 0

    def test_empty_card_list_show_summary_still_called(self):
        display = MagicMock()
        QuizEngine([], SequentialStrategy(), display).run()
        assert display.show_summary.call_count == 1

    def test_session_ends_after_all_cards_shown(self):
        cards = make_cards([("EC2", "EC"), ("S3", "S3")])
        display = make_display(["ec", "s3"])
        QuizEngine(cards, SequentialStrategy(), display).run()
        assert display.get_input.call_count == 2


class TestQuizEngineEOFAndInterrupt:
    def test_none_from_get_input_stops_loop_immediately(self):
        cards = make_cards([("EC2", "EC"), ("S3", "S3")])
        display = MagicMock()
        display.get_input.return_value = None
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_attempts == 0
        display.show_summary.assert_called_once()

    def test_none_from_get_input_does_not_record_attempt(self):
        cards = make_cards([("EC2", "EC")])
        display = MagicMock()
        display.get_input.return_value = None
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert "EC2" not in stats.card_stats

    def test_none_mid_session_shows_partial_summary(self):
        cards = make_cards([("EC2", "EC"), ("S3", "S3"), ("RDS", "RDS")])
        display = MagicMock()
        display.get_input.side_effect = ["ec", None]
        stats = QuizEngine(cards, SequentialStrategy(), display).run()
        assert stats.total_attempts == 1
        display.show_summary.assert_called_once_with(stats)

    def test_keyboard_interrupt_shows_summary_then_reraises(self):
        cards = make_cards([("EC2", "EC"), ("S3", "S3")])
        display = MagicMock()
        display.get_input.side_effect = ["ec", KeyboardInterrupt]
        with pytest.raises(KeyboardInterrupt):
            QuizEngine(cards, SequentialStrategy(), display).run()
        display.show_summary.assert_called_once()

    def test_keyboard_interrupt_partial_stats_in_summary(self):
        cards = make_cards([("EC2", "EC"), ("S3", "S3")])
        display = MagicMock()
        display.get_input.side_effect = ["ec", KeyboardInterrupt]
        captured_stats = []
        display.show_summary.side_effect = lambda s: captured_stats.append(s)
        with pytest.raises(KeyboardInterrupt):
            QuizEngine(cards, SequentialStrategy(), display).run()
        assert len(captured_stats) == 1
        assert captured_stats[0].total_attempts == 1


class TestQuizEngineMultiRound:
    def test_run_summary_shows_only_current_round_stats(self):
        cards = make_cards([("EC2", "Elastic Compute Cloud")])
        display = make_display(["elastic compute cloud", "elastic compute cloud"])
        engine = QuizEngine(cards, SequentialStrategy(), display)

        # Round 1
        r1_stats = engine.run()
        assert r1_stats.total_attempts == 1
        assert r1_stats.total_correct == 1

        # Round 2 with previous stats passed for ordering
        r2_stats = engine.run(previous_stats=r1_stats)
        assert r2_stats.total_attempts == 1
        assert r2_stats.total_correct == 1

    def test_adaptive_mode_multi_round_ordering_and_isolated_summaries(self):
        from utils.strategies import AdaptiveStrategy

        cards = make_cards(
            [
                ("pacho", "francisco"),
                ("mochi", "olga"),
                ("hijo", "martin"),
                ("bebe", "Victoria o Samuel"),
            ]
        )
        prompt_order = []
        summaries = []
        display = MagicMock()
        display.show_prompt.side_effect = lambda front: prompt_order.append(front)
        display.show_summary.side_effect = lambda s: summaries.append(s)

        engine = QuizEngine(cards, AdaptiveStrategy(), display)

        # --- Round 1: miss pacho and bebe ---
        display.get_input.side_effect = [
            "wrong",
            "olga",
            "martin",
            "wrong",
        ]
        prompt_order.clear()
        r1_stats = engine.run(previous_stats=None)
        assert prompt_order == ["pacho", "mochi", "hijo", "bebe"]
        assert r1_stats.total_attempts == 4
        assert r1_stats.total_correct == 2
        assert [c.front for c in r1_stats.missed_cards] == ["pacho", "bebe"]
        assert summaries[-1].total_attempts == 4

        # --- Round 2: pass r1_stats -> pacho and bebe first ---
        # User gets pacho and bebe right, but misses hijo
        display.get_input.side_effect = [
            "francisco",
            "Victoria o Samuel",
            "olga",
            "wrong",
        ]
        prompt_order.clear()
        r2_stats = engine.run(previous_stats=r1_stats)
        assert prompt_order[:2] == ["pacho", "bebe"]
        assert r2_stats.total_attempts == 4
        assert r2_stats.total_correct == 3
        assert [c.front for c in r2_stats.missed_cards] == ["hijo"]
        assert summaries[-1].total_attempts == 4
        assert summaries[-1].accuracy == 75.0

        # --- Round 3: pass r2_stats -> hijo first ---
        # User gets all 4 right!
        display.get_input.side_effect = [
            "martin",
            "francisco",
            "olga",
            "Victoria o Samuel",
        ]
        prompt_order.clear()
        r3_stats = engine.run(previous_stats=r2_stats)
        assert prompt_order[0] == "hijo"
        assert r3_stats.total_attempts == 4
        assert r3_stats.total_correct == 4
        assert r3_stats.missed_cards == []
        assert summaries[-1].total_attempts == 4
        assert summaries[-1].accuracy == 100.0


class TestMainLoop:
    def test_main_single_round_exit(self, monkeypatch):
        from main import main

        monkeypatch.setattr(
            "utils.display.Display.get_input", lambda self: "some answer"
        )
        monkeypatch.setattr(
            "utils.display.Display.ask_continue", lambda self, prompt="": False
        )
        exit_code = main(["--file", "data/aws_services.json", "--mode", "sequential"])
        assert exit_code == 0

    def test_main_multi_round_loop(self, monkeypatch):
        from main import main

        rounds = [True, False]
        monkeypatch.setattr(
            "utils.display.Display.get_input", lambda self: "some answer"
        )
        monkeypatch.setattr(
            "utils.display.Display.ask_continue",
            lambda self, prompt="": rounds.pop(0),
        )
        exit_code = main(["--file", "data/aws_services.json", "--mode", "adaptive"])
        assert exit_code == 0
        assert len(rounds) == 0

    def test_main_keyboard_interrupt_during_ask_continue(self, monkeypatch):
        from main import main

        def raise_interrupt(self, prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr(
            "utils.display.Display.get_input", lambda self: "some answer"
        )
        monkeypatch.setattr("utils.display.Display.ask_continue", raise_interrupt)
        exit_code = main(["--file", "data/aws_services.json", "--mode", "sequential"])
        assert exit_code == 130
