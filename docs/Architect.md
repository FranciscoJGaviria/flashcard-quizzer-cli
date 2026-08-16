# CLI Flashcard Quizzer — Architecture

## Overview

A modular, extensible CLI application for memorizing server acronyms and terms.
Built with Python 3.8+, JSON file storage, and the standard library.
Follows SOLID principles with the Strategy Pattern for quiz modes.

---

## 1. Directory Structure

```
project/starter/
├── main.py                          # Entry point: CLI arg parsing, dependency wiring
├── data/
│   └── aws_services.json            # Default flashcard dataset
├── utils/
│   ├── __init__.py
│   ├── models.py                    # Flashcard, CardStats, SessionStats dataclasses
│   ├── strategies.py                # CardSelectionStrategy ABC + 3 implementations
│   ├── engine.py                    # QuizEngine: orchestrates the quiz loop
│   ├── loader.py                    # FlashcardLoader: JSON loading and validation
│   └── display.py                   # CLI rendering: prompts, feedback, summary table
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_strategies.py
│   ├── test_engine.py
│   ├── test_loader.py
│   └── test_display.py
└── docs/
    └── Architect.md                 # This file
```

---

## 2. Module Responsibilities

| Module | Class(es) | Single Responsibility |
|---|---|---|
| `models.py` | `Flashcard`, `CardStats`, `SessionStats` | Pure data structures (dataclasses), no logic |
| `strategies.py` | `CardSelectionStrategy` (ABC), `SequentialStrategy`, `RandomStrategy`, `AdaptiveStrategy` | Card ordering algorithms only |
| `engine.py` | `QuizEngine` | Quiz loop, answer evaluation, session state — no I/O |
| `loader.py` | `FlashcardLoader` | Read JSON, validate schema, return `List[Flashcard]` |
| `display.py` | `Display` | All terminal I/O: prompts, feedback, summary table |
| `main.py` | — | CLI arg parsing, dependency wiring, application launch |

---

## 3. Strategy Pattern Specification

### Abstract Base Class

```python
# utils/strategies.py
from abc import ABC, abstractmethod
from typing import List
from utils.models import Flashcard, SessionStats

class CardSelectionStrategy(ABC):
    @abstractmethod
    def select(self, cards: List[Flashcard], stats: SessionStats) -> List[Flashcard]:
        """Return an ordered list of cards for this quiz session."""
        ...
```

### Concrete Strategy Contracts

| Strategy | Class | `select()` behavior |
|---|---|---|
| Sequential | `SequentialStrategy` | Returns cards in original index order (1 to N) |
| Random | `RandomStrategy` | Returns a shuffled copy; no immediate repeats within a session |
| Adaptive | `AdaptiveStrategy` | Sorts by miss count DESC; unseen cards come first on first pass |

`QuizEngine` accepts any `CardSelectionStrategy` — it never imports a concrete strategy directly.

---

## 4. Data Flow

```
  [CLI args / user input]
         │
         ▼
      main.py
    ┌────────────────────────────────────────┐
    │  1. parse args (file path, mode)       │
    │  2. FlashcardLoader.load(path)         │──► loader.py  (validates JSON)
    │  3. strategy = StrategyFactory(mode)   │──► strategies.py
    │  4. engine = QuizEngine(cards,         │
    │              strategy, display)        │
    └──────────────┬─────────────────────────┘
                   │
                   ▼
              engine.py
    ┌────────────────────────────────────────┐
    │  ordered = strategy.select(cards,      │
    │                            stats)      │
    │  for card in ordered:                  │
    │    display.show_prompt(card.front)     │──► display.py
    │    answer = display.get_input()        │◄── display.py
    │    evaluate answer (case-insensitive)  │
    │    display.show_feedback(is_correct)   │──► display.py
    │    update SessionStats                 │
    └──────────────┬─────────────────────────┘
                   │
                   ▼
         display.show_summary(stats)         ──► display.py
```

---

## 5. Key Class Interfaces

```python
# utils/models.py
@dataclass
class Flashcard:
    front: str                        # mandatory
    back: str                         # mandatory
    id: str = ""                      # optional
    category: str = ""                # optional
    description: str = ""             # optional

@dataclass
class CardStats:
    card: Flashcard
    attempts: int = 0
    correct: int = 0

    @property
    def misses(self) -> int: ...

@dataclass
class SessionStats:
    card_stats: Dict[str, CardStats]  # keyed by card.front
    total_attempts: int = 0
    total_correct: int = 0

    @property
    def accuracy(self) -> float: ...
    @property
    def missed_cards(self) -> List[Flashcard]: ...


# utils/loader.py
class FlashcardLoader:
    def load(self, path: str) -> List[Flashcard]:
        """Load and validate JSON. Raises friendly FlashcardLoadError on failure."""
        ...


# utils/engine.py
class QuizEngine:
    def __init__(
        self,
        cards: List[Flashcard],
        strategy: CardSelectionStrategy,
        display: "Display",
    ) -> None: ...

    def run(self) -> SessionStats: ...


# utils/display.py
class Display:
    def show_prompt(self, front: str) -> None: ...
    def get_input(self) -> str: ...
    def show_feedback(self, is_correct: bool, correct_answer: str) -> None: ...
    def show_summary(self, stats: SessionStats) -> None: ...
    def show_error(self, message: str) -> None: ...
```

