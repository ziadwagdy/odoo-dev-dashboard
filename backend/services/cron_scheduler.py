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
    """Load all enabled CronJobs from DB and schedule them.
    Also auto-creates enabled CronJobs for any registered project that doesn't have one yet."""
    try:
        from apps.projects.models import CronJob
        from services.registry import read_registry
        DEFAULT_SCHEDULE = '*/2 * * * *'
        # Auto-create for any new projects not yet in the DB
        registered = {p['name'] for p in read_registry()}
        existing = set(CronJob.objects.values_list('project', flat=True))
        for name in registered - existing:
            CronJob.objects.create(project=name, schedule=DEFAULT_SCHEDULE, enabled=True)
        # Schedule all enabled jobs
        jobs = CronJob.objects.filter(enabled=True)
        scheduler = get_scheduler()
        for job in jobs:
            _add_job(scheduler, job)
    except Exception as e:
        logger.error(f'Failed to setup cron jobs: {e}')


def reschedule_job(job):
    """Add or update a single job."""
    scheduler = get_scheduler()
    if scheduler.get_job(job.project):
        scheduler.remove_job(job.project)
    if job.enabled:
        _add_job(scheduler, job)


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
