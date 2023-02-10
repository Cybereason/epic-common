import pytest

from epic.common.importguard import ImportGuard, ImportGuardError


def test_import_error():
    assert issubclass(ImportGuardError, ImportError)


def test_successful_import():
    with ImportGuard("hint"):
        import os
    assert os


def test_failed_import():
    hint = "this is my installation hint"
    with pytest.raises(ImportGuardError, match=hint):
        with ImportGuard(hint):
            import no_such_module
