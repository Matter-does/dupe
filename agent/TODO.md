# Task Queue

## Priority order

- [x] T001 — Repository agent workflow (COMPLETED / FROZEN)
- [x] T002 — Complete Phase 4 correctness and regression gates (COMPLETED / FROZEN)
- [x] T003 — Competitive/technical research consolidation (COMPLETED / FROZEN)
- [x] T004 — Benchmark corpus specification and generator (COMPLETED / FROZEN)
- [x] T005 — J2 interpreter/native baseline benchmark (COMPLETED / FROZEN)
- [x] T006 — Automatic-parallelism experiment and evidence collection (COMPLETED / FROZEN)
- [x] T007 — Reusable filesystem analysis pass for a second read-only workload (COMPLETED / FROZEN)
- [x] T008 — CLI/product surface polish (COMPLETED / FROZEN / RELEASE READY)
- [x] T009 — Lightweight GUI shell over the engine (COMPLETED / FROZEN / RELEASE READY)
- [x] T010 — Demo workload and benchmark presentation (COMPLETED / FROZEN / RELEASE READY)
- [ ] T011 — Final CI/documentation/submission package (Implementation Complete — Awaiting Adversarial Review)

## Ordering rule
Do not start a later task while a prerequisite task is incomplete unless the task is explicitly independent. Performance work begins only after correctness is locked.

## Agent assignment rule
Antigravity is the default implementation agent. OpenCode is the continuation/fallback path. Claude Code through OmniRouter and GLM-5 are reviewers or independent implementers when assigned. ChatGPT defines/revises tasks from research and evidence.

## Completion rule
A task is removed from the active queue only after its acceptance criteria, verification, checkpoint, handoff, and Git boundary are complete.
