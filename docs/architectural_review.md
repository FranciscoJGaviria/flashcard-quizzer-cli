# Architectural Review: Flashcard Quizzer CLI

**Reviewer:** Senior Python Software Architect
**Date:** 2026-08-15
**Codebase snapshot:** 110 tests passing, 100% coverage, all linters clean

---

## 1. Executive Summary & Health Scorecard

The Flashcard Quizzer CLI is a well-structured application that correctly applies the Strategy Pattern, Dependency Injection, and clear layer separation. The implementation demonstrates solid TDD discipline and PEP 8 compliance. Most architectural goals from the spec are met. The identified issues are moderate rather than critical — no design is fundamentally broken — but several areas present real extensibility and resilience risks worth addressing before further growth.

### Health Scorecard

| Dimension | Score (1–5) | Notes |
|---|---|---|
| **Modular Design** | 4/5 | Clean layer boundaries; minor coupling issue in `engine.py` |
| **SOLID Adherence** | 4/5 | OCP and DIP well applied; SRP slightly strained in `display.py` |
| **Error Resilience** | 2/5 | No `KeyboardInterrupt`/`EOFError` handling; flat exception hierarchy |
| **Type Safety** | 4/5 | Full annotations; one structural typing gap (`Display` not an ABC) |
| **Testability** | 5/5 | 100% coverage, DI throughout, no hidden globals |

**Overall Health: GOOD — production-ready for a learning context, with targeted improvements needed for resilience.**

---

## 2. Component-by-Component Analysis

### `utils/models.py` — Domain Models

**Current Role & Strengths**
- Pure data containers with no I/O or business logic — textbook SRP compliance.
- `@dataclass` reduces boilerplate; computed properties (`accuracy`, `missed_cards`, `misses`) are logically appropriate here.
- `SessionStats` uses `field(default_factory=dict)` correctly to avoid the mutable-default trap.

**Architectural Issues / Smells**

1. **Mutable dataclasses** (`frozen=False` by default): `CardStats` and `SessionStats` are mutated in-place by `QuizEngine._update_stats`. This is an intentional design choice but makes it harder to reason about state, snapshot history, or parallelize in future. Fields like `total_attempts` and `total_correct` are being incremented externally, meaning the aggregate is not self-consistent — `total_correct` could diverge from the sum of `cs.correct` across all `card_stats` entries if a bug is introduced.

2. **`SessionStats` aggregates are redundant** (`total_attempts`, `total_correct`): These are derivable from `card_stats.values()`. Storing them separately creates a consistency risk — two sources of truth for the same data. If a card is added to `card_stats` without updating the totals, the stats silently diverge.

3. **No `__post_init__` validation**: `Flashcard(front="", back="")` is a valid Python object. Validation is deferred to the loader, which is correct, but a `frozen=True` dataclass or `__post_init__` guard would make the domain model self-defending.

**Risk Level:** LOW (for current scope); MEDIUM (if codebase grows)

---

### `utils/loader.py` — Data Ingestion

**Current Role & Strengths**
- Single responsibility: filesystem I/O + JSON parsing + schema validation.
- Pipeline of private helpers (`_read_file`, `_parse_json`, `_extract_cards_list`, `_validate_card`) is clean and testable.
- `REQUIRED_FIELDS` class constant correctly externalizes schema knowledge.
- `FlashcardLoadError` provides user-friendly messages, chaining `from exc` correctly preserves the cause.

**Architectural Issues / Smells**

1. **`_read_file` uses `Path.exists()` + `read_text()` (TOCTOU race)**: Between the `exists()` check and `read_text()`, the file could be deleted. The idiomatic Python approach is `try/except FileNotFoundError` on `read_text()` directly, eliminating the race.

   ```python
   # Current (TOCTOU risk)
   if not file.exists():
       raise FlashcardLoadError(f"File not found: {path}")
   return file.read_text(encoding="utf-8")

   # Recommended
   try:
       return Path(path).read_text(encoding="utf-8")
   except FileNotFoundError:
       raise FlashcardLoadError(f"File not found: {path}") from None
   except PermissionError as exc:
       raise FlashcardLoadError(f"Permission denied reading {path}") from exc
   ```

2. **`FlashcardLoadError` is a flat exception** — no subclass hierarchy. If a caller wants to distinguish "file missing" from "schema invalid" without parsing the message string, they cannot. A two-level hierarchy would future-proof this:

   ```python
   class FlashcardLoadError(Exception): ...
   class FlashcardFileError(FlashcardLoadError): ...
   class FlashcardSchemaError(FlashcardLoadError): ...
   ```

