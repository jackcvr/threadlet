import threading
import time

import pytest

from threadlet import (
    SimpleThreadPoolExecutor,
    ThreadPoolExecutor,
    go,
    wait,
    shutdown_executor,
)

MAX_WORKERS_VALUES = (1, 2, 4)


def test_executor_names():
    for _ in range(2):
        with SimpleThreadPoolExecutor(1) as tpe:
            for w in tpe.workers:
                assert w.name.startswith("ThreadPool-") and "-Worker-" in w.name


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_simple_executor_submit_success(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        assert threading.active_count() == initial_threads_count + max_workers
        f = tpe.submit(lambda: expected_result)
        assert f.result() is expected_result
    assert threading.active_count() == initial_threads_count


def test_simple_executor_submit_error(error_class):
    initial_threads_count = threading.active_count()
    max_workers = 2
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        assert threading.active_count() == initial_threads_count + max_workers
        f = tpe.submit(error_class.throw)
        with pytest.raises(error_class):
            f.result()
        assert threading.active_count() == initial_threads_count + max_workers


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_simple_executor_max_workers(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        for _ in range(max_workers * 10):
            tpe.submit(lambda: expected_result)
        assert threading.active_count() == initial_threads_count + max_workers
    assert threading.active_count() == initial_threads_count


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_submit_success(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with ThreadPoolExecutor(max_workers, idle_timeout=1) as tpe:
        assert threading.active_count() == initial_threads_count + 1
        f = tpe.submit(lambda: expected_result)
        assert f.result() is expected_result
        time.sleep(1.5)
        assert threading.active_count() == initial_threads_count + 1
    assert threading.active_count() == initial_threads_count


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_workers_lifetime_sequential(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with ThreadPoolExecutor(max_workers, idle_timeout=1) as tpe:
        assert threading.active_count() == initial_threads_count + 1
        for _ in range(max_workers):
            tpe.submit(lambda: expected_result).result()
        assert threading.active_count() == initial_threads_count + 1
    assert threading.active_count() == initial_threads_count


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_workers_lifetime_parallel(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with ThreadPoolExecutor(max_workers, idle_timeout=1) as tpe:
        assert threading.active_count() == initial_threads_count + 1
        for _ in range(2):
            fs = set()
            for _ in range(max_workers):
                fs.add(tpe.submit(time.sleep, 1))
            assert threading.active_count() == initial_threads_count + max_workers
            wait(fs)
            assert threading.active_count() == initial_threads_count + max_workers
            time.sleep(1.5)
            assert threading.active_count() == initial_threads_count + 1
    assert threading.active_count() == initial_threads_count


@pytest.mark.parametrize(
    "executor_class", [SimpleThreadPoolExecutor, ThreadPoolExecutor]
)
def test_executor_auto_shutdown(executor_class):
    initial_threads_count = threading.active_count()
    executor = executor_class(1)
    executor.__enter__()
    executor.submit(lambda: None).result()
    assert threading.active_count() == initial_threads_count + 1
    del executor
    assert threading.active_count() == initial_threads_count


def test_go_sequential(expected_result):
    initial_threads_count = threading.active_count()
    assert go(lambda: expected_result).result() is expected_result
    assert threading.active_count() == initial_threads_count + 1
    assert go(lambda: expected_result).result() is expected_result
    assert threading.active_count() == initial_threads_count + 1
    shutdown_executor()
    assert threading.active_count() == initial_threads_count


def test_go_parallel(expected_result):
    initial_threads_count = threading.active_count()
    max_workers = MAX_WORKERS_VALUES[-1]
    fs = set()
    for _ in range(max_workers):
        fs.add(go(lambda: time.sleep(1)))
    assert threading.active_count() == initial_threads_count + max_workers
    wait(fs)
    assert threading.active_count() == initial_threads_count + max_workers
    time.sleep(1.5)
    assert threading.active_count() == initial_threads_count + 1
    shutdown_executor()
    assert threading.active_count() == initial_threads_count
