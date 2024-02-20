import time
import signal
import datetime
import threading

from decorator import decorate
from contextlib import contextmanager
from typing import TypeVar, Any, TypeAlias
from collections.abc import Callable, Iterable

from .general import to_list


class Timer:
    """
    A context manager for timing the execution of a code block.
    """
    def __init__(self):
        self._store = threading.local()
        self.delta = 0

    @property
    def delta(self) -> datetime.timedelta:
        return self._store.delta

    @delta.setter
    def delta(self, value: float):
        self._store.delta = datetime.timedelta(seconds=value)

    def __enter__(self) -> "Timer":
        self._store.reference_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delta = time.perf_counter() - self._store.reference_time

    def __str__(self):
        return str(self.delta)

    @property
    def total_seconds(self) -> float:
        return self.delta.total_seconds()


C = TypeVar("C", bound=Callable)


def timed(function: C) -> C:
    """
    A decorator for timing functions.

    Attaches a Timer object to the function (as a "timer" attribute), which times each execution of the function.
    """
    timer = Timer()

    def timeit(func, *args, **kwargs):
        with timer:
            result = func(*args, **kwargs)
        return result

    wrapped = decorate(function, timeit)
    wrapped.timer = timer
    return wrapped


class TimeTracker(dict[Any, list]):
    """
    A dictionary subclass which tracks the total time spent between calls.
    It maps the given code section names to lists of floats - the number of seconds since tracking has started.

    Examples
    --------
    >>> class MyClass:
    ...   def __init__(self):
    ...     self.time_tracker = TimeTracker()
    ...
    ...   def calculate(self):
    ...     # Start the clock for this method
    ...     tracker = self.time_tracker.tracker("calculate")
    ...     ...  # do stuff
    ...     # Save elapsed time and start a new clock
    ...     tracker.track("do stuff")
    ...     ...  # do more stuff
    ...     # Again, save elapsed time and start a new clock
    ...     tracker.track("do more stuff")
    ...     ...  # do stuff here that is not tracked
    ...
    >>> mc = MyClass()
    >>> for i in range(2):
    ...   mc.calculate()
    ...
    >>> mc.time_tracker
    {"calculate: do_stuff": [0.3, 0.6], "calculate: do more stuff": [0.5, 0.1]}
    """
    class Tracker:
        def __init__(self, parent: "TimeTracker", prefix=None):
            self.parent = parent
            self.prefix = prefix
            self.reference_time = time.perf_counter()

        def track(self, name) -> None:
            """
            Add a new timing point to the list, under the given name.

            Parameters
            ----------
            name : object
                Name for the current timing entry.

            Returns
            -------
            None
            """
            if self.prefix is not None:
                name = f"{self.prefix}: {name}"
            current_time = time.perf_counter()
            self.parent.setdefault(name, []).append(current_time - self.reference_time)
            self.reference_time = current_time

    def tracker(self, prefix=None) -> Tracker:
        """
        Create a new Tracker and start its clock.

        Parameters
        ----------
        prefix : object, optional
            A common prefix for all entries of this tracker.

        Returns
        -------
        Tracker
        """
        return self.Tracker(self, prefix)


Timestamp: TypeAlias = datetime.datetime | datetime.date | str | float | int
TimeFormat: TypeAlias = str | Iterable[str] | None


def to_datetime(timestamp: Timestamp, time_format: TimeFormat = None) -> datetime.datetime:
    """
    Convert a wide range of inputs into a datetime.datetime.

    Parameters
    ----------
    timestamp : datetime, date, str, float or int
        The input to convert.
        If a number, it is the standard POSIX timestamp.
        If a string, can either be a formatted time string (see `time_format` below), or
        one of "today", "yesterday" or "now" (case-insensitive).

    time_format : str or iterable of str, optional
        Possible formats to consider when trying to convert a formatted time string.
        If not given, some reasonable defaults are tried.

    Returns
    -------
    datetime.datetime
        Converted input.
    """
    if isinstance(timestamp, datetime.datetime):
        return timestamp

    def date2datetime(date):
        return datetime.datetime.combine(date, datetime.time.min)

    if isinstance(timestamp, datetime.date):
        return date2datetime(timestamp)

    if isinstance(timestamp, str):
        time_str = timestamp.lower()

        if time_str == 'today':
            return date2datetime(datetime.date.today())

        if time_str == 'yesterday':
            return date2datetime(datetime.date.today()) - datetime.timedelta(days=1)

        if time_str == 'now':
            return datetime.datetime.now()

        if time_format is None:
            bases = ("%Y{0}%m{0}%d", "%d{0}%m{0}%y")
            separators = [''] + list('-./')
            times = [''] + ['{tsep}%H:%M{sec}'.format(tsep=ts, sec=s) for ts in ' T' for s in (':%S', '')]
            formats = [base.format(sep) + t for base in bases for t in times for sep in separators]
        else:
            formats = to_list(time_format)

        for f in formats:
            try:
                return datetime.datetime.strptime(timestamp, f)
            except ValueError:
                if f == formats[-1]:
                    raise ValueError("time data '%s' does not match any of %s formats" %
                                     (timestamp, 'expected' if time_format is None else 'given'))

    if isinstance(timestamp, float | int):
        return datetime.datetime.fromtimestamp(timestamp)

    raise TypeError("inappropriate timestamp type: " + type(timestamp).__name__)


def to_epoch_time(timestamp: Timestamp, time_format: TimeFormat = None) -> float:
    """
    Convert a wide range of inputs to seconds since the Epoch.

    Parameters
    ----------
    timestamp : datetime, date, str, float or int
        The input to convert.
        See `to_datetime` for more information.

    time_format : str or iterable of str, optional
        See `to_datetime` for more information.

    Returns
    -------
    float
        Seconds since the Epoch for the given input.

    See Also
    --------
    to_datetime : Convert to datetime.datetime.
    """
    dt = to_datetime(timestamp, time_format)
    return time.mktime(dt.timetuple()) + dt.microsecond / 1e6


# Inspired by http://stackoverflow.com/a/13821695/221917
@contextmanager
def timeout_if_possible(timeout_duration: int | None):
    """
    Execute the contained code block with a timeout. If exceeded, a TimeoutError is raised.
    Note that timeouts are not supported on Windows.
    Also, they are supported only in the main thread and only in whole seconds resolution.

    Parameters
    ----------
    timeout_duration : int or None
        Number of seconds until a timeout.
        If None, then no timeout is set.
    """
    if timeout_duration is None:
        # No timeout
        yield
        return
    elif timeout_duration != int(timeout_duration):
        raise TypeError(f"Only integer timeouts are allowed; got {timeout_duration}")
    timeout_duration = int(timeout_duration)

    if not (hasattr(signal, "alarm") and hasattr(signal, "SIGALRM")):
        # Likely not on Linux / Mac
        yield
    elif threading.current_thread() is not threading.main_thread():
        # Only main thread can be signal-interrupted
        yield
    else:
        def handler(_signum, _frame):
            raise TimeoutError()

        orig_signal_handler = signal.signal(signal.SIGALRM, handler)
        try:
            # Set the timeout handler
            # TODO: If _prev_alarm is nonzero, we just stole another handler's alarm! We should restore it at the end.
            _prev_alarm = signal.alarm(timeout_duration)
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, orig_signal_handler)
