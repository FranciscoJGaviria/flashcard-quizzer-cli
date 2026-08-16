# CLI Flashcard Quizzer — Implementation Report

**Date:** 2026-08-15
**Status:** Complete

---

## 1. Overview

A modular, extensible CLI application that quizzes users on AWS service acronyms.
Built with Python 3.10, JSON file storage, and the standard library only.
Implements the **Strategy Pattern** for quiz modes and follows **SOLID principles**
throughout.

---

## 2. Final Directory Structure

```
project/starter/
├── main.py                      # CLI entry point: arg parsing + dependency wiring
├── data/
│   └── aws_services.json        # 60-card AWS flashcard dataset
├── utils/
│   ├── __init__.py
│   ├── models.py                # Flashcard, CardStats, SessionStats dataclasses
│   ├── strategies.py            # CardSelectionStrategy ABC + 3 implementations
│   ├── engine.py                # QuizEngine: quiz loop, answer evaluation, stats
│   ├── loader.py                # FlashcardLoader: JSON loading + validation
│   └── display.py               # Display: all terminal I/O
├── tests/
│   ├── __init__.py
│   ├── test_models.py           # 12 tests
│   ├── test_strategies.py       # 22 tests
│   ├── test_engine.py           # 27 tests
│   ├── test_loader.py           # 19 tests
│   └── test_display.py          # 30 tests
└── docs/
    ├── Architect.md
    ├── implementation_report.md  # This file
    └── ...
```

---

## 3. Module-by-Module Implementation

### `utils/models.py` — Pure Data Structures

| Class | Fields | Properties |
|---|---|---|
| `Flashcard` | `front`, `back`, `id`, `category`, `description` | — |
| `CardStats` | `card`, `attempts`, `correct` | `misses` |
| `SessionStats` | `card_stats`, `total_attempts`, `total_correct` | `accuracy`, `missed_cards` |

All three are `@dataclass` with full type annotations and Google-style docstrings.
No business logic — pure data containers.

---

### `utils/strategies.py` — Strategy Pattern

Implements the **Strategy Pattern** as specified in the architecture.

| Class | Behaviour |
|---|---|
| `CardSelectionStrategy` (ABC) | `select(cards, stats) -> List[Flashcard]` abstract interface |
| `SequentialStrategy` | `list(cards)` — copy preserving original order |
| `RandomStrategy` | `random.shuffle` on a copy — never mutates original deck |
| `AdaptiveStrategy` | `sorted(..., key=miss_count, reverse=True)` — highest-miss cards first |

`QuizEngine` depends only on the ABC — zero coupling to concrete strategies.

---

### `utils/engine.py` — Quiz Loop (No I/O)

`QuizEngine` orchestrates the quiz loop with **no direct terminal access**.
All I/O is delegated to the injected `Display` instance (**Dependency Injection**).

```
run():
  ordered = strategy.select(cards, stats)
  for card in ordered:
    display.show_prompt(card.front)
    answer = display.get_input()
    is_correct = answer.strip().lower() == card.back.strip().lower()
    display.show_feedback(is_correct, card.back)
    _update_stats(stats, card, is_correct)
  display.show_summary(stats)
  return stats
```

Answer evaluation: **case-insensitive + whitespace-stripped**.

---

### `utils/loader.py` — JSON Loading & Validation

`FlashcardLoader` is the only module that touches the filesystem.

| Method | Responsibility |
|---|---|
| `load(path)` | Public entry point — orchestrates the pipeline |
| `_read_file(path)` | Reads raw text; raises `FlashcardLoadError` if missing |
| `_parse_json(raw, path)` | Decodes JSON; raises `FlashcardLoadError` on syntax error |
| `_extract_cards_list(data)` | Validates `"cards"` key exists and is a list |
| `_validate_card(card, index)` | Validates each card dict has non-empty `front` and `back` |

`REQUIRED_FIELDS = ("front", "back")` class constant.
`FlashcardLoadError` custom exception — no raw Python tracebacks exposed.

---

### `utils/display.py` — Terminal I/O

Single class handling all `print()` / `input()` calls.

| Method | Output |
|---|---|
| `show_prompt(front)` | `Card: {front}` |
| `get_input()` | `input("Your answer: ")` |
| `show_feedback(True, answer)` | `✓ Correct!` |
| `show_feedback(False, answer)` | `✗ Incorrect. The correct answer is: {answer}` |
| `show_summary(stats)` | Table: Total Questions, Correct, Accuracy %, Missed Terms |
| `show_error(message)` | `Error: {message}` |

