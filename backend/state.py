import queue
import threading

deploy_queues: dict[str, queue.Queue] = {}
branch_switch_queues: dict[str, queue.Queue] = {}
submodule_queues: dict[str, queue.Queue] = {}
pull_queues: dict[str, queue.Queue] = {}

_deploy_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def get_deploy_lock(name: str) -> threading.Lock:
    with _locks_lock:
        if name not in _deploy_locks:
            _deploy_locks[name] = threading.Lock()
        return _deploy_locks[name]
