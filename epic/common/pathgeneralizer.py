import os
import re
import shutil

from pathlib import Path
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager, AbstractContextManager
from typing import Union, TypeVar, IO, Literal, get_args, TypeAlias

from .importguard import ImportGuard


PG = TypeVar('PG', bound="PathGeneralizer")
GeneralizedPath: TypeAlias = Union[str, Path, "PathGeneralizer"]

_ProxyMode: TypeAlias = Literal['r', 'w', 'rw']


class PathGeneralizer(metaclass=ABCMeta):
    """
    An abstract class representing a path that can either be to a local file, or another remote resource.
    The object can be opened, read, written to, etc.
    The decision on the actual type of the object is done by inspecting the format of the path string provided.
    For example, a path starting with "gs://" is assumed to be located in Google cloud storage.

    Use the `from_path` factory class method to instantiate.
    """
    subclasses: list[type["PathGeneralizer"]] = []

    @classmethod
    def from_path(cls, path: GeneralizedPath) -> "PathGeneralizer":
        """
        Instantiate a PathGeneralizer.

        Parameters
        ----------
        path : str, pathlib.Path or PathGeneralizer
            If a string or a Path object, it is the path to the generalized file.
            If a PathGeneralizer, it is returned as is.

        Returns
        -------
        PathGeneralizer
             An instance of a subclass of PathGeneralizer.

        Raises
        ------
        ValueError
            If no suitable subclass for the provided path could be chosen.
        """
        if isinstance(path, PathGeneralizer):
            return path
        if isinstance(path, Path):
            path = str(path)
        for sc in cls.subclasses:
            if sc._supports(path):
                return sc(path)
        raise ValueError("no subclass supports the path provided")

    def __init__(self, path: str):
        self.path = path

    @classmethod
    @abstractmethod
    def _supports(cls, path: str) -> bool:
        pass

    @abstractmethod
    def _proxy(self, mode: _ProxyMode) -> AbstractContextManager[str]:
        pass

    @abstractmethod
    def exists(self) -> bool:
        """
        Get whether a file exists in the path specified.

        Returns
        -------
        bool
            Whether a file exists in the generalized path.
        """
        pass

    @abstractmethod
    def open(self, mode: str) -> IO:
        """
        Mimic the builtin `open(...)` function semantics.

        Parameters
        ----------
        mode : str
            Similar to the `mode` argument of the builtin `open()` function.

        Returns
        -------
        IO
            A file-like object that can be used to access the contents of the file at the generalized path.
        """
        pass

    @abstractmethod
    def copy_to(self, local_path: str | Path) -> None:
        """
        Read the contents of the file at the generalized path and write them to a local path.

        Parameters
        ----------
        local_path : str or pathlib.Path
            An actual valid path on the local file system (note: a `PathGeneralizer` is not accepted here)

        Returns
        -------
        None
        """
        pass

    @abstractmethod
    def copy_from(self, local_path: str | Path) -> None:
        """
        Read contents from a local path and write them to a file at the generalized path.

        Parameters
        ----------
        local_path : str or pathlib.Path
            An actual valid path on the local file system (note: a `PathGeneralizer` is not accepted here)

        Returns
        -------
        None
        """

    @classmethod
    def register(cls, subclass: type[PG]) -> type[PG]:
        """
        Register a `PathGeneralizer` subclass as a possible result of `PathGeneralizer.from_path()`.

        Use this as a decorator for the class.
        """
        cls.subclasses.append(subclass)
        return subclass

    def read_proxy(self):
        """
        A context manager providing a temporary read-only local copy of the file at the generalized path.

        Returns
        -------
        contextmanager[str]
            A context manager yielding the local path

        Examples
        --------
        >>> with PathGeneralizer.from_path("gs://my-bucket/some_file.txt").read_proxy() as local_path:
        ...     some_data = open(local_path).read()

        Warnings
        --------
        Any changes made to the file will be discarded upon exit. For a read-write alternative, see `read_write_proxy`.
        """
        return self._proxy('r')

    def write_proxy(self):
        """
        A context manager providing a temporary write-only local path, to be copied to the generalized path upon exit.

        Returns
        -------
        contextmanager[str]
            A context manager yielding the local path

        Examples
        --------
        >>> with PathGeneralizer.from_path("gs://my-bucket/existing_file.txt").write_proxy() as local_path:
        ...     assert not os.path.exists(local_path)
        ...     open(local_path, "w").write("this will be the contents of the new file")
        """
        return self._proxy('w')

    def read_write_proxy(self):
        """
        A context manager providing a temporary read-write local copy of the file at the generalized path, which will be
        copied to the generalized path upon exit.

        Returns
        -------
        contextmanager[str]
            A context manager yielding the local path

        Examples
        --------
        >>> with PathGeneralizer.from_path("gs://my-bucket/existing_file.txt").read_write_proxy() as local_path:
        ...     existing_data = open(local_path).read()
        ...     open(local_path, "w").write("this will overwrite the contents of the file")
        """
        return self._proxy('rw')

    def read(self, mode: str, size: int = -1) -> str | bytes:
        """
        Read the contents of the file at the generalized path.

        Parameters
        ----------
        mode : str
            Similar to the builtin `open(...)`, this can be "r", "rw", "rb", "w", "a", "r+" etc.
        size : int, optional
            Number of characters / bytes to read from the file (default: all).

        Returns
        -------
        str or bytes
            The contents that were read.
        """
        with self.read_proxy() as filepath, open(filepath, mode) as f:
            return f.read(size)

    def write(self, data: str | bytes, mode: str) -> None:
        """
        Write to the file at the generalized path.

        Parameters
        ----------
        data : str or bytes
            The contents to be written.
        mode : str
            Similar to `open(...)`, this can be "r", "rw", "rb", "w", "a", "r+" etc.

        Returns
        -------
        None
        """
        with self.write_proxy() as filepath, open(filepath, mode) as f:
            f.write(data)


