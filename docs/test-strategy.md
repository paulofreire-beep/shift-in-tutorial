# snip — test strategy (v1)

Status: **target**. No tests exist yet; this is the shape we will be held to, not a description of
the repo. Inputs: `docs/business-context.md`, `docs/quality-characteristics.md`, `docs/slis.md`.

## Risk and priorities

Quality priorities, highest first: functional correctness, performance efficiency, reliability,
security, maintainability. Two facts shape where tests go:

- **Follow (`GET /{code}`) is the hot path** and carries SLIs 1–3. Test and gate effort is weighted
  there.
- **Create (`POST /api/links`) is where validation and security risk live** (SLI 4). Stats accuracy
  (SLI 5) depends on the follow path incrementing reliably, so it is tested through follow.

## Target test pyramid

| Level | Weight (share of test effort) | Scope | Tooling (to be added to `pyproject.toml`) |
|-------|------------------------------|-------|-------------------------------------------|
| Unit | ~60% | Pure logic in isolation: code generation (`shortener.py`), storage behaviour (`store.py`), URL validation rules, click counting. Fast, no HTTP. | pytest, pytest-cov |
| Integration / API | ~30% | Routes through FastAPI's in-process test client with the real store: status codes, response bodies, redirect `Location`, 404s, rejected inputs. | pytest |
| System / end to end | ~10% | A running server, driven over HTTP as a user would: create → follow → stats. Weighted toward the redirect path (SLIs 1–3). | robotframework, plus a latency gate in CI |

Weights are a starting allocation, not a quota. Rebalance when a level stops catching defects the
others miss, and record the reason here. Rules of thumb:

- Push a check down to the lowest level that can prove it. A correctness rule that a unit test can
  prove does not need a system test as well.
- A system test earns its place by proving something lower levels cannot: wiring, the real HTTP
  contract, latency on a running server.
- Per the DoD, any observable behaviour change has at least one higher-level test.

## SLI to test-level map

| # | SLI (target) | Proven at | How |
|---|--------------|-----------|-----|
| 1 | Redirect latency, p95 < 50 ms | System, as a **CI gate** | Run the server, issue repeated `GET /{code}` calls, compute p95, fail the build above 50 ms. Not provable at unit level: it needs the real request path. |
| 2 | Redirect availability, ≥ 99.9% valid redirect or correct 404 | Integration, with a system smoke | Integration tests cover that every follow returns either a redirect or a 404 for an unknown code, never a 5xx. The 99.9% rate is an operational measure; in test we prove no input class produces an error response. |
| 3 | Resolve correctness, 100% exact stored URL | Unit + integration | Unit: stored URL is returned unchanged for varied inputs (query strings, fragments, unicode, trailing slashes). Integration: create then follow, and the `Location` header equals the submitted URL exactly. Also in the system journey. |
| 4 | Create validation, 100% invalid/unsafe rejected | Unit + integration | Unit: validation rules table-driven over invalid, malformed and unsafe inputs (script schemes such as `javascript:`, missing scheme, empty). Integration: each is rejected with a 4xx and **nothing is stored**. |
| 5 | Stats accuracy, 100% clicks equal follows | Integration | Create, follow N times, assert stats show exactly N. Include: unknown code does not create a count, stats reads do not increment, repeated and concurrent-looking follows are each counted once. |

SLIs with a CI gate (1 now, 3 as a close second) are enforced by the pipeline, not by convention. A
change that affects an SLI updates its gate in the same PR (DoD).

## Are the tests any good? Break the code on purpose

Line coverage shows what ran, not what was checked. Before trusting a test, prove it can fail.

**Hand mutation (the oracle check):**

1. Pick a behaviour a test claims to cover, such as "redirect goes to the exact stored URL".
2. Make a small deliberate fault in the source: return a different or truncated URL, flip a
   validation condition, skip the click increment, increment twice, return 200 instead of a
   redirect for an unknown code.
3. Run the suite. **A test must fail.** If everything stays green, the test does not assert the
   behaviour: strengthen it, then repeat.
4. Revert the fault. Never commit a mutation.

Priorities for mutation, in order: redirect resolution (SLI 3), validation rules (SLI 4), click
counting (SLI 5), then the rest. Record each mutation tried and the test that caught it in the PR
description, including any that survived and how the test was fixed.

**Review check for agent-written tests:** an agent can produce tests that pass and assert nothing
(no assertion, assertion on a constant, or a mock that returns the expected value). Every
agent-written test gets at least one hand mutation before it is accepted.

**Coverage** (pytest-cov) is a smoke signal for untested code, not a quality target. Low coverage
on the redirect path is a finding; high coverage is not evidence of good tests.

## Not in v1

- Load and soak testing beyond the p95 gate.
- Cross-browser or UI testing (snip is an API).
- Automated mutation tooling; hand mutation is the method for now.

## Revisit when

A new SLI is added, the p95 target changes, link expiry lands (it touches the redirect path, so
SLIs 1–3 are part of its acceptance criteria), or a defect escapes that the pyramid should have
caught.
