"""Wire the pieces together: registry -> database containers -> log stream -> rules -> alerts -> push."""
import logging
import os

from django import db

from .alerting import AlertManager
from .log_watcher import LogWatcher, docker_log_stream
from .registry import read_registry
from .webpush import WebPushNotifier

log = logging.getLogger(__name__)
_started = None


def containers():
    return [f"{p['name']}-db" for p in read_registry()]


def ignore_list():
    return {t.strip() for t in os.environ.get('SECURITY_IGNORE', '').split(',') if t.strip()}


def make_handler(notifiers=None):
    manager = AlertManager(notifiers=notifiers if notifiers is not None else [WebPushNotifier()], ignore=ignore_list())

    def handler(event):
        db.close_old_connections()
        try:
            manager.handle(event)
        finally:
            db.close_old_connections()
    return handler


def start():
    """Start the always-on watcher once per process (called from the ASGI entry point)."""
    global _started
    if os.environ.get('SECURITY_WATCH', 'on').lower() == 'off' or _started is not None:
        return _started
    _started = LogWatcher(containers, docker_log_stream, make_handler())
    _started.start()
    log.info('security watcher started for %d containers', len(containers()))
    return _started
