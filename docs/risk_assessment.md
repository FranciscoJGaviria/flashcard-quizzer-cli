# Holistic Risk Assessment: Flashcard Quizzer CLI

**Date:** 2026-08-15
**Reviewer role:** Senior Software Security & Reliability Engineer
**Codebase state:** Post-refactoring audit (128 tests, 100% coverage, flake8/mypy clean)

---

## 1. Executive Risk Summary

**Overall risk posture: LOW–MODERATE**

The refactored codebase is well-structured and has eliminated several classes of defects (TOCTOU race, bare `except:`, Python 3.10+ syntax, missing `KeyboardInterrupt` handler). The application is local-only with no network surface, no authentication, and no persistent state — this significantly constrains the attack surface.

The remaining risks are concentrated in three areas:

1. **Path traversal** — the `--file` CLI argument accepts arbitrary paths with no sandbox boundary. On a shared machine this could expose unintended files for reading (not writing, since the app is read-only).
2. **Memory exhaustion via large JSON** — no file size guard before `Path.read_text()`. A multi-gigabyte deck file causes an OOM condition before the JSON parser can report an error.
3. **Terminal escape injection** — card `front`/`back` fields are printed verbatim. A crafted JSON deck containing ANSI escape sequences can clear the terminal, hide output, or spoof prompts.
4. **Colorblind / no-color accessibility** — feedback uses Unicode symbols (`✓`/`✗`) without color, which is good, but there is no `--no-unicode` fallback for terminals that cannot render those characters.

No **critical** (data loss, privilege escalation, or remote exploitation) vulnerabilities were identified. All high-severity findings are **local-scope only**.

---

## 2. Comprehensive Risk Matrix

| ID | Dimension | Risk Description | Severity | Likelihood | Impact Domain | Prevention / Fix |
|:---|:---|:---|:---|:---|:---|:---|
| R1 | Security | Path traversal via `--file` accepts `../../etc/passwd` or symlinks | High | Medium | Local file read | Resolve & optionally confine path with `Path.resolve()` + allowlist |
| R2 | Security | Memory exhaustion (OOM) from a multi-GB deck file | High | Low | Application / host stability | Add file-size guard before `read_text()` |
| R3 | Security | ANSI escape injection from card text printed verbatim | Medium | Medium | Terminal manipulation / prompt spoofing | Strip or escape ANSI sequences before printing |
| R4 | Security | Exception messages expose absolute file paths to stdout | Low | High | Information disclosure | Trim paths to basename in user-facing messages |
| R5 | Reliability | `KeyboardInterrupt` in `Display.get_input()` propagates to raw traceback | Medium | Medium | UX — ugly crash | Catch `KeyboardInterrupt` inside `get_input()` or re-raise cleanly |
| R6 | Reliability | EOF in `get_input()` returns `""` → engine marks every remaining card as incorrect | Medium | High | Incorrect session result | Detect empty-string-from-EOF and break the quiz loop early |
| R7 | Reliability | Single-card deck: `AdaptiveStrategy` terminates after one card (correct, no loop risk) | Low | High | Trivial edge case — no bug | Already handled; documented for clarity |
| R8 | Reliability | Unicode/emoji in card text may cause `UnicodeEncodeError` on legacy Windows terminals | Low | Medium | Encoding crash | Encode with `errors="replace"` or advise `PYTHONIOENCODING=utf-8` |
| R9 | Ethical | `✓`/`✗` symbols may not render on Windows `cmd.exe` / legacy codepages | Low | Medium | Accessibility — garbled output | Provide ASCII fallback (`[OK]`/`[X]`) when unicode is unavailable |
| R10 | Ethical | `AdaptiveStrategy` does not cap miss-priority — a perpetually missed card always appears first, creating a punishing loop across sessions | Low | High | Learning fairness — demotivation | Cap miss influence or rotate after N consecutive misses |
| R11 | Ethical | Answer evaluation is exact-match only (case/whitespace stripped) — no synonym tolerance | Low | High | Learning accuracy — false negatives for valid paraphrases | Document limitation clearly; optionally support configurable fuzzy match |
| R12 | Ethical | No `--no-color`/`--no-unicode` CLI flag — no accessibility opt-out path | Low | Medium | Accessibility | Add `--plain` flag that replaces symbols with ASCII and suppresses ANSI |
| R13 | Reliability | `show_summary` prints to stdout always; no way to suppress on redirect | Low | Low | Scripting / automation | Not a bug in interactive use; noted for future `--quiet` flag |

---

## 3. Deep Dive into Top Risks

### R1 — Path Traversal via `--file` Argument

**Failure / Attack Scenario**

```bash
python main.py --file ../../etc/passwd
```

