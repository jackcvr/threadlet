import abc
import itertools
import threading
import typing as t
from concurrent.futures import _base
from contextlib import AbstractContextManager

_counter = itertools.count().__next__


class BaseWorker(AbstractContextManager):
    def __init__(self, *, name=None, **kwargs: t.Any) -> None:
        name = str(name or self.newname())
        self._thread = threading.Thread(target=self._run_forever, name=name, **kwargs)

    @property
    def thread(self) -> threading.Thread:
        return self._thread

    def __enter__(self) -> "BaseWorker":
        self.start()
        return self

    def __exit__(self, *_) -> t.Any:
        self.stop()
        self.join()
        return False

    @staticmethod
    def newname(template="Worker-{}"):
        return template.format(_counter())

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        if self._thread.is_alive():
            self._stop()

    def is_alive(self):
        return self._thread.is_alive()

    def join(self, timeout=None) -> bool:
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive()

    def wait(self, timeout=None):
        if not self.join(timeout):
            raise TimeoutError(f"Worker {self} did not stop after {timeout} seconds")

    @abc.abstractmethod
    def _run_forever(self) -> None:
        ...

    @abc.abstractmethod
    def _stop(self) -> None:
        ...


class BaseThreadPoolExecutor(AbstractContextManager):
    def __enter__(self) -> "BaseThreadPoolExecutor":
        return self

    def __exit__(self, *_) -> t.Any:
        self.shutdown(wait=True)
        return False

    @abc.abstractmethod
    def submit(self, target: t.Callable, /, *args: t.Any, **kwargs: t.Any) -> _base.Future:
        ...

    @abc.abstractmethod
    def shutdown(self, wait=True, *, cancel_futures=False) -> None:
        ...
