# Threadlet

Improved `Thread` and `ThreadPoolExecutor` classes.

---

### Installation
`pip3 install threadlet`

### Features

- Threads with results:

```python
from threadlet.thread import Thread

# threads now have "future" attribute of type concurrent.futures.Future.
# usage:
thread = Thread(target=sum, args=([1, 1],))
thread.start()
try:
    assert thread.future.result(1) == 2
finally:
    thread.join()  # pay attention that "future" attribute won't be available after joining
    # thread.future.result(1) #  raises AttributeError

# equals to:
with Thread(target=sum, args=([1, 1],)) as thread:
    assert thread.future.result(1) == 2

# equals to:
with Thread.submit(sum, [1, 1]) as thread:
    assert thread.future.result(1) == 2
```

- ThreadPoolExecutor with improved workers performance (fixed IDLE semaphore) and new features:
```python
import time
import threading
from threadlet.executor import ThreadPoolExecutor

MAX_WORKERS = 4
MIN_WORKERS = 2
WORK_TIME = 0.5
IDLE_TIMEOUT = 1

# "idle_timeout" argument:
# workers now are going to die after doing nothing for "idle_timeout" time.
with ThreadPoolExecutor(MAX_WORKERS, idle_timeout=IDLE_TIMEOUT) as tpe:
    assert threading.active_count() == 1
    for _ in range(2):
        for _ in range(MAX_WORKERS):
            tpe.submit(time.sleep, WORK_TIME)
        assert threading.active_count() == MAX_WORKERS + 1
        time.sleep(WORK_TIME + IDLE_TIMEOUT + 1)  # wait until workers die on timeout
        assert threading.active_count() == 1

# "min_workers" argument:
# this amount of workers are pre-created at start and not going to die ever in despite of "idle_timeout".
with ThreadPoolExecutor(MAX_WORKERS, min_workers=MIN_WORKERS, idle_timeout=IDLE_TIMEOUT) as tpe:
    assert threading.active_count() == MIN_WORKERS + 1
    for _ in range(MAX_WORKERS):
        tpe.submit(time.sleep, WORK_TIME)
    assert threading.active_count() == MAX_WORKERS + 1
    time.sleep(WORK_TIME + MIN_WORKERS + 1)  # wait until workers die on timeout
    assert threading.active_count() == MIN_WORKERS + 1
```

---

- Free software: MIT license