`Path("../../etc/passwd").read_text()` succeeds on any Unix system where the process has read access. The JSON parser then raises `FlashcardSchemaError: Invalid JSON` — but by then the file has already been fully read into memory and its content is visible in the exception message if it happens to be short enough to fit in a `json.JSONDecodeError` context string.

On shared machines (university labs, containers with mounted volumes) this is a viable information-disclosure path. The application is read-only, so **no file overwrite risk exists**.

**Root Cause in Code**

`utils/loader.py:78` — `Path(path).read_text(encoding="utf-8")` — accepts the path exactly as supplied by the user without any normalisation or boundary check.

`main.py:88` — `FlashcardLoader().load(args.file)` — passes `args.file` directly from `argparse` with no sanitisation.

**Remediation Code Snippet**

```python
# utils/loader.py — _read_file()
import os

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB guard (see R2)

def _read_file(self, path: str) -> str:
    resolved = Path(path).resolve()
    try:
        size = resolved.stat().st_size
        if size > MAX_FILE_BYTES:
            raise FlashcardFileError(
                f"File too large ({size // 1_048_576} MB). "
                f"Maximum allowed size is {MAX_FILE_BYTES // 1_048_576} MB."
            )
        return resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FlashcardFileError(f"File not found: {resolved.name}") from None
    except PermissionError as exc:
        raise FlashcardFileError(f"Permission denied reading {resolved.name}") from exc
```

Using `Path.resolve()` converts the path to an absolute canonical path (resolving `..` and symlinks). An optional allowlist can additionally confine the accepted paths:

```python
# Optional sandbox: only allow files within the project data directory
DATA_DIR = Path(__file__).parent.parent / "data"

def _check_sandbox(self, resolved: Path) -> None:
    try:
        resolved.relative_to(DATA_DIR)
    except ValueError:
        raise FlashcardFileError(
            f"File must be inside the data/ directory: {resolved.name}"
        )
```

---

### R2 — Memory Exhaustion from Large JSON File

**Failure / Attack Scenario**

An adversary (or accidental user error) supplies a 2 GB JSON file. `Path.read_text()` reads the entire file into a Python `str` before any validation occurs. On a system with limited RAM, this causes the OS to invoke the OOM killer, terminating the process (or an unrelated process) without a clean error message.

**Root Cause in Code**

`utils/loader.py:78` — no size check before `read_text()`.

**Remediation Code Snippet**

Add a `stat()` size check before reading (shown in R1 remediation above, `MAX_FILE_BYTES` guard). This resolves both R1 and R2 with a single change.

---

### R3 — ANSI Escape Injection from Card Text

**Failure / Attack Scenario**

A crafted deck JSON with a card whose `front` field contains an ANSI escape sequence:

```json
{"front": "\u001b[2J\u001b[H Legitimate Question", "back": "Answer"}
```

When `display.show_prompt(card.front)` executes `print(f"\nCard: {front}")`, the terminal interprets `\x1b[2J` (clear screen) and `\x1b[H` (cursor home), erasing all previous output. A more sophisticated payload can produce fake prompts:

```json
{"front": "\u001b[31mSECURITY ALERT\u001b[0m — enter your password:", "back": "Answer"}
```

This is a **prompt spoofing** vector on shared/kiosk terminals.

**Root Cause in Code**

`utils/display.py:54` — `print(f"\nCard: {front}")` — card text is printed verbatim with no sanitisation. Same issue on lines 80, 103.

**Remediation Code Snippet**

```python
import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def _sanitise(text: str) -> str:
    """Strip ANSI escape sequences from *text* before printing."""
    return _ANSI_ESCAPE.sub("", text)

# Usage in show_prompt:
def show_prompt(self, front: str) -> None:
    print(f"\nCard: {self._sanitise(front)}")
```

---

### R5 — `KeyboardInterrupt` During `get_input()` Bypasses Clean Exit

**Failure / Attack Scenario**

The user presses Ctrl+C **while the `input()` prompt is displayed**. Python raises `KeyboardInterrupt` inside `get_input()`. This propagates upward through the `for card in ordered` loop in `QuizEngine.run()`, bypassing `display.show_summary()`. Control returns to `main()`, where the outer `except KeyboardInterrupt` catches it and prints `[Quiz interrupted. Goodbye!]` with exit 130.

The exit is *clean* from the process perspective, but **the session summary is never shown** — the user loses all progress metrics. On a long session this is a significant usability failure.

**Root Cause in Code**

`utils/display.py:65-68` — `get_input()` catches `EOFError` but not `KeyboardInterrupt`.
`utils/engine.py:53-58` — the quiz loop has no finally block to display summary on interruption.

**Remediation Code Snippet**

