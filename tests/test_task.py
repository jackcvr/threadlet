import time

import pytest

from threadlet import spawn


def test_task_success(expected_result):
    f = spawn(lambda: expected_result)
    assert f.result() is expected_result


def test_task_error(error_class):
    f = spawn(error_class.throw)
    with pytest.raises(error_class):
        f.result()


def test_task_timeout():
    f = spawn(lambda: time.sleep(2))
    with pytest.raises(TimeoutError):
        f.result(1)
    f.result()
