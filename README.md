# threadlet

[![PyPI - Version](https://img.shields.io/pypi/v/threadlet.svg)](https://pypi.org/project/threadlet)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/threadlet.svg)](https://pypi.org/project/threadlet)

* **Task** is an entity intended to be run in a thread. Task contains a function and a `Future` object to store a result of the function execution.
You can start a task in a separate thread using `spawn` or `go` functions, see [Usage](#usage).
* **Worker** is a thread with a loop over incoming tasks.
* **SimpleThreadPoolExecutor** is a simple and efficient variant of `concurrent.futures.ThreadPoolExecutor` which spawns all the threads at the beginning.
* **ThreadPoolExecutor** is an adaptive variant of the `concurrent.futures.ThreadPoolExecutor` which automatically spawns and shutdowns threads accordingly to your demand.

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [Benchmarks](#benchmarks)
- [License](#license)

## Installation

```console
pip install threadlet
```

## Usage

```python
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


# run task in an adaptive thread pool executor
# which is going to be started automatically at first `go` call and shut down at application exit
future = go(calc, 2)
assert future.result() == 4
# is equivalent to:
with ThreadPoolExecutor() as tpe:
    future = tpe.submit(calc, 2)
    assert future.result() == 4

# create a task and start it in a separate thread
future = spawn(calc, 2)
assert future.result() == 4
# is equivalent to:
task = Task(Future(), calc, [2], {})
threading.Thread(target=task.run).start()
assert task.future.result() == 4

# spawns one thread(worker) to sequentially handle all submitted functions
with Worker() as w:
    f1 = w.submit(calc, 3)
    f2 = w.submit(calc, 4)
    assert f1.result() == 6
    assert f2.result() == 8

# spawns 4 threads(workers) to handle all tasks in parallel
with SimpleThreadPoolExecutor(4) as tpe:
    future = tpe.submit(calc, 5)
    assert future.result() == 10
```


## Benchmarks

* submit: call `submit` 1 mil times.
* e2e[N] (end to end[N workers]): submits 1 mil functions to thread pool executor with N workers
in a separate thread and consumes results in main thread.

```
concurrent.futures.thread.ThreadPoolExecutor submit: time=10.38s size=0.11mb, peak=28.26mb
                threadlet.ThreadPoolExecutor submit: time= 2.86s size=0.11mb, peak=19.53mb
          threadlet.SimpleThreadPoolExecutor submit: time= 2.67s size=0.10mb, peak=24.75mb

concurrent.futures.thread.ThreadPoolExecutor e2e[1]: time=22.38s size=0.12mb, peak=65.72mb
                threadlet.ThreadPoolExecutor e2e[1]: time= 3.35s size=0.12mb, peak=38.68mb
          threadlet.SimpleThreadPoolExecutor e2e[1]: time= 3.10s size=0.11mb, peak=45.29mb

concurrent.futures.thread.ThreadPoolExecutor e2e[2]: time=25.25s size=0.14mb, peak=56.03mb
                threadlet.ThreadPoolExecutor e2e[2]: time= 3.38s size=0.14mb, peak=72.27mb
          threadlet.SimpleThreadPoolExecutor e2e[2]: time= 3.31s size=0.13mb, peak=56.88mb

concurrent.futures.thread.ThreadPoolExecutor e2e[4]: time= 8.15s size=0.18mb, peak=51.52mb
                threadlet.ThreadPoolExecutor e2e[4]: time= 3.36s size=0.18mb, peak=68.47mb
          threadlet.SimpleThreadPoolExecutor e2e[4]: time= 3.11s size=0.17mb, peak=70.81mb

concurrent.futures.thread.ThreadPoolExecutor e2e[8]: time= 8.45s size=0.25mb, peak=64.48mb
                threadlet.ThreadPoolExecutor e2e[8]: time= 3.44s size=0.26mb, peak=63.17mb
          threadlet.SimpleThreadPoolExecutor e2e[8]: time= 3.43s size=0.23mb, peak=62.17mb
```

## License

`threadlet` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
