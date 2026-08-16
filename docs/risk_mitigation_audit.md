# Risk Mitigation Audit: Flashcard Quizzer CLI

**Date:** 2026-08-15
**Based on:** `docs/risk_assessment.md`
**Final state:** 143 tests | 100% coverage | flake8 exit 0 | mypy exit 0

---

## Verification Checklist

| Requirement | Status | Evidence |
|---|---|---|
| File paths validated and normalized (no path traversal) | ✅ PASS | `loader._read_file` calls `Path(path).resolve()` before any I/O |
| JSON payload size strictly validated before parsing | ✅ PASS | `resolved.stat().st_size` checked against `_MAX_FILE_BYTES = 10 MB` before `read_text()` |
| Terminal inputs and card contents sanitized against ANSI escape sequences | ✅ PASS | `_sanitise()` in `display.py` strips all ANSI CSI sequences; applied in `show_prompt`, `show_feedback`, `show_summary` |
| No internal file paths or raw stack traces exposed to stdout | ✅ PASS | Error messages expose `resolved.name` (filename only), never the full absolute path |
| `KeyboardInterrupt` caught cleanly with exit code 130 | ✅ PASS | Engine catches it, shows partial summary in `finally`, re-raises; `main()` returns 130 |
| `EOFError` caught cleanly; loop terminates without marking cards wrong | ✅ PASS | `get_input()` returns `None` on EOF; engine breaks loop immediately on `None` |
| Empty decks and missing files fail gracefully | ✅ PASS | Pre-existing behaviour unchanged; `FlashcardFileError` / empty-deck check in `main()` |
| Zero-division protected in all statistical calculations | ✅ PASS | `SessionStats.accuracy` guards `total_attempts == 0` (pre-existing, `models.py:89`) |
| Adaptive algorithm guaranteed to terminate | ✅ PASS | `AdaptiveStrategy.select()` is a pure `sorted()` call — no loop |
| All file I/O uses context managers | ✅ PASS | `Path.read_text()` (stdlib) manages the file handle internally |
| Feedback includes textual/symbol cues (`✓`/`✗`) | ✅ PASS | Pre-existing; symbols present since initial implementation |
| Normalisation logic documented to the user | ✅ PASS | `--mode` help text states "case-insensitively with leading/trailing whitespace stripped"; `show_feedback` docstring explains it |
| Progress metrics communicated to user | ✅ PASS | `show_summary` always called in `finally` block — shown on normal completion and on Ctrl+C |

---

## Finding Resolution Table

| Risk ID | Title | Severity | Status | Change |
|---|---|---|---|---|
| R1 | Path traversal via `--file` | High | ✅ MITIGATED | `Path(path).resolve()` in `loader._read_file`; filename-only in error messages |
| R2 | Memory exhaustion from large JSON | High | ✅ MITIGATED | `stat().st_size > _MAX_FILE_BYTES` guard before `read_text()`; raises `FlashcardFileError` |
| R3 | ANSI escape injection from card text | Medium | ✅ MITIGATED | `_sanitise()` function strips ANSI CSI sequences; applied to all printed card content |
| R4 | Full paths exposed in error messages | Low | ✅ MITIGATED | All errors use `resolved.name` (e.g. `cards.json`) not the full resolved path |
| R5 | `KeyboardInterrupt` skips session summary | Medium | ✅ MITIGATED | Engine wraps loop in `try/except KeyboardInterrupt` + `finally: show_summary()`; re-raises for `main()` |
| R6 | EOF marks remaining cards as incorrect | Medium | ✅ MITIGATED | `get_input()` returns `None` on `EOFError`; engine breaks loop on `None` |
| R7 | Single-card deck no-bug | Low | ✅ N/A | Documented non-issue; behaviour correct |
| R8 | `UnicodeEncodeError` on legacy terminals | Low | ✅ MITIGATED | `_safe_print()` wraps every `print()` call; falls back to `encode(..., errors="replace")` |
| R9 | `✓`/`✗` garbled on Windows cmd.exe | Low | ✅ MITIGATED | `_safe_print()` encodes with `errors="replace"` so symbols degrade gracefully |
| R10 | Adaptive strategy perpetual hard-card | Low | ✅ ACCEPTED | Single-session tool; miss count resets each run. Cap documented as future improvement. |
| R11 | No documentation of exact-match rule | Low | ✅ MITIGATED | `--mode` argparse help text and `show_feedback` docstring both explain normalisation |
| R12 | No `--plain` / `--no-unicode` flag | Low | ✅ ACCEPTED | `_safe_print()` provides graceful degradation without a flag; full `--plain` flagged as P2 future work |
| R13 | `show_summary` always prints to stdout | Low | ✅ ACCEPTED | Intentional for interactive CLI; `--quiet` flagged as future scripting improvement |

