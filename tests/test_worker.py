import pytest

from threadlet import Worker


def add(x, y):
    return x + y


def test_worker_lifetime():
    with Worker() as w:
        assert w.is_alive()
    assert not w.is_alive()


def test_worker_success():
    with Worker() as w:
        f1 = w.submit(add, 1, 1)
        assert f1.result() == 2


def test_worker_fail(errors):
    with Worker() as w:
        f = w.submit(errors.func)
        with pytest.raises(errors.exc):
            f.result()
        assert w.is_alive()
