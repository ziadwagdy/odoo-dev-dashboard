# Changelog

All notable changes to the Odoo Dev Dashboard are documented here.
Format: [version] — date

---

## [1.7.5] — 2026-07-29

### Changed
- **Branches tab — two-column layout for hr-base projects** — the Local/Remote branch lists now render as a 2-column grid (sm breakpoint+) when the project's registry `folder` matches `hr-base` (e.g. `worktrees/hr-base-17`) OR the project has an hr-base submodule (e.g. alif's `cnc-hr-base`), cutting page scroll height roughly in half for the long branch lists. Other projects keep the single-column list. `BranchTab.vue`: `isHrBase` computed checks both `props.folder` and the loaded `submodules` list.

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
