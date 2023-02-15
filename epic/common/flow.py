import copy
import functools


def check(predicate, message_or_exception_instance="check failed"):
    """
    Check truthful value (e.g. of a function call) and raise an Exception if not truthful.
    You can provide an optional error string or exception instance to be thrown.
    """
    if not predicate:
        if isinstance(message_or_exception_instance, Exception):
            raise message_or_exception_instance
        else:
            raise Exception(str(message_or_exception_instance))


def pragma_once(f):
    """
    Decorate a function so that it runs normally when first called, but immediately returns None on any subsequent call
    """
    @functools.wraps(f)
    def _f(*args, **kwargs):
        if hasattr(f, "__pragma_once__"):
            return
        setattr(f, "__pragma_once__", True)
        return f(*args, **kwargs)
    return _f


def clone_and_apply(f):
    """
    Decorator to replace a self-modifying method with a clone-self-and-return-modified method.
    Cloning is done by the instance's `clone()` method, or copy.deepcopy(self) as fallback.

    Examples
    --------
    >>> class MyClass:
    ...   def __init__(self, value):
    ...     self.value = value
    ...     self.this_does_not_change = id(self)
    ...
    ...   @clone_and_apply
    ...   def with_new_value(self, another_value):
    ...     self.value = another_value
    ...
    >>> mc = MyClass(100)
    >>> mc2 = mc.with_new_value(200)
    >>> mc.value
    100
    >>> mc2.value
    200
    >>> assert mc is not mc2
    >>> assert mc.this_does_not_change == mc2.this_does_not_change
    """
    @functools.wraps(f)
    def _f(self, *args, **kwargs):
        if hasattr(self, "clone"):
            clone = self.clone()
        else:
            clone = copy.deepcopy(self)
        f(clone, *args, **kwargs)
        return clone
    return _f
