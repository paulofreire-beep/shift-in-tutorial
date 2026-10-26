# CLAUDE.md

**snip** is an internal URL shortener: teams turn long links into short codes and count how often
each is followed. Source of truth for the context below: `docs/business-context.md`,
`docs/quality-characteristics.md`, `docs/slis.md`. If this file and those docs disagree, the docs win
— fix this file.

## Who snip serves (priority order)

1. **Recipients following short links** — the highest-volume path by far. Protect it first.
2. **Employees creating links** — lower volume; this is where input-validation and security risk live.
3. **Link owners checking click stats** — depends on the follow path counting reliably.

When two changes compete, favour the follow/redirect path (`GET /{code}`) over create, list, and stats.

## Quality bar (highest priority first)

1. **Functional correctness** — a code always resolves to the exact URL it was created for; click
   counts are accurate.
2. **Performance efficiency** — redirect is the hot path and must be fast.
3. **Reliability / availability** — redirect must stay up; create may degrade briefly.
4. **Security** — accept only safe, well-formed URLs; no open-redirect or script-scheme abuse.
5. **Maintainability** — `src/snip/` stays small enough that an agent or a human can hold all of it
   in their head; the tests, not familiarity, are what make changes to it safe.

Correctness outranks speed: never trade a wrong or lost redirect/click for latency.

## SLIs (targets, not a description of current code)

| # | SLI | Definition | Target |
|---|-----|------------|--------|
| 1 | Redirect latency | p95 server time for `GET /{code}` | < 50 ms |
| 2 | Redirect availability | `GET /{code}` returns a valid redirect or a correct 404 | ≥ 99.9% |
| 3 | Resolve correctness | follows that redirect to the exact stored URL | 100% |
| 4 | Create validation | invalid/unsafe URLs on create that are correctly rejected | 100% |
| 5 | Stats accuracy | recorded clicks equal actual follows | 100% |

SLIs 1–3 are the redirect hot path: weight test and review effort there. SLI 4 is the create-path
security gate. SLI 5 depends on the follow path incrementing reliably.

`start` does not meet every SLI yet, and no tests exist to say which. Do not assume the current
redirect, validation or click-counting code meets the table; check it against the targets above.

## Working agreements

- **Definition of Ready:** the story names its actor (recipient, link creator or link owner) and
  outcome; acceptance criteria are testable and agreed by the Three Amigos; which of SLIs 1–5 it
  affects is understood. If a request lacks these, ask before building.
- **Definition of Done:** reviewed and merged via PR; tests at the right level (see
  `docs/test-strategy.md`) pass in CI; any change that moves an SLI updates its pipeline gate; any
  observable change to a route's response is covered by at least one higher-level test.
- **State SLI impact** in every change summary and PR description: which SLIs (1–5) the change
  touches, and whether it moves any toward or away from target.
- Changes to follow/redirect, URL validation, or click counting need a test that would fail
  without the change.
- Do not relax an SLO target (e.g. the 50 ms p95) or loosen a redirect, validation or click-count
  assertion to make a change pass; raise it instead.

## Stack and conventions

- FastAPI app, Python 3.11+, source in `src/snip/` (`main.py` routes, `models.py`, `shortener.py`
  code generation, `store.py` storage). Routes: `POST /api/links`, `GET /api/links`,
  `GET /api/links/{code}/stats`, `GET /{code}`.
- Run: `pip install -e .`, then `uvicorn snip.main:app --reload --app-dir src`.
- Test tooling (pytest, pytest-cov, robotframework) is deliberately not in `pyproject.toml` yet;
  adding it is part of the workshop. The target pyramid and SLI-to-level map are in
  `docs/test-strategy.md`.
- Planned feature: link expiry (owners want links to stop working after a chosen time). It touches
  the redirect hot path, so its acceptance criteria must cover SLIs 1–3.
