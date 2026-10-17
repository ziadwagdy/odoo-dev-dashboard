"""APScheduler-based cron for auto-deploy."""
import logging
import queue
import time
import threading
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
    return _scheduler


def setup_cron_jobs():
    """Load all enabled CronJobs and BackupSchedules from DB and schedule them.
    Also auto-creates enabled CronJobs for any registered project that doesn't have one yet."""
    try:
        from apps.projects.models import CronJob, BackupSchedule
        from services.registry import read_registry
        DEFAULT_SCHEDULE = '*/2 * * * *'
        # Auto-create for any new projects not yet in the DB
        registered = {p['name'] for p in read_registry()}
        existing = set(CronJob.objects.values_list('project', flat=True))
        for name in registered - existing:
            CronJob.objects.create(project=name, schedule=DEFAULT_SCHEDULE, enabled=True)
        # Schedule all enabled deploy jobs
        setup_restore_test_job()
        setup_security_jobs()
        scheduler = get_scheduler()
        for job in CronJob.objects.filter(enabled=True):
            _add_job(scheduler, job)
        # Schedule all enabled backup jobs
        for bsched in BackupSchedule.objects.filter(enabled=True):
            _add_backup_job(scheduler, bsched)
    except Exception as e:
        logger.error(f'Failed to setup cron jobs: {e}')


def reschedule_job(job):
    """Add or update a single deploy cron job."""
    scheduler = get_scheduler()
    if scheduler.get_job(job.project):
        scheduler.remove_job(job.project)
    if job.enabled:
        _add_job(scheduler, job)


def reschedule_backup_job(bsched):
    """Add or update a single backup schedule job."""
    scheduler = get_scheduler()
    job_id = f'backup__{bsched.project}__{bsched.dbname}'
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    if bsched.enabled:
        _add_backup_job(scheduler, bsched)


def _add_backup_job(scheduler, bsched):
    parts = bsched.schedule.split()
    if len(parts) != 5:
        return
    minute, hour, day, month, day_of_week = parts
    job_id = f'backup__{bsched.project}__{bsched.dbname}'
    try:
        scheduler.add_job(
            _run_scheduled_backup,
            CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
            id=job_id,
            args=[bsched.project, bsched.dbname],
            replace_existing=True,
        )
    except Exception as e:
        logger.error(f'Failed to schedule backup job {job_id}: {e}')


def _add_job(scheduler, job):
    parts = job.schedule.split()
    if len(parts) != 5:
        return
    minute, hour, day, month, day_of_week = parts
    try:
        scheduler.add_job(
            _check_and_deploy,
            CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
            id=job.project,
            args=[job.project],
            replace_existing=True,
        )
    except Exception as e:
        logger.error(f'Failed to schedule job {job.project}: {e}')


def _check_and_deploy(project_name: str):
    """Called by scheduler: git fetch, compare, deploy if behind."""
    from services.registry import read_registry
    from services.git_service import get_git_info, git_pull, get_current_commit
    from state import deploy_queues, get_deploy_lock
    from apps.projects.models import CronJob, DeployHistory

    projects = {p['name']: p for p in read_registry()}
    p = projects.get(project_name)
    if not p or not p.get('folder'):
        return

    _branch, pending = get_git_info(p['folder'])
    if not pending:
        _update_cron_result(project_name, 'no_changes')
        return

    lock = get_deploy_lock(project_name)
    if not lock.acquire(blocking=False):
        return

    prev_commit = get_current_commit(p['folder'])
    q = queue.Queue()
    deploy_queues[project_name] = q
    started_at = time.time()
    outcome = 'failed'

    try:
        git_pull(p['folder'], q)
        new_commit = get_current_commit(p['folder'])
        outcome = 'success' if new_commit != prev_commit else 'no_change'
    except Exception as e:
        logger.error(f'Cron deploy failed for {project_name}: {e}')
        new_commit = prev_commit
    finally:
        duration = round(time.time() - started_at, 1)
        try:
            DeployHistory.objects.create(
                project=project_name, trigger_type='cron',
                prev_commit=prev_commit, new_commit=new_commit,
                outcome=outcome, duration_seconds=duration,
            )
        except Exception:
            pass
        _update_cron_result(project_name, outcome)
        lock.release()


