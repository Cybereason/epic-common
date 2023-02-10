class ImportGuardError(ImportError):
    pass


class ImportGuard:
    """
    A context manager used to provide a useful installation hint upon import failure.
    Useful when using external modules and packages without including them as explicit dependencies.

    Parameters
    ----------
    install_hint : str
        The string to display when an import statement fails within the context.

    Raises
    ------
    ImportGuardError
        If an import statement fails within the context.
        It is a subclass of ImportError.
    """
    def __init__(self, install_hint: str):
        self.install_hint = install_hint

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, ImportError):
            raise ImportGuardError("Error: %s | Installation hint: '%s'" % (str(exc_val), self.install_hint))
        return False
