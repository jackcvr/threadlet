import time

import pytest

from threadlet import go


def test_task_success(expected_result):
    f = go(lambda: expected_result)
    assert f.result() is expected_result


def test_task_fail(errors):
    f = go(errors.func)
    with pytest.raises(errors.exc):
        f.result()


def test_task_timeout():
    f = go(lambda: time.sleep(2))
    with pytest.raises(TimeoutError):
        f.result(1)
