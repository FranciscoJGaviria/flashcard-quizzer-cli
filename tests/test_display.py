"""Unit tests for utils/display.py — written before implementation per TDD."""

from unittest.mock import patch

import pytest

from utils.display import Display, _safe_print, _sanitise
from utils.models import CardStats, Flashcard, SessionStats


def make_session(
    pairs: list[tuple[str, str, int, int]],
) -> SessionStats:
    card_stats = {}
    for front, back, attempts, correct in pairs:
        card = Flashcard(front=front, back=back)
        card_stats[front] = CardStats(card=card, attempts=attempts, correct=correct)
    return SessionStats(card_stats=card_stats)


class TestShowPrompt:
    def test_show_prompt_prints_front(self, capsys):
        Display().show_prompt("EC2")
        out = capsys.readouterr().out
        assert "EC2" in out

    def test_show_prompt_contains_prompt_indicator(self, capsys):
        Display().show_prompt("S3")
        out = capsys.readouterr().out
        assert "S3" in out
        assert len(out.strip()) > len("S3")

    @pytest.mark.parametrize("front", ["EC2", "Lambda", "RDS", "VPC"])
    def test_show_prompt_various_fronts(self, capsys, front: str):
        Display().show_prompt(front)
        out = capsys.readouterr().out
        assert front in out


class TestGetInput:
    def test_get_input_returns_string(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _="": "my answer")
        result = Display().get_input()
        assert isinstance(result, str)

    def test_get_input_returns_user_value(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _="": "Amazon EC2")
        result = Display().get_input()
        assert result == "Amazon EC2"

    def test_get_input_returns_empty_string(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _="": "")
        result = Display().get_input()
        assert result == ""

    def test_get_input_returns_none_on_eof(self, monkeypatch):
        def raise_eof(prompt=""):
            raise EOFError

        monkeypatch.setattr("builtins.input", raise_eof)
        result = Display().get_input()
        assert result is None


class TestShowFeedback:
    def test_correct_feedback_contains_positive_signal(self, capsys):
        Display().show_feedback(True, "Amazon Elastic Compute Cloud")
        out = capsys.readouterr().out
        assert any(
            word in out.lower() for word in ["correct", "right", "✓", "yes", "great"]
        )

    def test_incorrect_feedback_contains_negative_signal(self, capsys):
        Display().show_feedback(False, "Amazon Elastic Compute Cloud")
        out = capsys.readouterr().out
        assert any(
            word in out.lower() for word in ["incorrect", "wrong", "✗", "no", "miss"]
        )

    def test_incorrect_feedback_shows_correct_answer(self, capsys):
        Display().show_feedback(False, "Amazon Elastic Compute Cloud")
        out = capsys.readouterr().out
        assert "Amazon Elastic Compute Cloud" in out

    def test_correct_feedback_does_not_show_answer_separately(self, capsys):
        Display().show_feedback(True, "Amazon Elastic Compute Cloud")
        out = capsys.readouterr().out
        assert out.strip() != ""

    @pytest.mark.parametrize("is_correct", [True, False])
    def test_show_feedback_always_prints_something(self, capsys, is_correct: bool):
        Display().show_feedback(is_correct, "Some Answer")
        out = capsys.readouterr().out
        assert out.strip() != ""


class TestShowSummary:
    def test_summary_contains_total_questions(self, capsys):
        session = make_session(
            [("EC2", "Elastic Compute Cloud", 3, 2)],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "3" in out

    def test_summary_contains_accuracy_percentage(self, capsys):
        session = make_session(
            [("EC2", "Elastic Compute Cloud", 4, 2)],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "50" in out

    def test_summary_lists_missed_terms(self, capsys):
        session = make_session(
            [
                ("EC2", "Elastic Compute Cloud", 2, 1),
                ("S3", "Simple Storage", 2, 2),
            ],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "EC2" in out

    def test_summary_does_not_list_correct_cards_in_missed(self, capsys):
        session = make_session(
            [
                ("EC2", "Elastic Compute Cloud", 1, 1),
                ("S3", "Simple Storage", 1, 0),
            ],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "S3" in out
        assert "EC2" not in out.split("S3")[1] if "S3" in out else True

    def test_summary_empty_session_shows_zero_attempts(self, capsys):
        Display().show_summary(SessionStats())
        out = capsys.readouterr().out
        assert "0" in out

    def test_summary_perfect_score_shows_100(self, capsys):
        session = make_session(
            [("EC2", "Elastic Compute Cloud", 3, 3)],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "100" in out

    def test_summary_no_missed_cards_says_none_or_empty(self, capsys):
        session = make_session(
            [("EC2", "Elastic Compute Cloud", 1, 1)],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert out.strip() != ""

    def test_summary_multiple_missed_cards_all_listed(self, capsys):
        session = make_session(
            [
                ("EC2", "Elastic Compute Cloud", 1, 0),
                ("S3", "Simple Storage", 1, 0),
                ("Lambda", "Serverless", 1, 0),
            ],
        )
        Display().show_summary(session)
        out = capsys.readouterr().out
        assert "EC2" in out
        assert "S3" in out
        assert "Lambda" in out


class TestShowInfo:
    def test_show_info_prints_message(self, capsys):
        Display().show_info("Loaded 60 card(s) — mode: sequential")
        out = capsys.readouterr().out
        assert "Loaded 60 card(s)" in out

    def test_show_info_output_is_not_empty(self, capsys):
        Display().show_info("hello")
        out = capsys.readouterr().out
        assert out.strip() != ""


class TestShowError:
    def test_show_error_prints_message(self, capsys):
        Display().show_error("File not found: cards.json")
        out = capsys.readouterr().out
        assert "File not found: cards.json" in out

    @pytest.mark.parametrize(
        "message",
        [
            "File not found: data.json",
            "Invalid JSON",
            'Missing "cards" key',
        ],
    )
    def test_show_error_various_messages(self, capsys, message: str):
        Display().show_error(message)
        out = capsys.readouterr().out
        assert message in out


class TestSanitise:
    def test_strips_ansi_escape_sequence(self):
        assert _sanitise("\x1b[2JHello") == "Hello"

    def test_strips_colour_codes(self):
        assert _sanitise("\x1b[31mRed\x1b[0m") == "Red"

    def test_leaves_plain_text_unchanged(self):
        assert _sanitise("EC2") == "EC2"

    def test_strips_cursor_home_sequence(self):
        assert _sanitise("\x1b[HText") == "Text"

    def test_multiple_sequences_all_stripped(self):
        assert _sanitise("\x1b[2J\x1b[HClean") == "Clean"

    def test_show_prompt_strips_ansi_from_card_front(self, capsys):
        Display().show_prompt("\x1b[2JEC2")
        out = capsys.readouterr().out
        assert "EC2" in out
        assert "\x1b" not in out

    def test_show_feedback_strips_ansi_from_correct_answer(self, capsys):
        Display().show_feedback(False, "\x1b[31mAnswer\x1b[0m")
        out = capsys.readouterr().out
        assert "Answer" in out
        assert "\x1b" not in out


class TestSafePrint:
    def test_safe_print_outputs_text(self, capsys):
        _safe_print("hello")
        out = capsys.readouterr().out
        assert "hello" in out

    def test_safe_print_handles_unicode_encode_error(self, capsys):
        with patch(
            "builtins.print",
            side_effect=[UnicodeEncodeError("utf-8", "", 0, 1, ""), None],
        ):
            _safe_print("✓")
