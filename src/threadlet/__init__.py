import itertools
import queue
import threading
import types
import typing as t
from concurrent.futures import _base

Future = _base.Future

SomeQueue = t.Union[queue.Queue, queue.SimpleQueue]


class Task:
    __slots__ = ("_target", "_args", "_kwargs", "_future")

    def __init__(self, target: t.Callable, *args: t.Any, **kwargs: t.Any) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._future: Future = Future()

    __class_getitem__: classmethod = classmethod(types.GenericAlias)

    @property
    def future(self):
        return self._future

    def __call__(self) -> None:
        if not self._future.set_running_or_notify_cancel():
            return
        try:
            result = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self._future.set_exception(e)
            # Break a reference cycle with the exception 'exc'
            self = None
        else:
            self._future.set_result(result)

    def start(self) -> Future:
        threading.Thread(target=self).start()
        return self._future


class Worker(threading.Thread):
    def __init__(self, q: SomeQueue = None, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self._queue = q or queue.SimpleQueue()

    def __enter__(self) -> "Worker":
        self.start()
        return self

    def __exit__(self, *_) -> t.Any:
        self.stop()
        self.join()
        return False

    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> Future:
        task = Task(target, *args, **kwargs)
        self._queue.put(task)
        return task.future

    def run(self) -> None:
        while True:
            task = self._queue.get()
            if task is None:
                break
            task()
            del task

    def stop(self) -> None:
        if self.is_alive():
            self._queue.put(None)


class SimpleThreadPoolExecutor:
    _counter = itertools.count().__next__

    def __init__(
        self, max_workers: int, queue_limit: int = None, *, name: str = None
    ) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self._max_workers = max_workers
        self._name = str(name or f"ThreadPool-{self.__class__._counter()}")
        self._queue: SomeQueue = (
            queue.Queue(maxsize=queue_limit) if queue_limit else queue.SimpleQueue()
        )
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
        task = Task(target, *args, **kwargs)
        self._queue.put(task)
        return task.future

    def shutdown(self, wait=True) -> None:
        for w in set(self._workers):
            w.stop()
        if wait:
            for w in set(self._workers):
                w.join()
