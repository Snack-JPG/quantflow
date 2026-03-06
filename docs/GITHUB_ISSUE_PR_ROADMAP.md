# QuantFlow GitHub Issue and PR Roadmap

This document turns the remediation audit into an execution-ready GitHub plan for a high-quality open source portfolio release.

## 1) Repository Setup (One-Time)

Create these labels:

- `type:bug`
- `type:feature`
- `type:refactor`
- `type:docs`
- `type:infra`
- `priority:P0`
- `priority:P1`
- `priority:P2`
- `area:backend`
- `area:frontend`
- `area:ci`
- `area:docs`
- `area:docker`
- `status:blocked`
- `good first issue`

Create these milestones:

- `M1 - Build and Runtime Stabilization`
- `M2 - Architecture and Test Realignment`
- `M3 - Frontend Contract and Feature Wiring`
- `M4 - OSS Polish and v1.0.0`

Create a GitHub project board with columns:

- `Backlog`
- `Ready`
- `In Progress`
- `Review`
- `Done`

## 2) Issue Backlog (Create in Order)

Each issue below includes dependencies and acceptance criteria so it can be worked independently and reviewed clearly.

### QF-001 - Fix Next.js production build rewrite configuration
- Type: `type:bug`
- Priority: `priority:P0`
- Area: `area:frontend`
- Milestone: `M1 - Build and Runtime Stabilization`
- Depends on: none
- Scope:
  - Replace invalid websocket rewrite config in `frontend/next.config.mjs`.
  - Ensure `npm run build` completes successfully.
- Acceptance criteria:
  - `npm run build` exits 0.
  - No Next.js rewrite validation error remains.

### QF-002 - Correct backend healthcheck endpoint paths
- Type: `type:bug`
- Priority: `priority:P0`
- Area: `area:docker`
- Milestone: `M1 - Build and Runtime Stabilization`
- Depends on: none
- Scope:
  - Update backend Docker and compose health checks to target `/api/health`.
- Acceptance criteria:
  - Docker health checks report healthy for backend service.

### QF-003 - Remove invalid connector entrypoints in docker-compose
- Type: `type:bug`
- Priority: `priority:P0`
- Area: `area:docker`
- Milestone: `M1 - Build and Runtime Stabilization`
- Depends on: none
- Scope:
  - Replace or remove commands referencing non-existent `app.connectors.*_connector` modules.
  - Align service commands with implemented connector package.
- Acceptance criteria:
  - `docker-compose up` does not fail due missing connector modules.

### QF-004 - Add missing frontend scripts used by CI (`type-check`, `test`)
- Type: `type:infra`
- Priority: `priority:P0`
- Area: `area:ci`
- Milestone: `M1 - Build and Runtime Stabilization`
- Depends on: none
- Scope:
  - Add scripts in `frontend/package.json` or update CI to valid commands.
- Acceptance criteria:
  - CI commands for type-check and test resolve to valid scripts.

### QF-005 - Make CI quality gates blocking and accurate
- Type: `type:infra`
- Priority: `priority:P0`
- Area: `area:ci`
- Milestone: `M1 - Build and Runtime Stabilization`
- Depends on: QF-004
- Scope:
  - Remove `continue-on-error` for mandatory quality checks.
  - Ensure workflows only run real scripts.
- Acceptance criteria:
  - CI fails on lint/type/test/build failures.
  - No false green due non-blocking core gates.

### QF-006 - Resolve strategy package import collision (`base.py` vs `base/`)
- Type: `type:refactor`
- Priority: `priority:P0`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: none
- Scope:
  - Consolidate strategy base package structure.
  - Ensure `import app.strategy` works consistently.
- Acceptance criteria:
  - `python -c "import app.strategy"` exits 0.
  - No duplicate/conflicting Strategy base definitions.

### QF-007 - Repair detection package exports
- Type: `type:bug`
- Priority: `priority:P0`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: none
- Scope:
  - Update `app.detection.__init__` exports to match implemented detectors/models.
- Acceptance criteria:
  - `from app.detection import ...` used by tests resolves successfully.

### QF-008 - Fix detector trade timestamp model mismatch
- Type: `type:bug`
- Priority: `priority:P1`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: none
- Scope:
  - Replace invalid `trade.timestamp` usage with `timestamp_us` conversion in affected detectors.
  - Validate no detector throws `AttributeError` for valid `Trade`.
- Acceptance criteria:
  - Detection engine runs with sample trades without runtime detector exceptions.

### QF-009 - Rewrite stale backend unit tests to match current modules
- Type: `type:refactor`
- Priority: `priority:P0`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: QF-006, QF-007
- Scope:
  - Replace imports referencing removed `app.services` and `app.models.order_book`.
  - Align tests to `app.analytics`, `app.core`, `app.detection`, `app.strategy`.
- Acceptance criteria:
  - `pytest tests/ -q` collects and runs without import errors.

### QF-010 - Rebuild integration tests around implemented connectors
- Type: `type:refactor`
- Priority: `priority:P1`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: QF-009
- Scope:
  - Replace outdated connector module references with current connector classes.
  - Keep tests deterministic using mocks.
- Acceptance criteria:
  - Integration tests pass in CI without external exchange dependency.

### QF-011 - Add pytest markers/config for benchmark suite
- Type: `type:infra`
- Priority: `priority:P2`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: none
- Scope:
  - Register benchmark marker and separate optional benchmark execution.
- Acceptance criteria:
  - No `PytestUnknownMarkWarning` for benchmark marker.

### QF-012 - Enforce backend typing/linting baseline
- Type: `type:infra`
- Priority: `priority:P1`
- Area: `area:backend`
- Milestone: `M2 - Architecture and Test Realignment`
- Depends on: QF-009
- Scope:
  - Make `ruff` and `mypy` part of CI pass criteria (with realistic strictness).
