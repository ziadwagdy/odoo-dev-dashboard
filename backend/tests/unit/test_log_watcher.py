import pytest

from services.log_watcher import LogWatcher, consume


def test_consume_routes_only_detected_lines_to_the_handler():
    seen = []
    lines = ['LOG: ok', 'FATAL:  password authentication failed for user "odoo_app"', 'LOG: ok']
    consume('a-db', lines, handler=seen.append)
    assert len(seen) == 1 and seen[0].rule == 'pg_auth_failure' and seen[0].source == 'a-db'


def test_consume_accepts_bytes_and_survives_garbage():
    seen = []
    consume('a-db', [b'FATAL:  password authentication failed for user "x"\n', b'\xff\xfe broken'], handler=seen.append)
    assert len(seen) == 1


def test_handler_errors_do_not_stop_the_stream():
    calls = []

    def handler(event):
        calls.append(event)
        raise RuntimeError('db locked')
    consume('a-db', ['FATAL:  password authentication failed for user "a"',
                     'FATAL:  password authentication failed for user "b"'], handler=handler)
    assert len(calls) == 2


def test_watcher_reconnects_after_a_stream_error_and_after_it_ends():
    attempts = {'n': 0}

    def stream(container):
        attempts['n'] += 1
        if attempts['n'] == 1:
            raise ConnectionError('container restarted')
        if attempts['n'] == 2:
            return iter(['FATAL:  password authentication failed for user "z"'])
        raise StopIteration

    seen = []
    w = LogWatcher(lambda: ['a-db'], stream, seen.append, sleep=lambda s: None, max_cycles=3)
    w.run()
    assert attempts['n'] >= 3 and len(seen) == 1


def test_watcher_follows_the_container_list_as_it_changes():
    containers = [['a-db'], ['a-db', 'b-db']]
    seen_containers = []

    def stream(container):
        seen_containers.append(container)
        return iter([])
    w = LogWatcher(lambda: containers.pop(0) if len(containers) > 1 else containers[0], stream, lambda e: None,
                   sleep=lambda s: None, max_cycles=2)
    w.run()
    assert 'b-db' in seen_containers
