import itertools
import os
import queue
import threading
import typing as t
from concurrent.futures import _base

Future = _base.Future


class Task(t.NamedTuple):
    future: Future
    target: t.Callable
    args: t.Iterable[t.Any]
    kwargs: t.Dict[str, t.Any]

    def run(self) -> None:
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

    def start(self) -> Future:
        threading.Thread(target=self.run).start()
        return self.future


def spawn(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> Future:
    return Task(Future(), target, args, kwargs).start()


class Worker(threading.Thread):
    def __init__(self, q: queue.SimpleQueue = None, **kwargs: t.Any) -> None:
        self._queue = q or queue.SimpleQueue()
        self._task = Task(Future(), self.run, (), {})
        super().__init__(target=self._task.run, **kwargs)

    @property
    def future(self):
        return self._task.future

    def __enter__(self) -> "Worker":
        self.start()
        return self

    def __exit__(self, *_) -> t.Any:
        self.stop()
        self.join()
        return False

    def run(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                break
            task.run()
            del task

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        task = Task(Future(), target, args, kwargs)
        self._queue.put(task)
        return task.future

    def stop(self) -> None:
        if self.is_alive():
            self._queue.put(None)


class SimpleThreadPoolExecutor:
    _counter = itertools.count().__next__

    def __init__(self, max_workers: int, *, name: str = None) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self._max_workers = max_workers
        self._name = str(name or f"ThreadPool-{self.__class__._counter()}")
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
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

    def __exit__(self, *_) -> t.Any:
        self.shutdown(wait=True)
        return False

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        task = Task(Future(), target, args, kwargs)
        self._queue.put(task)
        return task.future

    def shutdown(self, wait=True) -> None:
        for w in set(self._workers):
            w.stop()
        if wait:
            for w in set(self._workers):
                w.join()


class TempWorker(Worker):
    IDLE_TIMEOUT = 2

    def __init__(
        self, q: queue.SimpleQueue = None, idle_timeout=IDLE_TIMEOUT, **kwargs: t.Any
    ) -> None:
        super().__init__(q, **kwargs)
        self._idle_timeout = idle_timeout

    def run(self) -> None:
        while True:
            try:
                task = self._queue.get(timeout=self._idle_timeout)
            except TimeoutError:
                break
            if task is None:
                break
            task.run()
            del task


class SmartThreadPoolExecutor(SimpleThreadPoolExecutor):
    def __init__(
        self,
        max_workers: int,
        *,
        idle_timeout=TempWorker.IDLE_TIMEOUT,
        name: str = None,
    ):
        super().__init__(max_workers, name=name)
        self._idle_timeout = idle_timeout
        self._in_queue = 0

    def __enter__(self) -> "SmartThreadPoolExecutor":
        w = Worker(self._queue, name=f"{self._name}-Worker-0")
        self._workers.add(w)
        w.start()
        return self

    def _decrease_in_queue(self, _: Future):
        self._in_queue -= 1

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        if self._in_queue > 0:
            w = TempWorker(
                self._queue,
                idle_timeout=self._idle_timeout,
                name=f"{self._name}-TempWorker-{len(self._workers)}",
            )
            self._workers.add(w)
            w.future.add_done_callback(lambda _: self._workers.remove(w))
            w.start()
        task = Task(Future(), target, args, kwargs)
        task.future.add_done_callback(self._decrease_in_queue)
        self._queue.put(task)
        self._in_queue += 1
        return task.future


_pool = None


def go(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> Future:
    global _pool

    if _pool is None:
        import atexit

        _pool = SmartThreadPoolExecutor(os.cpu_count() * 2)
        _pool.__enter__()
        atexit.register(_pool.shutdown)

    return _pool.submit(target, *args, **kwargs)
