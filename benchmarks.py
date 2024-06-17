import queue
import time
import tracemalloc
import gc
import os
import types
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor as DefaultThreadPoolExecutor
from threadlet import SimpleThreadPoolExecutor, spawn, ThreadPoolExecutor

N = int(os.getenv("N", 1_000_000))


@contextmanager
def nogc():
    gc.disable()
    try:
        yield
    finally:
        gc.collect()
        gc.enable()


@contextmanager
def trace_time():
    s = time.monotonic()
    ns = types.SimpleNamespace()
    try:
        yield ns
    finally:
        delta = time.monotonic() - s
        ns.result = f"time={delta:5.2f}s"


def as_mb(size):
    return f"{size / (1 << 17):.2f}"


def cls_name(cls):
    return f"{cls.__module__}.{cls.__name__}"


@contextmanager
def trace_memory():
    tracemalloc.start()
    ns = types.SimpleNamespace()
    try:
        yield ns
    finally:
        size, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        ns.result = f"size={as_mb(size)}mb, peak={as_mb(peak)}mb"


def dummy():
    pass


for cls in [DefaultThreadPoolExecutor, ThreadPoolExecutor, SimpleThreadPoolExecutor]:
    res = {}
    for tracer in (trace_time, trace_memory):
        with nogc(), tracer() as t:
            with cls(1) as tpe:
                for _ in range(N):
                    tpe.submit(dummy)
            gc.collect()
        res[tracer] = t.result
    prefix = f"{cls_name(cls)} submit"
    print(f"{prefix:>51}: {res[trace_time]} {res[trace_memory]}")


def consume(q):
    while True:
        f = q.get()
        if f is None:
            break
        f.result()


for max_workers in (1, 2, 4, 8):
    q: queue.SimpleQueue = queue.SimpleQueue()
    for cls in [
        DefaultThreadPoolExecutor,
        ThreadPoolExecutor,
        SimpleThreadPoolExecutor,
    ]:
        res = {}
        for tracer in (trace_time, trace_memory):
            with cls(max_workers) as executor:
                with tracer() as t:
                    consumer = spawn(consume, q)
                    for i in range(N):
                        q.put(executor.submit(dummy))
                        if tracer is trace_memory and 0 < i < N and i % 100_000 == 0:
                            time.sleep(1.5)
                    q.put(None)
                    consumer.result()
                    if tracer is trace_memory:
                        time.sleep(2)
                    gc.collect()
                res[tracer] = t.result
        prefix = f"{cls_name(cls)} e2e[{max_workers}]"
        print(f"{prefix:>51}: {res[trace_time]} {res[trace_memory]}")
