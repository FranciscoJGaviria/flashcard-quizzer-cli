# AI-Assisted Development Project Report

**Student Name:** Francisco Javier Gaviria Sierra
**Project Title:** Flashcard Quizzer CLI (`flashcard-quizzer-cli`)
**Date:** 16/08/2026

---

## Executive Summary

The **Flashcard Quizzer CLI** is a modular, high-reliability command-line tool built in Python 3.8+ to help teams memorize acronyms and concepts (such as AWS services). Developed using only the Python standard library with zero external runtime dependencies, the application ingests structured JSON flashcard datasets, presents cards sequentially, randomly, or adaptively, evaluates user responses using flexible case-insensitive matching, and provides real-time performance analytics.

The architecture adheres to SOLID principles, incorporating the **Strategy Pattern** for interchangeable quiz algorithms, **Dependency Injection** to decouple terminal I/O from execution logic, and a **Factory Pattern** for CLI dispatching. Development followed strict Test-Driven Development (TDD), achieving 100% test coverage across core utility modules (97% project-wide) across 166 passing unit and integration tests.

AI assistants (Claude, Gemini) were used throughout development for architecture planning, test design, scaffolding, refactoring, and multi-round iterative improvements. By pairing AI generation with a systematic code review checklist, linting (`flake8`, `mypy`, `black`, `isort`), security auditing (`bandit`), and a pre-commit quality gate, all AI outputs were carefully audited, refined, or rejected.

---

## Project Overview

### Problem Statement
Cloud infrastructure engineering requires memorizing numerous acronyms and definitions (e.g., EC2, S3, IAM). Existing flashcard tools often require heavy GUIs or online accounts. Engineering teams need a lightweight, terminal-native, offline tool that loads custom JSON decks with instant startup and flexible study modes.

### Solution Approach
- **Layered Architecture:** Modular separation between data models (`models.py`), card ordering algorithms (`strategies.py`), quiz execution (`engine.py`), JSON ingestion (`loader.py`), and CLI rendering (`display.py`).
- **Strategy Design Pattern:** Pluggable quiz modes enabling Sequential, Random, and Adaptive study without modifying core engine logic.
- **Zero Runtime Dependencies:** Built purely on Python standard library modules (`json`, `random`, `dataclasses`, `argparse`, `typing`).
- **Graceful Error Recovery:** Custom exceptions and schema validation that prevent raw stack traces on corrupt datasets or filesystem errors.

### Final Features
- [x] **Sequential Quiz Mode:** Delivers cards in their original deck order.
- [x] **Randomized Quiz Mode:** Shuffles cards while preserving original deck immutability.
- [x] **Adaptive Mode:** Prioritizes cards with historical misses from preceding rounds to optimize learning.
- [x] **Interactive Multi-Round Loop:** Enables continuous study sessions with isolated per-round summary scorecards.
- [x] **Smart Answer Evaluation:** Case-insensitive, whitespace-trimmed string comparison.
- [x] **Session Analytics:** Per-card attempt/miss tracking and formatted summary scorecards.
- [x] **JSON Schema Validation:** Enforces root `"cards"` array, non-empty fields, directory checks, and 10MB size limit.
- [x] **Clean Signal Handling:** Handles `KeyboardInterrupt` (Ctrl+C) and `EOFError` gracefully with standard exit codes (130 / 0).

---

## AI Collaboration Experience

### AI Tools Used
- [x] Claude
- [x] Gemini

### Collaboration Workflow
1. **Context-Driven Prompting:** Prompts defined clear architectural boundaries, type hints, and error-handling constraints before requesting code.
2. **Test-First Generation:** AI generated unit tests against abstract interfaces prior to implementing feature code.
3. **Checklist Review:** AI code was systematically vetted against [`ai_guidance/code_review_checklist.md`](../ai_guidance/code_review_checklist.md) for security, type correctness, and style standards.
4. **Refinement & Rejection:** Suboptimal AI suggestions (such as in-place list mutations or coupled I/O) were rejected and corrected.

