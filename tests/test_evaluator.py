"""
The unit test module for evaluator.
"""
import os
import re
import shutil

import pytest

from autodse import database, logger
from autodse.evaluator import analyzer, scheduler
from autodse.evaluator.evaluator import BackupMode, Evaluator, MerlinEvaluator
from autodse.result import BitgenResult, HLSResult, MerlinResult, Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


@pytest.fixture(scope="function")
def required_args(mocker):
    #pylint:disable=missing-docstring

    def mock_run(jobs, keep_files, cmd, timeout):
        #pylint:disable=missing-docstring,unused-argument
        return [(job.key, Result.RetCode.PASS) for job in jobs]

    sche = scheduler.Scheduler()
    mocker.patch.object(sche, 'run', new=mock_run)

    args = {}
    args['db'] = database.PickleDatabase('pickleDB_test')
    args['scheduler'] = sche
    args['analyzer_cls'] = analyzer.MerlinAnalyzer
    args['dse_config'] = {}
    return args


def test_evaluator_phase1(required_args, test_dir, mocker):
    #pylint:disable=redefined-outer-name
    """Test evaluator from initialization to deisgn point application"""

    LOG.debug('=== Testing evaluator phase 1 start')

    # Initialization failure due to no auto pragmas
    with pytest.raises(SystemExit):
        eval_ins = Evaluator('{0}/temp_fixture/eval_src0'.format(test_dir),
                             '{0}/temp_eval_work'.format(test_dir), required_args['db'],
                             required_args['scheduler'], required_args['analyzer_cls'],
                             BackupMode.NO_BACKUP, required_args['dse_config'])

    # Create and initialize evaluator
    eval_ins = Evaluator('{0}/temp_fixture/eval_src1'.format(test_dir),
                         '{0}/temp_eval_work'.format(test_dir), required_args['db'],
                         required_args['scheduler'], required_args['analyzer_cls'],
                         BackupMode.NO_BACKUP, required_args['dse_config'])
    assert len(eval_ins.src_files) == 1 and eval_ins.src_files[0] == 'src/kernel1.cpp'
    assert 'kernel1.cpp:6' in eval_ins.auto_map and len(eval_ins.auto_map['kernel1.cpp:6']) == 2

    # Create a job
    job = eval_ins.create_job()
    assert job is not None and len([f for _, _, f in os.walk(job.path)]) == 2

    # Apply a design point successfully
    point = {'PE': 4, 'R': ''}
    assert eval_ins.apply_design_point(job, point)
    assert job.point is not None
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
                               '{0}/temp_eval_work'.format(test_dir), required_args['db'],
                               required_args['scheduler'], required_args['analyzer_cls'],
                               BackupMode.NO_BACKUP, required_args['dse_config'])

    # Test timeout setup, although we will not use it in this test
    eval_ins.set_timeout({'transform': 3, 'hls': 30, 'bitgen': 480})

    # Submit for evaluation (FAST)
    with mocker.patch.object(eval_ins.analyzer, 'desire', return_value=[]):

        def mock_analyze_ok(job, mode, config):
            #pylint:disable=unused-argument
            if mode == 'transform':
                result = MerlinResult()
                result.code_hash = job.point['PE']  # Pretend this is a code hash
            elif mode == 'hls':
                result = HLSResult()
            else:
                result = BitgenResult()
            result.valid = True
            return result

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_ok):
            # Fail due to miss setting up the command
            job0 = eval_ins.create_job()
            point = {'PE': 3, 'R': ''}
            eval_ins.apply_design_point(job0, point)
            results = eval_ins.submit([job0], 1)
            assert results[0][1].ret_code == Result.RetCode.UNAVAILABLE
            assert not eval_ins.build_scope_map()

            # Set up commands and re-submit, although we have mocked the execution so
            # those commands will not be executed in this test.
            eval_ins.set_command({
                'transform': 'make mcc_acc',
                'hls': 'make mcc_estimate',
                'bitgen': 'make mcc_bitgne'
            })
            job0 = eval_ins.create_job()
            point = {'PE': 3, 'R': ''}
            eval_ins.apply_design_point(job0, point)
            results = eval_ins.submit([job0], 1)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert eval_ins.db.count() == 1

            job0 = eval_ins.create_job()
            point = {'PE': 3, 'R': ''}
            eval_ins.apply_design_point(job0, point)
            results = eval_ins.submit([job0], 2)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert eval_ins.db.count() == 2

            # Submit another job with the same code hash to level 1 and 2
            job1 = eval_ins.create_job()
            point = {'PE': 3, 'R': 'reduction=a'}
            eval_ins.apply_design_point(job1, point)
            results = eval_ins.submit([job1], 1)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert eval_ins.db.count() == 3

            job1 = eval_ins.create_job()
            point = {'PE': 3, 'R': 'reduction=a'}
            eval_ins.apply_design_point(job1, point)
            results = eval_ins.submit([job1], 2)
            assert results[0][1].ret_code == Result.RetCode.DUPLICATED
            assert results[0][1].point['R'] == 'reduction=a'
            assert eval_ins.db.count() == 4

        with mocker.patch('autodse.evaluator.analyzer.MerlinAnalyzer.analyze_scope',
                          return_value={}):
            # Test build scope
            assert eval_ins.build_scope_map()
            assert eval_ins.db.count() == 5

        def mock_analyze_fail1(job, mode, config):
            #pylint:disable=unused-argument
            """Transform failure"""
            return None

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_fail1):
            # Fail to analyze transformation result
            job2 = eval_ins.create_job()
            point = {'PE': 5, 'R': ''}
            eval_ins.apply_design_point(job2, point)
            results = eval_ins.submit([job2], 1)
            assert results[0][1].ret_code == Result.RetCode.ANALYZE_ERROR
            assert eval_ins.db.count() == 6

            # No backup so the job directory should be gone
            assert not os.path.exists(job2.path)

        eval_ins.backup_mode = BackupMode.BACKUP_ERROR

        def mock_analyze_fail2(job, mode, config):
            #pylint:disable=unused-argument
            """HLS failure"""
            if mode == 'transform':
                result = MerlinResult()
                result.valid = True
                return result
            return None

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_fail2):
            # Fail to analyze HLS result
            job3 = eval_ins.create_job()
            point = {'PE': 6, 'R': ''}
            eval_ins.apply_design_point(job3, point)
            results = eval_ins.submit([job3], 2)
            assert results[0][1].ret_code == Result.RetCode.ANALYZE_ERROR
            assert os.path.exists(job3.path)
            assert eval_ins.db.count() == 7

        def mock_analyze_fail3(job, mode, config):
            #pylint:disable=unused-argument
            """Transform has errors"""
            if mode == 'transform':
                result = MerlinResult()
                result.criticals.append('memory_burst_failed')
                return result
            if mode == 'hls':
                return HLSResult()
            return BitgenResult()

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_fail3):
            # Fail to pass Merlin transform (early reject)
            job4 = eval_ins.create_job()
            point = {'PE': 7, 'R': ''}
            eval_ins.apply_design_point(job4, point)
            results = eval_ins.submit([job4], 1)
            assert results[0][1].ret_code == Result.RetCode.EARLY_REJECT
            assert not os.path.exists(job4.path)
            assert eval_ins.db.count() == 8

        def mock_analyze_fail4(job, mode, config):
            #pylint:disable=unused-argument
            """HLS runs out of resource"""
            if mode == 'transform':
                result = MerlinResult()
                result.valid = True
            elif mode == 'hls':
                result = HLSResult()
                result.valid = False
            return result

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_fail4):
            # HLS result is invalid
            job5 = eval_ins.create_job()
            point = {'PE': 7, 'R': ''}
            eval_ins.apply_design_point(job5, point)
            results = eval_ins.submit([job5], 2)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert not results[0][1].valid
            assert eval_ins.db.count() == 9

    LOG.debug('=== Testing evaluator phase 2 end')


