import threading
from threadlet import (
    spawn,
    go,
    Future,
    Task,
    Worker,
    SimpleThreadPoolExecutor,
    ThreadPoolExecutor,
)


def calc(x):
    return x * 2


def test_go():
    future = go(calc, 2)
    assert future.result() == 4
    with ThreadPoolExecutor() as tpe:
        future = tpe.submit(calc, 2)
        assert future.result() == 4


def test_spawn():
    future = spawn(calc, 2)
    assert future.result() == 4
    task = Task(Future(), calc, [2], {})
    threading.Thread(target=task.run).start()
    assert task.future.result() == 4


def test_worker():
    with Worker() as w:
        f1 = w.submit(calc, 3)
        f2 = w.submit(calc, 4)
        assert f1.result() == 6
        assert f2.result() == 8


def test_simple_executor():
    with SimpleThreadPoolExecutor(4) as tpe:
        future = tpe.submit(calc, 5)
        assert future.result() == 10