### Most Valuable AI Interactions

The following key interactions from [`docs/ai_edit_log.md`](ai_edit_log.md) illustrate how structured prompting and disciplined code review shaped the project:

#### Interaction 1: Architecture Planning & TDD Sequencing (`09/08/2026 - Design Modular Architecture` & `Refine Architecture`)
- **Context:** Establishing the high-level system architecture and implementation roadmap before writing code.
- **AI Prompt:** Used an XML-formatted prompt specifying application constraints, SOLID requirements, and explicitly requiring the AI to present the design for review before generating files. Followed up with a prompt establishing an inside-out implementation order (`models` → `strategies` → `engine` → `loader` → `display` → `main`) and a TDD mandate.
- **AI Response:** Produced [`docs/Architect.md`](Architect.md) with class interfaces, data flow diagrams, and a concrete testing strategy.
- **Modifications & Value:** Adding the explicit "ask me before finalizing" constraint prevented premature file generation and ensured TDD discipline was baked into the project from day one.

#### Interaction 2: Strategy Pattern Implementation & Immutability (`15/08/2026 - Implement strategies.py`)
- **Context:** Implementing the Strategy Pattern module for card ordering (`SequentialStrategy`, `RandomStrategy`, `AdaptiveStrategy`).
- **AI Prompt:** Provided a role-constrained prompt referencing [`docs/Architect.md`](Architect.md) and [`docs/design_patterns.md`](design_patterns.md) with requirements for type hints, Google-style docstrings, and table-driven pytest tests.
- **AI Response & Review:** AI provided the strategy classes, but in initial drafts attempted in-place list mutation (`random.shuffle(cards)`).
- **Modifications & Value:** Enforced defensive copying (`shuffled = list(cards)`) across all strategy methods to guarantee deck immutability and prevent side effects.

#### Interaction 3: QuizEngine Orchestration & Dependency Injection (`15/08/2026 - Implement engine.py`)
- **Context:** Orchestrating the interactive quiz loop while decoupling business logic from console I/O.
- **AI Prompt:** Prompt constrained `QuizEngine` to interact with the terminal exclusively through an injected `DisplayProtocol` interface.
- **AI Response:** Generated `QuizEngine` with methods for prompt display, answer evaluation, and summary generation.
- **Modifications & Value:** Enabled near-instantaneous, 100% automated test coverage in [`tests/test_engine.py`](../tests/test_engine.py) using mock display objects without spawning subshells.

#### Interaction 4: Architectural Code Review & Checklist Verification (`15/08/2026 - Architectural Code Review` & `Address Findings`)
- **Context:** Auditing the full codebase against 5 architectural dimensions (Separation of Concerns, SOLID, Error Handling, Complexity Control, Type Safety).
- **AI Prompt:** Prompted AI with an extensive review framework to produce [`docs/architectural_review.md`](architectural_review.md), followed by a checklist-driven remediation prompt.
- **AI Response:** Identified coupling risks, magic values, and broad exceptions.
- **Modifications & Value:** Resolved all findings by establishing the domain exception hierarchy (`FlashcardLoadError` / `FlashcardFileError` / `FlashcardSchemaError`), extracting constants, and validating with pre-commit gates.

#### Interaction 5: Holistic Risk Assessment & Multi-Dimensional Safeguards (`15/08/2026 - Holistic Risk Assessment` & `Address Findings`)
- **Context:** Evaluating edge cases, failure modes, security risks, and terminal accessibility.
- **AI Prompt:** Evaluated the system across Security (ANSI injection, path traversal), Reliability (Ctrl+C, EOF, empty decks), and Accessibility (colorblind cues).
- **AI Response:** Generated [`docs/risk_assessment.md`](risk_assessment.md) and corresponding mitigations in [`docs/risk_mitigation_audit.md`](risk_mitigation_audit.md).
- **Modifications & Value:** Implemented `_sanitise()` for ANSI escape neutralization, added symbol cues (`✓` / `✗`) alongside colors, and ensured graceful exit codes (`130` on SIGINT, `0` on EOF).

