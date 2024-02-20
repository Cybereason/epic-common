import random
import functools
import itertools

from collections import deque
from typing import TypeVar, Generic, overload
from collections.abc import Iterable, Callable, Hashable, Iterator, Sized

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
S = TypeVar('S')
H = TypeVar('H', bound=Hashable)

NO_DEFAULT = object()

__all__ = [
    'unique', 'batches', 'batches_lol', 'SizedIterable', 'maybe_sized_iter',
    'consume', 'map_with_retry', 'random_sample', 'reduce_with_default',
]


@overload
def unique(items: Iterable[H], key: None = None) -> Iterable[H]: ...
@overload
def unique(items: Iterable[T], key: Callable[[T], Hashable]) -> Iterable[T]: ...


def unique(items, key=None):
    """
    Iterate over unique items, maintaining the order of the elements.

    Parameters
    ----------
    items : iterable
        Items to iterate over.

    key : callable, optional
        If provided, used to compare items to each other, to determine uniqueness.

    Returns
    -------
    iterator
    """
    seen = set()
    for item in items:
        if (x := item if key is None else key(item)) not in seen:
            seen.add(x)
            yield item


def batches(items: Iterable[T], size: int) -> Iterable[Iterable[T]]:
    """
    Iterate over items in batches of fixed size.
    The last batch may be smaller.

    Note: Each batch MUST be consumed before the next one is retrieved.

    Parameters
    ----------
    items : iterable
        The items on which to iterate.

    size : int
        The size of each batch.

    See Also
    --------
    batches_lol : Split the items into batches and return a list of lists.
    """
    if size <= 0:
        raise ValueError(f"`size` must be positive; got {size}.")
    it = iter(items)
    while True:
        batch = itertools.islice(it, size)
        try:
            item = next(batch)
        except StopIteration:
            return
        yield itertools.chain([item], batch)


def batches_lol(items: Iterable[T], size: int) -> list[list[T]]:
    """
    Split an iterable into batches of fixed size.
    The last batch may be smaller.

    Parameters
    ----------
    items : iterable
        The items on which to iterate.

    size : int
        The size of each batch.

    Returns
    -------
    list of lists
        Input items split into batches.

    See Also
    --------
    batches : Lazily iterate over the items in batches.
    """
    return list(map(list[T], batches(items, size)))


class SizedIterable(Generic[T_co]):
    """
    An iterable which is also sized.
    Can be iterated over, and has a length.

    Parameters
    ----------
    items : iterable
        Items in the iterable.

    length : int
        Length of the object.
    """
    def __init__(self, items: Iterable[T_co], length: int):
        if length < 0:
            raise ValueError(f"`length` must be non-negative; got {length}.")
        self.items = items
        self.length = length

    def __iter__(self) -> Iterator[T_co]:
        return iter(self.items)

    def __len__(self):
        return self.length


@overload
def maybe_sized_iter(items: Iterable[T], length_object: Sized) -> SizedIterable[T]: ...
@overload
def maybe_sized_iter(items: Iterable[T], length_object=None) -> Iterable[T] | SizedIterable[T]: ...


def maybe_sized_iter(items, length_object=None):
    """
    Convert an iterable into a SizedIterable, if possible.

    This convenience function tries to deduce the length of the input iterable from the length object
    provided. If a length is found, the items are wrapped as a SizedIterable. Otherwise, the iterable is
    returned as is.
    Without a length object to provide the length, the iterable itself is used to check the length.

    Parameters
    ----------
    items : iterable
        The iterable to wrap.

    length_object : object, optional
        Object to provide the length of the items iterable.
        If not provided, `items` itself is used.

    Returns
    -------
    iterable or SizedIterable
        Either `items` itself, or `items` wrapped in a SizedIterable.
    """
    if length_object is None:
        length_object = items
    if isinstance(length_object, Sized):
        return SizedIterable(items, len(length_object))
    return items


def consume(items: Iterable) -> None:
    """
    Consume an iterable entirely.

    This is similar to using `list(items)`, but does not create any objects, like a long list of None.
    Consumption of the iterable is done at C speed.

    Source: itertools docs
    https://docs.python.org/3/library/itertools.html#itertools-recipes

    Parameters
    ----------
    items : iterable
        The iterable to consume.

    Returns
    -------
    None
    """
    deque(items, maxlen=0)


@overload
def map_with_retry(func: Callable[[T], S], items: Iterable[T], tries: int, default: S) -> Iterable[S]: ...
@overload
def map_with_retry(func: Callable[[T], S], items: Iterable[T], tries: int = ...) -> Iterable[S]: ...


def map_with_retry(func: Callable[[T], S], items: Iterable[T], tries: int = 3, default=NO_DEFAULT) -> Iterable[S]:
    """
    Map a function over items, but try again if an exception is raised by the function.

    If the function raises, it is tried again until the specified number of tries is exhausted.
    When that happens, either a default value is yielded or the exception is finally raised.

    Parameters
    ----------
    func : callable
        The function to map.

    items : iterable
        The items to feed to the function.

    tries : int, default 3
        The number of times to try running the `func` on each item before giving up.

    default : object, optional
        If provided, it is yielded in case all tries are exhausted.
        Otherwise, the last exception raised by the function is re-raised.
    """
    if tries <= 0:
        raise ValueError(f'`tries` must be a positive integer; got {tries}.')
    for item in items:
        for i in range(tries):
            try:
                yield func(item)
            except Exception:
                if i == tries - 1:
                    if default is NO_DEFAULT:
                        raise
                    yield default
            else:
                break


def random_sample(items: Iterable[T], size: int, seed: int | float | str | bytes | bytearray | None = None) -> list[T]:
    """
    Return a random sample of the given items.
    The provided iterable need not be sized, and it is iterated over exactly once.
    The order of the items is not preserved.

    Parameters
    ----------
    items : iterable
        The items to sample.

    size : int
        The size of the sample.

    seed : int or float or str or bytes or bytearray, optional
        The seed for the random generator.

    Returns
    -------
    list
        A subset of the items.
        Its length is the minimum between `size` and the number of items.
    """
    rand = random.Random(seed)
    result = []
    for i, item in enumerate(items):
        if i < size:
            result.append(item)
        elif (j := rand.randint(0, i)) < size:
            result[j] = item
    return result


def reduce_with_default(function: Callable[[T, T], T], items: Iterable[T], default: T) -> T:
    """
    Reduce an iterable using a function, similarly to `functools.reduce`.

    Like `functools.reduce` with an initial value, the default is the return value if the iterable is empty.
    However, unlike `functools.reduce`, if the iterable is not empty, the default is not used at all.

    Parameters
    ----------
    function : callable
        A two-argument function to apply cumulatively to the items of the iterable.

    items : iterable
        The items on which to apply the function.

    default : object
        Value to return if `items` is an empty iterable.

    Returns
    -------
    object
        The result of `functools.reduce` applied to `function` and `items`, unless `items` is empty,
        in which case `default` is returned.
    """
    it = iter(items)
    try:
        first = next(it)
    except StopIteration:
        return default
    return functools.reduce(function, it, first)
