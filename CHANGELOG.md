# Changelog

All notable changes to the Odoo Dev Dashboard are documented here.
Format: [version] — date

---

## [1.10.3] — 2026-10-17

### Security / Changed — the dashboard shows what people use, not how the server is wired
- **Removed from the UI and the API:** Odoo port, DB port, host folder, config-file path, addons paths (container filesystem paths) and the *Addons Paths* card. The overview now shows Odoo version, branch, updates to pull and address. Onboarding no longer displays assigned ports.
- **`/api/config` is no longer public with internal links:** anonymous users and non-admins only get the dashboard title; the log-viewer/files/terminal URLs go to admins. The container ID (for the log-viewer link) is admin-only.
- **Server-wide numbers are for managers and admins:** the host health stream, the Health page and the host disk figures in `/api/storage`.
- The Branches tab learns whether a project uses hr-base from a `uses_hr_base` flag instead of a host path.
- Fix: Modules tab *Update All* test and UI test harness (headless Chrome, both themes) added: `scripts/test-ui.sh`.

---

## [1.10.2] — 2026-10-17

### Fixed
- **Open as… showed "This project has no databases yet" on every project** (regression from 1.8.0): the picker read the database list as a bare array, but the API returns `{ databases: [...] }`. Parsing now lives in `utils/databases.ts` with tests.
- **Deploy / Delete appeared above the tab bar** instead of inside the Manage tab; the panel now renders below the tabs. Structure tests keep every tab panel after the tab bar and Deploy/Delete inside Manage.
- **User menu dropdown rendered under the page content**: the header now has its own stacking layer (`relative z-30`).
- **Submodule "Update All" is now "Pull"** (it is a git pull; module updates keep their own *Update All*).

### Changed
- **Module update API** (`POST /api/modules/<project>/<db>/update/<modules>`): manager/admin only up front (developers used to get a stream URL that then failed with 403), database and module names validated, and every update start is audited with user, IP, database and modules. The module list rejects unsafe database names.

---

## [1.10.1] — 2026-10-17

### Fixed
- The Security page had no sidebar and no way back; it now uses the same layout and breadcrumb as every other page. A regression test (`views/layout.test.ts`) fails if any page (except login) is missing the sidebar layout or breadcrumb.

---

## [1.10.0] — 2026-10-16

Phase 4a of `docs/ROADMAP.md` (detection and alerting), built test-first. Replaces the hourly log-polling jobs.

### Added
- **Always-on detection** (`services/detection.py`, `alerting.py`, `log_watcher.py`, `security_watch.py`): the dashboard streams every project database's log in real time and applies rules derived from the 2026 incident: `COPY … PROGRAM` / external-program attempts (critical), password-authentication failures (warning, escalating to high at 5 and critical at 20 repeats), `pg_hba` rejections (high). Repeats are folded into one alert with a count; payloads and secrets are scrubbed from the evidence line; the stream reconnects when a container restarts.
- **In-dashboard alerts:** a *Security* page (admins) with acknowledge-with-note, and a live badge in the sidebar.
- **Web Push** (`services/webpush.py`): admins can enable push notifications on any browser or phone (VAPID, no third-party account). High/critical alerts and escalations are pushed; plain new warnings stay in the dashboard. Payloads never contain evidence lines. Dead subscriptions are removed automatically. Service worker at `/sw.js`.
- Optional `SECURITY_IGNORE` (comma-separated tokens) to silence known sources, `SECURITY_WATCH=off` to disable.

### Tests
- 237 backend tests including a full alert drill (log line → alert → push); live drill with a real denied `COPY … PROGRAM` and a wrong-password login produced the expected critical and warning alerts.

---

## [1.9.0] — 2026-10-15

Phase 2 of `docs/ROADMAP.md` (database lifecycle safety), built test-first.

