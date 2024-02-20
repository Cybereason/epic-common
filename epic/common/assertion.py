import inspect
from types import UnionType
from decorator import decorator
from collections.abc import Callable
from typing import TypeVar, TypeAlias


C = TypeVar('C', bound=Callable)
TypeOrTypes: TypeAlias = type | tuple[type, ...] | UnionType


def assert_type(obj, type_or_types: TypeOrTypes, name: str | None = None) -> None:
    """
    Verify that an object is of a certain type. If not, raise a TypeError with an informative message.

    Parameters
    ----------
    obj : object
        The object to check.

    type_or_types : type, tuple of types or UnionType
        Possible types of the object.

    name : str, optional
        The name of the object, to appear in the exception message.
        If not provided, the value is used instead.

    Returns
    -------
    None

    Raises
    ------
    TypeError
        If the object is not of one of the types.
    """
    if not isinstance(obj, type_or_types):
        if isinstance(type_or_types, UnionType):
            type_or_types = tuple(type(t) if t is None else t for t in type_or_types.__args__)
        if isinstance(type_or_types, tuple):
            type_msg = f"one of {tuple(t.__name__ for t in type_or_types)}"
        else:
            type_msg = f"a '{type_or_types.__name__}'"
        if name is None:
            obj_msg = str(obj)
            if len(obj_msg) > (max_len := 20):
                obj_msg = f"{obj_msg[:max_len]}..."
        else:
            obj_msg = f"`{name}`"
        raise TypeError(f"{obj_msg} must be {type_msg}; got {type(obj).__name__}.")


def assert_types(**expected_types: TypeOrTypes) -> Callable[[C], C]:
    """
    A decorator factory which asserts the types of arguments given to a function.

    When the function is called, checks if the arguments are of the expected types.
    If any of them isn't, raises a TypeError.
    Otherwise, runs the function normally.

    Parameters
    ----------
    **expected_types : type, tuple of types or UnionType
        Each argument name is mapped to its expected type or types.
        Arguments not listed are not asserted.

    Returns
    -------
    decorator
        A signature-preserving decorator.

    Examples
    --------
    >>> @assert_types(x=int, y=float | None)
    ... def f(x, y, z):
    ...   # can safely assume `x` is an int and `y` is either a float or None
    ...   ...
    """
    def type_asserter(func, *args, **kwargs):
        call_args = inspect.signature(func).bind(*args, **kwargs).arguments
        for name, expected_type in expected_types.items():
            if name not in call_args:
                raise ValueError(f"Can't assert type of '{name}': no such argument in function.")
            assert_type(call_args[name], expected_type, name)
        return func(*args, **kwargs)
    return decorator(type_asserter)
