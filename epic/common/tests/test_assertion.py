import pytest

from epic.common.assertion import assert_type, assert_types


class TestAssertType:
    def test_basic(self):
        assert assert_type(1, int) is None
        with pytest.raises(TypeError):
            assert_type(1, float)

    def test_tuple(self):
        assert assert_type(1, (int, float)) is None
        with pytest.raises(TypeError):
            assert_type(1, (float, complex))

    def test_union(self):
        assert assert_type(1, int | float) is None
        with pytest.raises(TypeError):
            assert_type(1, float | complex)


def test_decorator():
    @assert_types(x=int, y=float | None)
    def f(x, y, z):
        pass

    assert f(1, 2.3, 'asdf') is None
    assert f(1, None, None) is None
    with pytest.raises(TypeError):
        f(3.14, 2.7, 'qwerty')
        f(1, 'zxc', None)
