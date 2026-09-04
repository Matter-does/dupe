# J2 on macOS CI

## Why macOS CI?

The public J2 0.1.0 release currently documents a macOS Apple Silicon distribution. The official repository provides the Apple Silicon tarball and the native build command `j2 build file.j2 -o out`.

This repository therefore treats GitHub Actions as the J2-native build environment while source editing can remain on Windows.

## Current workflow

`.github/workflows/j2.yml`:

- runs on the Apple Silicon `macos-15` GitHub-hosted runner;
- downloads the pinned J2 0.1.0 Apple Silicon tarball;
- verifies the published SHA-256;
- exposes the unpacked J2 directory on `PATH`;
- checks `j2 --version`;
- runs an interpreter smoke test with `j`;
- performs a native `j2 build` smoke test;
- runs project `.j2` tests when they exist;
- builds `src/dupe.j2` once that entrypoint exists.

The Apple Silicon architecture check is deliberate: the workflow should fail loudly rather than accidentally testing under a different architecture.

## First milestone

Before implementing filesystem-heavy logic, add tiny programs to `tests/` and use CI to establish exactly which J2 syntax and standard-library interfaces are available in 0.1.0.

Do not add an API merely because it appears plausible. Every filesystem, hashing, argument-parsing, JSON, and process interface must first be verified by compilation/execution or by the official J2 documentation.
