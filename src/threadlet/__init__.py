import itertools
import queue
import threading
import typing
import typing as t
from concurrent.futures import _base

Future = _base.Future


class Task(typing.NamedTuple):
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


def go(target: t.Callable, *args: t.Any, **kwargs: t.Any) -> Future:
    return Task(Future(), target, args, kwargs).start()


class Worker(threading.Thread):
    def __init__(self, q: queue.SimpleQueue = None, **kwargs: t.Any) -> None:
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
        task = Task(Future(), target, args, kwargs)
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
