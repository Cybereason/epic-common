from typing import Any
from collections.abc import Mapping, MutableMapping, Iterable, Sequence


NO_DEFAULT = object()


def walk_dict(dictionary: Mapping) -> Iterable[tuple[tuple, Any]]:
    """
    Iterate over all items of the mapping.

    If any of the values is a mapping, recursively iterate on it as well.
    Yielded items are pairs of ((tuple of nested keys), values).
    """
    for key, val in dictionary.items():
        yield (key,), val
        if isinstance(val, Mapping):
            for nested_keys, inner_value in walk_dict(val):
                yield (key, *nested_keys), inner_value


def flatten_dict(dictionary: Mapping, delim: str = '.') -> dict:
    """
    Flatten a possibly nested dictionary into a non-nested dictionary.

    Parameters
    ----------
    dictionary : mapping
        The dictionary to flatten.

    delim : str, default '.'
        Keys of nested levels will be joined together into a flat key using this delimiter.

    Returns
    -------
    dict
        Flattened dictionary.
    """
    flat = {}
    for k, v in dictionary.items():
        if isinstance(v, Mapping):
            for kk, vv in flatten_dict(v, delim).items():
                flat[f'{k}{delim}{kk}'] = vv
        else:
            flat[k] = v
    return flat


def dict_get_nested(dictionary: Mapping, nested_key: str | Iterable, default=NO_DEFAULT, delim: str = '.'):
    """
    Get a value from a possibly nested dictionary by specifying the full "nesting path" to it.

    Parameters
    ----------
    dictionary : mapping
        The dictionary to query.

    nested_key : str or iterable
        The key of the item to get.
        - If an iterable, it is the sequence of nested keys.
        - If a string, the delimiter `delim` is used to split it into a sequence of nested keys.

    default : object, optional
        The default value to return if the nested key does not exist.
        If not provided, a KeyError will be raised in that case.

    delim : str, default '.'
        The delimiter to use for splitting the nested key when it is a string.

    Returns
    -------
    object
        Value from the dictionary.

    Raises
    ------
    KeyError
        If the nested key does not exist and no default is provided.
    """
    item = dictionary
    for key in (nested_key.split(delim) if isinstance(nested_key, str) else nested_key):
        if isinstance(item, Mapping) and key in item:
            item = item[key]
        elif default is NO_DEFAULT:
            raise KeyError(nested_key)
        else:
            return default
    return item


def dict_get_any_nested(dictionary: Mapping, key, default=NO_DEFAULT):
    """
    Get a value from a possibly nested dictionary by specifying the innermost key to it.
    If several values have the same innermost key, one of them is arbitrarily returned.

    Parameters
    ----------
    dictionary : mapping
        The dictionary to query.

    key : object
        The key of the item to get.
        If the dictionary is nested, this is the innermost key.

    default : object, optional
        The default value to return if the key does not exist.
        If not provided, a KeyError will be raised in that case.

    Returns
    -------
    object
        Value from the dictionary.

    Raises
    ------
    KeyError
        If the key does not exist and no default is provided.
    """
    for path, value in walk_dict(dictionary):
        if path[-1] == key:
            return value
    if default is NO_DEFAULT:
        raise KeyError(key)
    return default


def dict_del_nested(dictionary: Mapping, nested_key: str | Sequence, delim: str = '.',
                    ignore_keyerror: bool = False) -> None:
    """
    Remove a value from a possibly nested dictionary by specifying the full "nesting path" to it.

    Parameters
    ----------
    dictionary : mapping
        The dictionary to query.

    nested_key : str or sequence
        The key of the item to get.
        - If a sequence, it is the sequence of nested keys.
        - If a string, the delimiter `delim` is used to split it into a sequence of nested keys.

    delim : str, default '.'
        The delimiter to use for splitting the nested key when it is a string.

    ignore_keyerror : bool, default False
        Whether to suppress a KeyError when the nested key does not exist.

    Returns
    -------
    None

    Raises
    ------
    KeyError
        If the nested key does not exist and `ignore_keyerror` is False.
    """
    *path, last = nested_key.split(delim) if isinstance(nested_key, str) else nested_key
    try:
        item = dict_get_nested(dictionary, path)
    except KeyError:
        if ignore_keyerror:
            return
        raise KeyError(nested_key)
    if isinstance(item, MutableMapping) and last in item:
        del item[last]
    elif not ignore_keyerror:
        raise KeyError(nested_key)
