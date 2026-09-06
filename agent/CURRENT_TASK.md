# Current Task

**Task:** T001 — Make the repository agent-ready
**Status:** IN PROGRESS

## Goal
Establish a persistent, agent-independent workflow so Antigravity, OpenCode, Claude Code, and GLM-5 can continue work from repository state without requiring the full ChatGPT conversation.

## Completed in this task
- repository-wide `AGENTS.md`
- revised project specification
- revised architecture
- research register
- architecture decisions
- hackathon execution model
- checkpoint/handoff/task-state files

## Remaining
- add task queue
- add minimal harness command specifications
- update README to point agents at durable context and revised product thesis
- verify repository files and Git history after changes

## Constraints
- Do not modify the Phase 3 implementation merely for the workflow change.
- Keep J2 0.1.0 as the pinned target unless explicitly changed.
- Do not add generic autonomous-agent infrastructure.

## Acceptance criteria
- Agents have a single documented contract.
- Current task and continuation state are explicit.
- Project thesis no longer presents `dupe` as merely another duplicate manager.
- Next work can be assigned atomically from `agent/tasks/`.
- The repository explains how Antigravity, OpenCode, Claude/OmniRouter, GLM-5, and CI fit together.

## Verification
- Review modified/new files.
- Inspect recent Git commits.
- Confirm no source files were unintentionally changed.
