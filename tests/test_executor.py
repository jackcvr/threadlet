import threading

import pytest

from threadlet import SimpleThreadPoolExecutor

MAX_WORKERS_VALUES = (1, 2, 4)


def test_executor_names():
    for _ in range(2):
        with SimpleThreadPoolExecutor(1) as tpe:
            for w in tpe.workers:
                assert w.name.startswith("ThreadPool-") and "-Worker-" in w.name


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_success(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        assert threading.active_count() == max_workers + initial_threads_count
        f = tpe.submit(lambda: expected_result)
        assert f.result() is expected_result
    assert threading.active_count() == initial_threads_count


def test_executor_fail(errors):
    initial_threads_count = threading.active_count()
    max_workers = 2
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        assert threading.active_count() == max_workers + initial_threads_count
        f = tpe.submit(errors.func)
        with pytest.raises(errors.exc):
            f.result()
        assert threading.active_count() == max_workers + initial_threads_count


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_max_workers(expected_result, max_workers):
    initial_threads_count = threading.active_count()
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        for _ in range(max_workers * 10):
            tpe.submit(lambda: expected_result)
        assert threading.active_count() == max_workers + initial_threads_count
    assert threading.active_count() == initial_threads_count