### Added
- **Neutralization is verified, not assumed.** After `odoo neutralize` the dashboard reads `database.is_neutralized` and fails the restore/duplicate if Odoo did not record it. The Database tab shows a *neutralized* / *not neutralized* badge per database.
- **Locked-down databases:** new, restored and duplicated databases get `REVOKE CONNECT … FROM PUBLIC` (idempotent; applied once to all 19 existing databases).
- **Safety snapshot before module updates** (`services/lifecycle.py`): a dump is taken first (databases up to 500 MB, newest 3 kept per database) and the update aborts if the snapshot fails. Streams through the existing module-update SSE endpoint.
- **Restore tests:** *Test latest backup* (manager/admin) restores the newest backup into a scratch database, checks users/modules and always drops the scratch DB; a weekly scheduled run (Sunday 03:30) does this for every project. Results are audit-logged.

### Fixed
- Module update ran `odoo -c /tmp/odoo-runtime.conf`, a file that does not exist in the containers; it now runs a proper argument list against `/etc/odoo/odoo.conf` (no shell string).

### Tests
- 183 backend tests, 8 frontend tests, smoke extended (leftover scratch databases, PUBLIC connect).

---

## [1.8.0] — 2026-10-15

Phase 1 of `docs/ROADMAP.md` (access control and accountability), built test-first.

### Security
- **"Open as" is role-gated** (`services/access_policy.py`, exhaustively unit tested): developers may open ordinary users of *neutralized* databases only; managers may open ordinary users anywhere and administrators of neutralized databases; admins may open anything; any other role is refused. A reason (≥ 8 characters) is required wherever the database is not neutralized or a manager targets an administrator. The picker greys out what the caller's role may not do, says why, and shows the neutralization state.
- **Four-eyes on settings changes:** the requester cannot approve their own request. A sole admin may use an explicit *self-approve* override with a written reason, which is audited as `config_self_approve`.
- **Richer audit trail:** `AuditLog` now carries `ip` and structured `meta` (database, target user, target-is-admin, neutralized, reason, link lifetime). Denied attempts are recorded as `denied`.
- Freshly created databases are neutralized so they count as safe development copies.

### Tests
- 146 backend tests (was 109), 8 frontend tests, 76-check live smoke, addon contract test.

---

## [1.7.15] — 2026-10-15

### Added (development process, no runtime change)
- **Automated tests, written test-first from here on** (`docs/ROADMAP.md`): 109 backend tests (unit + API, ~3 s, run in a `--target test` image that has no Docker socket and no network), 8 frontend tests (vitest), a read-only live smoke test (76 checks) and a contract test for the `dashboard_login` addon against real Odoo 17/18/19 containers. Entry points: `scripts/check.sh [--live]`, `scripts/test-backend.sh`, `scripts/test-frontend.sh`, `scripts/smoke.sh`, `scripts/test-addon.sh`.
- Dockerfile is multi-stage (`base` → `test` / `runtime`); the production image is unchanged and still has no test tooling.

---

## [1.7.14] — 2026-10-15

### Changed
- **Project header:** *Open as…* (database + user picker, passwordless, audited) replaces the plain *Open* link. **Deploy** and **Delete** moved out of the header into a new admin-only **Manage** tab (Deploy, live deploy output, Danger zone). `POST /api/project/<name>/deploy` is now admin-only on the server too.

### Security
- **Per-project database passwords.** New projects get their own random password for the `odoo_app` role, stored in `~/odoo-dev/secrets/<project>.pgpass` and mounted as the container's `~/.pgpass`; `odoo.conf` has no `db_password`, the compose file has no `PASSWORD`, and the stock entrypoint (which would put `--db_password` on the command line) is bypassed with `entrypoint: ["odoo"]`. The dashboard reads the same file; the initdb SQL that carried the password is blanked after first start. `scripts/pgpass-rollout.py` migrates existing stacks with automatic rollback.

---

## [1.7.13] — 2026-10-15