---

## 6. JSON Data Format

The flashcard JSON file must contain a `"cards"` array. Each card requires `"front"` and `"back"` fields. All other fields are optional metadata and are ignored by the quiz engine.

```json
{
  "title": "optional deck title",
  "cards": [
    {
      "front": "EC2",
      "back": "Amazon Elastic Compute Cloud",
      "id": "ec2",
      "category": "Compute",
      "description": "..."
    }
  ]
}
```

---

## 7. Implementation Order (Inside-Out, TDD)

Each step follows the TDD cycle: **write tests first → implement until all tests pass**.

| Step | Module | Test File | Depends On | Rationale |
|---|---|---|---|---|
| 1 | `models.py` | `test_models.py` | nothing | Pure data; no external dependencies |
| 2 | `strategies.py` | `test_strategies.py` | `models` | Algorithms only; isolated from I/O |
| 3 | `<role>
  Senior Python developer implementing planned modular @docs/Architect.md  following SOLID principles and TDD
  </role>

  <task>
  Implement strategies.py module following the architect.md definitions
  </task>

  <requirements>
  <code_quality>
  - Full type annotations throughout
  - Google-style docstrings with Args, Returns, Raises
  - Define REQUIRED_FIELDS = ('front', 'back') as class constant
  - Private helper method _validate_card(card: Dict[str, Any], index: int)
  - Module under 120 lines
  - Clear tests, build table-driven test suites using pytest
  - Use @docs/design_patterns.md  as reference
  </code_quality>
  </requirements>

  <constraints>
  - Python standard library only (json, pathlib, typing)
  - Follow PEP 8 style guide
  - No third-party dependencies
  - If you need any clarification, always ask me
  </constraints>` | `test_engine.py` | `models`, `strategies` | Core logic; I/O injected via `Display` mock |
| 4 | `loader.py` | `test_loader.py` | `models` | I/O boundary; file system interaction |
| 5 | `display.py` | `test_display.py` | `models` | Terminal I/O boundary; captured in tests |
| 6 | `main.py` | manual / integration | all modules | Wiring layer; tested end-to-end manually |

### TDD Rule

> For every module, the test file must be written and failing **before** any implementation code is written.
> Only write enough implementation to make the current failing test pass, then refactor.

---

## 8. 🛠️ Development Tools

### Code Quality Tools

- **Black**: Code formatter
  ```bash
  black .
  ```

- **isort**: Import organizer
  ```bash
  isort .
  ```

- **flake8**: Linting
  ```bash
  flake8 .
  ```

- **mypy**: Type checking
  ```bash
  mypy .
  ```

- **pytest**: Testing framework
  ```bash
  pytest --cov=. --cov-report=html
  ```

---

## 9. Testing & Coverage Strategy

Target: **≥ 80% code coverage** measured with `pytest --cov=. --cov-report=html`.

### Test File Breakdown

| Test file | Scenarios covered |
|---|---|
| `test_models.py` | Dataclass field defaults, `accuracy` property, `missed_cards` property, `misses` computed field |
| `test_strategies.py` | Sequential preserves order; Random produces no immediate repeats; Adaptive sorts by miss count DESC with unseen cards first |
| `test_engine.py` | Correct answer updates stats; incorrect answer updates miss count; session ends after all cards; `Display` calls mocked with `unittest.mock` |
| `test_loader.py` | Valid JSON loads correctly; missing file raises friendly error; malformed JSON raises friendly error; missing `front`/`back` fields raise validation error; extra optional fields are ignored |
| `test_display.py` | Prompt format; feedback messages (correct / incorrect); summary table renders Total, Accuracy %, missed terms list; `monkeypatch` captures stdout |

### Example Test Structure (engine)

```python
# tests/test_engine.py
from unittest.mock import MagicMock
from utils.models import Flashcard, SessionStats
from utils.strategies import SequentialStrategy
from utils.engine import QuizEngine

def test_correct_answer_increments_correct_count():
    cards = [Flashcard(front="EC2", back="Amazon Elastic Compute Cloud")]
    display = MagicMock()
    display.get_input.return_value = "amazon elastic compute cloud"  # case-insensitive
    engine = QuizEngine(cards, SequentialStrategy(), display)
    stats = engine.run()
    assert stats.total_correct == 1
    assert stats.total_attempts == 1
```

---

## 10. Extension Guide — Adding a New Strategy

Example: adding **Spaced Repetition** without changing any existing module.

1. Add `SpacedRepetitionStrategy(CardSelectionStrategy)` to `strategies.py`
2. Implement `select()` with SRS interval logic
3. Add `"spaced"` to the mode choices in `main.py` arg parser
4. Add `"spaced": SpacedRepetitionStrategy` to the strategy factory dict in `main.py`
5. Add `test_spaced_repetition_strategy` cases to `test_strategies.py`

**Zero changes** to `QuizEngine`, `Display`, `FlashcardLoader`, or `models`.

This satisfies the **Open/Closed Principle**: the core engine is open for extension, closed for modification.
