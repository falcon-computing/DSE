"""
The main module of job schedulers.
"""
import os
import shutil
import signal
import time
from typing import List, Optional

from ..logger import get_eval_logger
from ..result import Job
from ..util import copy_dir

LOG = get_eval_logger('Scheduler')


class Scheduler():
    """The base class of job scheduler with API definitions"""

    def __init__(self, max_worker: int = 8):
        self.max_worker = max_worker

    def run(self, jobs: List[Job], keep_files: List[str], cmd: str,
            timeout: Optional[int] = None) -> List[bool]:
        """The main API of scheduling and running given jobs

        Parameters
        ----------
        job:
            A list of job objects to be scheduled.

        keep_files:
            A list of file name (support wildcards) to indicate which files
            should be kept for result analysis.

        cmd:
            A string of command for execution. Note that we may extend this part
            to another evaluation function instead of a single string in the future.

        timeout:
            The timeout in minutes of the evaluation. None means no timeout.

        Returns
        -------
        int:
            Indicate the number of success jobs.
        """
        raise NotImplementedError()


class PythonSubprocessScheduler(Scheduler):
    """The scheduler implementation using Python subprocess."""

    @staticmethod
    def backup_files_and_rmtree(src_path: str, dst_path: str, file_list: List[str]) -> None:
        """Backup files from working directory to the job directory and remove working directory

        Paramteters
        -----------
        src_path:
            The working directory.

        dst_path:
            The job directory.

        file_list:
            A list of files we want to keep.

        Returns
        -------
        None:
            This function is slient and will not check if the backup was success or not.
        """
        for file_name in file_list:
            try:
                dst_file = os.path.join(dst_path, file_name)
                dst_full_path = os.path.dirname(dst_file)
                if not os.path.exists(dst_full_path):
                    os.makedirs(dst_full_path)
                shutil.move(os.path.join(src_path, file_name), dst_file)
            except FileNotFoundError as err:
                LOG.error('Failed to copy %s to %s: %s', os.path.join(src_path, file_name),
                          dst_path, str(err))

        shutil.rmtree(src_path)

    def run(self, jobs: List[Job], keep_files: List[str], cmd: str,
            timeout: Optional[int] = None) -> List[bool]:
        #pylint: disable=missing-docstring

        from subprocess import Popen, DEVNULL

        rets = [False] * len(jobs)

        # Batch jobs when the number is larger than the max workers
        for batch in range(int(len(jobs) / self.max_worker) + 1):
            procs = []
            for offset in range(self.max_worker):
                idx = batch * self.max_worker + offset
                if idx >= len(jobs):
                    break
                copy_dir(jobs[idx].path, '{0}_work'.format(jobs[idx].path))

                # Since we use shell=True to launch a new bash in order to make sure the command
                # is executed as it in the bash shell, we need to also set start_new_session=True
                # in order to send the kill signal when timeout or interrupt because proc.kill()
                # is not working when shell=True.
                # See https://stackoverflow.com/questions/4789837 for details.
                proc = Popen('cd {0}_work; {1}'.format(jobs[idx].path, cmd),
                             stdout=DEVNULL,
                             stderr=DEVNULL,
                             shell=True,
                             start_new_session=True)
                procs.append((idx, proc))

            if not procs:
                break

            time_limit = float('inf') if timeout is None else timeout
            LOG.debug('Launching batch %d with %d jobs and timeout %.2f mins', batch, len(procs),
                      time_limit)
            timer = time.time()
            try:
                while (time.time() - timer) < time_limit * 60.0 and procs:
                    old_procs = list(procs)
                    procs = []
                    for idx, proc in old_procs:
                        ret = proc.poll()
                        if ret is not None:
                            # Finished, check if success, remove from list, and backup wanted files
                            rets[idx] = ret == 0
                            self.backup_files_and_rmtree('{0}_work'.format(jobs[idx].path),
                                                         jobs[idx].path, keep_files)
                        else:
                            # Still running
                            procs.append((idx, proc))
                    time.sleep(1)

                if procs:
                    # One or more processes are timeout.
                    # Note that timeout is considered as a success run
                    LOG.debug('%d processes timeout (%.2f mins)', len(procs), time_limit)
                    for idx, proc in procs:
                        rets[idx] = True
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        self.backup_files_and_rmtree('{0}_work'.format(jobs[idx].path),
                                                     jobs[idx].path, keep_files)
            except KeyboardInterrupt:
                LOG.warning('Received user keyboard interrupt, stopping the process.')
                for idx, proc in procs:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    self.backup_files_and_rmtree('{0}_work'.format(jobs[idx].path), jobs[idx].path,
                                                 keep_files)
                break

        return rets