### Changed (breaking for the Settings tab)
- **odoo.conf is no longer shown or edited from the dashboard.** The Settings tab now shows an Odoo.sh-style curated set (HTTP workers, cron workers, memory soft/hard limits, CPU/request time limits, requests per worker, DB connections, log level) with types, ranges and the server's resources. The raw `odoo-conf` / `env` endpoints are gone.
- **Changes are requests, not writes.** `POST /api/settings/<project>/changes` validates (type, range, cross-field rules such as soft < hard and CPU ≤ request time, memory budget against the server's RAM, worker count against vCPUs, verbose log levels) and stores a `ConfigChangeRequest`. An admin sees the exact diff and warnings, must acknowledge warnings, and applies it: the current file is backed up, only the requested keys are rewritten (comments and every other line untouched), the container restarts, a health check runs, and the previous configuration is restored automatically if the application does not come back. Drift since the request was made blocks approval. Everything is in the audit log.
- Model `ConfigChangeRequest` (migration 0009).

---

## [1.7.12] — 2026-10-15

### Added
- **"Open as…" — sign in to any Odoo database without a password.** New Odoo addon `dashboard_login` (in `~/odoo-dev/dashboard-addons`, mounted read-only at `/mnt/dashboard-addons` in every stack; one codebase for Odoo 17, 18 and 19). The dashboard issues a 60-second, one-time, HMAC-signed link for the logged-in dashboard user and a chosen Odoo user; the addon verifies it and opens a normal Odoo session (record rules and the user's MFA still apply). Replay, tampered, expired, over-long, unknown-user, wrong-database and open-redirect cases are all refused (tested on real 17/18/19 containers). The addon installs itself on first use in a database. The HMAC key is derived from the project's otherwise unused master password, so no extra secret is distributed. Endpoints: `GET /api/db/<project>/login-users/<db>`, `POST /api/db/<project>/login-link/<db>` (audited with dashboard user, database and target user). UI: **Open as…** on every database.

### Security
- Default-credential audit of every Odoo database (offline hash check): `admin/admin` on four databases and `login == password` on several demo/portal/personal accounts were reset to random values; nobody needs them any more.

---

## [1.7.11] — 2026-10-15

### Security
- **Settings tab no longer exposes secrets.** `GET /api/settings/<project>/odoo-conf` and `/env` returned `admin_passwd`, `db_password` and any `*pass*/*secret*/*token*/*key*` value in clear text to every authenticated user. Values of such keys are now returned as `********`; sending `********` back on save keeps the stored value, so editing other settings never overwrites a secret. Both reads also enforce the project ACL (admin or assigned user). UI renders secret fields as password inputs.

### Changed
- Onboarding no longer shows the Odoo master password: it is generated 32 characters long and never displayed, because databases are created and restored through the dashboard as the logged-in user.

---

## [1.7.10] — 2026-10-15

### Security
- **Sessions expire.** `core/authentication.ExpiringTokenAuthentication` enforces an absolute lifetime (`SESSION_MAX_HOURS`, default 12) measured from login and an idle timeout (`SESSION_IDLE_MINUTES`, default 120). The same validator (`user_for_token_key`) is used by DRF views, the SSE streams and the notebook WebSocket, so a revoked/expired token stops working everywhere.
- **Login hardening:** a fresh token per login (old tokens are invalidated), lockout after 5 failed attempts per username / 30 per client IP for 15 minutes (HTTP 429), and failed/blocked logins are written to the audit log with the client IP (`CF-Connecting-IP`).
- **Password policy:** minimum 12 characters, not all digits, not the username, not repetitive (create user and change password).
- **Admin can revoke a user's sessions:** `POST /api/auth/users/<id>/revoke-sessions` (audited).

### Added
- **Create database without a master password:** `POST /api/db/<project>/create` initialises a new Odoo database through the project's own container and returns an individual, random admin password once (`Cache-Control: no-store`). UI: *+ New database* on the Database tab.
- **Issue an individual admin login:** `POST /api/db/<project>/admin-password/<db>` (admin/manager, audited) sets a fresh random password for `admin` (hashed inside the project container, passed via environment, never argv) and shows it once. UI: *Admin login* per database. Replaces sharing a fixed admin password.

---

## [1.7.9] — 2026-10-15

### Security
- **All `/stream/*` SSE endpoints, `/api/onboard/stream/*` and the notebook WebSocket now require authentication.** They are plain Django/Channels views outside DRF and previously had none: anyone who could reach the dashboard could read container logs and the onboarding credential events, and trigger module updates, git pulls and branch switches by URL. New `services/stream_auth.py`: DRF token from the `Authorization` header or `?token=` query parameter, per-project ACL (`UserProjectAssignment`), role requirements (module update / branch switch / submodule / git pull need admin or manager; onboarding stream and notebook kernel are admin only), registry membership check, and name validation (`SAFE_NAME`) for every value that reaches `docker exec`.
- **Notebook WebSocket**: closes with 4401 unless the token belongs to an admin, the `Origin` host is in `ALLOWED_HOSTS` and the project exists in the registry; project names are validated before they reach `sh -c` in `kernel_manager`.
- **GitHub webhook fails closed** when `GITHUB_WEBHOOK_SECRET` is unset (it used to accept everything).
- **Database names** are validated and used as `psycopg2.sql.Identifier` in `DROP`/`CREATE DATABASE` and in `pg_dump`/`pg_restore` arguments.
- Frontend: `utils/authedStreams.ts` appends the session token to same-origin EventSource/WebSocket requests; dashboard nginx logs `/stream/` and `/ws/` by path only so tokens never reach the access log.

---

## [1.7.8] — 2026-10-15

### Security
- **Onboarding no longer creates `odoo`/`odoo` superusers.** `onboard_service.create_docker_stack` now writes a per-project random password for the Postgres bootstrap superuser (`odoo`, never used by the app) and creates the dashboard/app role (`settings.DB_USER`, `odoo_app`) as `LOGIN CREATEDB NOSUPERUSER NOCREATEROLE` through `initdb/01-app-role.sql`. Previously the generated stack used `odoo`/`odoo` while the dashboard connects as `odoo_app`, so new projects showed no databases and were exposed to the same `COPY … FROM PROGRAM` vector as the 2026-09-02 incident.
- **`verify_db_access()`** runs right after the containers start and fails the onboarding loudly if the dashboard cannot log in to the new project's Postgres.
- Operational (not code): `odoo_app` removed from the superuser `odoo` role on five stacks, superuser passwords rotated, shared `odoo_app` password rotated everywhere, connection logging enabled on the five stacks that were targeted.

### Changed
- `build_addons_path` now takes the detected module paths and adds every directory that directly holds modules, so nested layouts (e.g. a `cnc-hr-base` submodule inside a submodule, as in `omc-holding`) are mounted in the generated `addons_path`.

---

## [1.7.7] — 2026-09-02

### Changed
- **Dashboard reaches project databases over a shared `odoo-dbnet` docker network** instead of via host-published Postgres ports. `db_service._db_endpoint()` resolves a project's registry `db_port` to `(<project>-db, 5432)` and connects by container name; `_connect`, `backup_database` and `restore_database` all use it. Falls back to `settings.DB_HOST` + the given port when a project can't be resolved.
- **`nginx` now binds `127.0.0.1:${PORT}` only** (was `0.0.0.0`). Public access is unchanged — Cloudflare Tunnel → host Nginx (`dashboard.zedev.org`) → `127.0.0.1:8892` — but the dashboard (root, `docker.sock`, `~/.ssh`) is no longer reachable by direct IP from the internet.
- **`backend` joined to `odoo-dbnet`** (external) alongside `default`.

### Security
- Context: a cryptominer was planted in a project's Postgres container on 2026-09-02 via an exposed `172.17.0.1:15xxx` port + `odoo`/`odoo` superuser (`COPY … FROM PROGRAM`). Onboard template (`onboard_service.py`) now generates DB ports on `127.0.0.1` and attaches new `db-*` services to `odoo-dbnet`.

---

## [1.7.6] — 2026-08-27

### Added
- **Manual "Neutralize" button on the Database tab** — a standalone Neutralize action next to Backup/Duplicate/Drop for each database, so DBs that land on the server outside the dashboard's own Restore/Duplicate flow (manual `pg_restore`, Odoo's own `/web/database/manager`, fresh installs) can be neutralized without SSH. Backend: `db_neutralize` view in `apps/projects/views.py` calling the existing `neutralize_database()` in `db_service.py` (unchanged), new route `POST /api/db/<project>/neutralize/<dbname>`. Frontend: `neutralize()` in `DatabaseTab.vue` opens a confirm modal (no text input needed — modal now conditionally renders its input field only when `modal.placeholder` is set) then POSTs and shows a toast.

---

## [1.7.5] — 2026-07-29

### Changed
- **Branches tab — side-by-side layout for hr-base projects** — when the project's registry `folder` matches `hr-base` (e.g. `worktrees/hr-base-17`) OR it has an hr-base submodule (e.g. alif's `cnc-hr-base`), the Branches card (repo's own local/remote branches) and Submodules card now render side by side in a 2-column grid at `lg`+ instead of stacked, so you don't have to scroll past the branch list to reach Submodules. Other projects keep the original stacked layout. `BranchTab.vue`: `isHrBase` computed (checks `props.folder` + loaded `submodules`) toggles a wrapper grid around the two cards; the submodule-branch modals were moved out of that wrapper since they're fixed-position overlays.

---

## [1.7.4] — 2026-07-23

### Added
- **Automatic database neutralization** — restoring or duplicating a database via the Database tab now automatically runs Odoo's built-in `neutralize` command against it (disables outgoing mail servers, cron jobs, payment providers, etc). Backend: `neutralize_database()` in `db_service.py`, invoked from `restore_database()`/`duplicate_database()` via a new `exec_in_container_sync()` helper in `docker_service.py` (needed a real exit code, unlike the streaming `exec_in_container()`). Frontend: DatabaseTab notifications now say "Restored and neutralized" / "Duplicated and neutralized", plus a hint under Backups on Disk. `/onboard` skill documents this as a mandatory step (new Step 14) for any database created outside the dashboard.

---

## [1.7.3] — 2026-06-21

### Fixed
- **Sidebar project navigation** — clicking a project in the sidebar while already on another project's page now correctly loads the new project. Root cause: `RouterView` was reusing the `ProjectDetailView` component across same-pattern routes, preventing `onMounted` from re-running. Fixed by adding `:key="$route.fullPath"` to `RouterView` in `App.vue`.

---

## [1.7.2] — 2026-06-01

### Changed
- **Repo URL is now optional on onboard** — leaving the field blank creates an empty `/mnt/project-addons` directory and proceeds with a plain Odoo install (no custom modules). Useful for creating a clean Odoo instance to restore a database into. Frontend shows "optional" badge and updated hint text; backend no longer rejects missing `repo_url`.

---

## [1.7.1] — 2026-05-05

### Added
- **Submodule branch visibility** — the Submodules section in the Branch tab now shows which branch each submodule is on, or "detached HEAD" if not on any branch.
- **Per-submodule branch switching** — each submodule row has a "Switch Branch" button that opens a branch picker modal (local + remote, searchable) with a confirm dialog and the same restart-container prompt as the main repo switch flow. Backend: new `list_submodule_branches` and `switch_submodule_branch` in `git_service.py`; new `/api/git/<project>/submodule-branches` and `/api/git/<project>/submodule-switch` endpoints; new `/stream/submodule-switch/<key>` SSE stream.
- **Submodule list redesign** — replaced the flat table with a card-per-submodule layout showing path, commit, branch pill, and status badge together.

---

## [1.7.0] — 2026-04-28

### Added
- **User-project assignment** — admins can now restrict which projects each user can see and operate on. Non-admin users only see their assigned projects across the dashboard, SSE streams, and all per-project API endpoints. A "Projects" button on the Users & Roles page opens a checkbox modal to manage access per user.
- **New users seeded with all projects** — when a new user is created, all current projects are assigned automatically so no one loses access on first login. Admins bypass all assignment checks and always see everything.
- **`UserProjectAssignment` model + migration 0008** — stores `(user, project_name)` pairs; cascade-deletes when a user is deleted; seeded for all existing non-admin users on migration.
- **`/api/auth/users/<id>/projects` endpoint** — GET returns current assignment list; POST replaces the full list (admin-only).
- **Storage breakdown on Health page** — "Disk — Project Breakdown" section shows per-project disk usage as a stacked bar (DB / Filestore / Code). Data fetched on demand via `/api/storage`. Uses parallel `docker exec du` inside each container for filestore, `du` on code folders, and `pg_database_size()` for databases.

### Improved
- **Users & Roles table redesign** — wider layout (`max-w-5xl`), role-coloured pill selects (purple/blue/emerald), role-based avatar colours, icon-only action buttons with tooltips, dedicated Projects column with count badge, cleaner audit log with bordered action badges.
- **`user_projects_assign` audit action** — recorded in the system audit log when an admin changes a user's project assignments.

### Fixed
- **Health page "Loading containers…" stuck** — SSE streams (`stream_status`, `stream_health_containers`) are plain Django async views that don't go through DRF middleware; `request.user` was not set on `ASGIRequest`. Fixed with `getattr(request, 'user', None)` so filtering gracefully falls back to showing all projects.
- **`sync_to_async` import** — was incorrectly imported from `django.utils.sync`; corrected to `asgiref.sync`.

---

## [1.6.0] — 2026-04-15

### Fixed
- **SPA reactivity after branch switch** — switching branches in the Branches tab now reactively updates the Overview tab's Branch card, Recent Commits, and Audit Log without any page reload. `BranchTab` emits `branch-changed` on SSE stream completion; `ProjectDetailView` listens and re-fetches the project snapshot + audit log in the background.
- **Container status after branch-tab restart** — clicking "Restart Now" in the branch-switch modal now triggers `refreshStatus()` in the parent view, so the status badge updates immediately without a manual reload.
- **Sidebar full height** — sidebar `<aside>` was sizing to content rather than viewport; added `h-full` to fill its flex wrapper.

### Improved
- **Light theme — nav item hover** — `hover:bg-white/5` was invisible on white; replaced with `rgba(border, 0.32)` tint.
- **Light theme — tab hover** — tabs had `hover:text-white` which rendered invisible; overridden to `rgb(--t-base)`.
- **Light theme — btn-ghost hover** — background now visible, border tightened.
- **Light theme — btn-danger** — border/text colour corrected for white backgrounds.
- **Light theme — cards** — dedicated shadow hierarchy (`box-shadow`) for surface depth and hover lift.
- **Light theme — sidebar & header** — subtle elevation shadows added.
- **Light theme — badges** — glow `box-shadow` removed/toned down (neon glows look wrong on white).
- **Light theme — status dots** — glow intensity reduced.
- **Light theme — tables** — row hover opacity increased; header/row borders corrected.
- **Light theme — log output** — border and inset shadow corrected.
- **Light theme — inputs** — focus ring uses accent colour with 10% fill.
- **Light theme — scrollbar** — custom webkit scrollbar with light-mode tint.

---

## [1.5.0] — 2026-04-14

### Added
- **Start button** — when a container is stopped/exited the Stop button is replaced by a Start button. Restart is hidden when the container is not running. Status refreshes automatically after start/stop/restart.
- **Expanded audit log** — the following actions are now recorded with user, timestamp, and outcome:
  - `container_restart`, `container_start`, `container_stop` — container lifecycle actions
  - `project_delete` — project deletion
  - `git_pull` — manual git pull from the Branches tab
  - `submodule_update` — submodule sync
  - `backup_schedule` — backup schedule changes
  - `cron_save` — auto-deploy cron schedule changes
  - `onboard` — new project onboarded (success or failure)
  - `user_create`, `user_delete`, `password_change`, `user_role_change` — user management actions (stored under project `system`)
- **User column in audit table** — the project audit log now shows who performed each action.
- **System audit log** — Users & Roles page shows a system-level audit table for all user management events.
- **`/api/auth/audit` endpoint** — returns the last 50 system-level audit entries.

### Fixed
- `AuditLog.user` field was missing its database migration; migration `0007_auditlog_user` added and applied.

---

## [1.4.0] — 2026-04-14

### Fixed
- **Light theme: notebook cells** — code textarea and stdout output blocks were showing dark text on dark background (invisible). Added `.notebook-code` utility class that locks both background (`#0a0c12`) and text (`#e2e8f0`) regardless of theme.
- **Light theme: cell header** — `bg-[#0f1117]/60` header bar was not overridden in light mode. Now maps to `rgb(var(--c-bg2))` via a `.notebook-header` override.
- **Light theme: HTML table output** — scoped `<style>` in `NotebookTab.vue` used hardcoded dark hex values for table/th/td. Added `:global([data-theme="light"])` overrides using light surface/border CSS variables.
- **Sidebar navigation** — project links in the sidebar appeared unresponsive because the `open` accordion state reset to `{}` every time the Sidebar component remounted (each view creates its own `SidebarLayout` instance). Added a route watcher that auto-opens the accordion for the version containing the currently active project. Navigation now works correctly and the active project is always visible in the sidebar.

### Added
- **Version number** — `src/version.ts` exports `APP_VERSION`. Displayed in the sidebar footer and on the docs page.
- **Comprehensive docs page** (`/help`) — rewritten with `SidebarLayout`, covering: overview, architecture diagram, quick start, full feature reference, onboard wizard flow, Notebook internals, port registry format, FAQ, and changelog.

---

## [1.3.0] — 2026-04-11

### Added
- Project environments grouping: tag projects as production / staging / dev for visual organisation in the dashboard table.

---

## [1.2.0] — 2026-04-09

### Added
- Audit log: records project actions (deploy, restart, stop, branch switch) with timestamp and user.
- Scheduled database backups: APScheduler cron jobs configurable per project from the Settings tab.
- GitHub webhook endpoint: auto-deploys a project when a push event is received for its tracked branch.
- Dozzle embed: project detail page embeds the Dozzle log viewer iframe for the project's container.
- FileBrowser integration: writable file access to the project directory from the browser.

---

## [1.1.0] — 2026-04-07

### Added
- Mobile-friendly project page: responsive tab layout, touch-friendly buttons.
- Help / docs view at `/help`.
- UX improvements: breadcrumb navigation, tab state preserved on page refresh via URL query param.

### Fixed
- Settings tab: config save was silently failing when `odoo.conf` had a trailing comment.

---

## [1.0.0] — 2026-04-05

### Added
- Full rewrite of the original Flask dashboard in **Django 5 + Vue 3**.
- Notebook tab: Jupyter kernel over WebSocket (`jupyter_client` + `ipykernel`). Full Odoo ORM available as `env` and `self`.
- Real-time SSE log streaming in the Logs tab.
- Real-time health gauges (host + per-container CPU/memory) via SSE.
- Branch management: switch, pull, submodule sync — all with streaming output.
- Database operations: backup, duplicate, drop, restore.
- Module list grouped by addons path with update trigger.
- Settings tab: in-browser odoo.conf and .env editor.
- Onboard wizard: full automation for cloning, building, and registering a new project.
- Light/dark/system theme toggle with smooth transitions.
- Role-based access (admin vs developer).
