import contextvars
import threading
import typing
from concurrent.futures import _base
from functools import partial

from .utils import FuturedFunc


class Thread(threading.Thread):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self._future: _base.Future = _base.Future()
        if self._target:
            self._target: typing.Callable = partial(
                contextvars.copy_context().run,
                FuturedFunc(future=self._future, func=self._target, args=self._args, kwargs=self._kwargs),
            )
            self._args: typing.Any = ()
            self._kwargs: typing.Any = {}

    def __enter__(self):
        if not self._started.is_set():
            self.start()
        return self

    def __exit__(self, *_):
        self.join()

    @property
    def future(self):
        return self._future

    def join(self, *args, **kwargs):
        try:
            super().join(*args, **kwargs)
        finally:
            if hasattr(self, "_future"):
                del self._future

    @classmethod
    def submit(cls, target: typing.Callable, *args: typing.Any, **kwargs: typing.Any) -> "Thread":
        t = cls(target=target, args=args, kwargs=kwargs)
        t.start()
        return t
