"""Unit tests for utils/loader.py — written before implementation per TDD."""

import json
import pathlib
from unittest.mock import patch

import pytest

from utils.loader import (
    FlashcardFileError,
    FlashcardLoader,
    FlashcardLoadError,
    FlashcardSchemaError,
)
from utils.models import Flashcard


def write_json(
    tmp_path: pathlib.Path, data: object, filename: str = "cards.json"
) -> str:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


VALID_DECK = {
    "title": "Test Deck",
    "cards": [
        {"front": "EC2", "back": "Amazon Elastic Compute Cloud"},
        {"front": "S3", "back": "Simple Storage Service"},
    ],
}


class TestFlashcardLoaderValidInput:
    def test_load_returns_list_of_flashcards(self, tmp_path):
        path = write_json(tmp_path, VALID_DECK)
        cards = FlashcardLoader().load(path)
        assert isinstance(cards, list)
        assert all(isinstance(c, Flashcard) for c in cards)

    def test_load_correct_number_of_cards(self, tmp_path):
        path = write_json(tmp_path, VALID_DECK)
        cards = FlashcardLoader().load(path)
        assert len(cards) == 2

    def test_load_maps_front_and_back_correctly(self, tmp_path):
        path = write_json(tmp_path, VALID_DECK)
        cards = FlashcardLoader().load(path)
        assert cards[0].front == "EC2"
        assert cards[0].back == "Amazon Elastic Compute Cloud"

    def test_load_optional_fields_mapped_when_present(self, tmp_path):
        deck = {
            "cards": [
                {
                    "front": "EC2",
                    "back": "Elastic Compute Cloud",
                    "id": "ec2",
                    "category": "Compute",
                    "description": "Virtual servers",
                }
            ]
        }
        path = write_json(tmp_path, deck)
        card = FlashcardLoader().load(path)[0]
        assert card.id == "ec2"
        assert card.category == "Compute"
        assert card.description == "Virtual servers"

    def test_load_extra_unknown_fields_are_ignored(self, tmp_path):
        deck = {
            "cards": [
                {
                    "front": "EC2",
                    "back": "Elastic Compute Cloud",
                    "full_name": "Amazon EC2",
                    "use_cases": ["hosting"],
                }
            ]
        }
        path = write_json(tmp_path, deck)
        cards = FlashcardLoader().load(path)
        assert len(cards) == 1
        assert cards[0].front == "EC2"

    def test_load_optional_fields_default_to_empty_string_when_absent(self, tmp_path):
        deck = {"cards": [{"front": "EC2", "back": "Elastic Compute Cloud"}]}
        path = write_json(tmp_path, deck)
        card = FlashcardLoader().load(path)[0]
        assert card.id == ""
        assert card.category == ""
        assert card.description == ""

    def test_load_real_aws_json_file(self):
        path = str(pathlib.Path("data/aws_services.json"))
        cards = FlashcardLoader().load(path)
        assert len(cards) > 0
        assert all(isinstance(c, Flashcard) for c in cards)
        assert all(c.front and c.back for c in cards)

    def test_load_empty_cards_array(self, tmp_path):
        path = write_json(tmp_path, {"cards": []})
        cards = FlashcardLoader().load(path)
        assert cards == []


