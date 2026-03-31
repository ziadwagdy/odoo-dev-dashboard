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
from services.git_service import git_pull, get_current_commit
from state import deploy_queues, get_deploy_lock
from apps.projects.models import DeployHistory, AuditLog

logger = logging.getLogger(__name__)


def _verify_signature(body: bytes, header: str) -> bool:
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning('GITHUB_WEBHOOK_SECRET not set — skipping signature verification')
        return True
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

    # Find matching project in registry by folder name or project name
    projects = {p['name']: p for p in read_registry()}
    matched = None
    for p in projects.values():
        folder = (p.get('folder') or '').rstrip('/')
        folder_name = folder.split('/')[-1].lower()
        if folder_name == repo_name or p['name'].lower() == repo_name:
            matched = p
            break

    if not matched:
        logger.info(f'GitHub webhook: no project matched repo={repo_name}')
        return JsonResponse({'ok': True, 'skipped': f'no project for repo={repo_name}'})

    project_name = matched['name']
    folder = matched.get('folder')
    if not folder:
        return JsonResponse({'ok': True, 'skipped': 'project has no folder'})

    # Acquire deploy lock (non-blocking — skip if already deploying)
    lock = get_deploy_lock(project_name)
    if not lock.acquire(blocking=False):
        return JsonResponse({'ok': True, 'skipped': 'deploy already in progress'})

    prev_commit = get_current_commit(folder)
    q = queue.Queue()
    deploy_queues[project_name] = q
    started_at = time.time()

    def _run():
        outcome = 'success'
        try:
            git_pull(folder, q)
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
    return JsonResponse({'ok': True, 'project': project_name})
