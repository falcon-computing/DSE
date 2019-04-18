"""
The unit test module for util.
"""
import pytest

from autodse import util

def test_save_eval():
    #pylint:disable=missing-docstring
    # Basic
    ret = util.safe_eval('[1,2,3,4,5]')
    assert ret == [1, 2, 3, 4, 5]

    # Has dependency
    ret = util.safe_eval('[x for x in [1,2,3,4,5] if x==1 or y==1]', {'y': 2})
    assert ret == [1]

    # Use builtin functions
    ret = util.safe_eval('range(3)')
    assert ret == range(3)
    ret = util.safe_eval('[ceil(x) for x in range(3)]')
    assert ret == [0, 1, 2]

    # Use not allowed builtins
    with pytest.raises(NameError):
        ret = util.safe_eval('[sin(x) for x in range(3)]')
