"""
The unit test module for analyzer.
"""
import os
import shutil

from autodse import logger
from autodse.util import copy_dir
from autodse.evaluator.analyzer import MerlinAnalyzer
from autodse.evaluator.evaluator import Job

LOG = logger.get_logger('UNIT-TEST', 'DEBUG', True)


def test_merlin_analyzer(test_dir):
    #pylint:disable=missing-docstring, redefined-outer-name

    LOG.debug('=== Testing MerlinAnalyzer start')

    ref_path = os.path.join(test_dir, 'temp_fixture/eval_src0')
    work_path = os.path.join(test_dir, 'temp_anal_work')
    if os.path.exists(work_path):
        shutil.rmtree(work_path)
    os.mkdir(work_path)

    # Create a job and make it like evaluated
    job_path = os.path.join(work_path, 'job1')
    copy_dir(ref_path, job_path)
    job = Job(job_path)
    job.key = 'testing'
    job.status = Job.Status.EVALUATED

    # Merlin transform failure (no merlin.log was generated)
    result = MerlinAnalyzer.analyze(job, 'transform')
    assert not result

    # Merlin transform failure (merlin.log has errors)
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('ERROR: [MERCC-3060] Merlin flow stopped with error(s).\n')
        filep.write('Total time: 6.78 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'transform')
    assert not result

    # Merlin transform w/o critical messages
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 65.50 seconds\n')

    result = MerlinAnalyzer.analyze(job, 'transform')
    assert not result.criticals
    assert result.eval_time == 65.50

    # Merlin transform with critical messages
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write("WARNING: [BURST-205] Memory burst NOT inferred : variable 'v1' "
                    "(kernel1.cpp:4)in scope 'v1' (kernel1.cpp:14) with big on-chip buffer\n")
        filep.write("WARNING: [CGPIP-202] Coarse-grained pipelining NOT applied on loop\n")
        filep.write("WARNING: [CGPAR-201] Coarse-grained parallelization NOT applied: loop\n")
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 78.40 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'transform')
    assert result
    assert len(result.criticals) == 3
    assert result.eval_time == 78.40

    # Copy prepared HLS reports to pretend we have passed the HLS
    hls_ref_path = os.path.join(test_dir, 'temp_fixture/anal_rpts0')
    job_rpt_path = os.path.join(job.path, '.merlin_prj/run/implement/exec/hls/report_merlin')
    os.makedirs(job_rpt_path, exist_ok=True)
    shutil.copy(os.path.join(hls_ref_path, 'final_info.json'), job_rpt_path)
    shutil.copy(os.path.join(hls_ref_path, 'hierarchy.json'), job_rpt_path)
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 65.50 seconds\n')
        filep.write('INFO: [MERCC-1026] Estimation successfully.\n')
        filep.write('Total time: 26.12 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'hls')
    assert result
    assert result.perf == 196608.0
    assert result.eval_time == 91.62
    LOG.info([(k, u) for k, u in result.res_util.items()])
    assert abs(result.res_util['util-BRAM'] - 0.089) < 0.01
    assert abs(result.res_util['util-DSP'] - 0.0) < 0.01
    assert abs(result.res_util['util-LUT'] - 0.095) < 0.01
    assert abs(result.res_util['util-FF'] - 0.094) < 0.01
    assert result.res_util['total-BRAM'] == 226
    assert result.res_util['total-DSP'] == 0
    assert result.res_util['total-LUT'] == 74689
    assert result.res_util['total-FF'] == 147604

    LOG.debug('=== Testing MerlinAnalyzer end')
