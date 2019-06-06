"""
The unit test module for the main entry.
"""

import os
import shutil

import pytest

from autodse import logger
from autodse.__main__ import Main
from autodse.result import BitgenResult, Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_main(test_dir, mocker):
    #pylint:disable=missing-docstring, redefined-outer-name

    mock_args = mocker.patch('autodse.main.arg_parser').return_value
    mock_args.src_dir = '{0}/temp_fixture/main_src'.format(test_dir)
    mock_args.work_dir = '{0}/temp_main_work'.format(test_dir)
    mock_args.config = '{0}/temp_fixture/main_src/config.json'.format(test_dir)
    mock_args.db = None

    # Check mode
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.mode = 'invalid-mode'
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    mock_args.mode = 'fast-check'

    # Src dir not found
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.src_dir = '{0}/temp_fixture/xxx'.format(test_dir)
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    # Set to right src dir
    mock_args.src_dir = '{0}/temp_fixture/main_src'.format(test_dir)

    # Work dir cannot contain src dir
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.work_dir = '{0}/temp_fixture'.format(test_dir)
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    # Work dir cannot be a sub-dir of src dir
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.work_dir = '{0}/temp_fixture/main_src/work'.format(test_dir)
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    # Set to right work dir
    mock_args.work_dir = '{0}/temp_main_work'.format(test_dir)

    # Config file not found
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.config = '{0}/temp_fixture/main_src/a.json'.format(test_dir)
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    # Config file is not a valid json file
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mock_args.config = '{0}/temp_fixture/main_src/Makefile'.format(test_dir)
        Main().main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    # Set to right config
    mock_args.config = '{0}/temp_fixture/main_src/config.json'.format(test_dir)

    # Test fast check
    mock_args.mode = 'fast-check'
    Main().main()

    # Test complete check with a pre-run DB
    mock_args.mode = 'complete-check'
    shutil.copy('{0}/temp_fixture/main_src/result.db'.format(test_dir),
                '{0}/check.db'.format(mock_args.work_dir))
    Main().main()

    # Test fast DSE with a pre-run DB
    mock_args.mode = 'fast-dse'
    shutil.copy('{0}/temp_fixture/main_src/result.db'.format(test_dir),
                '{0}/result.db'.format(mock_args.work_dir))
    Main().main()
    assert os.path.exists('{0}/temp_main_work/logs'.format(test_dir))
    assert os.path.exists('{0}/temp_main_work/summary_fast.rpt'.format(test_dir))
    assert os.path.exists('{0}/temp_main_work/result.db'.format(test_dir))
    assert os.path.exists('{0}/temp_main_work/output/fast'.format(test_dir))
    assert os.path.exists('{0}/temp_main_work/output/fast/output.rpt'.format(test_dir))
    with open('{0}/temp_main_work/output/fast/output.rpt'.format(test_dir), 'r') as filep:
        for line in filep:
            if line.startswith('|0'): # The best result has lower resource utilization
                assert line.find('45064192') != -1
                assert line.find('BRAM:11.0%') != -1
            elif line.startswith('|1'):
                assert line.find('45064192') != -1
                assert line.find('BRAM:21.0%') != -1

    def mock_submitter(jobs):
        #pylint:disable=missing-docstring

        ret = []
        for job in jobs:
            result = BitgenResult()
            result.ret_code = Result.RetCode.PASS
            result.path = job.path
            result.valid = True
            result.freq = 300.0
            result.perf = 45064192
            result.quality = 1.0 / (result.perf / result.freq)
            ret.append((job, result))
        return ret

    # Mock explorer to test the accurate DSE mode
    with mocker.patch('autodse.evaluator.evaluator.MerlinEvaluator.submit_lv3',
                      side_effect=mock_submitter):
        # Test accurate DSE
        mock_args.mode = 'accurate-dse'
        shutil.rmtree(mock_args.work_dir)
        os.makedirs(mock_args.work_dir)
        shutil.copy('{0}/temp_fixture/main_src/result.db'.format(test_dir),
                    '{0}/result.db'.format(mock_args.work_dir))
        Main().main()
        assert os.path.exists('{0}/temp_main_work/logs'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/summary_fast.rpt'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/summary_accurate.rpt'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/fast'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/fast/output.rpt'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/fast/2'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/result.db'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/accurate'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/accurate/output.rpt'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/accurate/2'.format(test_dir))
        assert os.path.exists('{0}/temp_main_work/output/best'.format(test_dir))
