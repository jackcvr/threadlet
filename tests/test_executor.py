import operator
import threading
import time
from concurrent import futures

import pytest

from threadlet import TimeoutError
from threadlet.executor import BrokenThreadPool, ThreadPoolExecutor


def test_executor_shutdown():
    max_workers = 4
    with ThreadPoolExecutor(max_workers, idle_timeout=5) as tpe:
        for _ in range(max_workers):
            tpe.submit(time.sleep, 0.1)
        assert threading.active_count() == max_workers + 1
    assert threading.active_count() == 1


@pytest.mark.parametrize("max_workers", (1, 2, 3, 4))
def test_executor_submit_success(max_workers):
    numbers = [1, 2]
    expected_res = sum(numbers)
    with ThreadPoolExecutor(max_workers) as tpe:
        f = tpe.submit(sum, numbers)
        assert f.result(1) == expected_res


@pytest.mark.parametrize("max_workers", (1, 2, 3, 4))
def test_executor_submit_error(max_workers):
    numbers = [1, 0]
    with ThreadPoolExecutor(max_workers) as tpe:
        f = tpe.submit(operator.truediv, *numbers)
        with pytest.raises(ZeroDivisionError):
            f.result()
        del f


@pytest.mark.parametrize("max_workers", (1, 2))
def test_executor_submit_timeout(max_workers):
    with ThreadPoolExecutor(max_workers) as tpe:
        f = tpe.submit(time.sleep, 2)
        with pytest.raises(TimeoutError):
            f.result(timeout=1)
        assert f.result(timeout=2) is None


def test_executor_worker_error():
    def raise_init_error():
        raise RuntimeError("init")

    with ThreadPoolExecutor(1, initializer=raise_init_error) as tpe:
        f = tpe.submit(time.sleep, 2)
        with pytest.raises(BrokenThreadPool):
            f.result(1)
        del f


@pytest.mark.parametrize("max_workers", (3, 4))
def test_executor_idle_timeout_none(max_workers):
    with ThreadPoolExecutor(max_workers, idle_timeout=None) as tpe:
        for _ in range(max_workers):
            tpe.submit(time.sleep, 0.1)
        assert threading.active_count() == max_workers + 1
        time.sleep(1)
        assert threading.active_count() == max_workers + 1


@pytest.mark.parametrize("max_workers", (3, 4))
def test_executor_idle_timeout(max_workers):
    idle_timeout = 1
    work_time = 0.5
    with ThreadPoolExecutor(max_workers, idle_timeout=idle_timeout) as tpe:
        assert threading.active_count() == 1
        for _ in range(2):
            for _ in range(max_workers):
                tpe.submit(time.sleep, work_time)
            assert threading.active_count() == max_workers + 1
            time.sleep(work_time + idle_timeout + 1)
            assert threading.active_count() == 1


@pytest.mark.parametrize("max_workers", (1, 2, 3, 4))
def test_executor_min_workers(max_workers):
    idle_timeout = 1
    work_time = 0.5
    min_workers = max_workers - 1
    with ThreadPoolExecutor(max_workers, min_workers=min_workers, idle_timeout=idle_timeout) as tpe:
        assert threading.active_count() == min_workers + 1
        for _ in range(max_workers):
            tpe.submit(time.sleep, work_time)
        assert threading.active_count() == max_workers + 1
        time.sleep(work_time + idle_timeout + 1)
        assert threading.active_count() == min_workers + 1


@pytest.mark.parametrize("max_workers", (1, 2, 3, 4))
def test_executor_max_workers(max_workers):
    idle_timeout = 1
    work_time = 0.1
    task_limit = max_workers * 10

    def task():
        nonlocal done_tasks
        time.sleep(work_time)
        done_tasks += 1

    with ThreadPoolExecutor(max_workers, idle_timeout=idle_timeout) as tpe:
        assert threading.active_count() == 1

        done_tasks = 0
        fs = []
        for _ in range(task_limit):
            fs.append(tpe.submit(task))

        assert threading.active_count() == max_workers + 1
        futures.wait(fs)
        assert threading.active_count() == max_workers + 1
        time.sleep(work_time + idle_timeout + 1)
        assert threading.active_count() == 1
        assert done_tasks == task_limit
