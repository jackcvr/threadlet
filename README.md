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
$ poetry run python bench.py
submit(sum, [1, 1]) max_workers=1 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 53.84559869102668 sec
threadlet.ThreadPoolExecutor	time spent: 17.472730049979873 sec

submit(sum, [1, 1]) max_workers=2 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 32.173576364992186 sec
threadlet.ThreadPoolExecutor	time spent: 17.78240813605953 sec

submit(sum, [1, 1]) max_workers=3 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 26.404446740983985 sec
threadlet.ThreadPoolExecutor	time spent: 18.011656531016342 sec

submit(sum, [1, 1]) max_workers=4 times=1000000:
---
concurrent.ThreadPoolExecutor	time spent: 27.120515974005684 sec
threadlet.ThreadPoolExecutor	time spent: 18.49675698694773 sec

futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 7.935382907046005 sec
threadlet.ThreadPoolExecutor	time spent: 6.419799988041632 sec

futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 24.490970341023058 sec
threadlet.ThreadPoolExecutor	time spent: 22.15484855300747 sec

futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 27.927631865022704 sec
threadlet.ThreadPoolExecutor	time spent: 24.41949982009828 sec

futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 24.974768674001098 sec
threadlet.ThreadPoolExecutor	time spent: 22.670274398988113 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=1
---
concurrent.ThreadPoolExecutor	time spent: 23.258484753081575 sec
threadlet.ThreadPoolExecutor	time spent: 13.741036918014288 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=2
---
concurrent.ThreadPoolExecutor	time spent: 17.593475122004747 sec
threadlet.ThreadPoolExecutor	time spent: 13.501336795976385 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=3
---
concurrent.ThreadPoolExecutor	time spent: 18.075485203997232 sec
threadlet.ThreadPoolExecutor	time spent: 14.378516206052154 sec

submit(sum, [1, 1]) 1000000 times then futures.wait(<1000000 futures>) max_workers=4
---
concurrent.ThreadPoolExecutor	time spent: 18.52698116505053 sec
threadlet.ThreadPoolExecutor	time spent: 13.637682205997407 sec
```

---

- Free software: MIT license
