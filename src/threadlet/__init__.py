import itertools
import os
import queue
import threading
import types
import typing as t
from concurrent.futures import _base

from .abc import BaseThreadPoolExecutor, BaseWorker

QueueType = t.Union[queue.Queue, queue.SimpleQueue]

TimeoutError = _base.TimeoutError
as_completed = _base.as_completed
wait = _base.wait


class Item:
    __slots__ = ("target", "args", "kwargs", "future")

    def __init__(self, target: t.Callable, args: t.Any, kwargs: t.Any) -> None:
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.future: _base.Future = _base.Future()

    def __call__(self) -> None:
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            result = self.target(*self.args, **self.kwargs)
        except BaseException as e:
            self.future.set_exception(e)
            # Break a reference cycle with the exception 'exc'
            self = None
        else:
            self.future.set_result(result)

    __class_getitem__ = classmethod(types.GenericAlias)


def run_in_thread(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> _base.Future:
    item = Item(target, args, kwargs)
    threading.Thread(target=item).start()
    return item.future


def _cancel_all_futures(q: QueueType) -> None:
    while True:
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if item is not None:
            item.future.cancel()


class Worker(BaseWorker):
    def __init__(self, q: QueueType = None, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self._queue = q or queue.SimpleQueue()

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> _base.Future:
        item = Item(target, args, kwargs)
        self._queue.put(item)
        return item.future

    def _run_forever(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            item()
            del item

    def _stop(self) -> None:
        self._queue.put(None)


class SimpleThreadPoolExecutor(BaseThreadPoolExecutor):
    _counter = itertools.count().__next__

    def __init__(self, max_workers: int, *, name: str = None, queue_limit: int = None) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self._max_workers = max_workers
        self._name = str(name or f"ThreadPool-{self.__class__._counter()}")
        self._queue: QueueType = queue.Queue(maxsize=queue_limit) if queue_limit else queue.SimpleQueue()
        self._workers: t.Set[Worker] = set()

    @property
    def workers(self) -> t.Set[Worker]:
        return self._workers

    def __enter__(self) -> "SimpleThreadPoolExecutor":
        for i in range(self._max_workers):
            w = Worker(self._queue, name=f"{self._name}-Worker-{i}")
            self._workers.add(w)
            w.start()
        return self

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> _base.Future:
        item = Item(target, args, kwargs)
        self._queue.put(item)
        return item.future

    def shutdown(self, wait=True) -> None:
        for w in set(self._workers):
            w.stop()
        if wait:
            for w in set(self._workers):
                w.join()


class _PoolWorker(Worker):
    def __init__(
        self,
        q: QueueType = None,
        *,
        idle_timeout: float = None,
        executor: "ThreadPoolExecutor" = None,
        **kwargs,
    ) -> None:
        super().__init__(q, **kwargs)
        if executor is None:
            raise ValueError("executor must be provided")
        self._idle_timeout = idle_timeout
        self._executor = executor

    def _run_forever(self) -> None:
        try:
            while True:
                try:
                    item = self._queue.get_nowait()
                except queue.Empty:
                    self._executor.idle_sem.release()
                    try:
                        item = self._queue.get(timeout=self._idle_timeout)
                    except queue.Empty:
                        break
                if item is None:
                    break
                item()
                del item
        finally:
            self._executor.idle_sem.acquire(blocking=False)
            self._executor.workers.discard(self)
            del self._executor


class ThreadPoolExecutor(SimpleThreadPoolExecutor):
    MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
    IDLE_TIMEOUT = 5

    def __init__(
        self,
        max_workers: int = MAX_WORKERS,
        *,
        min_workers: int = 0,
        idle_timeout: float = IDLE_TIMEOUT,
        queue_limit: int = None,
    ) -> None:
        super().__init__(max_workers, queue_limit=queue_limit)
        if min_workers > max_workers:
            raise ValueError("min_workers must be less(or equal) than max_workers")
        self._min_workers = min_workers
        self._idle_timeout = idle_timeout
        self._idle_sem = threading.Semaphore(0)
        self._shutdown_lock = threading.Lock()

    @property
    def idle_sem(self) -> threading.Semaphore:
        return self._idle_sem

    def __enter__(self) -> "ThreadPoolExecutor":
        for _ in range(self._min_workers):
            self._add_worker(idle_timeout=None)
        return self

    def _add_worker(self, *, idle_timeout: t.Optional[float]) -> None:
        worker = _PoolWorker(
            self._queue,
            name=f"{self._name}-Worker-{len(self._workers)}",
            idle_timeout=idle_timeout,
            executor=self,
        )
        self._workers.add(worker)
        worker.start()

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> _base.Future:
        with self._shutdown_lock:
            item = Item(target, args, kwargs)
            self._queue.put(item)
            workers_num = len(self._workers)
            has_idle_workers = self._idle_sem.acquire(blocking=False)
            if workers_num < self._max_workers and not has_idle_workers:
                self._add_worker(idle_timeout=self._idle_timeout)
            return item.future

    def shutdown(self, wait=True, *, cancel_futures=False) -> None:
        with self._shutdown_lock:
            if cancel_futures:
                _cancel_all_futures(self._queue)
            for w in set(self._workers):
                w.stop()
        if wait:
            for w in set(self._workers):
                w.join()
