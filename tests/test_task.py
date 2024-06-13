import time

import pytest

from threadlet import Task


def test_task_success(expected_result):
    f = Task(lambda: expected_result).start()
    assert f.result() is expected_result


def test_task_fail(errors):
    f = Task(errors.func).start()
    with pytest.raises(errors.exc):
        f.result()


def test_task_timeout():
    f = Task(lambda: time.sleep(2)).start()
    with pytest.raises(TimeoutError):
        f.result(1)
