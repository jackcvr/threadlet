import threading
import time
from concurrent import futures
from contextlib import contextmanager

import threadlet

BIG_AMOUNT = 1_000_000
NUMBERS = [1, 1]


@contextmanager
def timer():
    class Res:
        spent = 0

    res = Res()
    st = time.monotonic()
    try:
        yield res
    finally:
        res.spent = time.monotonic() - st


@contextmanager
def bench(executor):
    with executor:
        with timer() as t:
            yield executor
    name = f"{executor.__class__.__module__.split('.')[0]}.{executor.__class__.__name__}"
    print(f"{name}\ttime spent: {t.spent} sec")


@contextmanager
def title(s):
    print(f"{s}\n---")
    yield
    print()


def bench_submit(max_workers):
    with title(f"submit(sum, {NUMBERS}) max_workers={max_workers} times={BIG_AMOUNT}:"):
        with bench(futures.ThreadPoolExecutor(max_workers)) as tpe:
            for _ in range(BIG_AMOUNT):
                tpe.submit(tpe.submit(sum, NUMBERS))

        with bench(threadlet.ThreadPoolExecutor(max_workers)) as tpe:
            for _ in range(BIG_AMOUNT):
                tpe.submit(tpe.submit(sum, NUMBERS))


def bench_wait_all(max_workers):
    start = threading.Event()

    def sum_(*args):
        start.wait()
        return sum(*args)

    with title(f"futures.wait(<{BIG_AMOUNT} futures>) max_workers={max_workers}"):
        with futures.ThreadPoolExecutor(max_workers) as tpe:
            fs = []
            for _ in range(BIG_AMOUNT):
                fs.append(tpe.submit(sum_, NUMBERS))
            with bench(tpe):
                start.set()
                futures.wait(fs)

        start.clear()

        with threadlet.ThreadPoolExecutor(max_workers) as tpe:
            fs = []
            for _ in range(BIG_AMOUNT):
                fs.append(tpe.submit(sum_, NUMBERS))
            with bench(tpe):
                start.set()
                futures.wait(fs)


def bench_submit_and_wait_all(max_workers):
    with title(
        f"submit(sum, {NUMBERS}) {BIG_AMOUNT} times then futures.wait(<{BIG_AMOUNT} futures>) max_workers={max_workers}"
    ):
        with bench(futures.ThreadPoolExecutor(max_workers)) as tpe:
            fs = []
            for _ in range(BIG_AMOUNT):
                fs.append(tpe.submit(sum, NUMBERS))
            futures.wait(fs)

        with bench(threadlet.ThreadPoolExecutor(max_workers)) as tpe:
            fs = []
            for _ in range(BIG_AMOUNT):
                fs.append(tpe.submit(sum, NUMBERS))
            futures.wait(fs)


def main():
    for n in range(1, 5):
        bench_submit(n)

    for n in range(1, 5):
        bench_wait_all(n)

    for n in range(1, 5):
        bench_submit_and_wait_all(n)


if __name__ == "__main__":
    main()
