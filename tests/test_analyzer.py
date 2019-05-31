"""
The unit test module for analyzer.
"""
import os
import shutil

from autodse import logger
from autodse.util import copy_dir
from autodse.evaluator.analyzer import MerlinAnalyzer
from autodse.evaluator.evaluator import Job
from autodse.result import Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_merlin_analyzer(test_dir):
    #pylint:disable=missing-docstring, redefined-outer-name

    LOG.debug('=== Testing MerlinAnalyzer start')

    # Make up a config
    config = {'max-util': {'BRAM': 0.8, 'DSP': 0.8, 'FF': 0.8, 'LUT': 0.8}}

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
    job.status = Job.Status.APPLIED

    # Merlin transform failure (no merlin.log was generated)
    result = MerlinAnalyzer.analyze(job, 'transform', config)
    assert not result

    # Merlin transform failure (merlin.log has errors)
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('ERROR: [MERCC-3060] Merlin flow stopped with error(s).\n')
        filep.write('Total time: 6.78 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'transform', config)
    assert not result

    # Merlin transform w/o critical messages
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 65.50 seconds\n')
    lc_path = os.path.join(job_path, '.merlin_prj/run/implement/export/lc')
    os.makedirs(lc_path, exist_ok=True)
    with open(os.path.join(lc_path, '__merlinkerneltest.cpp'), 'w') as filep:
        filep.write('#include<string>\n')
        filep.write('    //Original: #pragma ACCEL pipeline flatten\n')
        filep.write('for (int i = 0; i < 256; ++i) {\n')
        filep.write('    #pragma HLS unroll\n')
        filep.write('    a[i] = b[i];\n')
        filep.write('}\n')
    result = MerlinAnalyzer.analyze(job, 'transform', config)
    assert result is not None
    assert not result.criticals
    assert result.code_hash
    old_code_hash = result.code_hash
    assert result.valid
    assert result.eval_time == 65.50

    # Merlin transform with duplications
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 78.40 seconds\n')
    with open(os.path.join(lc_path, '__merlinkerneltest.cpp'), 'w') as filep:
        filep.write('#include<string>\n')
        filep.write('  //Original: #pragma ACCEL parallel factor=256\n')
        filep.write('for (int i = 0; i < 256; ++i) {\n')
        filep.write('  #pragma HLS unroll\n')
        filep.write('  a[i] = b[i];\n')
        filep.write('}\n')
    result = MerlinAnalyzer.analyze(job, 'transform', config)
    assert result is not None
    assert result.valid
    assert result.code_hash and result.code_hash == old_code_hash

    # Merlin transform with critical messages
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write("WARNING: [BURST-205] Memory burst NOT inferred : variable 'v1' "
                    "(kernel1.cpp:4)in scope 'v1' (kernel1.cpp:14) with big on-chip buffer\n")
        filep.write("WARNING: [CGPIP-202] Coarse-grained pipelining NOT applied on loop\n")
        filep.write("WARNING: [CGPAR-201] Coarse-grained parallelization NOT applied: loop\n")
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 78.40 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'transform', config)
    assert result is not None
    assert not result.valid
    assert len(result.criticals) == 3
    assert result.eval_time == 78.40

    # Copy prepared HLS reports to pretend we have passed the HLS
    # Note that we fake the DSP resource util (which should be 0) to test out of resource.
    hls_ref_path = os.path.join(test_dir, 'temp_fixture/anal_rpts0')
    job_rpt_path = os.path.join(job.path, '.merlin_prj/run/implement/exec/hls/report_merlin')
    topo_path = os.path.join(job.path,
                             '.merlin_prj/run/implement/exec/hls/report_merlin/gen_token')
    os.makedirs(job_rpt_path, exist_ok=True)
    os.makedirs(topo_path, exist_ok=True)
    shutil.copy(os.path.join(hls_ref_path, 'final_info.json'), job_rpt_path)
    shutil.copy(os.path.join(hls_ref_path, 'hierarchy.json'), job_rpt_path)
    shutil.copy(os.path.join(hls_ref_path, 'topo_info.json'), topo_path)
    with open(os.path.join(job_path, 'merlin.log'), 'w') as filep:
        filep.write('INFO: [MERCC-1040] Compilation finished successfully\n')
        filep.write('Total time: 65.50 seconds\n')
        filep.write('INFO: [MERCC-1026] Estimation successfully.\n')
        filep.write('Total time: 26.12 seconds\n')
    result = MerlinAnalyzer.analyze(job, 'hls', config)
    assert result is not None

    assert abs(result.quality - 0.00055) < 1e-5
    assert result.perf == 1800.0
    assert result.eval_time == 91.62
    print(result.res_util)
    assert abs(result.res_util['util-BRAM'] - 0.0320032) < 0.01
    # Note that we manually modified the DSP utilization for testing
    assert abs(result.res_util['util-DSP'] - 0.99) < 0.01
    assert abs(result.res_util['util-LUT'] - 0.00732098) < 0.01
    assert abs(result.res_util['util-FF'] - 0.0070664) < 0.01
    assert result.res_util['total-BRAM'] == 81
    assert result.res_util['total-DSP'] == 0
    assert result.res_util['total-LUT'] == 5766
    assert result.res_util['total-FF'] == 11131

    # Hotspot analysis should output 4 hierarchy paths and each path should have 3 components
    assert len(result.ordered_paths) == 4
    assert all([len(path) == 3 for path in result.ordered_paths])

    # The first path should be computation bound
    assert all([node.is_compute_bound for node in result.ordered_paths[0]])

    # The rest paths should be memory bound except for the last component
    LOG.info(result.ordered_paths[1])
    assert len([node for node in result.ordered_paths[1] if node.is_compute_bound]) == 1
    assert len([node for node in result.ordered_paths[2] if node.is_compute_bound]) == 1
    assert len([node for node in result.ordered_paths[3] if node.is_compute_bound]) == 1

    # Result is invalid due to out of DSP utilization
    assert not result.valid

    # Test scope analysis with a fake auto map
    auto_map = {
        'kernel1.cpp:6': ['auto-in-top1', 'auto-in-top2'],
        'kernel1.cpp:7': ['auto-in-top3'],
        'kernel2.cpp:2': ['auto-not-for-loop']
    }
    scope_map = MerlinAnalyzer.analyze_scope(job, auto_map)
    assert len(scope_map) == 4
    LOG.info(scope_map)
    assert 'auto-in-top1' in scope_map and scope_map['auto-in-top1'] == 'L_0_0_0_2_2_0_2'
    assert 'auto-in-top2' in scope_map and scope_map['auto-in-top2'] == 'L_0_0_0_2_2_0_2'
    assert 'auto-in-top3' in scope_map and scope_map['auto-in-top3'] == 'L_0_0_0_2_2_0_2'
    assert 'auto-not-for-loop' in scope_map and scope_map['auto-not-for-loop'] == 'UNKNOWN'

    # Test bitgen log analysis
    bitgen_log_path = os.path.join(test_dir, 'temp_fixture/anal_rpts1')
    shutil.copy(os.path.join(bitgen_log_path, 'success.log'), os.path.join(job.path, 'merlin.log'))
    result = MerlinAnalyzer.analyze(job, 'bitgen', config)
    assert result is not None
    assert result.valid
    assert result.freq > 0
    assert any([v > 0 for k, v in result.res_util.items() if k.startswith('util')])

    shutil.copy(os.path.join(bitgen_log_path, 'fail.log'), os.path.join(job.path, 'merlin.log'))
    result = MerlinAnalyzer.analyze(job, 'bitgen', config)
    assert result is not None
    assert not result.valid
    assert result.ret_code == Result.RetCode.UNAVAILABLE

    LOG.debug('=== Testing MerlinAnalyzer end')