```python
# utils/engine.py — run()
def run(self) -> SessionStats:
    stats = SessionStats()
    ordered = self._strategy.select(self._cards, stats)
    try:
        for card in ordered:
            self._display.show_prompt(card.front)
            raw = self._display.get_input()
            is_correct = self._evaluate_answer(raw, card.back)
            self._display.show_feedback(is_correct, card.back)
            stats.record_attempt(card, is_correct)
    except KeyboardInterrupt:
        pass  # re-raised after partial summary
    finally:
        if stats.total_attempts > 0:
            self._display.show_summary(stats)
    return stats
```

With this change, Ctrl+C mid-quiz still shows the partial summary before the `[Quiz interrupted]` message in `main()`.

---

### R6 — EOF Returns `""` But Engine Continues Loop

**Failure / Attack Scenario**

When stdin is closed (`Ctrl+D` or piped empty input), `get_input()` returns `""` for every subsequent call. `_evaluate_answer("", card.back)` returns `False` for all cards. The engine silently marks every remaining card as incorrect, then shows a misleading summary with 0% accuracy.

**Root Cause in Code**

`utils/display.py:67` — `except EOFError: return ""` is correct for a single EOF, but does not signal to the engine that no more input is available.

`utils/engine.py:55-58` — the engine loop has no sentinel check to detect repeated empty answers from EOF.

**Remediation Code Snippet**

The cleanest fix is a sentinel: let `get_input()` return `None` on EOF, and let the engine break on `None`:

```python
# utils/display.py
from typing import Optional

def get_input(self) -> Optional[str]:
    try:
        return input("Your answer: ")
    except EOFError:
        return None

# utils/engine.py — run() inner loop
raw = self._display.get_input()
if raw is None:
    break
```

This requires updating `DisplayProtocol.get_input` return type to `Optional[str]` and adjusting `_evaluate_answer` to handle `None` (or guard before calling it).

---

## 4. Prioritized Mitigation Action Plan

### P0 — Critical Reliability & Security Safeguards

These address crash-or-corrupt-output conditions and local information-disclosure vectors.

| # | Action | File(s) | Effort |
|---|---|---|---|
| 1 | Add file-size guard (`stat().st_size`) before `read_text()` | `utils/loader.py` | 5 min |
| 2 | Use `Path.resolve()` on the incoming path; expose only `resolved.name` in error messages | `utils/loader.py` | 5 min |
| 3 | Strip ANSI escape sequences from card text before printing | `utils/display.py` | 10 min |
| 4 | Move `KeyboardInterrupt` catch into `engine.run()` with `finally` to ensure partial summary is shown | `utils/engine.py` | 10 min |
| 5 | Change `get_input()` sentinel from `""` to `None`; break loop on `None` | `utils/display.py`, `utils/engine.py` | 15 min |

---

### P1 — Algorithmic & State Robustness

These address edge-case correctness and UX degradation scenarios.

| # | Action | File(s) | Effort |
|---|---|---|---|
| 6 | Document (or guard) that `✓`/`✗` require UTF-8 terminal; add `PYTHONIOENCODING=utf-8` note to README/startup banner | `utils/display.py`, docs | 10 min |
| 7 | Handle `UnicodeEncodeError` in `show_prompt`/`show_feedback` with `errors="replace"` on stdout | `utils/display.py` | 10 min |
| 8 | Add optional miss-count cap to `AdaptiveStrategy` (e.g. cap contribution at 5 misses) to prevent perpetual front-loading of a single hard card | `utils/strategies.py` | 15 min |

---

### P2 — Accessibility & Terminal UX Improvements

These improve inclusivity and scripting ergonomics without changing core logic.

| # | Action | File(s) | Effort |
|---|---|---|---|
| 9 | Add `--plain` CLI flag that routes through a `PlainDisplay` (ASCII-only `[OK]`/`[X]`, no ANSI) | `main.py`, `utils/display.py` | 30 min |
| 10 | Add contextual hint on incorrect answer: show how close the user was (character diff or word match percentage) | `utils/display.py` | 20 min |
| 11 | Document in `--help` that answer matching is exact (case/whitespace normalised) so learners are not surprised by misses | `main.py` argparse help text | 5 min |

---

## 5. Accepted Non-Issues

| Item | Rationale |
|---|---|
| No network surface | Application is 100% local; no HTTP, socket, or subprocess calls. Remote exploitation is impossible. |
| No persistent state | Session stats exist only in memory. No files are written. No privacy risk from data retention. |
| No authentication | Single-user local tool. No credentials, sessions, or access control to misuse. |
| `ZeroDivisionError` in `accuracy` | Already guarded: `if self.total_attempts == 0: return 0.0` at `models.py:89`. Not a risk. |
| Infinite loop in `AdaptiveStrategy` | `select()` runs once per session and is a pure sort. No loop. No risk. |
| `show_summary` always prints to stdout | Acceptable for interactive CLI. Noted as a future `--quiet` flag opportunity, not a defect. |

---

*End of risk assessment.*
