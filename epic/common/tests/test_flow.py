import pytest

from epic.common.flow import check, pragma_once, clone_and_apply


def test_check():
    check(1 == 1)
    check(1 == 1, "all is good")
    check(1 == 1, FileNotFoundError("no worries all is found"))
    with pytest.raises(Exception, match='^check failed$'):
        check(False)
    with pytest.raises(Exception, match='^something went wrong$'):
        check(False, "something went wrong")
    with pytest.raises(Exception, match='^123$'):
        check(False, 123)
    with pytest.raises(FileNotFoundError, match='^where is my file$'):
        check(False, FileNotFoundError("where is my file"))


def test_pragma_once():
    a = []

    @pragma_once
    def append_to_a(n):
        a.append(n)
        return n

    assert len(a) == 0
    assert append_to_a(1) == 1
    assert len(a) == 1
    assert append_to_a(2) is None
    assert len(a) == 1

    @pragma_once
    def append_to_a(n):
        a.append(n)
        return n

    assert append_to_a(3) == 3
    assert len(a) == 2
    assert append_to_a(4) is None
    assert len(a) == 2


def test_clone_and_apply():
    class MyClass:
        def __init__(self, value):
            self.value = value
            self.this_does_not_change = id(self)
            self.internal_dict = {
                'key': 'value'
            }

        @clone_and_apply
        def with_new_value(self, another_value):
            self.value = another_value

    mc = MyClass(100)
    mc2 = mc.with_new_value(200)
    assert mc is not mc2
    assert mc.value == 100
    assert mc2.value == 200
    assert mc.this_does_not_change == mc2.this_does_not_change
    assert mc.this_does_not_change == id(mc)
    assert mc.this_does_not_change != id(mc2)
    assert mc.internal_dict == mc2.internal_dict
    assert mc.internal_dict is not mc2.internal_dict
