import _thread
import gc
import threading
import time

import pytest


def _threading_setup():
    return _thread._count(), threading._dangling.copy()


def _threading_cleanup(*original_values):
    _MAX_COUNT = 100

    for count in range(_MAX_COUNT):
        values = _thread._count(), threading._dangling
        if values == original_values:
            break

        if not count:
            # Display a warning at the first iteration
            dangling_threads = values[1]
            print(
                f"threading_cleanup() failed to cleanup "
                f"{values[0] - original_values[0]} threads "
                f"(count: {values[0]}, "
                f"dangling: {len(dangling_threads)})"
            )
            for thread in dangling_threads:
                print(f"Dangling thread: {thread!r}")

            # Don't hold references to threads
            dangling_threads = None
        values = None

        time.sleep(0.01)

        for _ in range(3):
            gc.collect()


@pytest.fixture(autouse=True)
def threading_cleanup():
    thread_key = _threading_setup()
    try:
        yield
    finally:
        _threading_cleanup(*thread_key)


@pytest.fixture
def expected_result():
    return object()


class MyError(Exception):
    @classmethod
    def throw(cls):
        raise cls


@pytest.fixture(scope="session")
def error_class():
    return MyError
