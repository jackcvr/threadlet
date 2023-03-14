# threadlet

[![PyPI - Version](https://img.shields.io/pypi/v/threadlet.svg)](https://pypi.org/project/threadlet)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/threadlet.svg)](https://pypi.org/project/threadlet)

Improved ThreadPoolExecutor

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Features](#features)
- [Benchmarks](#benchmarks)

## Installation

```console
pip install threadlet
```

## License

`threadlet` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Features

```python
import time
import threading
from threadlet import Task, Worker, ThreadPoolExecutor, wait


def calc(x):
    return x * 2

# spawns new thread each time to run function in it
future = Task.run(calc, 2)
assert future.result() == 4

# spawns one thread to handle all submitted functions
with Worker() as w:
    future = w.submit(calc, 3)
    assert future.result() == 6

# "idle_timeout" argument (5 seconds by default):
# workers are going to die after doing nothing for "idle_timeout" seconds.
with ThreadPoolExecutor(4, idle_timeout=1) as tpe:
    assert threading.active_count() == 1
    fs = set()
    for _ in range(100):
        fs.add(tpe.submit(time.sleep, 0.1))
    assert threading.active_count() == 1 + 4  # main thread + 4 workers
    wait(fs)
    time.sleep(1)  # wait until workers die by timeout
    assert threading.active_count() == 1

# "min_workers" argument:
# amount of workers which are pre-spawned at start and not going to die ever in despite of "idle_timeout".
with ThreadPoolExecutor(4, min_workers=2, idle_timeout=1) as tpe:
    assert threading.active_count() == 1 + 2  # main thread + 2 pre-spawned workers
    fs = set()
    for _ in range(100):
        fs.add(tpe.submit(time.sleep, 0.1))
    assert threading.active_count() == 1 + 4  # main thread + 4 workers
    wait(fs)
    time.sleep(1)  # wait until workers die by timeout
    assert threading.active_count() == 1 + 2  # as at starting point
```

### Benchmarks

```bash
+----------------+---------+-----------------------+-----------------------+
| Benchmark      | default | threadlet             | threadlet_simple      |
+================+=========+=======================+=======================+
| max_workers=1  | 101 ms  | 64.0 ms: 1.58x faster | 57.7 ms: 1.76x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=2  | 97.6 ms | 65.2 ms: 1.50x faster | 55.4 ms: 1.76x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=4  | 103 ms  | 62.8 ms: 1.63x faster | 56.1 ms: 1.83x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=8  | 95.9 ms | 63.5 ms: 1.51x faster | 57.9 ms: 1.66x faster |
+----------------+---------+-----------------------+-----------------------+
| Geometric mean | (ref)   | 1.56x faster          | 1.75x faster          |
+----------------+---------+-----------------------+-----------------------+
```
