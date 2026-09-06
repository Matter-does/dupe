# J2 Hackathon Agent Contract

## Purpose
This repository is the durable source of truth for the J2 hackathon project. Chat sessions are planning/research surfaces, not the project's persistent execution state.

## Read before coding
1. `AGENTS.md`
2. `docs/PROJECT.md`
3. `docs/J2_REFERENCE.md` when present, otherwise `docs/J2-API-0.1.0.md`
4. `agent/CURRENT_TASK.md`
5. `agent/CHECKPOINT.md`
6. `agent/HANDOFF.md`

Then inspect:
- `git status`
- `git log --oneline -10`
- the relevant source, test, and workflow files

## J2 rules
- Target J2 0.1.0 unless the project explicitly changes the pinned version.
- Never invent J2 syntax, standard-library APIs, compiler behavior, or capability behavior.
- Verify uncertain J2 behavior with a minimal executable probe.
- Prefer J2-native implementation for application logic.
- Do not silently replace J2 with Python, JavaScript, Rust, or another language.
- Python is permitted for independent test or oracle infrastructure when the task explicitly requires an external oracle.

## Product direction
`dupe` is being developed as a J2-native filesystem intelligence engine. Exact duplicate detection is the first validated workload, not the entire product thesis.

Do not expand into a feature-for-feature clone of established desktop duplicate managers. Do not add deletion, trash, media-specific fuzzy matching, elaborate result management, or other large feature areas unless an explicit task requires them.

## Engineering rules
- Preserve working code unless a concrete defect or accepted design change requires modification.
- Keep dependencies minimal.
- Keep output deterministic where practical.
- Treat filesystem input as read-only unless a task explicitly specifies a destructive operation and its safety contract.
- Keep benchmark results reproducible.

## Verification
Never claim a task is complete without running the relevant verification.

When applicable, completion includes:
- formatter passes
- relevant tests pass
- J2 interpreter execution passes
- J2 native build/execution passes
- interpreter/native equivalence is checked
- `git diff` is reviewed
- `agent/CHECKPOINT.md` is updated
- `agent/HANDOFF.md` is updated

## Task discipline
- Work only on the current task unless a blocking defect requires adjacent changes.
- Do not redo completed work recorded in `agent/CHECKPOINT.md`.
- Update the checkpoint when a meaningful atomic step completes.
- Record failed approaches and important discoveries in the handoff.
- A task is complete only when its acceptance criteria are evidenced.

## Git discipline
- Prefer one coherent commit per completed atomic task or reviewable change.
- Do not rewrite unrelated history.
- Do not commit generated benchmark output unless the task says to retain it.
- Use isolated worktrees when multiple agents need concurrent changes.

## Agent roles
- Antigravity: primary implementation agent.
- OpenCode: persistent terminal execution and continuation/fallback.
- Claude Code through OmniRouter: adversarial architecture, J2 semantics, correctness, and benchmark review.
- GLM-5: independent implementation/review and second opinion.
- ChatGPT: research, architecture, specification, task decomposition, and evidence synthesis.

## Continuation protocol
When resuming work, start from repository state, not conversation memory:
1. Read the required files above.
2. Inspect `git status`, recent commits, and the current diff.
3. Read `CURRENT_TASK`, `CHECKPOINT`, and `HANDOFF`.
4. Resume the first unfinished atomic action.
5. Verify before declaring completion.
6. Update checkpoint and handoff before finishing.