### Challenges with AI Collaboration
- **Premature I/O Coupling:** AI models frequently attempt to call `print()` or `input()` inside core logic unless strictly constrained by interface protocols.
- **In-Place List Mutations:** AI code often uses mutating operations (`list.sort()`, `random.shuffle()`) instead of returning new copies, risking caller state pollution.
- **Cumulative State Assumptions:** When adding multi-round loops, AI initially accumulated all historical stats into a single object, requiring human architectural guidance to isolate per-round metrics from cross-round adaptive prioritization.

---

## Software Engineering Practices

### Code Quality Measures
- [x] Formatting: Black (88-char limit) & isort
- [x] Linting: Flake8 (0 errors) & Mypy (strict static typing)
- [x] Security Scanning: Bandit (0 vulnerabilities)
- [x] Documentation: Comprehensive Google-style docstrings
- [x] Quality Gate: Pre-commit hooks running linters, security scans, and test suite on every commit

### Testing Strategy
- **Unit & Integration Testing:** Comprehensive suites across models, strategies, loader, display, engine, and CLI entry point.
- **Edge Case Coverage:** Validated empty decks, malformed JSON, directory inputs, division by zero guards, `EOFError`, and `KeyboardInterrupt`.
- **Coverage:** **97% total project coverage** (100% across all `utils/` modules) across 166 passed tests.

### Design Patterns Used
- **Strategy Pattern (`utils/strategies.py`):** `CardSelectionStrategy` ABC with `SequentialStrategy`, `RandomStrategy`, and `AdaptiveStrategy` implementations.
- **Factory Pattern (`main.py`):** `STRATEGIES` dictionary mapping CLI mode strings to strategy classes.
- **Dependency Injection (`utils/engine.py`):** `QuizEngine` receives `CardSelectionStrategy` and `DisplayProtocol` via constructor.

### Code Structure and Organization
The codebase separates concerns cleanly: `main.py` handles CLI routing and multi-round session coordination; `utils/models.py` contains pure dataclasses; `utils/strategies.py` encapsulates selection algorithms; `utils/engine.py` orchestrates the quiz loop; `utils/loader.py` manages file I/O and schema validation; and `utils/display.py` handles terminal rendering and ANSI sanitization.

---

## Technical Challenges and Solutions

### Challenge 1: Testing Interactive CLI Logic
- **Problem:** Direct calls to `input()` and `print()` make automated testing difficult and brittle.
- **Solution:** Applied Dependency Injection by isolating terminal I/O in `Display`. In tests, a mock display is supplied to verify prompts, user responses, and summaries deterministically.
- **Lessons Learned:** Architectural separation of I/O allows near-instantaneous, 100% unit test coverage.

### Challenge 2: Graceful Schema and File Validation
- **Problem:** Corrupted JSON files, missing keys, or directory paths risked terminating the CLI with confusing stack traces.
- **Solution:** Implemented `FlashcardLoadError` hierarchy and a validation pipeline in `FlashcardLoader` handling missing files, directories, size limits (>10MB), and schema errors.
- **Lessons Learned:** Domain-specific exceptions provide clean error boundaries and a polished user experience.

### Challenge 3: Multi-Round Adaptive Handoff vs. Summary Isolation
- **Problem:** Cumulative stats across rounds polluted the end-of-round scorecard, displaying previously missed terms even after a perfect round.
- **Solution:** Separated `round_stats` (current round metrics displayed to user) from `previous_stats` (passed to `AdaptiveStrategy` for ordering the next round).
- **Lessons Learned:** Decoupling presentation state from algorithmic scheduling state ensures clean UX and responsive learning feedback.