def test_evaluator_phase3(required_args, test_dir, mocker):
    #pylint:disable=redefined-outer-name
    """Test evaluator of bitgen"""

    LOG.debug('=== Testing evaluator phase 3 start')

    # Create and initialize evaluator and a job
    eval_ins = MerlinEvaluator('{0}/temp_fixture/eval_src1'.format(test_dir),
                               '{0}/temp_eval_work'.format(test_dir), required_args['db'],
                               required_args['scheduler'], required_args['analyzer_cls'],
                               BackupMode.NO_BACKUP, required_args['dse_config'])

    # Test timeout setup and command, although we will not use them in this test
    eval_ins.set_timeout({'transform': 3, 'hls': 30, 'bitgen': 480})
    eval_ins.set_command({'bitgen': 'make mcc_bitgne'})

    # Submit for evaluation (ACCURATE)
    with mocker.patch.object(eval_ins.analyzer, 'desire', return_value=[]):

        def mock_analyze_ok(job, mode, config):
            #pylint:disable=unused-argument
            result = BitgenResult()
            result.freq = 300.0
            result.valid = True
            return result

        with mocker.patch.object(eval_ins.analyzer, 'analyze', side_effect=mock_analyze_ok):
            job0 = eval_ins.create_job()
            point = {'PE': 3, 'R': ''}
            eval_ins.apply_design_point(job0, point)

            # No quality due to the miss of HLS result
            results = eval_ins.submit([job0], 3)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert results[0][1].freq == 300.0
            assert results[0][1].quality == -float('inf')
            assert eval_ins.db.count() == 1

            # Fake a HLS result and commit to DB
            fake_hls_result = HLSResult()
            fake_hls_result.valid = True
            fake_hls_result.perf = 10e6
            eval_ins.db.commit('lv2:PE-3.R-NA', fake_hls_result)

            # With quality by borrowing the HLS cycle
            job1 = eval_ins.create_job()
            eval_ins.apply_design_point(job1, point)
            results = eval_ins.submit([job1], 3)
            assert results[0][1].ret_code == Result.RetCode.PASS
            assert results[0][1].quality != -float('inf')
            assert eval_ins.db.count() == 2

    LOG.debug('=== Testing evaluator phase 3 end')
