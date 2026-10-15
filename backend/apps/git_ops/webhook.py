"""GitHub push webhook handler.

Setup:
  1. Set GITHUB_WEBHOOK_SECRET in your .env file.
  2. In GitHub repo Settings → Webhooks, add:
       Payload URL: https://<your-domain>/api/git/webhook/github
       Content type: application/json
       Secret: <same value as GITHUB_WEBHOOK_SECRET>
       Events: Just the push event

The webhook matches the pushed repo+branch against the port registry and
triggers a deploy via the same path as the dashboard Deploy button.
"""
import hashlib
import hmac
import json
import logging
import os
import queue
import threading
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from services.registry import read_registry
from services.git_service import git_pull, get_current_commit, get_current_branch, get_remote_repo_name
from services.docker_service import restart_container
from state import deploy_queues, get_deploy_lock
from apps.projects.models import DeployHistory, AuditLog

logger = logging.getLogger(__name__)


def _verify_signature(body: bytes, header: str) -> bool:
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
    if not secret:
        # fail closed: an unset secret must never mean "accept anything"
        logger.error('GITHUB_WEBHOOK_SECRET not set — rejecting webhook')
        return False
    expected = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or '')


@csrf_exempt
def github_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    body = request.body
    sig_header = request.headers.get('X-Hub-Signature-256', '')
    if not _verify_signature(body, sig_header):
        logger.warning('GitHub webhook: invalid signature')
        return JsonResponse({'error': 'invalid signature'}, status=403)

    event = request.headers.get('X-GitHub-Event', '')
    if event != 'push':
        return JsonResponse({'ok': True, 'skipped': f'event={event}'})

    try:
        payload = json.loads(body)
    except Exception:
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    # Extract repo name and branch from payload
    repo_name = (payload.get('repository') or {}).get('name', '').lower()
    ref = payload.get('ref', '')  # e.g. refs/heads/17-dev
    pushed_branch = ref.removeprefix('refs/heads/')

    if not repo_name or not pushed_branch:
        return JsonResponse({'ok': True, 'skipped': 'no repo or branch'})

    # Find ALL projects whose git remote matches the pushed repo
    all_projects = read_registry()
    matched = [
        p for p in all_projects
        if p.get('folder') and get_remote_repo_name(p['folder']) == repo_name
    ]

    if not matched:
        logger.info(f'GitHub webhook: no project matched repo={repo_name}')
        return JsonResponse({'ok': True, 'skipped': f'no project for repo={repo_name}'})

    # Filter to only worktrees currently on the pushed branch
    deployable = []
    for p in matched:
        current = get_current_branch(p['folder'])
        if current == pushed_branch:
            deployable.append(p)
        else:
            logger.info(
                f'GitHub webhook: skipping {p["name"]} '
                f'(on {current!r}, push was to {pushed_branch!r})'
            )

    if not deployable:
        return JsonResponse({'ok': True, 'skipped': f'no worktrees on branch={pushed_branch}'})

    # Spawn one deploy thread per matching project
    triggered = []
    for p in deployable:
        project_name = p['name']
        folder       = p['folder']
        container    = p['container']

        lock = get_deploy_lock(project_name)
        if not lock.acquire(blocking=False):
            logger.info(f'GitHub webhook: deploy already in progress for {project_name}, skipping')
            continue

        prev_commit = get_current_commit(folder)
        q = queue.Queue()
        deploy_queues[project_name] = q
        started_at = time.time()

        def _run(project_name=project_name, folder=folder, container=container,
                 prev_commit=prev_commit, q=q, started_at=started_at, lock=lock):
            outcome = 'success'
            try:
                exit_code = git_pull(folder, q)
                if exit_code != 0:
                    outcome = 'failed'
                else:
                    try:
                        restart_container(container)
                        q.put(f'--- container {container} restarted ---')
                    except Exception as e:
                        logger.error(f'Webhook: restart failed for {container}: {e}')
                        outcome = 'failed'
            except Exception as e:
                logger.error(f'Webhook deploy failed for {project_name}: {e}')
                outcome = 'failed'
            finally:
                new_commit = get_current_commit(folder)
                duration = round(time.time() - started_at, 1)
                try:
                    DeployHistory.objects.create(
                        project=project_name, trigger_type='webhook',
                        prev_commit=prev_commit, new_commit=new_commit,
                        outcome=outcome, duration_seconds=duration,
                    )
                except Exception:
                    pass
                try:
                    AuditLog.objects.create(
                        project=project_name, action='deploy',
                        detail=f'webhook push {pushed_branch} {(prev_commit or "")[:7]}→{(new_commit or "")[:7]}',
                        outcome=outcome,
                    )
                except Exception:
                    pass
                lock.release()

        threading.Thread(target=_run, daemon=True).start()
        logger.info(f'GitHub webhook: triggered deploy for {project_name} (branch={pushed_branch})')
        triggered.append(project_name)

    return JsonResponse({'ok': True, 'triggered': triggered})
