# Flashcard Quizzer

A CLI flashcard application for memorizing terms and acronyms. Built with Python 3.8+ and the standard library, it loads JSON decks, presents cards one by one, evaluates answers intelligently, and shows real-time session analytics.

## Features

- **Three quiz modes**: Sequential, Random, and Adaptive (Leitner-style spaced repetition)
- **Smart answer evaluation**: Case-insensitive, whitespace-stripped comparison
- **Session analytics**: Per-card accuracy tracking and end-of-session summary table
- **Custom decks**: Load any JSON deck with schema validation and helpful error messages
- **Zero dependencies**: Pure Python standard library — no pip installs needed to run

---

## Architecture & Documentation

Comprehensive architectural design, implementation reports, and quality audits are available in the `docs/` directory:

- [Architecture & Technical Design](docs/Architect.md) — System architecture, SOLID principles, and Strategy Pattern design
- [Final Project Report](docs/report_template.md) — Official AI-assisted development project report and reflection
- [Implementation Report](docs/implementation_report.md) — Module-by-module implementation, TDD workflow, and test metrics
- [Architectural Code Review](docs/architectural_review.md) — Rigorous inspection of code quality, boundaries, and coupling
- [Risk Assessment](docs/risk_assessment.md) — Holistic evaluation of security, reliability, performance, and maintainability risks
- [Refactoring Audit](docs/refactoring_audit.md) — Detailed log of refactoring iterations and checklist validations
- [Risk Mitigation Audit](docs/risk_mitigation_audit.md) — Verification of risk mitigation controls across all modules
- [AI Interaction Log](docs/ai_edit_log.md) — Full prompt history, decision records, and lessons learned

**Key principles:**

- **SOLID** — each module has a single responsibility; strategies are open for extension
- **Strategy Pattern** — `CardSelectionStrategy` ABC with `Sequential`, `Random`, and `Adaptive` implementations
- **Layered Separation of Concerns** — `loader` → `models` → `engine` → `display`; `main.py` wires them together
- **Red-Green-Refactor TDD** — all modules developed test-first with >80% coverage

---

## Installation & Quick Start

**Prerequisites:** Python 3.8+

```bash
# 1. Clone the repo and enter the project directory
git clone git@github.com:FranciscoJGaviria/flashcard-quizzer-cli.git
cd flashcard-quizzer-cli

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run a quiz immediately with the built-in AWS deck
python main.py
```

---

## CLI Usage

```
python main.py [--file PATH] [--mode {sequential,random,adaptive}] [--help]
```

| Argument | Default | Description |
|---|---|---|
| `--file PATH` | `data/aws_services.json` | Path to a flashcard JSON deck |
| `--mode MODE` | `sequential` | Quiz mode: `sequential`, `random`, or `adaptive` |
| `--help` | — | Show usage and exit |

**Examples:**

```bash
# Default: sequential mode with the built-in deck
python main.py

# Random order
python main.py --mode random

# Adaptive mode — missed cards appear first
python main.py --mode adaptive

# Custom deck in sequential mode
python main.py --file path/to/my_deck.json

# Custom deck in random mode
python main.py --file path/to/my_deck.json --mode random
```

**Sample session output:**

```
Loaded 60 card(s) — mode: adaptive

Card: EC2
Your answer: amazon elastic compute cloud
✓ Correct!

Card: S3
Your answer: storage
✗ Incorrect. The correct answer is: Amazon Simple Storage Service

...

========================================
         SESSION SUMMARY
========================================
  Total Questions : 60
  Correct         : 47
  Accuracy        : 78%
----------------------------------------
  Missed Terms:
    - S3
========================================

Play another round? (y/n): y
```

In `--mode adaptive`, choosing to play another round immediately prioritizes previously missed terms (such as `S3`) at the top of the deck.

Press `Ctrl+C` at any time to end the session early — your partial stats are still displayed.

---

## Flashcard Deck Format

Decks are JSON files with a top-level `"cards"` array. Each card object requires `"front"` and `"back"`; all other fields are optional.

**Schema:**

```json
{
  "cards": [
    {
      "id": "string (optional)",
      "front": "string (required) — prompt shown to the user",
      "back": "string (required) — expected answer",
      "category": "string (optional)",
      "description": "string (optional)"
    }
  ]
}
```

**Minimal valid example:**

```json
{
  "cards": [
    {
      "front": "HTML",
      "back": "HyperText Markup Language"
    },
    {
      "id": "css",
      "front": "CSS",
      "back": "Cascading Style Sheets",
      "category": "Web"
    }
  ]
}
```

Save the file as UTF-8 encoded JSON (`.json`) and pass it with `--file`.

---

## Developer & Testing Guide

### Running Tests

```bash
# Run the full test suite
pytest

# Run with terminal coverage summary
pytest --cov=utils --cov=main --cov-report=term-missing

# Run with HTML coverage report (opens htmlcov/index.html)
pytest --cov=. --cov-report=html

# Run a specific test file verbosely
pytest tests/test_strategies.py -v
```

