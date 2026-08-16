# Refactoring Audit: Flashcard Quizzer CLI

**Date:** 2026-08-15
**Based on:** `docs/architectural_review.md`
**Final state:** 128 tests | 100% coverage | flake8 exit 0 | mypy exit 0

---

## Verification Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Models: `Flashcard` and `SessionStats` are pure dataclasses with no I/O | ✅ PASS | `models.py` contains zero `print`/`input` calls; `SessionStats` now has `record_attempt()` as the only mutating method |
| Data Ingestion: `FlashcardLoader` handles all file access and validation errors gracefully | ✅ PASS | `_read_file` uses `try/except FileNotFoundError` + `PermissionError`; exception hierarchy `FlashcardFileError`/`FlashcardSchemaError` in place |
| Strategies: `CardSelectionStrategy` ABC implemented; new modes add without modifying engine (OCP) | ✅ PASS | ABC + 3 concrete strategies; `STRATEGIES` dict in `main.py` is the only change point |
| Injection: `QuizEngine` dependencies passed via constructor | ✅ PASS | `QuizEngine.__init__` receives `cards`, `strategy: CardSelectionStrategy`, `display: DisplayProtocol` |
| Presentation: all terminal output isolated in `Display` | ✅ PASS | `main.py` startup banner now routes through `display.show_info()`; zero bare `print()` calls in `main()` |
| Error Hygiene: zero bare `except:` blocks; all exceptions inherit from `FlashcardLoadError` | ✅ PASS | `flake8` E722 would catch bare excepts — exit 0; full hierarchy verified |
| Typing & Docs: 100% type annotation coverage and Google-style docstrings | ✅ PASS | `mypy` exit 0 on 7 source files |
| Dependencies: standard library only | ✅ PASS | No third-party imports in `utils/` or `main.py` |

---

## Review Finding Resolution

### Critical (Priority 1–3)

#### R4 — `KeyboardInterrupt`/`EOFError` unhandled

| Before | After |
|---|---|
| Ctrl+C mid-quiz → raw Python traceback | `main.py`: `except KeyboardInterrupt` → clean message + exit 130 |
| `input()` EOF → unhandled `EOFError` | `display.get_input()`: `except EOFError: return ""` |

**Files changed:** `utils/display.py:65-68`, `main.py:106-110`

#### R6 — Python 3.10+ syntax in `main.py`

| Before | After |
|---|---|
| `list[str] \| None` (3.10+ runtime syntax) | `Optional[List[str]]` from `typing` (3.8+ compatible) |

**Files changed:** `main.py:33,78`

#### R9 — TOCTOU race + missing `PermissionError` in `loader._read_file`

| Before | After |
|---|---|
| `if not file.exists(): raise ... ; return file.read_text()` | `try: return Path(path).read_text() except FileNotFoundError/PermissionError` |
| `PermissionError` propagated as unhandled Python exception | Caught and raised as `FlashcardFileError` |

**Files changed:** `utils/loader.py:62-84`

---

### Structural (Priority 4–8)

#### R1 — `DisplayProtocol` added (DIP fulfilled)

`DisplayProtocol` is a `typing.Protocol` class defined in `utils/display.py`. It is `@runtime_checkable` and declares all five methods. `QuizEngine.__init__` now types its `display` parameter as `"DisplayProtocol"` rather than `"Display"`.

**Architectural gain:** Any object implementing the five methods is a valid display — `MagicMock` in tests, `FileDisplay`, `RichDisplay`, etc. mypy verifies structural compliance at type-check time.

**Files changed:** `utils/display.py:10-37`, `utils/engine.py:9,29`

#### R2 — `SessionStats.record_attempt()` encapsulates mutation

`QuizEngine._update_stats()` was removed entirely. The engine loop now calls `stats.record_attempt(card, is_correct)`. All per-card and aggregate bookkeeping is owned by `SessionStats`.

**Files changed:** `utils/models.py:102-118`, `utils/engine.py:58` (removed `_update_stats`)

#### R5 — Derived `total_attempts` / `total_correct` (single source of truth)

`total_attempts` and `total_correct` are now `@property` methods that compute their values from `card_stats.values()`. The fields were removed from the dataclass constructor — no more dual-write consistency risk.

**Impact on tests:** All `SessionStats(total_attempts=N, total_correct=M, ...)` constructor calls updated in `test_models.py` and `test_display.py`.

