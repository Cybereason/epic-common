import math
import logging
import numbers
import functools

from io import IOBase
from types import MappingProxyType
from collections import defaultdict
from collections.abc import Iterable, Callable, Hashable, Mapping
from typing import TypeVar, TypeGuard, Generic, ParamSpec, Concatenate, overload, cast

B = TypeVar('B', bound=bytes | bytearray)
C_contra = TypeVar('C_contra', bound=type, contravariant=True)
P = ParamSpec('P')
R = TypeVar('R', bound=numbers.Real)
S = TypeVar('S')
T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)

__all__ = [
    'is_iterable', 'to_iterable', 'to_list', 'to_bytes', 'to_number', 'classproperty',
    'indexer_dict', 'hash_content', 'human_readable', 'get_single',
    'pass_none', 'coalesce',
]


def is_iterable(obj) -> TypeGuard[Iterable]:
    """
    Test whether an object is iterable, but NOT a string or a bytes instance.
    """
    return isinstance(obj, Iterable) and not isinstance(obj, str | bytes | bytearray)


def to_iterable(obj: T | Iterable[T]) -> Iterable[T]:
    """
    Convert an object to an iterable.

    Strings, bytes, bytearrays and Mappings are treated as single objects. For those types of
    inputs, a tuple of length 1 is returned.
    """
    # Mappings need special handling since iterating over them means only iterating over the keys
    if is_iterable(obj) and not isinstance(obj, Mapping):
        return obj
    return cast(T, obj),


def to_list(obj: T | Iterable[T]) -> list[T]:
    """
    Convert an object to a list.

    - If already a list, the object is returned as is; no new list is created.
    - If a single item (including a string, a bytes or a Mapping), a list of
      length 1 containing the object is returned.
    - If an iterable, the object is converted to a list.
    """
    # Avoid making a new list if already given a list
    return obj if isinstance(obj, list) else list(to_iterable(obj))


@overload
def to_bytes(obj: B, encoding: str = ..., errors: str = ...) -> B: ...
@overload
def to_bytes(obj, encoding: str = ..., errors: str = ...) -> bytes: ...


def to_bytes(obj, encoding='utf-8', errors='replace'):
    """
    Convert an object to a byte sequence - either a bytes or a bytearray.
    """
    if isinstance(obj, bytes | bytearray):
        return obj
    if isinstance(obj, memoryview):
        return obj.tobytes()
    if not isinstance(obj, str):
        obj = str(obj)
    return obj.encode(encoding, errors=errors)


@overload
def to_number(obj: R) -> R: ...
@overload
def to_number(obj) -> numbers.Real: ...


def to_number(obj):
    """
    Convert an object to a number.
    """
    if isinstance(obj, numbers.Real):
        return obj
    try:
        return int(obj)
    except ValueError:
        return float(obj)


# noinspection PyPep8Naming
class classproperty(Generic[C_contra, T_co]):
    """
    Class property decorator.
    The property is read-only.

    Examples
    --------
    >>> class MyClass:
    ...   X = 1
    ...
    ...   @classproperty
    ...   def prop(cls):
    ...     return cls.X + 1
    ...
    >>> MyClass.prop
    2
    """
    def __init__(self, func: Callable[[C_contra], T_co]):
        self.func = func

    def __get__(self, owner, owner_cls: C_contra) -> T_co:
        return self.func(owner_cls)


def indexer_dict() -> defaultdict[Hashable, int]:
    """
    Create and return a new `collections.defaultdict` which assigns to new keys the current number of elements.

    In essence, it gives a collection of items the unique indices `{0, ..., n-1}`, where `n` is the
    number of unique items.

    Returns
    -------
    collections.defaultdict
    """
    dd = defaultdict[Hashable, int]()
    dd.default_factory = dd.__len__
    return dd