3. **`_extract_cards_list` conflates two checks in one condition** (`not isinstance(data, dict) or "cards" not in data`): Both produce the same error message. A caller cannot distinguish "got a list at root" from "got a dict without cards key". Separate conditions with separate messages would improve debuggability.

4. **`FlashcardLoader` is stateless** — it has no instance state, only one public method. A module-level function `load_flashcards(path: str) -> List[Flashcard]` would be simpler and equally testable, avoiding unnecessary class ceremony. The class form is only justified if subclassing/DI of the loader is anticipated (it currently is not).

**Risk Level:** LOW–MEDIUM

---

### `utils/strategies.py` — Card Selection Strategies

**Current Role & Strengths**
- Textbook Strategy Pattern: ABC + three concrete implementations.
- `SequentialStrategy` and `RandomStrategy` correctly ignore `stats`, maintaining interface compliance without side effects.
- `AdaptiveStrategy` correctly handles missing stats entries (defaults to 0 misses).
- No mutation of the input `cards` list in any strategy — defensive copies throughout.

**Architectural Issues / Smells**

1. **`select()` receives the full `SessionStats` but only uses `card_stats`**: This creates an unnecessarily wide interface. If `SessionStats` gains fields unrelated to selection (e.g., a timer), strategies get access to data they should not see. A tighter protocol would pass only `Dict[str, CardStats]` or a read-only view.

2. **`AdaptiveStrategy` is a one-pass sort with a stability assumption**: Python's `sorted()` is stable, so equal-miss cards preserve original order. This is correct but undocumented — the docstring says "unseen cards appear last, preserving their relative original order" but does not mention that this relies on sort stability. An explicit note or test asserting stable-sort behavior would make the guarantee explicit.