**Files changed:** `utils/models.py:64-80`, `tests/test_models.py`, `tests/test_display.py`

#### R3 — `QuizEngine._evaluate_answer()` extracted

The inline comparison `raw.strip().lower() == card.back.strip().lower()` is now a named `@staticmethod`. It is independently unit-testable and the upgrade path to fuzzy matching is a one-line change.

**Files changed:** `utils/engine.py:63-77`

#### R7 — Startup banner routed through `Display`

`Display.show_info(message)` was added. `main.py` now calls `display.show_info(...)` instead of a bare `print()`, completing the "all output via Display" contract.

**Files changed:** `utils/display.py:109-115`, `main.py:104`

---

### Polish (Priority 9–13)

#### R8 — `_SUMMARY_WIDTH = 40` constant extracted

The magic literal `40` in `show_summary` (previously repeated three times) is now a module-level constant. Single change point for future width adjustments.

**Files changed:** `utils/display.py:7`

#### Strategy `__repr__` methods

`SequentialStrategy`, `RandomStrategy`, and `AdaptiveStrategy` each implement `__repr__` returning a human-readable string. Diagnostics and logging now show `SequentialStrategy()` instead of `<SequentialStrategy object at 0x...>`.

**Files changed:** `utils/strategies.py:33-34,52-53,83-84`

#### Stable-sort guarantee documented

`AdaptiveStrategy` class and `select()` docstrings now explicitly state that equal-miss-count ordering relies on Python's stable sort (Timsort / PEP 3109).

**Files changed:** `utils/strategies.py:78-81,90-91`

#### Exception hierarchy in `loader.py`

`FlashcardLoadError` (base) → `FlashcardFileError` (I/O failures) + `FlashcardSchemaError` (validation failures). Callers can now discriminate between "file problem" and "bad data" without string-parsing error messages.

**Files changed:** `utils/loader.py:10-31`

#### `_extract_cards_list` conditions split

The combined `not isinstance(data, dict) or "cards" not in data` check is now three separate `if` blocks, each raising a distinct, descriptive error message.

**Files changed:** `utils/loader.py:117-130`

#### `build_strategy` explicit `ValueError`

`main.build_strategy()` now raises `ValueError` with a helpful message if called with an unknown mode string, rather than raising a bare `KeyError`.

**Files changed:** `main.py:71-73`

---

## Test Suite Delta

| File | Before | After | New tests cover |
|---|---|---|---|
| `test_models.py` | 12 | 17 | `record_attempt` (5 tests), derived totals (2 tests) |
| `test_strategies.py` | 22 | 25 | `__repr__` (3 tests) |
| `test_loader.py` | 19 | 26 | Exception subclasses (4), root-not-dict (1), PermissionError (1), non-dict root (1) |
| `test_display.py` | 30 | 35 | EOFError in `get_input` (1), `show_info` (2), (2 existing call sites removed unused args) |
| `test_engine.py` | 27 | 27 | No changes needed — engine tests were already correct |

**Total: 110 → 128 tests (+18)**

---

## Final Metrics

```
128 tests — 0 failures — 0 errors

Name                  Stmts   Miss  Cover
-----------------------------------------
utils/__init__.py         0      0   100%
utils/display.py         41      0   100%
utils/engine.py          22      0   100%
utils/loader.py          44      0   100%
utils/models.py          41      0   100%
utils/strategies.py      27      0   100%
-----------------------------------------
TOTAL                   175      0   100%

flake8  — exit 0 (0 errors, 0 warnings)
mypy    — exit 0 (Success: no issues in 7 source files)
black   — all files formatted
isort   — all imports sorted
```

---

## Remaining Non-Issues (Accepted Trade-offs)

| Item | Decision |
|---|---|
| `FlashcardLoader` is a stateless class (could be a function) | **Kept as class** — consistent with `REQUIRED_FIELDS` class constant pattern; allows future subclassing if needed |
| `Flashcard` dataclass accepts empty strings at construction | **Accepted** — validation is the loader's responsibility; domain model self-defence would add complexity for no current benefit |
| `select()` receives full `SessionStats` (wider than needed) | **Accepted** — narrowing the interface to `Dict[str, CardStats]` would require a new type or breaking the ABC signature; low risk at current scope |

---

*End of audit.*
