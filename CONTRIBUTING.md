# Contributing to dupe

Thank you for your interest in `dupe`. This document outlines the project philosophy, development workflow, and architectural boundaries for contributors.

## Project Philosophy & Boundaries

1. **J2 is the Computational Authority:**
   All core filesystem analysis, directory traversal, candidate filtering, SHA-256 hashing, duplicate grouping, and checksum inventory logic reside in the frozen J2 modules (`src/*.j2`). The computational core is deterministic and self-contained.

2. **GUI and CLI are Presentation Shells:**
   The Python command-line interface and Tk desktop application (`gui/`) serve solely as decoupled presentation layers. They format arguments, invoke the engine executable or interpreter via `EngineAdapter`, validate output schemas, and render results. No business logic or file hashing belongs in the presentation layer.

3. **Tests and CI are Verification Authorities:**
   Every change must be validated against the automated test suite, security harness, and Phase 4 differential correctness fuzzer. Continuous Integration on macOS 15 Apple Silicon arm64 runners verifies live J2 compilation and execution.

4. **Zero Runtime Dependencies:**
   The presentation layer and test suite must remain free of external Python dependencies. Only Python standard library modules may be used in production code.

## Development Setup

### Prerequisites

- **Python 3.10+** (with `tkinter` support).
- **macOS 15 Apple Silicon (arm64)** (required for native J2 compiler and interpreter execution).
- On Linux or Windows hosts, the Python test suite and GUI run in simulated/adapter mode without native J2 binary execution.

### Clone & Environment

```bash
git clone https://github.com/Matter-does/dupe.git
cd dupe
```

## Running Tests

### Full Test Suite
Run the complete unit and integration test suite:
```bash
python -m unittest discover -s tests -v
```
*(On non-macOS systems without J2, live J2 integration tests skip cleanly with documented notices.)*

### Security Verification Suite
Verify the T012 defensive security hardening suite (SEC-001 through SEC-005):
```bash
python tests/security/verify_t012_security.py
```

### Phase 4 Differential Correctness
Run the offline differential correctness fuzzer and SHA-256 ground truth oracle:
```bash
python tests/phase4_differential.py --offline
```

## Running the Application

### Desktop GUI
Launch the lightweight Tkinter GUI:
```bash
python -m gui.app
```

### J2 Engine Execution (macOS Apple Silicon)
Compile the standalone native binary:
```bash
j2 build src/main.j2 -o build/dupe
```

Run duplicate detection:
```bash
./build/dupe <target_directory>
```

Run checksum inventory:
```bash
./build/dupe checksum <target_directory>
```

Or execute via the J2 interpreter:
```bash
j2 --allow-fs src/main.j2 <target_directory>
```

## Pull Request Guidelines

- Ensure `git status` remains clean and all existing tests pass without regressions.
- Preserve the frozen core engine files (`src/*.j2`) and baseline benchmarks (`benchmarks/`).
- Maintain strict type validation, safe subprocess boundaries, and zero external runtime dependencies.
