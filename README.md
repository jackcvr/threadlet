# threadlet

[![PyPI - Version](https://img.shields.io/pypi/v/threadlet.svg)](https://pypi.org/project/threadlet)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/threadlet.svg)](https://pypi.org/project/threadlet)

Improved ThreadPoolExecutor

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Features](#feature)
- [Benchmarks](#benchmarks)

## Installation

```console
pip install threadlet
```

## License

`threadlet` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Features

- ThreadPoolExecutor has improved worker performance(fixed IDLE semaphore) and new features:

```python
import time
import threading
from src.threadlet import ThreadPoolExecutor

MAX_WORKERS = 4
MIN_WORKERS = 2
WORK_TIME = 0.5
IDLE_TIMEOUT = 1

# "idle_timeout" argument:
# workers are going to die after doing nothing for "idle_timeout" time.
with ThreadPoolExecutor(MAX_WORKERS, idle_timeout=IDLE_TIMEOUT) as tpe:
    assert threading.active_count() == 1
    for _ in range(2):
        for _ in range(MAX_WORKERS):
            tpe.submit(time.sleep, WORK_TIME)
        assert threading.active_count() == MAX_WORKERS + 1
        time.sleep(WORK_TIME + IDLE_TIMEOUT + 1)  # wait until workers die on timeout
        assert threading.active_count() == 1

# "min_workers" argument:
# amount of workers which are pre-created at start and not going to die ever in despite of "idle_timeout".
with ThreadPoolExecutor(MAX_WORKERS, min_workers=MIN_WORKERS, idle_timeout=IDLE_TIMEOUT) as tpe:
    assert threading.active_count() == MIN_WORKERS + 1
    for _ in range(MAX_WORKERS):
        tpe.submit(time.sleep, WORK_TIME)
    assert threading.active_count() == MAX_WORKERS + 1
    time.sleep(WORK_TIME + MIN_WORKERS + 1)  # wait until workers die on timeout
    assert threading.active_count() == MIN_WORKERS + 1
```

### Benchmarks
```bash
$ hatch run python bench.py
submit(sum, [1, 1]) max_workers=1 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 35.846524495995254 sec
threadlet.ThreadPoolExecutor	time spent: 9.654531788008171 sec

submit(sum, [1, 1]) max_workers=2 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 20.530997663998278 sec
threadlet.ThreadPoolExecutor	time spent: 9.87691844299843 sec

submit(sum, [1, 1]) max_workers=3 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 18.194354530991404 sec
threadlet.ThreadPoolExecutor	time spent: 10.295373222994385 sec

submit(sum, [1, 1]) max_workers=4 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 17.788576000006287 sec
threadlet.ThreadPoolExecutor	time spent: 9.785075725012575 sec

futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 4.7045610019995365 sec
threadlet.ThreadPoolExecutor	time spent: 4.117530146002537 sec

futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 14.486180779000279 sec
threadlet.ThreadPoolExecutor	time spent: 11.843326850997983 sec

futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 15.543228420996456 sec
threadlet.ThreadPoolExecutor	time spent: 13.239023308997275 sec

futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 14.84883911900397 sec
threadlet.ThreadPoolExecutor	time spent: 14.350311642992892 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 15.129414690003614 sec
threadlet.ThreadPoolExecutor	time spent: 8.69144295899605 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 11.656284885000787 sec
threadlet.ThreadPoolExecutor	time spent: 8.352584471998853 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 13.135249231010675 sec
threadlet.ThreadPoolExecutor	time spent: 9.08623450199957 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 12.53088517699507 sec
threadlet.ThreadPoolExecutor	time spent: 9.53293534599652 sec
```
