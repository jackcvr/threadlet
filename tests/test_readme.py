import threading
from threadlet import Task, Worker, SimpleThreadPoolExecutor


def test_readme_sample():
    def calc(x):
        return x * 2

    # run task asynchronously in a separate thread
    future = Task(calc, 2).start()
    assert future.result() == 4

    # ^ equivalent to:
    task = Task(calc, 2)
    threading.Thread(target=task).start()
    assert task.future.result() == 4

    # spawns one thread to sequentially handle all submitted functions
    with Worker() as w:
        f1 = w.submit(calc, 3)
        f2 = w.submit(calc, 4)
        assert f1.result() == 6
        assert f2.result() == 8

    # spawns 4 threads to handle all tasks in parallel
    with SimpleThreadPoolExecutor(4) as tpe:
        future = tpe.submit(calc, 5)
        assert future.result() == 10