---

### `main.py` — CLI Entry Point & Wiring

Implements a **Factory Pattern** via the `STRATEGIES` dict:

```python
STRATEGIES: Dict[str, Type[CardSelectionStrategy]] = {
    "sequential": SequentialStrategy,
    "random": RandomStrategy,
    "adaptive": AdaptiveStrategy,
}
```

Adding a new mode requires only:
1. A new strategy class in `strategies.py`
2. One new entry in `STRATEGIES` — **zero changes to engine, display, or loader**.

CLI interface:

```bash
python main.py [--file PATH] [--mode {sequential,random,adaptive}]
```

Default: `--file data/aws_services.json --mode sequential`

---

## 4. Design Patterns Applied

| Pattern | Where | Purpose |
|---|---|---|
| **Strategy** | `strategies.py` + `engine.py` | Swap quiz modes without changing engine |
| **Factory** | `main.py` (`STRATEGIES` dict) | Map CLI mode strings to strategy classes |
| **Dependency Injection** | `QuizEngine.__init__` | Receive `Display` and `CardSelectionStrategy` — enables mocking in tests |

---

## 5. TDD Compliance

Every module was implemented following the TDD cycle:

1. Write failing tests first
2. Implement the minimum code to pass
3. Refactor

| Step | Test written & failing | Implementation | Tests passing |
|---|---|---|---|
| 1 — models | ✅ | ✅ | ✅ |
| 2 — strategies | ✅ | ✅ | ✅ |
| 3 — engine | ✅ | ✅ | ✅ |
| 4 — loader | ✅ | ✅ | ✅ |
| 5 — display | ✅ | ✅ | ✅ |
| 6 — main | — (manual/integration) | ✅ | ✅ |

---

## 6. Test Results

**110 tests — 0 failures — 0 errors**

| Test file | Tests | Key scenarios |
|---|---|---|
| `test_models.py` | 12 | Field defaults, `accuracy`, `missed_cards`, `misses` |
| `test_strategies.py` | 22 | Order preserved; shuffle verified; miss-count sort (parametrized) |
| `test_engine.py` | 27 | Correct/incorrect stats; case-insensitive eval; Display mock call counts |
| `test_loader.py` | 19 | Valid JSON; missing file; malformed JSON; missing fields; empty strings |
| `test_display.py` | 30 | Prompt text; feedback signals; summary table; error messages |

---

## 7. Code Coverage

```
Name                  Stmts   Miss  Cover
-----------------------------------------
utils/__init__.py         0      0   100%
utils/display.py         27      0   100%
utils/engine.py          29      0   100%
utils/loader.py          38      0   100%
utils/models.py          30      0   100%
utils/strategies.py      21      0   100%
-----------------------------------------
TOTAL                   145      0   100%
```

**Target: ≥ 80% — Achieved: 100%**

---

## 8. Code Quality

| Tool | Result | Notes |
|---|---|---|
| **black** | ✅ Pass | 5 files reformatted; 8 unchanged |
| **isort** | ✅ Pass | 3 files fixed |
| **flake8** | ✅ Pass (exit 0) | 0 errors, 0 warnings |
| **mypy** | ✅ Pass (exit 0) | No issues in 7 source files |

---

## 9. How to Run

```bash
# Default quiz (sequential, AWS deck)
python main.py

# Random mode
python main.py --mode random

# Adaptive mode with custom deck
python main.py --mode adaptive --file data/aws_services.json

# Run all tests
pytest

# Run tests with coverage
pytest --cov=utils --cov-report=term-missing

# Quality checks
black . && isort . && flake8 . --max-line-length=100 && mypy main.py utils/
```

---

## 10. Extension Guide

To add a **Spaced Repetition** mode (zero changes to engine/display/loader):

1. Add `SpacedRepetitionStrategy(CardSelectionStrategy)` to `utils/strategies.py`
2. Implement `select()` with SRS interval logic
3. Add `"spaced": SpacedRepetitionStrategy` to `STRATEGIES` in `main.py`
4. Add tests to `tests/test_strategies.py`

This satisfies the **Open/Closed Principle**.
