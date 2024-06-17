import time

import pytest

from threadlet import Worker, TempWorker, DeadWorker


def add(x, y):
    return x + y


def test_worker_lifetime():
    with Worker() as w:
        assert w.is_alive()
        assert w.future.running()
    assert not w.is_alive()
    assert w.future.done()


def test_temp_worker_lifetime():
    with TempWorker(idle_timeout=1) as w:
        assert w.is_alive()
        time.sleep(1.5)
        assert not w.is_alive()
        with pytest.raises(DeadWorker):
            w.submit(add, 1, 1)


@pytest.mark.parametrize("worker_class", (Worker, TempWorker))
def test_any_worker_submit_success(worker_class):
    with worker_class() as w:
        f1 = w.submit(add, 1, 1)
        assert f1.result() == 2
    with pytest.raises(DeadWorker):
        w.submit(add, 1, 1)


@pytest.mark.parametrize("worker_class", (Worker, TempWorker))
def test_any_worker_submit_error(error_class, worker_class):
    with worker_class() as w:
        f = w.submit(error_class.throw)
        with pytest.raises(error_class):
            f.result()
        assert w.is_alive()
