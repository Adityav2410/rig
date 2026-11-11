import threading
import time
from concurrent.futures import ThreadPoolExecutor

from rig.util.locked_dict import LockedDict


def test_threads_that_miss_together_share_one_value_and_build_it_once() -> None:
    d: LockedDict[str, object] = LockedDict()
    built = []

    def slow_factory() -> object:
        time.sleep(0.01)  # widen the window in which a second thread could also miss
        built.append(1)
        return object()

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _: d.get_or_create("k", slow_factory), range(8)))

    assert len({id(v) for v in values}) == 1
    assert built == [1]


def test_set_and_pop() -> None:
    d: LockedDict[str, threading.Lock] = LockedDict()
    lock = threading.Lock()
    d["a"] = lock
    assert d.pop("a") is lock
    assert d.pop("a") is None
