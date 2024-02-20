import queue
import threading
import multiprocessing as mp

from collections.abc import Iterator
from multiprocessing.managers import SyncManager
from typing import Literal, TypeVar, Generic, ClassVar, TypeAlias


T = TypeVar("T")
Backend: TypeAlias = Literal["multiprocessing", "threading"]


class IterableQueue(Generic[T]):
    """
    A queue which is iterable, i.e., instead of getting items with timeout and catching and empty
    queue exception, items are retrieved simply by iterating over the queue. The price to pay for it is
    that we must mark when no more inputs will be placed in the queue (using the `no_more_input` method).
    After doing so, no more input can ever be placed in the queue.
    The queue can be based on either a multiprocessing or a threading queue.

    Parameters
    ----------
    backend : {'multiprocessing', 'threading'}
        Determines the type of queue this IterableQueue uses.

    maxsize : int, default 0
        Maximum size of the queue. If reached, the queue will block on input.
        A size of 0 means unlimited size.

    interval : float, default 0.5
        Number of seconds between each check if the queue is available for putting/getting items.
    """
    _MP_MANAGER: ClassVar[SyncManager | None] = None

    def __init__(self, backend: Backend, maxsize: int = 0, interval: float = 0.5):
        if backend == "multiprocessing":
            manager = self._get_manager()
            self.queue = manager.Queue(maxsize=maxsize)
            self._no_more_input = manager.Event()
        elif backend == "threading":
            self.queue = queue.Queue(maxsize=maxsize)
            self._no_more_input = threading.Event()
        else:
            raise ValueError(f"Invalid value for `backend`: {backend}")
        self.interval = interval

    @classmethod
    def _get_manager(cls) -> SyncManager:
        if cls._MP_MANAGER is None:
            cls._MP_MANAGER = mp.Manager()
        return cls._MP_MANAGER

    def no_more_input(self) -> None:
        """
        Mark this queue as closed, i.e., from now on no more input is accepted.
        """
        self._no_more_input.set()

    def put(self, item: T) -> None:
        """
        Put an item into the queue.
        """
        while True:
            if self._no_more_input.is_set():
                break
            try:
                self.queue.put(item, timeout=self.interval)
                break
            except queue.Full:
                continue

    def __iter__(self) -> Iterator[T]:
        """
        Retrieve items from the queue.
        """
        while True:
            # Must check the event *before* checking if the queue is empty, to prevent a case
            # in which, after we get an empty queue exception, the user enters more items and
            # then sets the event, all before we check the event.
            no_more_input = self._no_more_input.is_set()
            try:
                yield self.queue.get(timeout=self.interval)
            except queue.Empty:
                # If the queue is empty and no more input is expected, we're done here
                if no_more_input:
                    return
