import queue
import time
import timeit
from concurrent.futures import ThreadPoolExecutor, wait
from threadlet import SimpleThreadPoolExecutor

N = 1_000_000


def dummy():
    pass


for cls in (ThreadPoolExecutor, SimpleThreadPoolExecutor):
    g = globals()

    with cls(1) as pool:
        res = timeit.timeit("pool.submit(dummy)", number=N, globals=dict(g, pool=pool))
        print(f"{cls=} submit: {res}")

    with cls(1) as pool:
        res = timeit.timeit(
            "pool.submit(dummy).result()", number=N, globals=dict(g, pool=pool)
        )
        print(f"{cls=} submit and wait: {res}")

    for max_workers in (1, 2, 4, 8):
        with cls(max_workers) as pool:
            q: queue.SimpleQueue = queue.SimpleQueue()
            for _ in range(N):
                q.put(1)
            fs = set()
            start = time.monotonic()
            for _ in range(N):
                fs.add(pool.submit(q.get_nowait))
            wait(fs)
            res = time.monotonic() - start
            print(f"{cls=} {max_workers=} consume: {res}")
