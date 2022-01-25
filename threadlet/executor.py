import itertools
import logging
import os
import queue
import threading
import typing
import weakref
from concurrent.futures import _base

from .thread import Thread
from .utils import FuturedFunc

logger = logging.getLogger(__name__)

_threads_shutdowns: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_shutdown = False
# Lock that ensures that new workers are not created while the interpreter is
# shutting down. Must be held while mutating _threads_shutdowns and _shutdown.
_global_shutdown_lock = threading.Lock()


def _python_exit():
    global _shutdown
    with _global_shutdown_lock:
        _shutdown = True
    items = tuple(_threads_shutdowns.items())
    for _, shutdown in items:
        shutdown()
    for t, _ in items:
        t.join()


# Register for `_python_exit()` to be called just before joining all
# non-daemon threads. This is used instead of `atexit.register()` for
# compatibility with subinterpreters, which no longer support daemon threads.
# See bpo-39812 for context.
threading._register_atexit(_python_exit)  # type: ignore

# At fork, reinitialize the `_global_shutdown_lock` lock in the child process
if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_global_shutdown_lock.acquire,
        after_in_child=_global_shutdown_lock._at_fork_reinit,  # type: ignore
        after_in_parent=_global_shutdown_lock.release,
    )


class ThreadPoolExecutor(_base.Executor):
    MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
    IDLE_TIMEOUT = 5

    # Used to assign unique thread names when thread_name_prefix is not supplied.
    _counter = itertools.count().__next__

    def __init__(
        self,
        max_workers: typing.Optional[int] = None,
        min_workers: int = 0,
        idle_timeout: typing.Optional[int] = IDLE_TIMEOUT,
        thread_name_prefix: str = "",
        initializer: typing.Optional[typing.Callable] = None,
        initargs: typing.Sequence = (),
        worker_class: typing.Callable = Thread,
    ):
        """Initializes a new ThreadPoolExecutor instance.

        Args:
            max_workers: The maximum number of threads that can be used to execute the given calls.
            idle_timeout: IDLE time each worker can live before exit.
            thread_name_prefix: An optional name prefix to give our threads.
            initializer: A callable used to initialize worker threads.
            initargs: A tuple of arguments to pass to the initializer.
            worker_class: Class to create workers from.
        """
        if max_workers is None:
            max_workers = self.MAX_WORKERS
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")

        if min_workers > max_workers:
            raise ValueError("min_workers must be less(or equal) than max_workers")

        if initializer is not None and not callable(initializer):
            raise TypeError("initializer must be a callable")

        self._max_workers = max_workers
        self._min_workers = min_workers
        self._idle_timeout = idle_timeout
        self._work_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._idle_semaphore = threading.Semaphore(0)
        self._threads: typing.Set[threading.Thread] = set()
        self._futures: typing.Set[_base.Future] = set()
        self._is_broken = False
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._thread_name_prefix = thread_name_prefix or f"ThreadPoolExecutor-{self._counter()}"  # type: ignore
        self._initializer = initializer
        self._initargs = initargs
        self._worker_class = worker_class

    def __enter__(self) -> "ThreadPoolExecutor":
        for _ in range(self._min_workers):
            self._add_thread(idle_timeout=None)
        return self

    def submit(self, fn: typing.Callable, /, *args: typing.Any, **kwargs: typing.Any) -> _base.Future:
        with self._shutdown_lock, _global_shutdown_lock:
            if self._is_broken:
                raise RuntimeError("cannot schedule new futures as workers are broken")
            elif self._shutdown:
                raise RuntimeError("cannot schedule new futures after shutdown")
            elif _shutdown:
                raise RuntimeError("cannot schedule new futures after interpreter shutdown")

            f: _base.Future = _base.Future()
            f.add_done_callback(self._work_done_cb)
            self._work_queue.put_nowait(FuturedFunc(f, fn, args, kwargs))
            self._futures.add(f)
            if not self._idle_semaphore.acquire(blocking=False):
                num_threads = len(self._threads)
                if num_threads < self._max_workers:
                    self._add_thread(idle_timeout=self._idle_timeout, num_threads=num_threads)
            return f

    submit.__doc__ = _base.Executor.submit.__doc__

    def _work_done_cb(self, f: _base.Future) -> None:
        self._futures.discard(f)

    def _add_thread(self, idle_timeout: typing.Optional[int], num_threads: typing.Optional[int] = None) -> None:
        thread_name = f"{(self._thread_name_prefix or self)}_{num_threads or len(self._threads)}"
        t = self._worker_class(name=thread_name, target=self._worker, args=(idle_timeout,))
        t.future.add_done_callback(self._thread_done_cb)
        t.start()
        self._threads.add(t)
        _threads_shutdowns[t] = self._shutdown_thread

    def _thread_done_cb(self, f: _base.Future) -> None:
        if _shutdown:
            self._shutdown = True
        self._idle_semaphore.acquire(blocking=False)
        self._threads.discard(threading.current_thread())
        e = f.exception()
        if e:
            self._is_broken = True
            logger.critical("Exception in worker", exc_info=e)
            self.shutdown(wait=False, cancel_futures=True)

    def _worker(self, idle_timeout: int = None) -> None:
        if self._initializer:
            self._initializer(*self._initargs)

        while True:
            try:
                work_item = self._work_queue.get_nowait()
            except queue.Empty:
                self._idle_semaphore.release()
                try:
                    work_item = self._work_queue.get(timeout=idle_timeout)
                except queue.Empty:
                    return

            if work_item is None:
                return

            try:
                work_item()
            finally:
                # Delete references to object. See issue16284
                del work_item

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        with self._shutdown_lock:
            if cancel_futures:
                for f in frozenset(self._futures):
                    f.cancel()
            if not self._shutdown:
                while True:
                    try:
                        self._work_queue.get_nowait()
                    except queue.Empty:
                        break
                for _ in range(len(self._threads)):
                    self._shutdown_thread()
            self._shutdown = True
        if wait:
            for t in frozenset(self._threads):
                t.join()

    shutdown.__doc__ = _base.Executor.shutdown.__doc__

    def _shutdown_thread(self) -> None:
        self._work_queue.put_nowait(None)
