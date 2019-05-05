"""
The unit test module for util.
"""
import shutil
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
    ret = util.safe_eval('[sin(x) for x in range(3)]')
    assert ret is None


def test_copy_dir(mocker):
    #pylint:disable=missing-docstring

    # Normal copy
    patcher = mocker.patch('shutil.copytree', return_value=None)
    assert util.copy_dir('a', 'b')
    patcher.assert_called_once()

    # Encounter errors
    patcher.side_effect = shutil.Error()
    assert not util.copy_dir('a', 'b')
    patcher.side_effect = OSError()
    assert not util.copy_dir('a', 'b')
