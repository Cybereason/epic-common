import re
import builtins

import pytest

import epic
from epic.common.inspection import fullname, fullname2obj
from epic.common.importguard import ImportGuard, ImportGuardError


class TestFullname:
    def test_fullname(self):
        # a python stdlib module
        assert fullname(re) == 're'

        # a c stdlib module
        import _json
        assert fullname(_json) == '_json'
        assert fullname(_json.scanstring) == '_json.scanstring'

        # a third-party module and its members
        assert fullname(epic) == 'epic'
        assert fullname(epic.common) == 'epic.common'
        assert fullname(fullname) == 'epic.common.inspection.fullname'
        assert fullname(ImportGuard) == 'epic.common.importguard.ImportGuard'
        assert fullname(ImportGuardError) == 'epic.common.importguard.ImportGuardError'

        # builtin objects
        assert fullname(str) == 'builtins.str'
        assert fullname(object) == 'builtins.object'
        assert fullname(type) == 'builtins.type'

        # things in __main__
        import __main__
        exec("class MainClass: pass", __main__.__dict__)
        from __main__ import MainClass
        assert fullname(MainClass) == '__main__.MainClass'

        # methods and class methods
        from epic.common.pathgeneralizer import PathGeneralizer
        assert fullname(PathGeneralizer) == 'epic.common.pathgeneralizer.PathGeneralizer'
        assert fullname(PathGeneralizer.from_path) == 'epic.common.pathgeneralizer.PathGeneralizer.from_path'
        assert fullname(PathGeneralizer._supports) == 'epic.common.pathgeneralizer.PathGeneralizer._supports'
        assert fullname(PathGeneralizer.exists) == 'epic.common.pathgeneralizer.PathGeneralizer.exists'

        # class instance
        with pytest.raises(ValueError):
            fullname(ImportGuard(''))

        # simple values
        for value in ['str', 123, None]:
            with pytest.raises(ValueError):
                fullname(value)

    def test_fullname2obj(self):
        assert fullname2obj('epic.common.inspection.fullname2obj') == fullname2obj
        assert fullname2obj('epic.common.inspection') == epic.common.inspection
        assert fullname2obj('epic.common') == epic.common
        assert fullname2obj('epic') == epic
        assert fullname2obj('builtins') == builtins
        assert fullname2obj('builtins.str') == builtins.str == str
        # quopri was chosen to be a module that was definitely not imported until this call
        assert fullname2obj('quopri.decode').__name__ == 'decode'
        with pytest.raises(AttributeError, match="module 'epic.common.inspection' has no attribute 'obj2fullname'"):
            fullname2obj("epic.common.inspection.obj2fullname")
        with pytest.raises(ModuleNotFoundError, match="No module named 'epic.common.antigravity'"):
            fullname2obj("epic.common.antigravity.minus_g")
        with pytest.raises(ModuleNotFoundError, match="No module named 'cipe'"):
            fullname2obj("cipe.nommoc.noitcepsni.emanlluf2jbo")
        with pytest.raises(ModuleNotFoundError, match=re.escape("No module named '***'")):
            fullname2obj("***")
