import itertools
import queue
import threading
import typing as t
import weakref
from dataclasses import dataclass, field
from concurrent.futures import _base

# aliases
Future = _base.Future
wait = _base.wait
as_completed = _base.as_completed


class DeadWorker(RuntimeError):
    def __init__(self):
        super().__init__("Cannot submit new future: worker is down")


@dataclass(frozen=True)
class Task:
    future: Future
    target: t.Callable
    args: t.Iterable[t.Any] = ()
    kwargs: t.Dict[str, t.Any] = field(default_factory=dict)

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


def spawn(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> Future:
    f: Future = Future()
    threading.Thread(target=Task(f, target, args, kwargs).run).start()
    return f


class Worker(threading.Thread):
    _counter = itertools.count().__next__

    def __init__(self, q: queue.SimpleQueue = None, name=None, **kwargs: t.Any) -> None:
        super().__init__(name=name or f"Worker-{self.__class__._counter()}", **kwargs)
        self._queue = q or queue.SimpleQueue()
        self._future: Future = Future()
        self.on_idle: t.Optional[t.Callable] = None

    @property
    def future(self):
        return self._future

    def __enter__(self) -> "Worker":
        self.start()
        return self

    def __exit__(self, *_) -> t.Any:
        self.stop()
        self.join()
        return False

    def run(self) -> None:
        if not self._future.set_running_or_notify_cancel():
            return
        try:
            while True:
                task = self._get_task()
                if task is None:
                    break
                task.run()
                del task
        except BaseException as e:
            self._future.set_exception(e)
            # Break a reference cycle with the exception 'exc'
            self = None
        else:
            self._future.set_result(None)

    def _get_task(self):
        try:
            return self._queue.get(block=False)
        except queue.Empty:
            if self.on_idle:
                self.on_idle()
            return self._queue.get()

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        if not self.is_alive():
            raise DeadWorker
        f: Future = Future()
        self._queue.put(Task(f, target, args, kwargs))
        return f

    def stop(self) -> None:
        if self.is_alive():
            self._queue.put(None)


def _stop_workers(workers, wait=True) -> None:
    for w in workers:
        if w.is_alive():
            w.stop()
    if wait:
        _base.wait((w.future for w in workers))


class SimpleThreadPoolExecutor:
    _counter = itertools.count().__next__

    def __init__(self, max_workers: int, *, name: str = None) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self._max_workers = max_workers
        self._name = str(name or f"ThreadPool-{self.__class__._counter()}")
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._workers: t.Set[Worker] = set()
        self._shutdown_lock = threading.Lock()
        self._is_down = False
        weakref.finalize(self, _stop_workers, self._workers, True)

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
        with self._shutdown_lock:
            if self._is_down:
                raise DeadWorker
            f: Future = Future()
            self._queue.put(Task(f, target, args, kwargs))
            return f

    def shutdown(self, wait=True) -> None:
        with self._shutdown_lock:
            if self._is_down:
                return
            self._is_down = True
            _stop_workers(self._workers, wait=wait)


class TempWorker(Worker):
    IDLE_TIMEOUT = 1

    def __init__(
        self, q: queue.SimpleQueue = None, idle_timeout=IDLE_TIMEOUT, **kwargs: t.Any
    ) -> None:
        super().__init__(q, **kwargs)
        self._idle_timeout = idle_timeout

    def _get_task(self):
        try:
            return self._queue.get(block=False)
        except queue.Empty:
            if self.on_idle:
                self.on_idle()
            try:
                return self._queue.get(timeout=self._idle_timeout)
            except queue.Empty:
                return None


def _discard_worker(executor_ref, w: Worker):
    self = executor_ref()
    if not self:
        return
    with self._idle_lock:
        self._workers.discard(w)
        if self._idle_workers > 0:
            self._idle_workers -= 1


def _inc_idle_workers(executor_ref):
    self = executor_ref()
    if not self:
        return
    with self._idle_lock:
        self._idle_workers += 1


class ThreadPoolExecutor(SimpleThreadPoolExecutor):
    def __init__(
        self,
        max_workers: int = None,
        *,
        idle_timeout=TempWorker.IDLE_TIMEOUT,
        name: str = None,
    ):
        super().__init__(max_workers or self.get_default_max_workers(), name=name)
        self._idle_timeout = idle_timeout
        self._idle_lock = threading.Lock()
        self._idle_workers = 0

    def __enter__(self) -> "ThreadPoolExecutor":
        w = Worker(self._queue, name=f"{self._name}-Worker-0")
        self_ref = weakref.ref(self)
        w.on_idle = lambda: _inc_idle_workers(self_ref)
        self._workers.add(w)
        w.start()
        return self

    @classmethod
    def get_default_max_workers(cls):
        import os

        return min(64, os.cpu_count() * 2)

    def set_max_workers(self, n: int) -> None:
        self._max_workers = n

    def set_idle_timeout(self, timeout: int) -> None:
        self._idle_timeout = timeout

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        with self._shutdown_lock:
            if self._is_down:
                raise DeadWorker

            f: Future = Future()
            self._queue.put(Task(f, target, args, kwargs))

            with self._idle_lock:
                if len(self._workers) < self._max_workers and self._idle_workers == 0:
                    w = TempWorker(
                        self._queue,
                        idle_timeout=self._idle_timeout,
                        name=f"{self._name}-TempWorker-{len(self._workers)}",
                    )
                    self_ref = weakref.ref(self)
                    w.on_idle = lambda: _inc_idle_workers(self_ref)
                    w.future.add_done_callback(lambda _: _discard_worker(self_ref, w))
                    self._workers.add(w)
                    w.start()
                elif self._idle_workers > 0:
                    self._idle_workers -= 1

            return f


_executor: t.Optional[ThreadPoolExecutor] = None
_max_workers: t.Optional[int] = None
_idle_timeout: int = TempWorker.IDLE_TIMEOUT


def set_max_workers(n):
    global _max_workers

    _max_workers = n
    if _executor is not None:
        _executor.set_max_workers(_max_workers)


def set_idle_timeout(timeout):
    global _idle_timeout

    _idle_timeout = timeout
    if _executor is not None:
        _executor.set_idle_timeout(timeout)


def start_executor():
    global _executor

    if _executor is None:
        _executor = ThreadPoolExecutor(_max_workers, idle_timeout=_idle_timeout)
        _executor.__enter__()


def shutdown_executor():
    global _executor

    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


threading._register_atexit(shutdown_executor)  # type: ignore


def go(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> Future:
    start_executor()
    return _executor.submit(target, *args, **kwargs)
