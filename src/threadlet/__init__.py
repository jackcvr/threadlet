import itertools
import os
import queue
import threading
import typing
import weakref
from concurrent.futures import TimeoutError  # noqa
from concurrent.futures import _base

_threads_queues: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_shutdown = False
# Lock that ensures that new workers are not created while the interpreter is
# shutting down. Must be held while mutating _threads_queues and _shutdown.
_global_shutdown_lock = threading.Lock()


def _python_exit():
    global _shutdown
    with _global_shutdown_lock:
        _shutdown = True
    items = list(_threads_queues.items())
    for _, q in items:
        q.put(None)
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


def _worker(executor_reference, work_queue, initializer, initargs, idle_timeout):
    if initializer is not None:
        try:
            initializer(*initargs)
        except BaseException:
            _base.LOGGER.critical("Exception in initializer:", exc_info=True)
            executor = executor_reference()
            if executor is not None:
                executor._initializer_failed()
            return
    try:
        while True:
            try:
                work_item = work_queue.get_nowait()
            except queue.Empty:
                # attempt to increment idle count
                executor = executor_reference()
                if executor is not None:
                    executor._idle_semaphore.release()
                del executor
                try:
                    work_item = work_queue.get(timeout=idle_timeout)
                except queue.Empty:
                    return

            if work_item is None:
                executor = executor_reference()
                # Exit if:
                #   - The interpreter is shutting down OR
                #   - The executor that owns the worker has been collected OR
                #   - The executor that owns the worker has been shutdown.
                if _shutdown or executor is None or executor._shutdown:
                    # Flag the executor as shutting down as early as possible if it
                    # is not gc-ed yet.
                    if executor is not None:
                        executor._shutdown = True
                    # Notice other workers
                    work_queue.put(None)
                    return
                del executor

            try:
                work_item()
            finally:
                # Delete references to object. See issue16284
                del work_item
    except BaseException:
        _base.LOGGER.critical("Exception in worker", exc_info=True)
    finally:
        executor = executor_reference()
        if executor is not None:
            executor._idle_semaphore.acquire(blocking=False)
            executor._threads.discard(threading.current_thread())
        del executor


class BrokenThreadPool(_base.BrokenExecutor):
    """
    Raised when a worker thread in a ThreadPoolExecutor failed initializing.
    """


class FuturedFunc(typing.NamedTuple):
    future: _base.Future
    func: typing.Callable
    args: typing.Any = None
    kwargs: typing.Any = None

    def __call__(self, *args, **kwargs):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            args = args or self.args or ()
            kwargs = kwargs or self.kwargs or {}
            res = self.func(*args, **kwargs)
        except BaseException as e:
            self.future.set_exception(e)
            # Break a reference cycle with the exception 'exc'
            self = None
        else:
            self.future.set_result(res)


class ThreadPoolExecutor(_base.Executor):
    # ThreadPoolExecutor is often used to:
    # * CPU bound task which releases GIL
    # * I/O bound task (which releases GIL, of course)
    #
    # We use cpu_count + 4 for both types of tasks.
    # But we limit it to 32 to avoid consuming surprisingly large resource
    # on many core machine.
    MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
    IDLE_TIMEOUT = 2

    # Used to assign unique thread names when thread_name_prefix is not supplied.
    _counter = itertools.count().__next__

    def __init__(
        self,
        max_workers=None,
        min_workers=0,
        idle_timeout=IDLE_TIMEOUT,
        thread_name_prefix="",
        initializer=None,
        initargs=(),
        worker_class=threading.Thread,
    ):
        """Initializes a new ThreadPoolExecutor instance.
        Args:
            max_workers: The maximum number of threads that can be used to
                execute the given calls.
            thread_name_prefix: An optional name prefix to give our threads.
            initializer: A callable used to initialize worker threads.
            initargs: A tuple of arguments to pass to the initializer.
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
        self._work_queue = queue.SimpleQueue()
        self._idle_semaphore = threading.Semaphore(0)
        self._threads = set()
        self._broken = False
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._thread_name_prefix = thread_name_prefix or ("ThreadPoolExecutor-%d" % self._counter())
        self._initializer = initializer
        self._initargs = initargs
        self._worker_class = worker_class

    def __enter__(self):
        for _ in range(self._min_workers):
            self._add_thread(idle_timeout=None)
        return self

    def submit(self, fn, /, *args, **kwargs):
        with self._shutdown_lock, _global_shutdown_lock:
            if self._broken:
                raise BrokenThreadPool(self._broken)

            if self._shutdown:
                raise RuntimeError("cannot schedule new futures after shutdown")
            if _shutdown:
                raise RuntimeError("cannot schedule new futures after " "interpreter shutdown")

            f = _base.Future()
            self._work_queue.put(FuturedFunc(f, fn, args, kwargs))
            self._adjust_thread_count()
            return f

    submit.__doc__ = _base.Executor.submit.__doc__

    def _adjust_thread_count(self):
        # if idle threads are available, don't spin new threads
        if self._idle_semaphore.acquire(blocking=False):
            return

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            self._add_thread(self._idle_timeout, num_threads)

    def _add_thread(self, idle_timeout, num_threads=None):
        # When the executor gets lost, the weakref callback will wake up
        # the worker threads.
        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        thread_name = f"{self._thread_name_prefix or self}_{num_threads or len(self._threads)}"
        t = self._worker_class(
            name=thread_name,
            target=_worker,
            args=(weakref.ref(self, weakref_cb), self._work_queue, self._initializer, self._initargs, idle_timeout),
        )
        t.start()
        self._threads.add(t)
        _threads_queues[t] = self._work_queue

    def _initializer_failed(self):
        with self._shutdown_lock:
            self._broken = "A thread initializer failed, the thread pool " "is not usable anymore"
            # Drain work queue and mark pending futures failed
            while True:
                try:
                    work_item = self._work_queue.get_nowait()
                except queue.Empty:
                    break
                if work_item is not None:
                    work_item.future.set_exception(BrokenThreadPool(self._broken))

    def shutdown(self, wait=True, *, cancel_futures=False):
        with self._shutdown_lock:
            self._shutdown = True
            if cancel_futures:
                # Drain all work items from the queue, and then cancel their
                # associated futures.
                while True:
                    try:
                        work_item = self._work_queue.get_nowait()
                    except queue.Empty:
                        break
                    if work_item is not None:
                        work_item.future.cancel()

            # Send a wake-up to prevent threads calling
            # _work_queue.get(block=True) from permanently blocking.
            self._work_queue.put(None)
        if wait:
            for t in frozenset(self._threads):
                t.join()

    shutdown.__doc__ = _base.Executor.shutdown.__doc__
