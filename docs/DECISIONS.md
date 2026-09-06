# Architecture Decisions

## ADR-001 — Repository is the durable context layer
**Decision:** Agents must recover project state from repository artifacts and Git history rather than chat transcripts.

**Reason:** Chat sessions are not a reliable long-running execution substrate. Repository state is persistent, reviewable, and agent-independent.

## ADR-002 — ChatGPT is planning/research, not the primary executor
**Decision:** Use ChatGPT for research, architecture, specification, task decomposition, and evidence synthesis. Use coding agents for repository execution.

**Reason:** This separates reasoning from durable implementation and allows work to continue through different agents.

## ADR-003 — Antigravity is the primary builder
**Decision:** Antigravity receives normal implementation tasks first.

**Reason:** Keep one lead implementation path while preserving OpenCode as continuation/fallback and Claude/GLM as independent reviewers.

## ADR-004 — Tasks are atomic and resumable
**Decision:** Every substantial change gets a task ID with explicit requirements, verification, and definition of done.

**Reason:** Agents should resume the first unfinished atomic action instead of reconstructing project intent.

## ADR-005 — J2 automatic parallelism is the technical thesis
**Decision:** Do not force concurrency with explicit thread APIs. Structure independent work so J2 can potentially parallelize it, then measure the result.

**Reason:** The hackathon value is evidence about J2's execution model, not merely another manually parallel duplicate finder.

## ADR-006 — Exact duplicate detection is the baseline workload
**Decision:** Keep the Phase 3 exact duplicate scanner as the correctness/reference workload.

**Reason:** It is useful, deterministic, independently testable, and provides a concrete workload for the J2 experiment.

## ADR-007 — Do not clone mature duplicate-manager features
**Decision:** No feature-for-feature recreation of dupeGuru/Czkawka-style cleanup workflows without an explicit accepted task.

**Reason:** Feature accumulation would obscure the J2 research contribution and greatly expand scope.

## ADR-008 — Evidence before claims
**Decision:** J2 behavior and performance claims require executable probes, tests, CI evidence, authoritative documentation, or reproducible benchmarks.

**Reason:** New-language projects are especially vulnerable to assumptions about syntax, APIs, compiler behavior, and automatic parallelism.
