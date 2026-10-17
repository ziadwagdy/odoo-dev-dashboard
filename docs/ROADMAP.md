# Roadmap: secure, usable multi-project Odoo dev platform

Source material: `~/odoo-hosting-research/reports/Odoo hosting security and usability.md`
(Odoo.sh and comparable platforms) and the 2026-09/10 incident work (`CHANGELOG.md` 1.7.7 – 1.7.14).

## 1. Principles

1. **Tests first (red → green → refactor).** For every behaviour change the first commit-worthy
   artifact is a failing test that states the rule. Characterization tests are written for
   security-critical code that already exists *before* it is touched.
2. **One phase = one shippable increment.** A phase ends only when its exit criteria
   (tests + live validation) are green. No phase starts on top of a red one.
3. **Every change is reversible.** Each phase lists its rollback. Infrastructure steps ship as
   idempotent scripts with a dry run and automatic rollback.
4. **Secure by default, least privilege, no shared secrets, everything audited.**
5. **Small blast radius.** Pilot on one stack, then roll out; never change all 13 at once.
6. **Evidence-grade claims.** A control is "done" only when a test or a live probe shows it.

## 2. Test strategy

| Layer | What | Where | Runs |
|---|---|---|---|
| Unit | Pure logic: setting validation, token signing, name validation, masking, password policy, lockout counters | `backend/tests/unit` | every commit, no Docker, < 10 s |
| Integration (API) | DRF endpoints with Django test DB: authN/authZ matrix, change-request workflow, audit entries. Docker, Postgres and the filesystem are **faked at the boundary** | `backend/tests/api` | every commit, < 60 s |
| Contract (Odoo addon) | `dashboard_login` against real Odoo 17/18/19 containers with a scratch database | `scripts/test-addon.sh` | before addon changes and each release |
| Frontend unit | Auth store, stream-auth wrapper, settings diff logic | `frontend/src/**/*.test.ts` (vitest) | every commit |
| UI (headless Chrome) | Real browser against the live dashboard in dark and light theme: layout, stacking, themed surfaces, role visibility, no leaked internals, flows | `frontend/e2e` | `scripts/test-ui.sh`, before each UI release |
| Smoke (live, read-only) | Health, unauthenticated 401s, nginx blocks, DB listing, process args, shared-password-dead | `scripts/smoke.sh` | after every deploy |

Rules: tests never touch real containers except the contract/smoke layers; a bug found in
production gets a regression test before the fix; coverage is tracked for `services/` and
`apps/*/views.py` (target ≥ 80% lines on security-relevant modules, not a global number).

Tooling: `pytest` + `pytest-django`, `pytest-mock`, `freezegun` (session expiry); test image is a
Docker build target (`--target test`) so the production image stays `--no-dev`;
`scripts/test-backend.sh` is the single entry point.

## 3. Phases

### Phase 0: Test harness and characterization (foundation)
*Why first:* nothing is testable today.
- Test image target, `core/test_settings.py` (in-memory channel layer, temp data dir),
  `scripts/test-backend.sh`, `scripts/smoke.sh`.
- Characterization tests for existing security code: `stream_auth`, `core.authentication`
  (absolute + idle expiry), login lockout, password policy, `settings_schema.validate/write_values`,
  `config_service` masking, `sso.make_token`, db-name validation, webhook fail-closed.
- **Exit:** `scripts/test-backend.sh` green; smoke script green against the live dashboard;
  suite < 60 s.  **Rollback:** none needed (no runtime change).

### Phase 1: Access control and accountability (dashboard code)
- *Requester ≠ approver* on config change requests (a lone admin may approve only with an
  explicit, audited "self-approval" override); four-eyes by default.
- *Role-gate "Open as"*: who may sign in as whom (developers → non-admin users of
  neutralized databases only; managers/admins → any); never to an un-neutralized DB without admin.
- *Audit enrichment*: reason (required for admin sign-ins), target user, source IP, link expiry,
  outcome; read-only audit view with filters and export.
- **Exit:** tests for the full role × action matrix green; smoke green; one manual walkthrough
  per role. **Rollback:** revert the release; no data migration besides additive audit fields.

### Phase 2: Database lifecycle safety
- *Neutralization is verified, not assumed:* check `database.is_neutralized` after
  restore/duplicate, expose the state per database (badge), block "Open as" until neutralized
  unless an admin overrides with a reason.
- *Tighten new/restored databases:* `REVOKE CONNECT … FROM PUBLIC`, owner = the project role.
- *Pre-update snapshot* before module updates and config applies that restart a stack.
- *Scheduled restore test:* restore the latest backup to a scratch database, run smoke queries,
  drop it, alert on failure.
- **Exit:** tests with fake DB layer + one live restore-test on a small stack.
  **Rollback:** feature flags per behaviour; scratch DBs are always cleaned up in `finally`.

### Phase 3: Platform hardening (infrastructure, scripts with dry-run and rollback)
- nginx: cookie `Secure/SameSite`, `proxy_cookie_flags`, security headers, verify `proxy_mode`.
- Login-abuse detection: CrowdSec or fail2ban jail for Odoo login failures; alerts into the
  existing watch jobs.
- `docker-socket-proxy` in front of the Docker API for the dashboard and Dozzle; per-stack
  memory / CPU / pids limits; drop unneeded capabilities where Odoo tolerates it.
- Split Alif off `odoo17-db`.
- Cloudflare Access in front of the dashboard and operational endpoints (**user decision**).
- **Exit:** `scripts/smoke.sh` extended with each new control; every stack healthy.
  **Rollback:** each script keeps a timestamped backup and a one-command undo.

### Phase 4: Observability and audit
- Detection rules as code (the current "watch" prompts become scripts + tests), log shipping
  off-box (object-lock bucket), audit-log export and retention policy.
- Per-stack resource dashboard (worker memory vs limits) feeding the settings validator.
- **Exit:** alert drill (inject a fake `COPY … PROGRAM` line, expect a notification).

### Phase 5: Developer experience (Odoo.sh parity)
- Per-branch ephemeral databases with TTL, "update modules" with automatic revert,
  build/update status, one-click staging from a backup, shell/SQL console with auditing.
- **Exit:** user-facing acceptance checklist signed off by the team.

## 4. Definition of done (every phase)
1. New behaviour has tests written first; suite green locally and in the test image.
2. `CHANGELOG.md` entry and version bump; commit message states the *why*.
3. Deployed through the normal build; `scripts/smoke.sh` green on the live host.
4. Rollback verified (or explicitly "revert commit").
4b. **UI work respects the existing design system and is tested in a real browser:** new UI uses the
   theme tokens/classes (`bg-surface`, `border-border`, the light-theme overrides in `style.css`), never
   introduces colours that only work in one theme, and gets a headless-Chrome test
   (`scripts/test-ui.sh`, Playwright) that runs in **both** the dark and light theme, checks the
   behaviour it adds, and leaves screenshots in `~/ui-test-artifacts/` that are looked at.
5. Evidence recorded: what was tested, what was observed.

## 5. Open decisions (need the owner)
- Cloudflare Access: which identities/emails may reach the dashboard?
- Which databases count as "production-like" (never openable by developers without approval)?
- Off-host backup target (bucket/provider) and retention.
