# threadlet

[![PyPI - Version](https://img.shields.io/pypi/v/threadlet.svg)](https://pypi.org/project/threadlet)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/threadlet.svg)](https://pypi.org/project/threadlet)

* **Task** is an entity intended to be run in a thread. Task contains a function and a `Future` object to store a result of the function execution.
* **Worker** is a thread with a loop over incoming tasks.
* **SimpleThreadPoolExecutor** is a more efficient variant of the `concurrent.futures.ThreadPoolExecutor` which spawns all the threads at the beginning.

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Usage](#usage)

## Installation

```console
pip install threadlet
```

## License

`threadlet` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Usage

```python
from threadlet import go, Worker, SimpleThreadPoolExecutor


def calc(x):
    return x * 2


# `go` function creates a task and starts it in a separate thread
future = go(calc, 2)
assert future.result() == 4
## ^ equivalent to:
# future = Task(Future(), calc, [2]).start()
# assert future.result() == 4
## or
# task = Task(Future(), calc, [2])
# threading.Thread(target=task.run).start()
# assert task.future.result() == 4

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
```
