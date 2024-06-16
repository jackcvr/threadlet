import queue
import time
import timeit
from concurrent.futures import ThreadPoolExecutor
from threadlet import SimpleThreadPoolExecutor, spawn

N = 1_000_000


def dummy():
    pass


def produce(q):
    for _ in range(N):
        q.put(pool.submit(dummy))
    q.put(None)


def consume(q):
    while True:
        if q.get() is None:
            break


for cls in (ThreadPoolExecutor, SimpleThreadPoolExecutor):
    g = globals()

    with cls(1) as pool:
        res = timeit.timeit("pool.submit(dummy)", number=N, globals=dict(g, pool=pool))
        print(f"{cls=} submit: {res}")

    for max_workers in (1, 2, 4, 8):
        with cls(max_workers) as pool:
            q: queue.SimpleQueue = queue.SimpleQueue()
            start = time.monotonic()
            consumer = spawn(consume, q)
            producer = spawn(produce, q)
            producer.result()
            consumer.result()
            res = time.monotonic() - start
            print(f"{cls=} {max_workers=} end to end: {res}")
