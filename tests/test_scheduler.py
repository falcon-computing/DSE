"""
The unit test module for scheduler.
"""
import os
import shutil

from autodse import logger
from autodse.result import Result
from autodse.util import copy_dir
from autodse.evaluator.evaluator import Job
from autodse.evaluator.scheduler import PythonSubprocessScheduler

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_python_scheduler(test_dir):
    #pylint:disable=missing-docstring, redefined-outer-name

    LOG.debug('=== Testing PythonSubprocessScheduler start')

    work_path = os.path.join(test_dir, 'temp_sche_work')
    if os.path.exists(work_path):
        shutil.rmtree(work_path)
    os.mkdir(work_path)

    # Create multiple jobs and make them ready for evaluation
    jobs = []
    ref_path = os.path.join(test_dir, 'temp_fixture/eval_src1')
    for i in range(8):
        job_path = os.path.join(work_path, 'job{0}'.format(i))
        copy_dir(ref_path, job_path)
        job = Job(job_path)
        job.key = 'job{0}'.format(i)
        job.status = Job.Status.APPLIED
        jobs.append(job)

    # Scheduler with non-dividable workers
    sche = PythonSubprocessScheduler(3)
    sche.run(jobs[:4], ['bin/test'], 'make run; mkdir bin; mv test bin/')
    assert all([os.path.exists(os.path.join(job.path, 'bin/test')) for job in jobs[:4]])

    # Scheduler with dividable workers and keep files with a wildcard
    sche = PythonSubprocessScheduler(4)
    sche.run(jobs[4:], ['bin/test*'], 'make run; mkdir bin; cp test bin/test; cp test bin/test2')
    assert all([os.path.exists(os.path.join(job.path, 'bin/test')) for job in jobs[4:]])
    assert all([os.path.exists(os.path.join(job.path, 'bin/test2')) for job in jobs[4:]])

    # Create another set of jobs which never finish
    jobs = []
    ref_path = os.path.join(test_dir, 'temp_fixture/eval_src2')
    for i in range(8, 10):
        job_path = os.path.join(work_path, 'job{0}'.format(i))
        copy_dir(ref_path, job_path)
        job = Job(job_path)
        job.key = 'job{0}'.format(i)
        job.status = Job.Status.APPLIED
        jobs.append(job)

    # Timeout
    rets = sche.run(jobs[:2], ['test'], 'make', 0.05)
    assert all([ret == Result.RetCode.TIMEOUT for _, ret in rets])

    # TODO: keyboard interrupt testing. Have no idea about how to test it.

    LOG.debug('=== Testing PythonSubprocessScheduler end')