class TestFlashcardLoaderFileErrors:
    def test_missing_file_raises_flashcard_load_error(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        with pytest.raises(FlashcardLoadError, match="not found"):
            FlashcardLoader().load(missing)

    def test_missing_file_raises_flashcard_file_error(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        with pytest.raises(FlashcardFileError):
            FlashcardLoader().load(missing)

    def test_malformed_json_raises_flashcard_load_error(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(FlashcardLoadError, match="[Ii]nvalid"):
            FlashcardLoader().load(str(p))

    def test_malformed_json_raises_flashcard_schema_error(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(FlashcardSchemaError):
            FlashcardLoader().load(str(p))

    def test_error_message_contains_file_path(self, tmp_path):
        missing = str(tmp_path / "missing.json")
        with pytest.raises(FlashcardLoadError) as exc_info:
            FlashcardLoader().load(missing)
        assert "missing.json" in str(exc_info.value)

    def test_permission_error_raises_flashcard_file_error(self, tmp_path):
        path = write_json(tmp_path, VALID_DECK)
        with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
            with pytest.raises(FlashcardFileError, match="[Pp]ermission"):
                FlashcardLoader().load(path)

    def test_file_too_large_raises_flashcard_file_error(self, tmp_path):
        path = write_json(tmp_path, VALID_DECK)
        import os

        large_size = 11 * 1024 * 1024
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = os.stat_result(
                (0, 0, 0, 0, 0, 0, large_size, 0, 0, 0)
            )
            with pytest.raises(FlashcardFileError, match="[Ll]arge"):
                FlashcardLoader().load(path)

    def test_directory_path_raises_flashcard_file_error(self, tmp_path):
        with pytest.raises(FlashcardFileError, match="[Dd]irectory"):
            FlashcardLoader().load(str(tmp_path))

    def test_root_directory_raises_flashcard_file_error(self):
        with pytest.raises(FlashcardFileError, match="[Dd]irectory"):
            FlashcardLoader().load("/")


class TestFlashcardLoaderSchemaErrors:
    def test_missing_cards_key_raises_flashcard_load_error(self, tmp_path):
        path = write_json(tmp_path, {"title": "No cards key"})
        with pytest.raises(FlashcardLoadError, match="[Cc]ards"):
            FlashcardLoader().load(path)

    def test_missing_cards_key_raises_flashcard_schema_error(self, tmp_path):
        path = write_json(tmp_path, {"title": "No cards key"})
        with pytest.raises(FlashcardSchemaError):
            FlashcardLoader().load(path)

    def test_cards_not_a_list_raises_flashcard_load_error(self, tmp_path):
        path = write_json(tmp_path, {"cards": "not a list"})
        with pytest.raises(FlashcardLoadError, match="[Cc]ards"):
            FlashcardLoader().load(path)

    @pytest.mark.parametrize("missing_field", ["front", "back"])
    def test_card_missing_required_field_raises_flashcard_load_error(
        self, tmp_path, missing_field: str
    ):
        card = {"front": "EC2", "back": "Elastic Compute Cloud"}
        del card[missing_field]
        path = write_json(tmp_path, {"cards": [card]})
        with pytest.raises(FlashcardLoadError, match=missing_field):
            FlashcardLoader().load(path)

    def test_error_message_includes_card_index(self, tmp_path):
        deck = {
            "cards": [
                {"front": "EC2", "back": "OK"},
                {"front": "S3"},
            ]
        }
        path = write_json(tmp_path, deck)
        with pytest.raises(FlashcardLoadError, match="[12]"):
            FlashcardLoader().load(path)

    def test_card_item_not_a_dict_raises_flashcard_load_error(self, tmp_path):
        path = write_json(tmp_path, {"cards": ["not a dict"]})
        with pytest.raises(FlashcardLoadError):
            FlashcardLoader().load(path)

    def test_empty_front_raises_flashcard_load_error(self, tmp_path):
        path = write_json(tmp_path, {"cards": [{"front": "", "back": "something"}]})
        with pytest.raises(FlashcardLoadError, match="front"):
            FlashcardLoader().load(path)

    def test_empty_back_raises_flashcard_load_error(self, tmp_path):
        path = write_json(tmp_path, {"cards": [{"front": "EC2", "back": ""}]})
        with pytest.raises(FlashcardLoadError, match="back"):
            FlashcardLoader().load(path)

    def test_root_not_a_dict_raises_flashcard_schema_error(self, tmp_path):
        path = write_json(tmp_path, ["list", "at", "root"])
        with pytest.raises(FlashcardSchemaError, match="[Oo]bject"):
            FlashcardLoader().load(path)