3. **No `__repr__` or `__str__`** on strategies: When a strategy is logged or printed (e.g., in `main.py`'s startup banner), Python shows `<SequentialStrategy object at 0x...>`. A `__repr__` would be useful for diagnostics.

**Risk Level:** LOW

---

### `utils/engine.py` — Orchestration Engine

**Current Role & Strengths**
- Zero direct I/O — all terminal interaction delegated to `Display`.
- Clean separation: `run()` orchestrates, `_update_stats()` handles state mutation.
- `TYPE_CHECKING` guard correctly avoids circular import while preserving type annotations.

**Architectural Issues / Smells**

1. **`Display` is a concrete class, not an interface (ABC/Protocol)**. `QuizEngine` depends on `"Display"` (string annotation) rather than an abstract type. This works with `MagicMock` in tests but violates the Dependency Inversion Principle formally — there is no contract defining what a valid display must provide. If a future `FileDisplay` or `WebDisplay` is created, there is no ABC to implement, making the contract implicit rather than explicit.

   Recommended: Add a `DisplayProtocol` (using `typing.Protocol`) or an ABC `BaseDisplay` that `Display` inherits from, and type `QuizEngine.__init__` against that abstraction.

2. **`_update_stats` has implicit coupling to `SessionStats` internals**: `engine.py` directly mutates `stats.card_stats`, `stats.total_attempts`, and `stats.total_correct`. This means `QuizEngine` knows the internal structure of `SessionStats`. If `SessionStats` is ever refactored (e.g., aggregates become properties derived from `card_stats`), `engine.py` must change too. A `stats.record_attempt(card, is_correct)` method on `SessionStats` would encapsulate this.

3. **`KeyboardInterrupt` and `EOFError` are unhandled in `run()`**: If the user presses Ctrl+C mid-quiz, Python prints a raw traceback. `EOFError` is raised if stdin is closed (e.g., piped input ends). Both should be caught and handled gracefully:

   ```python
   try:
       raw = self._display.get_input()
   except (KeyboardInterrupt, EOFError):
       self._display.show_summary(stats)
       raise  # or return stats early
   ```

4. **Answer evaluation logic is hardcoded in `run()`** (line 56: `raw.strip().lower() == card.back.strip().lower()`). The evaluation rule — case-insensitive, stripped — is reasonable but embedded in the loop body with no name. Extracting this as `_evaluate_answer(raw, card) -> bool` would make the rule explicit, independently testable, and swappable (e.g., for fuzzy matching later).

**Risk Level:** MEDIUM

---

### `utils/display.py` — CLI View / Presentation Layer

**Current Role & Strengths**
- All `print()` and `input()` calls are confined to this one class — clean I/O boundary.
- `show_summary` uses a fixed-width table format, consistent and readable.
- `show_error` is simple and non-invasive.

**Architectural Issues / Smells**

1. **No `DisplayProtocol` / ABC** (mirrors engine issue above): `Display` is a concrete class with no formal interface. Tests mock it with `MagicMock` successfully, but the implicit contract is not machine-checkable. If `get_input()` is accidentally renamed, mypy will not catch the mismatch against `QuizEngine`'s type annotation.

2. **Magic numbers in `show_summary`**: The separator width `40` appears three times (lines 50, 56, 66). If the format is changed to 60 characters, all three must be updated manually.

   ```python
   # Current
   print("\n" + "=" * 40)
   print("-" * 40)
   print("=" * 40)

   # Recommended
   _WIDTH = 40
   print("\n" + "=" * _WIDTH)
   print("-" * _WIDTH)
   print("=" * _WIDTH)
   ```

3. **`show_summary` is a single 17-line method doing formatting, logic (missed card filtering via `stats.missed_cards`), and output**: For the current scope this is fine, but if summary formatting grows (e.g., per-card accuracy rows), this method will become a maintenance burden. Extracting `_format_missed_section(missed)` would be a first step.

4. **`show_feedback` accesses `correct_answer` even on correct answers**: The parameter is always passed and always present, but is only displayed on incorrect attempts. This is minor but worth noting — the method signature implies the answer is always needed, which could lead callers to always compute it eagerly.

5. **`get_input()` has no `KeyboardInterrupt`/`EOFError` handling**: `input()` raises `EOFError` on piped EOF. Catching it here and returning a sentinel (or re-raising a domain exception) would allow `QuizEngine` to handle it cleanly without knowing about `input()` internals.

**Risk Level:** LOW–MEDIUM

---

### `main.py` — Composition Root

**Current Role & Strengths**
- Clean Factory Pattern via `STRATEGIES` dict — adding a new mode is one line.
- `main()` returns `int` exit code, `sys.exit(main())` at the bottom — correct pattern.
- `parse_args()` and `build_strategy()` are isolated, making `main()` thin and testable.
- `DEFAULT_DATA_FILE` constant avoids hardcoding the path inside functions.

**Architectural Issues / Smells**

1. **`KeyboardInterrupt` is not caught**: If the user presses Ctrl+C after loading (inside `QuizEngine.run()`), `main()` prints a raw Python traceback. A top-level handler would provide a clean exit:

   ```python
   try:
       QuizEngine(cards, strategy, display).run()
   except KeyboardInterrupt:
       print("\n\n[Quiz interrupted. Goodbye!]")
       return 130  # POSIX convention for Ctrl+C
   ```

2. **Startup banner uses a bare `print()`** (line 92) instead of routing through `display.show_info()` or similar. This breaks the "all output via `Display`" contract — `main.py` should not call `print()` directly if the goal is to isolate I/O in `Display`.

   ```python
   # Current (violates Display boundary)
   print(f"\nLoaded {len(cards)} card(s) — mode: {args.mode}\n")

   # Recommended
   display.show_info(f"Loaded {len(cards)} card(s) — mode: {args.mode}")
   ```

3. **`list[str] | None` syntax** (lines 29, 67) uses Python 3.10+ union shorthand (`X | Y`). The project header says "Python 3.8+". This is a compatibility violation — `Optional[List[str]]` or `Union[List[str], None]` from `typing` should be used for 3.8/3.9 compatibility.

   ```python
   # Current (Python 3.10+ only)
   def parse_args(argv: list[str] | None = None) -> argparse.Namespace:

   # Compatible with Python 3.8+
   from typing import List, Optional
   def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
   ```

4. **`build_strategy` could raise `KeyError`** if called with an invalid mode string. While `argparse` enforces `choices`, if `build_strategy` is ever called programmatically with an arbitrary string, the error message will be unhelpful. A guard or explicit `ValueError` would be more informative.

**Risk Level:** LOW–MEDIUM

---

## 3. Specific Refactoring Recommendations

### R1 — Add a `DisplayProtocol` or ABC

**File:** `utils/display.py`, `utils/engine.py`
**Issue Category:** DIP Violation, Missing Interface Contract
**Current Pattern:** `QuizEngine` receives `"Display"` as a string annotation — no formal interface.
**Recommended Solution:**
```python
# utils/display.py  — add above the Display class
from typing import Protocol

class DisplayProtocol(Protocol):
    def show_prompt(self, front: str) -> None: ...
    def get_input(self) -> str: ...
    def show_feedback(self, is_correct: bool, correct_answer: str) -> None: ...
    def show_summary(self, stats: SessionStats) -> None: ...
    def show_error(self, message: str) -> None: ...

# utils/engine.py — change type annotation
from utils.display import DisplayProtocol

class QuizEngine:
    def __init__(
        self,
        cards: List[Flashcard],
        strategy: CardSelectionStrategy,
        display: DisplayProtocol,
    ) -> None:
```
**Architectural Benefit:** Formalises the contract; mypy can now verify any mock or alternative Display implementation structurally. Enables `FileDisplay`, `RichDisplay`, etc. without modifying `QuizEngine`.

---

### R2 — Encapsulate Stats Mutation in `SessionStats`

**File:** `utils/engine.py`, `utils/models.py`
**Issue Category:** Tight Coupling, SRP Violation
**Current Pattern:**
```python
# engine.py:74-84 — engine directly mutates model internals
if card.front not in stats.card_stats:
    stats.card_stats[card.front] = CardStats(card=card)
cs = stats.card_stats[card.front]
cs.attempts += 1
if is_correct:
    cs.correct += 1
stats.total_attempts += 1
if is_correct:
    stats.total_correct += 1
```
**Recommended Solution:**
```python
# utils/models.py — add method to SessionStats
def record_attempt(self, card: "Flashcard", is_correct: bool) -> None:
    if card.front not in self.card_stats:
        self.card_stats[card.front] = CardStats(card=card)
    cs = self.card_stats[card.front]
    cs.attempts += 1
    if is_correct:
        cs.correct += 1
    self.total_attempts += 1
    if is_correct:
        self.total_correct += 1

# utils/engine.py — simplify _update_stats or inline
stats.record_attempt(card, is_correct)
```
**Architectural Benefit:** `SessionStats` becomes self-consistent. The engine no longer needs to know the internal layout of the model. The `total_attempts`/`total_correct` aggregates are always updated atomically with the per-card stats.

---

### R3 — Extract `_evaluate_answer` in `QuizEngine`

**File:** `utils/engine.py`
**Issue Category:** Magic Logic, Testability
**Current Pattern:**
```python
# engine.py:56 — embedded rule, not independently testable
is_correct = raw.strip().lower() == card.back.strip().lower()
```
**Recommended Solution:**
```python
@staticmethod
def _evaluate_answer(raw: str, expected: str) -> bool:
    return raw.strip().lower() == expected.strip().lower()
```
**Architectural Benefit:** The evaluation rule is named, documented, and independently unit-testable. Changing to fuzzy matching (e.g., `difflib.SequenceMatcher`) becomes a one-line change in one method.

---

### R4 — Handle `KeyboardInterrupt` and `EOFError` Gracefully

**File:** `main.py`, `utils/engine.py`, `utils/display.py`
**Issue Category:** Error Resilience, Poor UX
**Current Pattern:** `KeyboardInterrupt` propagates to the terminal as a raw traceback.
**Recommended Solution (in `main.py`):**
```python
try:
    QuizEngine(cards, strategy, display).run()
except KeyboardInterrupt:
    print("\n\n[Quiz interrupted. Goodbye!]")
    return 130
```
**And in `display.py`:**
```python
def get_input(self) -> str:
    try:
        return input("Your answer: ")
    except EOFError:
        return ""
```
**Architectural Benefit:** Clean exit on Ctrl+C or piped input; no raw Python traceback shown to users. Returns the POSIX-standard exit code 130 for SIGINT.

---

### R5 — Remove Redundant Aggregates from `SessionStats` or Make Them Derived

**File:** `utils/models.py`
**Issue Category:** Two Sources of Truth, Consistency Risk
**Current Pattern:** `total_attempts` and `total_correct` stored as mutable integers alongside per-card `card_stats` that contain the same data.
**Recommended Solution — Option A (derived properties):**
```python
@property
def total_attempts(self) -> int:
    return sum(cs.attempts for cs in self.card_stats.values())

@property
def total_correct(self) -> int:
    return sum(cs.correct for cs in self.card_stats.values())
```
This eliminates two fields and the consistency risk entirely. For 60 cards, the O(n) cost per access is negligible.

**Option B (keep fields, add `record_attempt` method per R2):** Mutation is always done through the method, so consistency is maintained by encapsulation rather than by removing the fields.

**Architectural Benefit:** Single source of truth for session totals; no silent divergence possible.

---

### R6 — Fix Python Version Compatibility in `main.py`

**File:** `main.py`
**Issue Category:** Compatibility, Spec Violation
**Current Pattern:**
```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
def main(argv: list[str] | None = None) -> int:
```
**Recommended Solution:**
```python
from typing import List, Optional

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
def main(argv: Optional[List[str]] = None) -> int:
```
**Architectural Benefit:** Aligns with the stated "Python 3.8+" requirement. The `X | Y` syntax in annotations is only valid at runtime in Python 3.10+.

---

### R7 — Route Startup Banner Through `Display`

**File:** `main.py`
**Issue Category:** Layer Boundary Violation, SRP
**Current Pattern:**
```python
print(f"\nLoaded {len(cards)} card(s) — mode: {args.mode}\n")
```
**Recommended Solution:**
```python
# utils/display.py
def show_info(self, message: str) -> None:
    print(f"\n{message}\n")

# main.py
display.show_info(f"Loaded {len(cards)} card(s) — mode: {args.mode}")
```
**Architectural Benefit:** All terminal output flows through `Display`, making it possible to suppress or redirect output in tests without patching `builtins.print` in `main.py` separately.

---

### R8 — Extract Magic Width Constant in `Display.show_summary`

**File:** `utils/display.py`
**Issue Category:** Magic Values, DRY
**Current Pattern:** Literal `40` repeated three times in `show_summary`.
**Recommended Solution:**
```python
_SUMMARY_WIDTH = 40

def show_summary(self, stats: SessionStats) -> None:
    print("\n" + "=" * _SUMMARY_WIDTH)
    ...
    print("-" * _SUMMARY_WIDTH)
    print("=" * _SUMMARY_WIDTH)
```
**Architectural Benefit:** Single change point if the display width is ever adjusted.

---

### R9 — Fix TOCTOU Race in `FlashcardLoader._read_file`

**File:** `utils/loader.py`
**Issue Category:** Race Condition, Non-idiomatic Python
**Current Pattern:**
```python
file = Path(path)
if not file.exists():
    raise FlashcardLoadError(f"File not found: {path}")
return file.read_text(encoding="utf-8")
```
**Recommended Solution:**
```python
try:
    return Path(path).read_text(encoding="utf-8")
except FileNotFoundError:
    raise FlashcardLoadError(f"File not found: {path}") from None
except PermissionError as exc:
    raise FlashcardLoadError(f"Permission denied reading {path}") from exc
```
**Architectural Benefit:** Eliminates the TOCTOU race; also handles `PermissionError` which the current code silently propagates as an unhandled exception.

---

## 4. Prioritized Action Plan

### Critical Refactorings
*(Breaking violations or significant resilience gaps)*

| Priority | Ref | File | Issue |
|---|---|---|---|
| 1 | R4 | `main.py`, `engine.py`, `display.py` | `KeyboardInterrupt`/`EOFError` unhandled — raw traceback on Ctrl+C |
| 2 | R6 | `main.py` | `list[str] \| None` syntax breaks Python 3.8/3.9 — spec violation |
| 3 | R9 | `utils/loader.py` | TOCTOU race + `PermissionError` not caught |

---

### Structural Improvements
*(Extensibility, loose coupling, pattern alignment)*

| Priority | Ref | File | Issue |
|---|---|---|---|
| 4 | R1 | `display.py`, `engine.py` | Missing `DisplayProtocol` — DIP not fully realized |
| 5 | R2 | `models.py`, `engine.py` | Engine mutates model internals — encapsulate in `SessionStats.record_attempt()` |
| 6 | R5 | `models.py` | Redundant aggregates create two-source-of-truth risk |
| 7 | R3 | `engine.py` | Inline answer evaluation rule — extract `_evaluate_answer()` |
| 8 | R7 | `main.py`, `display.py` | Bare `print()` in `main.py` breaks Display boundary |

---

### Polish & Quality Enhancements
*(Type annotations, constants, documentation)*

| Priority | Ref | File | Issue |
|---|---|---|---|
| 9 | R8 | `display.py` | Magic width `40` repeated three times — extract constant |
| 10 | — | `strategies.py` | Add `__repr__` to strategy classes for diagnostics |
| 11 | — | `strategies.py` | Document stable-sort guarantee in `AdaptiveStrategy.select()` docstring |
| 12 | — | `loader.py` | Split `FlashcardLoadError` into `FlashcardFileError` + `FlashcardSchemaError` for caller discrimination |
| 13 | — | `loader.py` | Consider replacing stateless `FlashcardLoader` class with a module-level function |

---

*End of report.*
