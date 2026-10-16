"""Stream container logs, run them through the detection rules, hand events to a handler."""
import logging
import threading
import time

from .detection import detect

log = logging.getLogger(__name__)


def consume(container, lines, handler):
    """Feed an iterable of log lines (str or bytes, possibly several lines per chunk) through
    the rules. A failing handler never stops the stream."""
    for chunk in lines:
        text = chunk.decode('utf-8', errors='replace') if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        for line in text.splitlines():
            event = detect(container, line)
            if event is None:
                continue
            try:
                handler(event)
            except Exception:
                log.exception('alert handler failed for %s', container)


class LogWatcher:
    def __init__(self, containers_fn, stream_fn, handler, sleep=time.sleep, max_cycles=None, backoff=5):
        self.containers_fn, self.stream_fn, self.handler = containers_fn, stream_fn, handler
        self.sleep, self.max_cycles, self.backoff = sleep, max_cycles, backoff
        self._stop = threading.Event()

    # sequential variant: deterministic, used by the tests
    def run(self):
        cycles = 0
        while not self._stop.is_set() and (self.max_cycles is None or cycles < self.max_cycles):
            for container in list(self.containers_fn()):
                self._watch_once(container)
            cycles += 1
            self.sleep(self.backoff)

    def _watch_once(self, container):
        try:
            consume(container, self.stream_fn(container), self.handler)
        except Exception as e:                      # container restarted, daemon hiccup, ...
            log.warning('log stream for %s ended: %s', container, e)

    # production variant: one thread per container, picks up new containers every minute
    def start(self):
        threads = {}

        def loop(container):
            while not self._stop.is_set():
                self._watch_once(container)
                self.sleep(self.backoff)

        def supervisor():
            while not self._stop.is_set():
                for container in list(self.containers_fn()):
                    t = threads.get(container)
                    if t is None or not t.is_alive():
                        t = threading.Thread(target=loop, args=(container,), daemon=True, name=f'logwatch-{container}')
                        threads[container] = t
                        t.start()
                self._stop.wait(60)

        threading.Thread(target=supervisor, daemon=True, name='logwatch-supervisor').start()

    def stop(self):
        self._stop.set()


def docker_log_stream(container_name):
    """Live log stream of a container, starting now."""
    from .docker_service import get_docker_client
    container = get_docker_client().containers.get(container_name)
    return container.logs(stream=True, follow=True, since=int(time.time()))