### Test Suite Structure

| File | Focus |
|---|---|
| `tests/test_models.py` | Unit tests for `Flashcard`, `CardStats`, `SessionStats` dataclasses |
| `tests/test_strategies.py` | Unit tests for `Sequential`, `Random`, and `Adaptive` strategy logic |
| `tests/test_engine.py` | Unit + integration tests for `QuizEngine` quiz loop and answer evaluation |
| `tests/test_loader.py` | Unit tests for `FlashcardLoader` — valid decks, missing files, schema errors |
| `tests/test_display.py` | Unit tests for `Display` prompts, feedback, and summary rendering |

### Code Quality Tools

```bash
# Format code
black .

# Organize imports
isort .

# Lint
flake8 .

# Type check
mypy main.py utils/

# Run all quality checks in sequence
black . && isort . && flake8 . && mypy main.py utils/ && pytest
```

### Pre-commit Automated Quality Gate

A pre-commit configuration (`.pre-commit-config.yaml`) is included to enforce code quality, security, and test passing before any commit is accepted.

**1. Install git hooks:**
```bash
pre-commit install
```

**2. Run manually on all files anytime:**
```bash
pre-commit run --all-files
```

**Automated checks executed before every `git commit`:**
- **File Hygiene**: Trims trailing whitespace, enforces single trailing newlines, validates JSON/YAML, and prevents accidental commits of files >10 MB.
- **Formatting**: Runs `black` (88-char line limit) and `isort` (Black profile).
- **Style & Linting**: Runs `flake8` configured via `.flake8`.
- **Type Checking**: Runs `mypy` on `main.py` and `utils/`.
- **Security Scanning**: Runs `bandit` AST security linter.
- **Unit Tests & Coverage**: Runs full `pytest` test suite with `pytest-cov`.

> **Note**: If any test fails or any linter reports an issue, `git commit` is automatically aborted until the issue is resolved.

---

## Project Structure

```
starter/
├── main.py                     # CLI entry point: arg parsing + dependency wiring
├── data/
│   └── aws_services.json       # Built-in 60-card AWS services deck
├── utils/
│   ├── models.py               # Flashcard, CardStats, SessionStats dataclasses
│   ├── strategies.py           # CardSelectionStrategy ABC + 3 implementations
│   ├── engine.py               # QuizEngine: quiz loop and answer evaluation
│   ├── loader.py               # FlashcardLoader: JSON loading and validation
│   └── display.py              # Display: all terminal I/O
├── tests/
│   ├── test_models.py
│   ├── test_strategies.py
│   ├── test_engine.py
│   ├── test_loader.py
│   └── test_display.py
├── docs/
│   ├── Architect.md            # Full architecture and design reference
│   ├── report_template.md      # Final AI-assisted development report
│   ├── implementation_report.md# Module-by-module implementation report
│   ├── architectural_review.md # Architectural code review audit
│   ├── risk_assessment.md      # Holistic risk assessment
│   ├── refactoring_audit.md    # Refactoring audit and checklist validations
│   ├── risk_mitigation_audit.md# Risk mitigation verification audit
│   ├── design_patterns.md      # Design patterns guide
│   └── ai_edit_log.md          # AI interaction and prompt log
├── requirements.txt
└── README.md
```

---

## Troubleshooting & FAQ

**`Error: File not found: my_deck.json`**
The path passed to `--file` does not exist relative to your working directory. Run `python main.py --file /absolute/path/to/deck.json` or ensure you are in the correct directory.

**`Error: Missing required top-level "cards" array in JSON file.`**
Your JSON must have a root-level `"cards"` key whose value is an array. Wrap your card objects: `{ "cards": [ ... ] }`.

**`Error: Card at index N is missing required field "front".`**
Every card object must include non-empty `"front"` and `"back"` string fields. Check the card at the reported index.

**`Error: Invalid JSON in deck.json: ...`**
The file contains a JSON syntax error. Use a JSON validator (e.g. `python -m json.tool deck.json`) to locate and fix the problem.

**`UnicodeDecodeError` when loading a deck**
The loader requires UTF-8 encoding. Re-save your JSON file as UTF-8 (most editors: *Save with Encoding → UTF-8*).

**`Error: File too large (N MB). Maximum allowed size is 10 MB.`**
Decks are limited to 10 MB. Split the deck into smaller files and use `--file` to select one at a time.

---

## Built With

- [Python](https://www.python.org/) — core language (3.8+)
- [pytest](https://docs.pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) — testing and coverage
- [Black](https://black.readthedocs.io/) — code formatter
- [isort](https://pycqa.github.io/isort/) — import organizer
- [flake8](https://flake8.pycqa.org/) — linter
- [mypy](https://mypy.readthedocs.io/) — static type checker
- [pre-commit](https://pre-commit.com/) — git hook framework
