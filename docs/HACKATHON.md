# Hackathon Execution Model

## Roles

| System | Role | Primary responsibility |
|---|---|---|
| ChatGPT | Research / architecture | research, specifications, task decomposition, evidence synthesis |
| Antigravity | Primary builder | implementation and local verification |
| OpenCode | Continuation / fallback | persistent terminal execution and recovery |
| Claude Code via OmniRouter | Adversarial reviewer | architecture, J2 semantics, correctness, benchmark review |
| GLM-5 | Independent reviewer | second opinion, tests, alternative implementation/review |
| GitHub Actions | Verification authority | reproducible CI, J2 interpreter/native checks, later benchmarks |

## Operating loop

```text
research/specification
        ↓
bounded task
        ↓
agent implementation
        ↓
local verification
        ↓
commit
        ↓
CI verification
        ↓
independent review
        ↓
checkpoint + handoff
        ↓
next task
```

## Continuation rule
An agent that starts or resumes work must not depend on the prior ChatGPT transcript. It must read repository state and the current task state first.

## Minimum continuation prompt

```text
Read AGENTS.md, docs/PROJECT.md, the J2 reference, agent/CURRENT_TASK.md,
agent/CHECKPOINT.md, and agent/HANDOFF.md.
Inspect git status, git diff, and recent commits.
Resume the first unfinished atomic action.
Do not redo completed work.
Verify before declaring completion.
Update checkpoint and handoff before finishing.
```

## Parallel-agent rule
Do not have multiple agents modify the same working tree concurrently. Use separate Git worktrees or branches for independent work. Reviewers should default to read-only until a concrete fix is requested.

## Harness scope
The project only needs enough harness infrastructure to make J2 application development resumable and verifiable. Do not turn the hackathon into a generic autonomous-agent platform.

## Definition of done
A task is done when implementation, relevant tests, J2 execution/build checks, required review, Git state, checkpoint, and handoff all satisfy the task's acceptance criteria.
