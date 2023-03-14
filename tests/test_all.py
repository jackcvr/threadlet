import operator
import threading
import time

import pytest

from threadlet import SimpleThreadPoolExecutor, Task, ThreadPoolExecutor, TimeoutError, Worker, wait

MAX_WORKERS_VALUES = (1, 2, 4)


@pytest.fixture
def expected_result():
    return object()


def test_task_run(expected_result):
    f = Task.run(lambda: expected_result)
    assert f.result() is expected_result


def test_worker(expected_result):
    with Worker() as w:
        f = w.submit(lambda: expected_result)
        assert f.result() is expected_result
    assert w.join()


def test_worker_names():
    for _ in range(2):
        with Worker() as w:
            assert w.thread.name.startswith("Worker-")


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_simple_thread_pool_executor(expected_result, max_workers):
    assert threading.active_count() == 1
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        assert threading.active_count() == max_workers + 1
        f = tpe.submit(lambda: expected_result)
        assert f.result() is expected_result
    assert threading.active_count() == 1


def test_simple_thread_pool_executor_names():
    for _ in range(2):
        with SimpleThreadPoolExecutor(2) as tpe:
            for w in tpe.workers:
                name = w.thread.name
                assert name.startswith("ThreadPool-") and "-Worker-" in name


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_simple_thread_pool_executor_max_workers(expected_result, max_workers):
    assert threading.active_count() == 1
    with SimpleThreadPoolExecutor(max_workers) as tpe:
        fs = []
        for _ in range(max_workers * 10):
            fs.append(tpe.submit(lambda: expected_result))
        assert threading.active_count() == max_workers + 1
        wait(fs)
        assert threading.active_count() == max_workers + 1
    assert threading.active_count() == 1


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_thread_pool_executor(expected_result, max_workers):
    with ThreadPoolExecutor(max_workers) as tpe:
        time.sleep(0.1)
        assert threading.active_count() == 1
        f = tpe.submit(lambda: expected_result)
        assert f.result() is expected_result
    assert len(tpe._workers) == 0


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_thread_pool_executor_submit_error(max_workers):
    numbers = [1, 0]
    with ThreadPoolExecutor(max_workers) as tpe:
        f = tpe.submit(operator.truediv, *numbers)
        with pytest.raises(ZeroDivisionError):
            f.result()
        del f


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_thread_pool_executor_submit_timeout(max_workers):
    with ThreadPoolExecutor(max_workers) as tpe:
        f = tpe.submit(time.sleep, 0.2)
        with pytest.raises(TimeoutError):
            f.result(0.1)
        assert f.result(1) is None


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_thread_pool_executor_idle_timeout_none(max_workers):
    with ThreadPoolExecutor(max_workers, idle_timeout=None) as tpe:
        for _ in range(max_workers):
            tpe.submit(time.sleep, 0.1)
        assert threading.active_count() == max_workers + 1
        time.sleep(0.2)
        assert threading.active_count() == max_workers + 1


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_thread_pool_executor_idle_timeout(max_workers):
    idle_timeout = 0.5
    work_time = 0.1
    with ThreadPoolExecutor(max_workers, idle_timeout=idle_timeout) as tpe:
        for _ in range(2):
            fs = set()
            for _ in range(max_workers):
                fs.add(tpe.submit(time.sleep, work_time))
            assert threading.active_count() == max_workers + 1
            wait(fs)
            time.sleep(idle_timeout + 0.1)
            assert threading.active_count() == 1


@pytest.mark.parametrize("max_workers", MAX_WORKERS_VALUES)
def test_executor_min_workers(max_workers):
    idle_timeout = 0.5
    work_time = 0.1
    min_workers = max_workers - 1
    with ThreadPoolExecutor(max_workers, min_workers=min_workers, idle_timeout=idle_timeout) as tpe:
        fs = set()
        for _ in range(max_workers):
            fs.add(tpe.submit(time.sleep, work_time))
        assert threading.active_count() == max_workers + 1
        wait(fs)
        time.sleep(idle_timeout + 0.1)
        assert threading.active_count() == min_workers + 1