@PathGeneralizer.register
class GoogleCloudStoragePath(PathGeneralizer):
    """
    A PathGeneralizer representing objects stored in Google cloud storage.
    """
    URI_REGEX = re.compile(r"^gs://([^/]+)/(.+)$")

    _cached_gs_client = None
    _cached_gs_client_pid = None

    @classmethod
    def _supports(cls, path: str) -> bool:
        return cls.URI_REGEX.match(path) is not None

    @contextmanager
    def _proxy(self, mode: _ProxyMode):
        # Avoid a circular import
        from .io import with_temp_file
        assert mode in get_args(_ProxyMode)
        with with_temp_file(".gs") as filepath:
            if 'r' in mode:
                self.copy_to(filepath)
            yield filepath
            if 'w' in mode:
                self.copy_from(filepath)

    def open(self, mode: str) -> IO:
        return self._gs_blob().open(mode)

    def exists(self) -> bool:
        return self._gs_blob().exists()

    @classmethod
    def _gs_client(cls):
        if cls._cached_gs_client is None or cls._cached_gs_client_pid != os.getpid():
            with ImportGuard("pip install google-cloud-storage"):
                from google.cloud import storage
            cls._cached_gs_client = storage.Client()
            cls._cached_gs_client_pid = os.getpid()
        return cls._cached_gs_client

    def _gs_blob(self):
        bucket_name, path = self.URI_REGEX.match(self.path).groups()
        return self._gs_client().bucket(bucket_name).blob(path)

    def read(self, mode, size=-1) -> str | bytes:
        with self.open(mode) as f:
            return f.read(size)

    def write(self, data: str | bytes, mode: str) -> None:
        self._gs_blob().upload_from_string(data)

    def copy_to(self, local_path: str | Path) -> None:
        self._gs_blob().download_to_filename(str(local_path), raw_download=True)

    def copy_from(self, local_path: str | Path) -> None:
        self._gs_blob().upload_from_filename(str(local_path))


@PathGeneralizer.register
class FileSystemPath(PathGeneralizer):
    """
    A PathGeneralizer representing objects in the local file system.
    """
    EXCLUDED_URI_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

    @classmethod
    def _supports(cls, path: str) -> bool:
        # Generally speaking, different file systems could support wildly different valid paths.
        # We opt to accept most anything as long as it doesn't look too much like a URI (starting with `scheme://`)
        return (
            path and
            path == path.strip() and
            not re.match(cls.EXCLUDED_URI_REGEX, path)
        )

    @contextmanager
    def _proxy(self, mode: str):
        yield self.path

    def open(self, mode: str) -> IO:
        return open(self.path, mode)

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def copy_to(self, local_path: str | Path) -> None:
        shutil.copy(self.path, local_path)

    def copy_from(self, local_path: str | Path) -> None:
        shutil.copy(local_path, self.path)
