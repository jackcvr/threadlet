import operator

import pytest

from threadlet import Future
from threadlet.utils import FuturedFunc

NUMBERS = [1, 2]
EXPECTED_RES = sum(NUMBERS)


def get_sum(x, y):
    return x + y


def test_futured_func_single_run():
    f = Future()
    futured_get_sum = FuturedFunc(f, get_sum, NUMBERS)
    futured_get_sum()
    assert f.result(1) == EXPECTED_RES


def test_futured_func_single_run_overridden_args():
    new_numbers = [n + 1 for n in NUMBERS]
    new_expected_res = get_sum(*new_numbers)
    assert new_expected_res != EXPECTED_RES

    f = Future()
    futured_get_sum = FuturedFunc(f, get_sum, NUMBERS)
    futured_get_sum(*new_numbers)
    assert f.result(1) == new_expected_res


def test_futured_func_multiple_run():
    f = Future()
    futured_get_sum = FuturedFunc(f, get_sum, NUMBERS)
    futured_get_sum()
    assert f.result(1) == EXPECTED_RES
    with pytest.raises(RuntimeError, match="unexpected state"):
        futured_get_sum()


def test_futured_func_error():
    f = Future()
    futured_div = FuturedFunc(f, operator.truediv, [1, 0])
    futured_div()
    with pytest.raises(ZeroDivisionError):
        f.result(1)