def hash_content(obj) -> int:
    """
    Hash the content of an object, even if the object itself is not hashable.

    For hashable objects, returns their built-in hash.
    For other objects, attempts to obtain a "representation" of the object's content,
    either its state (using `__getstate__`), its `__dict__` or its items, and hash them recursively,
    together with information about the object's type.
    That means that for mutable objects, multiple calls to `hash_content` may not return the same value.

    Parameters
    ----------
    obj : object
        Object to hash.

    Returns
    -------
    int
        A value consistent with the current content of `obj`.
    """
    if isinstance(obj, Hashable):
        try:
            return hash(obj)
        except TypeError:
            pass
    typename = type(obj).__name__
    if hasattr(obj, '__getstate__') and (state := obj.__getstate__()) is not None:
        obj = state
    elif isinstance(obj, logging.getLoggerClass()):
        obj = obj.name
    elif hasattr(obj, '__dict__'):
        if isinstance(obj.__dict__, MappingProxyType):
            objdict = {k: v for k, v in obj.__dict__.items() if not k.startswith('__')}
        else:
            objdict = obj.__dict__.copy()
        objdict['___name'] = getattr(obj, '__name__', None)
        objdict['___classname'] = typename
        if isinstance(obj, dict):
            obj = obj.copy()
            obj['___objdict'] = objdict
        else:
            obj = objdict
    if isinstance(obj, Mapping):
        obj = frozenset((k, hash_content(v)) for k, v in obj.items())
    elif is_iterable(obj) and not isinstance(obj, IOBase):
        obj = tuple(map(hash_content, obj))
    return hash((obj, typename))


def human_readable(number: float, binary: bool = False, n_digits: int = 2) -> str:
    """
    Convert a number to a string representation that is easier for humans to read.
    The number is displayed using the standard SI prefixes for very large and small scales.

    Parameters
    ----------
    number : int or float
        The number to convert.

    binary : bool, default False
        Whether to use the standard binary prefixes (Kibi, etc.), and a multiplier of 1024 instead of 1000.

    n_digits : int, default 2
        The maximum number of digits to display after the decimal point.

    Returns
    -------
    str
        Representation of the input number.
    """
    if number > 0:
        sign = ''
    elif number < 0:
        sign = '-'
        number = -number
    else:
        return '0'
    # The generic math.log with base 2/10 gives less accurate results, which can cause rounding errors.
    log, exponent, base, kilo, units_suffix = (
        math.log2, 10, 1024, 'K', 'i',
    ) if binary else (
        math.log10, 3, 1000, 'k', '',
    )
    scale = int(log(number) // exponent)
    scaled_number = number / base ** scale
    precision = int(math.log10(scaled_number)) + n_digits + 1  # log10 because, still, digits...
    if scale > 0:
        units = f" {(kilo + 'MGTPEZYRQ')[scale - 1]}{units_suffix}"
    elif scale < 0:
        units = f" {'mµnpfazyrq'[-scale - 1]}{units_suffix}"
    else:
        units = ''
    return f"{sign}{scaled_number:.{precision}g}{units}"


def get_single(items: Iterable[T]) -> T:
    """
    Get THE single item from the given iterable.
    If the iterable contain more or fewer than a single item, an exception is raised.

    Parameters
    ----------
    items : iterable
        An iterable containing only a single item.

    Returns
    -------
    object
        The single item in `items`.

    Raises
    ------
    ValueError
        If `items` contain more or fewer than a single item.
    """
    it = iter(items)
    try:
        item = next(it)
    except StopIteration:
        raise ValueError("Cannot get single value; no values found")
    try:
        next(it)
    except StopIteration:
        return item
    raise ValueError(f"Cannot get single value; more than one value found: {items!r}")


def pass_none(func: Callable[Concatenate[T, P], S]) -> Callable[Concatenate[T | None, P], S | None]:
    """
    Decorate a function so that if called with None as its first argument, it returns None.
    """
    @functools.wraps(func)
    def none_shall_pass(value: T | None, *args: P.args, **kwargs: P.kwargs) -> S | None:
        return None if value is None else func(value, *args, **kwargs)
    return none_shall_pass


def coalesce(*args: T) -> T | None:
    """
    Return the first argument that is not None, or None if no such argument was provided.
    """
    for arg in args:
        if arg is not None:
            return arg