def _update_cron_result(project_name: str, result: str):
    try:
        from apps.projects.models import CronJob
        CronJob.objects.filter(project=project_name).update(
            last_run=datetime.now(timezone.utc),
            last_result=result,
        )
    except Exception:
        pass


def _run_scheduled_backup(project_name: str, dbname: str):
    """Called by scheduler: back up dbname for project and prune old backups."""
    import os
    from django.conf import settings
    from services.registry import get_project
    from services.db_service import backup_database, list_backup_files
    from apps.projects.models import BackupSchedule, AuditLog

    p = get_project(project_name)
    if not p:
        return

    backup_dir = os.path.join(settings.DATA_DIR, 'backups', project_name)
    result = 'failed'
    try:
        backup_database(p['db_port'], dbname, backup_dir)
        result = 'success'

        # Prune oldest backups beyond retention count
        try:
            schedule = BackupSchedule.objects.get(project=project_name, dbname=dbname)
            retention = schedule.retention
            # list_backup_files returns newest-first; filter by dbname prefix
            all_files = list_backup_files(project_name, backup_dir)
            db_files = [f for f in all_files if f['filename'].startswith(f'{dbname}-')]
            for old in db_files[retention:]:
                old_path = os.path.join(backup_dir, old['filename'])
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        except BackupSchedule.DoesNotExist:
            pass

    except Exception as e:
        logger.error(f'Scheduled backup failed {project_name}/{dbname}: {e}')

    # Update last_run + last_result
    try:
        BackupSchedule.objects.filter(project=project_name, dbname=dbname).update(
            last_run=datetime.now(timezone.utc),
            last_result=result,
        )
    except Exception:
        pass

    # Write audit log
    try:
        AuditLog.objects.create(
            project=project_name,
            action='backup',
            detail=f'{dbname} (scheduled)',
            outcome=result,
        )
    except Exception:
        pass


# ── weekly restore test of every project's latest backup ───────────────────
def run_weekly_restore_tests():
    """Sunday night: prove that the latest backup of every project really restores."""
    import os
    from django.conf import settings
    from apps.projects.models import AuditLog
    from services import lifecycle
    from services.registry import read_registry

    def record(project, outcome):
        AuditLog.objects.create(
            project=project, action='restore_test', user='scheduler',
            outcome='success' if outcome['ok'] else 'failed',
            detail='scheduled', meta={k: outcome.get(k) for k in ('checks', 'seconds', 'error')})

    results = lifecycle.run_restore_tests(
        read_registry(), os.path.join(settings.DATA_DIR, 'backups'), record)
    for r in results:
        if r['status'] == 'no-backup':
            AuditLog.objects.create(project=r['project'], action='restore_test', user='scheduler',
                                    outcome='failed', detail='no backup exists yet', meta={})
    return results


def setup_restore_test_job():
    scheduler = get_scheduler()
    if not scheduler.get_job('restore-tests'):
        scheduler.add_job(run_weekly_restore_tests, CronTrigger(day_of_week='sun', hour=3, minute=30),
                          id='restore-tests', replace_existing=True, max_instances=1, coalesce=True)


def run_persistence_scan():
    from django import db
    from services import security_watch
    from services.persistence_scan import scan_all
    db.close_old_connections()
    try:
        scan_all(security_watch.make_handler())
    finally:
        db.close_old_connections()


def run_daily_digest():
    from django import db
    from services import webpush
    from services.digest import send_daily_digest
    from apps.security.models import PushSubscription
    db.close_old_connections()
    try:
        def send(title, body, severity):
            payload = {'title': title, 'body': body, 'severity': severity, 'url': '/security', 'tag': 'daily-digest'}
            for sub in PushSubscription.objects.filter(user__groups__name='admin').distinct():
                webpush._deliver(sub, payload)
        send_daily_digest(send)
    finally:
        db.close_old_connections()


def setup_security_jobs():
    scheduler = get_scheduler()
    scheduler.add_job(run_persistence_scan, CronTrigger(minute='*/10'), id='persistence-scan',
                      replace_existing=True, max_instances=1, coalesce=True)
    scheduler.add_job(run_daily_digest, CronTrigger(hour=8, minute=0), id='daily-digest',
                      replace_existing=True, max_instances=1, coalesce=True)
