from concurrent import futures

import pyperf

MAX_WORKERS_VALUES = (1, 2, 4, 8)
LIMIT = 10_000

runner = pyperf.Runner()


def run_nowait():
    pass


def run_wait(ev):
    ev.wait()


def submit_all(submit_func):
    fs = set()
    for _ in range(LIMIT):
        fs.add(submit_func(run_nowait))
    return futures.wait(fs)


def start_benchmark(executor):
    for max_workers in MAX_WORKERS_VALUES:
        with executor(max_workers) as tpe:
            runner.bench_func(f"max_workers={max_workers}", submit_all, tpe.submit)
