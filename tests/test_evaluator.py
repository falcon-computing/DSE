"""
The unit test module for evaluator.
"""
import os
import re
import shutil

import pytest

from autodse import logger
from autodse.evaluator import evaluator

LOG = logger.get_logger('UNIT-TEST')


@pytest.fixture
def test_dir(request):
    #pylint:disable=missing-docstring

    file_path = request.module.__file__
    return os.path.abspath(os.path.join(file_path, os.pardir))


def test_evaluator_phase1(test_dir, mocker):
    #pylint:disable=redefined-outer-name
    """Test evaluator from initialization to deisgn point application"""

    # Initialization failure due to no auto pragmas
    with pytest.raises(RuntimeError):
        eval_ins = evaluator.Evaluator('{0}/fixture/eval_src0'.format(test_dir),
                                       '{0}/temp_eval_work'.format(test_dir))

    # Create and initialize evaluator
    eval_ins = evaluator.Evaluator('{0}/fixture/eval_src1'.format(test_dir),
                                   '{0}/temp_eval_work'.format(test_dir))
    assert len(eval_ins.src_files) == 1 and eval_ins.src_files[0] == 'kernel1.cpp'

    # Create a job
    job_path = eval_ins.create_job()
    assert job_path is not None and len(os.listdir(job_path)) == 2

    # Apply a design point successfully
    point = {'PE': 4, 'R': ''}
    assert eval_ins.apply_design_point(job_path, point)
    with open('{0}/kernel1.cpp'.format(job_path), 'r') as filep:
        assert not re.findall(r'(auto{(.*?)})', filep.read(), re.IGNORECASE)

    # Apply design point with missing parameter in the config
    job_path = eval_ins.create_job()
    point = {'PE': 4}
    assert eval_ins.apply_design_point(job_path, point)

    # Fail to apply design point due to miss parameter in the kernel file
    job_path = eval_ins.create_job()
    point = {'PE': 4, 'R': '', 'some_param': 1}
    assert not eval_ins.apply_design_point(job_path, point)

    # Fail to create a job due to OS error when copying files
    mocker.patch('autodse.evaluator.evaluator.copy_dir', return_value=False)
    assert eval_ins.create_job() is None

    shutil.rmtree('{0}/temp_eval_work'.format(test_dir))