---

## Code Quality Analysis

### Metrics
- **Lines of Code:** ~1,100 lines (source and test code)
- **Test Coverage:** 97% overall (100% across `utils/` modules)
- **Unit Tests:** 166 passing tests in 0.18s
- **Static Analysis:** Flake8: 0 errors; Mypy: 0 errors; Bandit: 0 security issues

### Self-Assessment
- **Code Readability:** **5/5** — Clean naming, type annotations, and descriptive docstrings.
- **Code Maintainability:** **5/5** — SOLID architecture allows adding new modes without modifying engine code.
- **Test Quality:** **5/5** — Comprehensive suite testing happy paths, edge cases, and failure modes.
- **Documentation:** **5/5** — Complete README, architecture docs, AI edit logs, and reports.

---

## Learning Outcomes

### Technical Skills Developed
- Implementing the **Strategy Pattern** and **Dependency Injection** in Python standard library.
- Setting up pre-commit automation pipelines with `black`, `isort`, `flake8`, `mypy`, and `bandit`.
- Designing thorough unit test suites using `pytest` and `pytest-cov`.

### AI Collaboration Skills
- Formulated the **"Prompt as Specification"** approach: providing exact constraints, XML tags, and interface definitions yields reliable AI code.
- Practiced disciplined code review, treating AI output as draft proposals requiring verification against checklists.
- Learned when to leverage AI (test scaffolding, boilerplate, risk matrices) versus manual architectural direction (state decoupling, security invariants).

### Software Engineering Insights
- Strong architectural boundaries significantly simplify testing and long-term maintenance.
- Automated pre-commit gates prevent code quality regressions before commits are created.

---

## Reflection

### What Worked Well
- **Structured XML Prompting:** Explicitly defining `<role>`, `<task>`, `<requirements>`, and `<constraints>` (as logged in `ai_edit_log.md`) produced focused, production-grade code on the first attempt.
- **Inside-Out TDD:** Writing domain models and strategy tests before wiring the CLI engine ensured rock-solid core logic.
- **Multi-Round Architecture:** Isolating per-round stats while handing off prior misses to `AdaptiveStrategy` delivered an intuitive, responsive quiz experience.

### What Could Be Improved & Future Enhancements
1. **Multi-Session Persistence:** Full Leitner Box or SM-2 spaced repetition scheduler with SQLite storage across distinct CLI launches.
2. **Fuzzy String Matching:** Minor typographical forgiveness in answer evaluation using Levenshtein distance.
3. **Import/Export:** Support for importing and exporting Anki (`.apkg`) and CSV decks.

---

## Conclusion

The Flashcard Quizzer CLI project illustrates how combining solid software engineering practices with structured AI collaboration produces reliable, maintainable software. By actively auditing AI suggestions against quality checklists and maintaining strict testing discipline, the project achieved 100% core test coverage, full PEP 8 compliance, and clean architectural extensibility.

---

## Appendices

### Appendix A: AI Interaction Log
Full interaction records and decision rationale are maintained in [`docs/ai_edit_log.md`](ai_edit_log.md).

### Appendix B: Additional Documentation & Technical Audits
- [Implementation Report](implementation_report.md) — Module-by-module breakdown, test results, and extension guide
- [Architectural Code Review](architectural_review.md) — Inspection of SOLID principles, decoupling, and quality standards
- [Risk Assessment](risk_assessment.md) — Comprehensive assessment of security, reliability, performance, and testing risks
- [Refactoring Audit](refactoring_audit.md) — Detailed log of refactoring iterations and checklist validations
- [Risk Mitigation Audit](risk_mitigation_audit.md) — Verification of implemented risk mitigation controls
- [Architecture Specification](Architect.md) — High-level architecture and design specifications
- [Design Patterns Guide](design_patterns.md) — Strategy pattern guide and usage examples