- Acceptance criteria:
  - Lint and type checks pass in CI for backend app code.

### QF-013 - Fix frontend TypeScript compile errors across app
- Type: `type:bug`
- Priority: `priority:P0`
- Area: `area:frontend`
- Milestone: `M3 - Frontend Contract and Feature Wiring`
- Depends on: QF-001
- Scope:
  - Resolve TS errors in `live-trading`, `research`, chart components, websocket hook, and strategy builder.
- Acceptance criteria:
  - `npx tsc --noEmit` exits 0.

### QF-014 - Align websocket message contracts between backend and frontend
- Type: `type:feature`
- Priority: `priority:P1`
- Area: `area:frontend`
- Milestone: `M3 - Frontend Contract and Feature Wiring`
- Depends on: QF-013
- Scope:
  - Ensure frontend message union includes backend-emitted types (including analytics/alerts).
  - Remove unsafe `any` for core message payloads.
- Acceptance criteria:
  - WS events parse with strict typing and no runtime handler mismatch.

### QF-015 - Wire Live Trading page to real backend streams
- Type: `type:feature`
- Priority: `priority:P1`
- Area: `area:frontend`
- Milestone: `M3 - Frontend Contract and Feature Wiring`
- Depends on: QF-014
- Scope:
  - Replace mock data loops with real API/WS-backed data.
  - Keep graceful fallback/empty states.
- Acceptance criteria:
  - Live page renders live orderbook/trades/stats from backend.

### QF-016 - Wire Strategy Builder to real backtest API
- Type: `type:feature`
- Priority: `priority:P1`
- Area: `area:frontend`
- Milestone: `M3 - Frontend Contract and Feature Wiring`
- Depends on: QF-013
- Scope:
  - Replace synthetic backtest generation with backend-driven run/result flow.
- Acceptance criteria:
  - User can trigger a real backtest and view returned metrics/trades/equity curve.

### QF-017 - Implement research query path or mark as scoped demo
- Type: `type:feature`
- Priority: `priority:P2`
- Area: `area:frontend`
- Milestone: `M3 - Frontend Contract and Feature Wiring`
- Depends on: none
- Scope:
  - Either implement backend query endpoint integration, or explicitly label this page as demo/prototype.
- Acceptance criteria:
  - Behavior and labeling are truthful; no ambiguous fake-as-real UI.

### QF-018 - Reconcile API docs with actual endpoints
- Type: `type:docs`
- Priority: `priority:P0`
- Area: `area:docs`
- Milestone: `M4 - OSS Polish and v1.0.0`
- Depends on: QF-015, QF-016, QF-017
- Scope:
  - Update `docs/API.md` and README endpoint references to implemented routes only.
- Acceptance criteria:
  - Every documented endpoint is tested and exists in app.

### QF-019 - Add open source project governance files
- Type: `type:docs`
- Priority: `priority:P1`
- Area: `area:docs`
- Milestone: `M4 - OSS Polish and v1.0.0`
- Depends on: none
- Scope:
  - Add `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and issue/PR templates.
- Acceptance criteria:
  - New contributors can follow setup + contribution path without ad-hoc guidance.

### QF-020 - v1.0.0 release hardening and launch checklist
- Type: `type:infra`
- Priority: `priority:P1`
- Area: `area:ci`
- Milestone: `M4 - OSS Polish and v1.0.0`
- Depends on: QF-005, QF-009, QF-013, QF-018, QF-019
- Scope:
  - Final release checklist, changelog, tag, and smoke tests.
- Acceptance criteria:
  - All core CI gates green on clean clone.
  - Release notes and version tag published.

## 3) PR Roadmap (Recommended Sequence)

Use one PR per issue for auditability unless explicitly grouped below.

1. PR-01: QF-001 + QF-004
2. PR-02: QF-002 + QF-003
3. PR-03: QF-005
4. PR-04: QF-006 + QF-007
5. PR-05: QF-008
6. PR-06: QF-009 + QF-010 + QF-011
7. PR-07: QF-012
8. PR-08: QF-013 + QF-014
9. PR-09: QF-015
10. PR-10: QF-016
11. PR-11: QF-017
12. PR-12: QF-018 + QF-019
13. PR-13: QF-020

Branch naming convention:

- `codex/qf-001-next-build-rewrite-fix`
- `codex/qf-002-healthcheck-path-fix`
- etc.

PR template checklist (add to every PR description):

- [ ] Issue linked (`Closes #...`)
- [ ] Acceptance criteria validated
- [ ] Tests added/updated
- [ ] Docs updated (if behavior changed)
- [ ] Screenshots/log output attached (if UI/runtime change)

## 4) Milestone Exit Gates

### M1 Exit Gate
- Backend/frontend build commands pass.
- Docker services start without hard failures.
- CI runs valid scripts only.

### M2 Exit Gate
- Backend tests collect and run cleanly.
- No stale module paths in tests/code.
- Detection engine runs without timestamp-model runtime errors.

### M3 Exit Gate
- Frontend typecheck passes.
- Live Trading and Strategy Builder use real backend paths.
- Data contracts are typed and stable.

### M4 Exit Gate
- Docs are truthful and complete.
- OSS governance files exist.
- v1.0.0 release checklist complete and tag ready.

## 5) Optional `gh` CLI Bootstrapping

If you want to create issues quickly from this roadmap:

1. Create labels and milestones first in GitHub UI.
2. Create each issue with:

```bash
gh issue create --title "QF-001: Fix Next.js production build rewrite configuration" --body-file /path/to/body.md --label "type:bug,priority:P0,area:frontend" --milestone "M1 - Build and Runtime Stabilization"
```

Repeat for each QF issue using this document as the source of truth.
