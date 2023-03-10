import threading
from concurrent import futures

import pyperf

MAX_WORKERS_VALUES = (1, 2, 4, 8)

runner = pyperf.Runner()


def _run(ev):
    ev.wait()


def _submit_many(executor, limit=10_000, **kwargs):
    fs = set()
    for _ in range(limit):
        fs.add(executor.submit(_run, **kwargs))
    return fs


def _submit_and_wait(executor, max_workers, limit=10_000):
    with executor(max_workers) as tpe:
        start_event = threading.Event()
        fs = _submit_many(tpe, limit, start_event=start_event)
        start_event.set()
        futures.wait(fs)


def start_benchmark(executor):
    for max_workers in MAX_WORKERS_VALUES:
        runner.bench_func(f"max_workers={max_workers}", _submit_and_wait, executor, max_workers)
