"""
The unit test module for evaluator.
"""
import os
import re
import shutil

import pytest

from autodse import database, logger
from autodse.evaluator import analyzer, scheduler
from autodse.evaluator.evaluator import BackupMode, EvalMode, Evaluator, MerlinEvaluator
from autodse.result import BitgenResult, HLSResult, MerlinResult

LOG = logger.get_logger('UNIT-TEST', 'DEBUG', True)


@pytest.fixture(scope="function")
def required_args(mocker):
    #pylint:disable=missing-docstring

    def mock_run(jobs, keep_files, cmd, timeout):
        #pylint:disable=missing-docstring,unused-argument
        return [True] * len(jobs)

    sche = scheduler.Scheduler()
    mocker.patch.object(sche, 'run', new=mock_run)

    args = {}
    args['db'] = database.PickleDatabase('pickleDB_test')
    args['scheduler'] = sche
    args['analyzer_cls'] = analyzer.MerlinAnalyzer
    return args


def test_evaluator_phase1(required_args, test_dir, mocker):
    #pylint:disable=redefined-outer-name
    """Test evaluator from initialization to deisgn point application"""

    LOG.debug('=== Testing evaluator phase 1 start')

    # Initialization failure due to no auto pragmas
    with pytest.raises(RuntimeError):
        eval_ins = Evaluator('{0}/temp_fixture/eval_src0'.format(test_dir),
                             '{0}/temp_eval_work'.format(test_dir), EvalMode.FAST,
                             required_args['db'], required_args['scheduler'],
                             required_args['analyzer_cls'], BackupMode.NO_BACKUP)

    # Create and initialize evaluator
    eval_ins = Evaluator('{0}/temp_fixture/eval_src1'.format(test_dir),
                         '{0}/temp_eval_work'.format(test_dir), EvalMode.FAST, required_args['db'],
                         required_args['scheduler'], required_args['analyzer_cls'],
                         BackupMode.NO_BACKUP)
    assert len(eval_ins.src_files) == 1 and eval_ins.src_files[0] == 'src/kernel1.cpp'

    # Create a job
    job = eval_ins.create_job()
    assert job is not None and len([f for _, _, f in os.walk(job.path)]) == 2

    # Apply a design point successfully
    point = {'PE': 4, 'R': ''}
    assert eval_ins.apply_design_point(job, point)
    with open('{0}/src/kernel1.cpp'.format(job.path), 'r') as filep:
        assert not re.findall(r'(auto{(.*?)})', filep.read(), re.IGNORECASE)

    # Fail to re-apply another design point to the same job
    assert not eval_ins.apply_design_point(job, point)

    # Apply design point with missing parameter in the config
    job = eval_ins.create_job()
    point = {'PE': 4}
    assert eval_ins.apply_design_point(job, point)

    # Fail to apply design point due to miss parameter in the kernel file
    job = eval_ins.create_job()
    point = {'PE': 4, 'R': '', 'some_param': 1}
    assert not eval_ins.apply_design_point(job, point)

    # Fail to create a job due to OS error when copying files
    mocker.patch('autodse.evaluator.evaluator.copy_dir', return_value=False)
    assert eval_ins.create_job() is None

    shutil.rmtree('{0}/temp_eval_work'.format(test_dir))

    LOG.debug('=== Testing evaluator phase 1 end')


def test_evaluator_phase2(required_args, test_dir, mocker):
    #pylint:disable=redefined-outer-name
    """Test evaluator of running jobs and collect results"""

    LOG.debug('=== Testing evaluator phase 2 start')

    # Create and initialize evaluator and a job
    eval_ins = MerlinEvaluator('{0}/temp_fixture/eval_src1'.format(test_dir),
                               '{0}/temp_eval_work'.format(test_dir), EvalMode.FAST,
                               required_args['db'], required_args['scheduler'],
                               required_args['analyzer_cls'], BackupMode.NO_BACKUP)
    job = eval_ins.create_job()

    # Apply a design point
    point = {'PE': 4, 'R': ''}
    eval_ins.apply_design_point(job, point)

    def mock_analyze_ok(job, mode):
        if mode == 'transform':
            return MerlinResult(job.key)
        if mode == 'hls':
            return HLSResult(job.key)
        return BitgenResult(job.key)

    def mock_analyze_fail1(job, mode):
        #pylint:disable=unused-argument
        """Transform failure"""
        return None

    def mock_analyze_fail2(job, mode):
        """HLS failure"""
        if mode == 'transform':
            return MerlinResult(job.key)
        return None

    def mock_analyze_fail3(job, mode):
        """Transform has errors"""
        if mode == 'transform':
            result = MerlinResult(job.key)
            result.criticals.append('memory_burst_failed')
            return result
        if mode == 'hls':
            return HLSResult(job.key)
        return BitgenResult(job.key)

    # Submit for evaluation (FAST)
    mocker.patch.object(eval_ins.analyzer, 'desire', return_value=[])
    mocker.patch.object(eval_ins.analyzer, 'analyze', new=mock_analyze_ok)
    results = eval_ins.submit([job])
    assert results[0].ret_code == 0

    # Fail to analyze transformation result
    job2 = eval_ins.create_job()
    point = {'PE': 5, 'R': ''}
    eval_ins.apply_design_point(job2, point)
    mocker.patch.object(eval_ins.analyzer, 'analyze', new=mock_analyze_fail1)
    results = eval_ins.submit([job2])
    assert results[0].ret_code == -1

    # No backup so the job directory should be gone
    assert not os.path.exists(job2.path)

    eval_ins.backup_mode = BackupMode.BACKUP_ERROR

    # Fail to analyze HLS result
    job3 = eval_ins.create_job()
    point = {'PE': 6, 'R': ''}
    eval_ins.apply_design_point(job3, point)
    mocker.patch.object(eval_ins.analyzer, 'analyze', new=mock_analyze_fail2)
    results = eval_ins.submit([job3])
    assert results[0].ret_code == -1
    assert not os.path.exists(job3.path)
    assert os.path.exists('{0}/temp_eval_work/{1}'.format(test_dir, job3.key))

    # Fail to pass Merlin transform (early reject)
    job4 = eval_ins.create_job()
    point = {'PE': 7, 'R': ''}
    eval_ins.apply_design_point(job4, point)
    mocker.patch.object(eval_ins.analyzer, 'analyze', new=mock_analyze_fail3)
    results = eval_ins.submit([job4])
    assert results[0].ret_code == 0
    assert not os.path.exists(job4.path)

    LOG.debug('=== Testing evaluator phase 2 end')
