import contextvars
import operator
import threading
import time

import pytest

from threadlet import Future, TimeoutError
from threadlet.thread import Thread
from threadlet.utils import FuturedFunc

NUMBERS = [1, 2]
EXPECTED_RES = sum(NUMBERS)

ctx_var: contextvars.ContextVar = contextvars.ContextVar("ctx_var")


def test_thread_submit_success0():
    t = Thread(target=sum, args=(NUMBERS,))
    t.start()
    try:
        assert t.future.result(1) == EXPECTED_RES
    finally:
        t.join()
    with pytest.raises(AttributeError):
        t.future.result(1)
    assert threading.active_count() == 1


def test_thread_submit_success1():
    with Thread(target=sum, args=(NUMBERS,)) as t:
        assert t.future.result(1) == EXPECTED_RES
    assert threading.active_count() == 1


def test_thread_submit_success2():
    with Thread.submit(sum, NUMBERS) as t:
        assert t.future.result(1) == EXPECTED_RES
    assert threading.active_count() == 1


def test_thread_submit_no_future():
    with Thread.submit(time.sleep, 1):
        assert threading.active_count() == 2
    assert threading.active_count() == 1


def test_thread_submit_error():
    numbers = [1, 0]
    with Thread.submit(operator.truediv, *numbers) as t:
        with pytest.raises(ZeroDivisionError):
            t.future.result(1)
    assert threading.active_count() == 1


def test_thread_submit_timeout():
    with Thread.submit(time.sleep, 2) as t:
        with pytest.raises(TimeoutError):
            t.future.result(timeout=1)
        assert t.future.result(2) is None
    assert threading.active_count() == 1


def test_contextvar_success():
    x = 1
    ctx_var.set(x)
    with Thread.submit(target=ctx_var.get) as t:
        assert t.future.result(1) == x


def test_contextvar_error():
    f = Future()
    ctx_var.set(1)
    t = threading.Thread(target=FuturedFunc(f, ctx_var.get))
    t.start()
    with pytest.raises(LookupError):
        f.result(1)
    del f
    t.join(1)
    assert not t.is_alive()
