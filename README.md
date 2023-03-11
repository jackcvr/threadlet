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
from threadlet import run_in_thread, Worker, ThreadPoolExecutor, wait


def calc(x):
    return x * 2

# spawns new thread each time to run function in it
future = run_in_thread(calc, 2)
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
| max_workers=1  | 94.7 ms | 70.6 ms: 1.34x faster | 64.7 ms: 1.46x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=2  | 150 ms  | 87.2 ms: 1.72x faster | 78.5 ms: 1.91x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=4  | 163 ms  | 99.2 ms: 1.64x faster | 95.4 ms: 1.71x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=8  | 169 ms  | 99.6 ms: 1.70x faster | 91.0 ms: 1.86x faster |
+----------------+---------+-----------------------+-----------------------+
| Geometric mean | (ref)   | 1.59x faster          | 1.72x faster          |
+----------------+---------+-----------------------+-----------------------+

+----------------+---------+-----------------------+-----------------------+
| Benchmark      | default | threadlet             | threadlet_simple      |
+================+=========+=======================+=======================+
| max_workers=1  | 28.5 MB | 27.7 MB: 1.03x faster | 27.2 MB: 1.05x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=2  | 29.2 MB | 28.7 MB: 1.02x faster | 28.6 MB: 1.02x faster |
+----------------+---------+-----------------------+-----------------------+
| max_workers=4  | 29.4 MB | 28.7 MB: 1.02x faster | not significant       |
+----------------+---------+-----------------------+-----------------------+
| max_workers=8  | 30.0 MB | 28.9 MB: 1.04x faster | 29.1 MB: 1.03x faster |
+----------------+---------+-----------------------+-----------------------+
| Geometric mean | (ref)   | 1.03x faster          | 1.03x faster          |
+----------------+---------+-----------------------+-----------------------+
```
