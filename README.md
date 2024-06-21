# threadlet

[![PyPI - Version](https://img.shields.io/pypi/v/threadlet.svg)](https://pypi.org/project/threadlet)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/threadlet.svg)](https://pypi.org/project/threadlet)

```python
from threadlet import spawn, go


def plus2(n):
  return n + 2


future = spawn(plus2, 1)  # run in thread
assert future.result() == 3

future = go(plus2, 2)  # run in adaptive thread pool executor
assert future.result() == 4
```

* **spawn** is a helper which runs your function in a separate thread and returns `Future`.
* **go** is a similar helper, but runs task in adaptive thread pool executor.
* **Task** is an object for encapsulating some function, its arguments and `Future` to storing its result.
* **Worker** is a thread with a loop for executing incoming tasks.
* **SimpleThreadPoolExecutor** is a simple variant of `concurrent.futures.ThreadPoolExecutor` which spawns all the threads at the beginning.
* **ThreadPoolExecutor** is an adaptive variant of the `concurrent.futures.ThreadPoolExecutor` which automatically spawns and shutdowns threads depending on load.

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


# execute function in an adaptive thread pool executor
# which is going to be started automatically at first `go` call and shut down at application exit
future = go(calc, 2)
assert future.result() == 4
# is equivalent to:
with ThreadPoolExecutor() as tpe:
    future = tpe.submit(calc, 2)
    assert future.result() == 4

# execute function in a separate thread:
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

* submit: submits 1 million futures.
* e2e[N] (end to end[N workers]): submits 1 million futures using N workers and consumes results in a separate thread.

```
concurrent.futures.thread.ThreadPoolExecutor submit: time=12.94s size=0.04mb, peak=43.61mb
                threadlet.ThreadPoolExecutor submit: time= 2.89s size=0.04mb, peak=20.35mb
          threadlet.SimpleThreadPoolExecutor submit: time= 2.72s size=0.04mb, peak=24.49mb

concurrent.futures.thread.ThreadPoolExecutor e2e[1]: time=15.80s size=0.04mb, peak=28.56mb
                threadlet.ThreadPoolExecutor e2e[1]: time= 4.32s size=0.02mb, peak=19.48mb
          threadlet.SimpleThreadPoolExecutor e2e[1]: time= 4.23s size=0.02mb, peak=26.45mb

concurrent.futures.thread.ThreadPoolExecutor e2e[2]: time=33.36s size=0.07mb, peak=32.00mb
                threadlet.ThreadPoolExecutor e2e[2]: time= 4.35s size=0.02mb, peak=35.83mb
          threadlet.SimpleThreadPoolExecutor e2e[2]: time= 4.18s size=0.02mb, peak=41.81mb

concurrent.futures.thread.ThreadPoolExecutor e2e[4]: time= 7.49s size=0.11mb, peak=42.97mb
                threadlet.ThreadPoolExecutor e2e[4]: time= 4.37s size=0.03mb, peak=28.21mb
          threadlet.SimpleThreadPoolExecutor e2e[4]: time= 4.30s size=0.02mb, peak=39.81mb

concurrent.futures.thread.ThreadPoolExecutor e2e[8]: time= 7.30s size=0.21mb, peak=41.04mb
                threadlet.ThreadPoolExecutor e2e[8]: time= 4.49s size=0.05mb, peak=29.20mb
          threadlet.SimpleThreadPoolExecutor e2e[8]: time= 4.18s size=0.03mb, peak=38.36mb
```

## License

`threadlet` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