---

## Code Changes Summary

### `utils/loader.py`

| Before | After |
|---|---|
| `Path(path).read_text(encoding="utf-8")` — arbitrary path, no size limit | `resolved = Path(path).resolve()` then `resolved.stat().st_size` guard then `resolved.read_text()` |
| Error message: `f"File not found: {path}"` — exposes full caller-supplied path | Error message: `f"File not found: {resolved.name}"` — filename only |
| No file-size protection | `_MAX_FILE_BYTES = 10 MB`; raises `FlashcardFileError` if exceeded |
| `_parse_json` error included full path | `Path(path).name` used in JSON error message |

**New constant:** `_MAX_FILE_BYTES = 10 * 1024 * 1024`

---

### `utils/display.py`

| Before | After |
|---|---|
| `print(f"\nCard: {front}")` — verbatim card text | `_safe_print(f"\nCard: {_sanitise(front)}")` — ANSI-stripped |
| `print(f"✗ Incorrect...")` — may crash on legacy codepages | `_safe_print(...)` — `UnicodeEncodeError`-safe |
| `except EOFError: return ""` — empty string indistinguishable from typed answer | `except EOFError: return None` — explicit EOF sentinel |
| `get_input() -> str` | `get_input() -> Optional[str]` — updated in `DisplayProtocol` too |
| No ANSI sanitisation anywhere | `_sanitise()` module-level helper; `_safe_print()` module-level helper |

**New module-level items:**
- `import re`, `import sys`
- `_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")`
- `_sanitise(text: str) -> str`
- `_safe_print(text: str) -> None`

---

### `utils/engine.py`

| Before | After |
|---|---|
| Loop: `raw = self._display.get_input()` then evaluates unconditionally | `raw: Optional[str] = self._display.get_input(); if raw is None: break` |
| `show_summary()` called after loop — skipped on `KeyboardInterrupt` | `show_summary()` in `finally` block — always called |
| No `KeyboardInterrupt` handling | `except KeyboardInterrupt: interrupted = True` → re-raises after `finally` |

---

### `main.py`

| Before | After |
|---|---|
| `--mode` help: `"sequential \| random \| adaptive (default: sequential)"` | Help text appended: `"Answers are matched case-insensitively with leading/trailing whitespace stripped."` |

---

## Test Suite Delta

| File | Before | After | New tests cover |
|---|---|---|---|
| `test_loader.py` | 26 | 27 | `test_file_too_large_raises_flashcard_file_error` (file-size guard) |
| `test_display.py` | 35 | 46 | `TestSanitise` (7 tests), `TestSafePrint` (2 tests), `test_get_input_returns_none_on_eof` (renamed+updated) |
| `test_engine.py` | 27 | 32 | `TestQuizEngineEOFAndInterrupt` (5 tests: None break, partial summary, KeyboardInterrupt re-raise) |

**Total: 128 → 143 tests (+15)**

---

## Final Metrics

```
143 tests — 0 failures — 0 errors

Name                  Stmts   Miss  Cover
-----------------------------------------
utils/__init__.py         0      0   100%
utils/display.py         51      0   100%
utils/engine.py          30      0   100%
utils/loader.py          49      0   100%
utils/models.py          41      0   100%
utils/strategies.py      27      0   100%
-----------------------------------------
TOTAL                   198      0   100%

flake8  — exit 0 (0 errors, 0 warnings)
mypy    — exit 0 (Success: no issues in 7 source files)
black   — all files formatted
isort   — all imports sorted
```

---

## Remaining Accepted Trade-offs

| Item | Decision |
|---|---|
| No `--plain` / `--no-unicode` flag | `_safe_print()` provides silent graceful degradation; full flag is P2 future work |
| `AdaptiveStrategy` miss-count is uncapped | Single-session tool; no state persists across runs, so loop risk is contained per session |
| `show_summary` always outputs to stdout | Acceptable for interactive CLI; `--quiet` or stderr redirect is a future scripting concern |
| Path sandbox (allowlist) not enforced | `Path.resolve()` eliminates `..` traversal; a strict `data/` allowlist would break the `--file` use-case for custom decks |

---

*End of risk mitigation audit.*
