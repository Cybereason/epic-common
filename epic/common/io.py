import os
import json
import pickle
import tempfile
import warnings

from collections.abc import Iterable
from contextlib import contextmanager

from .pathgeneralizer import GeneralizedPath, PathGeneralizer

__all__ = [
    'pload', 'pdump', 'readf', 'writef', 'execfile', 'iterlines',
    'jload', 'jdump', 'with_temp_file',
]


def pload(filename: GeneralizedPath, fix_imports: bool = True, encoding: str = "ASCII", errors: str = "strict"):
    """
    Load a pickled object from a file.

    Parameters
    ----------
    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    fix_imports
    encoding
    errors
        Arguments sent to pickle.load.

    Returns
    -------
    object
        Loaded object.
    """
    with PathGeneralizer.from_path(filename).open("rb") as f:
        return pickle.load(f, fix_imports=fix_imports, encoding=encoding, errors=errors)


def pdump(data, filename: GeneralizedPath, protocol: int = pickle.HIGHEST_PROTOCOL, fix_imports: bool = True) -> None:
    """
    Pickle an object and dump it into a file.

    Parameters
    ----------
    data : object
        Object to dump.

    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    protocol : int, default pickle.HIGHEST_PROTOCOL
        The protocol to use.
        Note that while the default for pickle.dump is pickle.DEFAULT_PROTOCOL, here the highest protocol is used.

    fix_imports : bool, default True
        Sent to pickle.dump.

    Returns
    -------
    None
    """
    with PathGeneralizer.from_path(filename).open("wb") as f:
        pickle.dump(data, f, protocol=protocol, fix_imports=fix_imports)


def readf(filename: GeneralizedPath, size: int = -1) -> bytes:
    """
    Read the contents of a file.

    Parameters
    ----------
    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    size : int, default -1
        Number of bytes to read.
        A negative value means to read all content.

    Returns
    -------
    bytes
        The contents of the file.
    """
    return PathGeneralizer.from_path(filename).read("rb", size)


def writef(data: bytes | bytearray, filename: GeneralizedPath) -> None:
    """
    Write data into a file.

    Parameters
    ----------
    data : bytes or bytearray
        The data to write.

    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    Returns
    -------
    None
    """
    PathGeneralizer.from_path(filename).write(data, "wb")


def execfile(filename: GeneralizedPath, global_vars: dict | None = None, local_vars: dict | None = None, /) -> None:
    """
    Execute the code in the given file with the given global and local variables.

    Parameters
    ----------
    filename : str, pathlib.Path or PathGeneralizer
        The path to the file to execute.
        Can also be a path to a remote resource (see PathGeneralizer).

    global_vars : dict, optional
        A dictionary of global variables to be used in the execution context.
        Default is an empty dictionary.

    local_vars : dict, optional
        A dictionary of local variables to be used in the execution context.
        Defaults to the global variables.

    Returns
    -------
    None
    """
    path_str = filename.path if isinstance(filename, PathGeneralizer) else str(filename)
    if global_vars is None:
        global_vars = {}
    contents = PathGeneralizer.from_path(filename).read("rb")
    compiled_code = compile(contents, path_str, "exec")
    exec(compiled_code, global_vars, local_vars)


def iterlines(filename: GeneralizedPath, ignore_comments: bool = True) -> Iterable[str]:
    """
    Iterate over lines in a file.
    Leading and trailing whitespaces are stripped.
    Lines containing only whitespaces are skipped.

    Parameters
    ----------
    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    ignore_comments : bool, default True
        Whether to skip lines beginning with '#'.

    Returns
    -------
    iterator
        Each item is a line from the file, as a string.
    """
    with PathGeneralizer.from_path(filename).open('r') as f:
        for line in f:
            line = line.strip()
            if line and not (ignore_comments and line.startswith('#')):
                yield line


def jload(filename: GeneralizedPath, **kwargs):
    """
    Load the contents of a JSON file.

    Parameters
    ----------
    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    **kwargs :
        Sent to `json.load`.

    Returns
    -------
    object
        Loaded object.
    """
    with PathGeneralizer.from_path(filename).open("r") as f:
        return json.load(f, **kwargs)


def jdump(data, filename: GeneralizedPath, *, indent: int | None = 2, **kwargs) -> None:
    """
    Dump an object to a JSON file.

    Parameters
    ----------
    data : object
        Object to dump.

    filename : str, pathlib.Path or PathGeneralizer
        The path of the file.
        Can also be a path to a remote resource (see PathGeneralizer).

    indent : int or None, default 2
        The indentation of the JSON representation.

    **kwargs :
        Sent to `json.dump`.

    Returns
    -------
    None
    """
    with PathGeneralizer.from_path(filename).open('w') as f:
        json.dump(data, f, indent=indent, **kwargs)
        f.write('\n')


@contextmanager
def with_temp_file(suffix: str = ""):
    """
    A context manager yielding a path to a new temporary file, deleting it upon exit.

    Parameters
    ----------
    suffix : str, default ""
        Suffix for the temporary file.
        A "." is NOT added between the name and the suffix.
    """
    filename = tempfile.mktemp(suffix=suffix)
    try:
        yield filename
    finally:
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except PermissionError:
                warnings.warn(f"Temporary file {filename} was not deleted!")
