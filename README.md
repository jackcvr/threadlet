# Threadlet

Improved `Thread` and `ThreadPoolExecutor` classes.

---

### Installation
`pip3 install threadlet`

### Features

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

### Benchmarks

```bash
$ poetry run python bench.py
submit(sum, [1, 1]) max_workers=1 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 51.68451470899163 sec
threadlet.ThreadPoolExecutor	time spent: 14.034955328999786 sec

submit(sum, [1, 1]) max_workers=2 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 30.85988494398771 sec
threadlet.ThreadPoolExecutor	time spent: 14.149454248996335 sec

submit(sum, [1, 1]) max_workers=3 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 23.788395736002713 sec
threadlet.ThreadPoolExecutor	time spent: 14.243532117005088 sec

submit(sum, [1, 1]) max_workers=4 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 24.605877805995988 sec
threadlet.ThreadPoolExecutor	time spent: 14.26560322700243 sec

futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 7.2795372900000075 sec
threadlet.ThreadPoolExecutor	time spent: 5.727786898991326 sec

futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 21.606328508001752 sec
threadlet.ThreadPoolExecutor	time spent: 18.455558971996652 sec

futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 22.43454322699108 sec
threadlet.ThreadPoolExecutor	time spent: 21.441624792001676 sec

futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 25.23331410800165 sec
threadlet.ThreadPoolExecutor	time spent: 21.244171070997254 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 18.50262119299441 sec
threadlet.ThreadPoolExecutor	time spent: 11.705895610997686 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 15.47274379299779 sec
threadlet.ThreadPoolExecutor	time spent: 11.893112275007297 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 17.14120809501037 sec
threadlet.ThreadPoolExecutor	time spent: 11.979401491989847 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 16.178104474005522 sec
threadlet.ThreadPoolExecutor	time spent: 12.229133631990408 sec
```

---

- Free software: MIT license
