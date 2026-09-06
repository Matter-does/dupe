# Current Task

**Task:** T001 — Make the repository agent-ready
**Status:** COMPLETE

## Completed
- repository-wide `AGENTS.md`
- revised project specification
- revised architecture
- research register
- architecture decisions
- hackathon execution model
- explicit current-task/checkpoint/handoff state
- durable task queue
- T002/T003/T004/T005/T006 task definitions
- minimal harness specification
- README updated to reflect repository-first workflow and revised product thesis

## Acceptance criteria
- [x] Agents have a single documented contract.
- [x] Current task and continuation state are explicit.
- [x] Project thesis no longer presents `dupe` as merely another duplicate manager.
- [x] Next work can be assigned atomically from `agent/tasks/`.
- [x] The repository explains how Antigravity, OpenCode, Claude/OmniRouter, GLM-5, and CI fit together.

## Verification
- [x] Phase 3 source implementation was not intentionally modified by this workflow change.
- [x] Durable workflow documents were added.
- [x] README updated.
- [ ] Full remote CI status review remains part of T002.

## Next task
T002 — Complete Phase 4 correctness and regression gates.
