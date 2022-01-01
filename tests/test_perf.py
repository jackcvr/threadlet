import contextlib
import threading
import time
import timeit
from concurrent import futures

import pytest

from threadlet import Future  # noqa
from threadlet.executor import ThreadPoolExecutor

BIG_AMOUNT = 1_000_000
MEDIUM_AMUNT = 100_000


@pytest.fixture(autouse=True)
def new_line():
    print()


def sum_(x, y):
    return x + y


@contextlib.contextmanager
def calctime():
    class Res:
        value = 0

    res = Res()
    st = time.monotonic()
    try:
        yield res
    finally:
        res.value = time.monotonic() - st


@pytest.mark.parametrize(
    "name,executor_class,max_workers,stmt,number",
    [
        ("OLD", futures.ThreadPoolExecutor, 1, "executor.submit(sum_, 1, 1)", BIG_AMOUNT),
        ("NEW", ThreadPoolExecutor, 1, "executor.submit(sum_, 1, 1)", BIG_AMOUNT),
        ("OLD", futures.ThreadPoolExecutor, 1, "executor.submit(sum_, 1, 1).result()", MEDIUM_AMUNT),
        ("NEW", ThreadPoolExecutor, 1, "executor.submit(sum_, 1, 1).result()", MEDIUM_AMUNT),
    ],
)
def test_executor_submit_time(name, executor_class, max_workers, stmt, number):
    global_vars = globals()
    with executor_class(max_workers) as tpe:
        value = timeit.timeit(stmt, number=number, globals=dict(global_vars, executor=tpe))
        print("time:", value)
        print("threads: ", threading.active_count() - 1)


@pytest.mark.parametrize(
    "name,executor_class,max_workers,number",
    [
        ("OLD", futures.ThreadPoolExecutor, 1, BIG_AMOUNT),
        ("NEW", ThreadPoolExecutor, 1, BIG_AMOUNT),
        ("OLD", futures.ThreadPoolExecutor, 2, BIG_AMOUNT),
        ("NEW", ThreadPoolExecutor, 2, BIG_AMOUNT),
    ],
)
def test_executor_total_time(name, executor_class, max_workers, number):
    with executor_class(max_workers) as tpe:
        fs = []
        with calctime() as r:
            for _ in range(number):
                fs.append(tpe.submit(sum_, 1, 1))
            futures.wait(fs)
        print("time:", r.value)
        print("threads: ", threading.active_count() - 1)
