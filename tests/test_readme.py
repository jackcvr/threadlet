import threading
from threadlet import spawn, Task, Future, Worker, SimpleThreadPoolExecutor


def calc(x):
    return x * 2


def test_task_go():
    future = spawn(calc, 2)
    assert future.result() == 4


def test_task_start():
    future = Task(Future(), calc, [2], {}).start()
    assert future.result() == 4


def test_task_thread_start():
    task = Task(Future(), calc, [2], {})
    threading.Thread(target=task.run).start()
    assert task.future.result() == 4


def test_worker():
    # spawns one thread to sequentially handle all submitted functions
    with Worker() as w:
        f1 = w.submit(calc, 3)
        f2 = w.submit(calc, 4)
        assert f1.result() == 6
        assert f2.result() == 8


def test_executor():
    # spawns 4 threads to handle all tasks in parallel
    with SimpleThreadPoolExecutor(4) as tpe:
        future = tpe.submit(calc, 5)
        assert future.result() == 10
