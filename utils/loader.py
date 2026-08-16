"""Flashcard loader for the CLI Flashcard Quizzer application."""

import json
from pathlib import Path
from typing import Any, List

from utils.models import Flashcard

_MAX_FILE_BYTES = 10 * 1024 * 1024


class FlashcardLoadError(Exception):
    """Base exception for all flashcard loading failures.

    Provides a user-friendly message instead of a raw Python stack trace.
    Catch this base class when you do not need to distinguish sub-types.
    """


class FlashcardFileError(FlashcardLoadError):
    """Raised when the flashcard file cannot be accessed.

    Covers: file not found, permission denied, file too large, and other
    I/O errors.
    """


class FlashcardSchemaError(FlashcardLoadError):
    """Raised when the JSON structure fails schema validation.

    Covers: missing ``"cards"`` key, non-list ``"cards"`` value,
    individual card missing required fields, or empty field values.
    """


class FlashcardLoader:
    """Reads a JSON file and returns a validated list of Flashcard objects.

    The JSON file must contain a top-level ``"cards"`` array. Each element
    must be a dict with non-empty ``"front"`` and ``"back"`` string fields.
    All other fields are optional and are silently ignored.

    Security notes:
        - The supplied path is resolved to its canonical absolute form via
          ``Path.resolve()`` before any I/O, preventing ``..``-based path
          traversal from leaking directory structure information.
        - Files larger than ``_MAX_FILE_BYTES`` (10 MB) are rejected before
          reading to prevent memory-exhaustion from maliciously large payloads.
        - Error messages expose only the filename (``resolved.name``), never
          the full resolved path, to avoid leaking host directory layout.
    """

    REQUIRED_FIELDS = ("front", "back")

    def load(self, path: str) -> List[Flashcard]:
        """Load and validate a flashcard JSON file.

        Args:
            path: Absolute or relative path to the JSON file.

        Returns:
            A list of Flashcard objects in the order they appear in the file.

        Raises:
            FlashcardFileError: If the file is missing, cannot be read, or
                exceeds the maximum allowed size.
            FlashcardSchemaError: If JSON is invalid or any card fails
                schema validation.
        """
        raw = self._read_file(path)
        data = self._parse_json(raw, path)
        cards_data = self._extract_cards_list(data)
        return [self._validate_card(card, i) for i, card in enumerate(cards_data)]

    def _read_file(self, path: str) -> str:
        """Read raw text from *path* after resolving and size-checking it.

        Resolves the path to its canonical form (no ``..`` components,
        symlinks followed) before performing any I/O, eliminating path-
        traversal vectors. Rejects files larger than ``_MAX_FILE_BYTES``.

        Args:
            path: Path to the JSON file as supplied by the caller.

        Returns:
            The file contents as a string.

        Raises:
            FlashcardFileError: If the file does not exist, cannot be read,
                or exceeds the maximum allowed file size.
        """
        resolved = Path(path).resolve()
        try:
            size = resolved.stat().st_size
            if size > _MAX_FILE_BYTES:
                raise FlashcardFileError(
                    f"File too large ({size // 1_048_576} MB). "
                    f"Maximum allowed size is {_MAX_FILE_BYTES // 1_048_576} MB."
                )
            return resolved.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FlashcardFileError(f"File not found: {resolved.name}") from None
        except PermissionError as exc:
            raise FlashcardFileError(
                f"Permission denied reading {resolved.name}"
            ) from exc

    def _parse_json(self, raw: str, path: str) -> Any:
        """Parse *raw* as JSON.

        Args:
            raw: Raw JSON string.
            path: Original path, used in the error message.

        Returns:
            The decoded JSON value.

        Raises:
            FlashcardSchemaError: If *raw* is not valid JSON.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FlashcardSchemaError(
                f"Invalid JSON in {Path(path).name}: {exc}"
            ) from exc

    def _extract_cards_list(self, data: Any) -> List[Any]:
        """Extract and validate the top-level ``"cards"`` array.

        Args:
            data: Decoded JSON value (expected to be a dict).

        Returns:
            The list stored under the ``"cards"`` key.

        Raises:
            FlashcardSchemaError: If the root is not a dict, ``"cards"`` is
                absent, or ``"cards"`` is not a list.
        """
        if not isinstance(data, dict):
            raise FlashcardSchemaError(
                f"Expected a JSON object at root, got: {type(data).__name__}"
            )
        if "cards" not in data:
            raise FlashcardSchemaError(
                'Missing required top-level "cards" array in JSON file.'
            )
        cards = data["cards"]
        if not isinstance(cards, list):
            raise FlashcardSchemaError(
                '"cards" must be a JSON array, got: ' + type(cards).__name__
            )
        return cards

    def _validate_card(self, card: Any, index: int) -> Flashcard:
        """Validate a single card dict and return a Flashcard.

        Args:
            card: Raw card value from the JSON array.
            index: Zero-based position in the array, used in error messages.

        Returns:
            A populated Flashcard instance.

        Raises:
            FlashcardSchemaError: If *card* is not a dict, or any required
                field is missing or empty.
        """
        if not isinstance(card, dict):
            raise FlashcardSchemaError(
                f"Card at index {index} must be a JSON object, "
                f"got: {type(card).__name__}"
            )
        for field in self.REQUIRED_FIELDS:
            if field not in card:
                raise FlashcardSchemaError(
                    f'Card at index {index} is missing required field "{field}".'
                )
            if not str(card[field]).strip():
                raise FlashcardSchemaError(
                    f'Card at index {index} has an empty "{field}" field.'
                )
        return Flashcard(
            front=card["front"],
            back=card["back"],
            id=card.get("id", ""),
            category=card.get("category", ""),
            description=card.get("description", ""),
        )
