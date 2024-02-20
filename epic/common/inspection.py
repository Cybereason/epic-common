import importlib

from typing import TypeGuard
from types import LambdaType, ModuleType


def is_lambda_function(obj) -> TypeGuard[LambdaType]:
    """
    Test whether an object is a lambda function.
    """
    return isinstance(obj, LambdaType) and obj.__name__ == "<lambda>"


def fullname2obj(name: str):
    """
    Convert a dotted string name into an imported object.

    The input name (str) takes the following format:

        [[package1.][package2.] ... [packageN.]]module[.obj][[.member1][.member2] ... [.memberN]]

    Meaning, any sequence of dotted import specification, followed by an optional dot and an object name to import,
    followed by an optional sequence of dotted attributes to get recursively.
    This allows importing packages, modules, objects in modules and members of objects in modules (e.g. class members).

    Parameters
    ----------
    name : str
        Name of the object to import.

    Returns
    -------
    object
        Imported module, object or member.

    Raises
    ------
    ValueError
        If the name provided is invalid.
    ModuleNotFoundError
        If the module to be imported could not be found.
    AttributeError
        If the object could not be found in the module.

    See Also
    --------
    fullname : Inverse function.
    """
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid name '{name}'")
    # Import from left to right until we fail to import (but at least once)
    module = None
    tokens = name.split(".")
    for i in range(len(tokens)):
        try:
            module = importlib.import_module(".".join(tokens[:i+1]))
        except ModuleNotFoundError:
            if i == 0:
                raise
            break
    else:
        return module
    # Make the rest of the journey by getting attributes recursively
    result = module
    for j, token in enumerate(tokens[i:]):
        try:
            result = getattr(result, token)
        except AttributeError:
            if i + j + 1 == len(tokens):
                raise
            else:
                raise ModuleNotFoundError(f"No module named '{'.'.join(tokens[:i + j + 1])}'")
    return result


def fullname(obj) -> str:
    """
    Return the fully qualified dotted name of an object, as a string.

    This is the inverse of fullname2obj, for those objects whose import path can be inferred from their properties.

    Parameters
    ----------
    obj : object
        An object whose fully qualified name is sought.

    Returns
    -------
    str
        A fully qualified dotted name, for example: 'package.module.attr', 'builtin.str', 'package.module' and so on.

    Raises
    ------
    ValueError
        If the object's fully qualified name cannot be inferred.

    See Also
    --------
    fullname2obj : Inverse function.
    """
    name: str | None = getattr(obj, '__qualname__', getattr(obj, '__name__', None))
    if name is None:
        raise ValueError("object has no name")
    module = getattr(obj, '__module__', None)
    if module is None:
        if isinstance(obj, ModuleType):
            return name
        raise ValueError("object has no fully-qualified name")
    return f'{module}.{name}'
