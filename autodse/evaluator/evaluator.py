"""
The main module of evaluator.
"""
import os
import re
import shutil
import tempfile
from enum import Enum
from typing import List, Optional, Set, Tuple, Type

from ..database import Database
from ..logger import get_logger
from ..parameter import DesignPoint, gen_key_from_design_point
from ..result import BitgenResult, HLSResult, Job, MerlinResult, ResultBase
from ..util import copy_dir
from .analyzer import Analyzer, MerlinAnalyzer
from .scheduler import Scheduler

LOG = get_logger('Evaluator')


class EvalMode(Enum):
    FAST = 0
    ACCURATE = 1
    PROFILE = 2


class Evaluator():
    """Main evaluator class"""

    def __init__(self,
                 src_path: str,
                 work_path: str,
                 mode: EvalMode,
                 db: Database,
                 scheduler: Scheduler,
                 analyzer_cls: Type[Analyzer],
                 temp_prefix: str = 'eval'):
        self.mode = mode
        self.db = db
        self.src_path = src_path
        self.work_path = work_path
        self.temp_dir_prefix = '{0}_'.format(temp_prefix)
        self.scheduler = scheduler
        self.analyzer = analyzer_cls

        if os.path.exists(self.work_path):
            shutil.rmtree(self.work_path, ignore_errors=True)
        os.mkdir(self.work_path)

        # Scan the folder and identify the files with design parameters (auto keyword)
        # Note that since we directly scan the text in source code, we will not know if
        # an auto keyword is in comments or macros. Now we expect these invalid parameters
        # will not have corresponding definitions in design point and will ignore them when
        # applying the design point. If a valid parameter does not have corresponding definition
        # in the design point, then the Merlin compiler will error out so we could let user know.
        self.src_files: List[str] = []
        for root, _, files in os.walk(src_path):
            for file_name in files:
                file_abs_path = os.path.join(root, file_name)
                with open(file_abs_path, 'r') as filep:
                    autos = re.findall(r'(auto{(.*?)})', filep.read(), re.IGNORECASE)
                    if autos:
                        self.src_files.append(os.path.relpath(file_abs_path, src_path))

        if not self.src_files:
            LOG.error('Cannot find any kernel files with auto pragma.')
            raise RuntimeError()

    def create_job(self) -> Optional[Job]:
        """Create a new folder and copy source code for a design point to be evaluated

        Returns
        -------
        Job:
            A created Job object.
        """

        path = tempfile.mkdtemp(prefix=self.temp_dir_prefix, dir='{0}/'.format(self.work_path))
        if not copy_dir(self.src_path, path):
            return None
        LOG.debug('Created a new job at %s', path)
        return Job(path)

    def apply_design_point(self, job: Job, point: DesignPoint) -> bool:
        """Apply the given design point to the source code in job path. Change job status to
           'APPLIED' if success.

        Parameters
        ----------
        job:
            The job object with status INIT to be applied

        point:
            The design point that indicates specific values to design parameters

        Returns
        -------
        bool:
            Indicate if the application was success or not
        """

        if job.status != Job.Status.INIT:
            LOG.error('Job with key %s at %s cannot be applied again', job.key, job.path)
            return False

        job_path = job.path
        applied: Set[str] = set()
        for file_name in self.src_files:
            with open(os.path.join(job_path, file_name),
                      'r') as src_file, open('{0}/applier_temp.txt'.format(job_path),
                                             'w') as dest_file:
                for line in src_file:
                    for auto, ds_id in re.findall(r'(auto{(.*?)})', line, re.IGNORECASE):
                        if ds_id not in point:
                            LOG.debug('Parameter %s not found in design point', ds_id)
                        else:
                            # Replace "auto{?}" with a specific value
                            line = line.replace(auto, str(point[ds_id]))
                            applied.add(ds_id)
                    dest_file.write(line)
            os.replace('{0}/applier_temp.txt'.format(job_path),
                       '{0}/{1}'.format(job_path, file_name))

        # Check if all design parameters were applied
        error = 0
        for ds_id in point.keys():
            if ds_id not in applied:
                LOG.error('Cannot find the corresponding auto{%s} in source files', ds_id)
                error += 1

        # Assign the key to the job
        job.key = gen_key_from_design_point(point)
        job.status = Job.Status.APPLIED
        return error == 0

    def submit(self, jobs: List[Job], timeout: int = 0) -> int:
        """Submit a list of jobs for evaluation and get desired result files.
           When this method returns, the wanted result files should be available locally except for
           duplicated jobs.

        Parameters
        ----------
        job:
            The job object to be submitted.

        timeout:
            The timeout of the evaluation. Set to 0 to indicate no timeout.

        Returns
        -------
        int:
            The number of success jobs.
        """

        pending_dup: List[Job] = []
        for job in jobs:
            if job.status != Job.Status.APPLIED:
                LOG.error('Job at %s is not ready for evaluation', job.path)
            else:
                pending_dup.append(job)

        if not pending_dup:
            LOG.error('No valid jobs for evaluation')
            return 0

        LOG.debug('Check %d jobs for duplications', len(pending_dup))

        pending_eval: List[Job] = []

        # Check and bypass duplications
        dups = 0
        for job, result in zip(pending_dup, self.db.batch_query([job.key for job in pending_dup])):
            if result:
                dups += 1
                LOG.debug('Job %s is evaluated already', job.key)
            else:
                pending_eval.append(job)

        if not pending_eval:
            LOG.debug('All jobs are duplications')
            return dups

        LOG.debug('Submit %d jobs for evaluation', len(pending_eval))

        # Determine the submission flow
        if self.mode == EvalMode.FAST:
            submitter = self.submit_fast
        elif self.mode == EvalMode.ACCURATE:
            submitter = self.submit_accurate
        else:
            LOG.error('Evaluation mode %s does has not yet supported', self.mode)
            return 0

        # Submit un-evaluated jobs
        return submitter(pending_eval, timeout) + dups

    def submit_fast(self, jobs: List[Job], timeout: int = 0) -> int:
        """The job submission flow for fast mode.

        Parameters
        ----------
        job:
            The job object to be submitted.

        timeout:
            The timeout of the evaluation. Set to 0 to indicate no timeout.

        Returns
        -------
        int:
            Indicate the number of success jobs.
        """
        raise NotImplementedError()

    def submit_accurate(self, jobs: List[Job], timeout: int = 0) -> int:
        """The job submission flow for accurate mode.

        Parameters
        ----------
        job:
            The job object to be submitted.

        timeout:
            The timeout of the evaluation. Set to 0 to indicate no timeout.

        Returns
        -------
        int:
            Indicate the number of success jobs.
        """
        raise NotImplementedError()


class MerlinEvaluator(Evaluator):
    """Evaluate Merlin compiler projects"""

    def __init__(self, src_path: str, work_path: str, mode: EvalMode, db: Database,
                 scheduler: Scheduler, analyzer_cls: Type[MerlinAnalyzer]):
        super(MerlinEvaluator, self).__init__(src_path, work_path, mode, db, scheduler,
                                              analyzer_cls, 'merlin')

    def submit_fast(self, jobs: List[Job], timeout: int = 0) -> int:
        #pylint:disable=missing-docstring

        success = 0

        # Run Merlin transformations and make sure it works as expected
        pending_hls: List[Job] = []
        pending_commit: List[Tuple[str, ResultBase]] = []
        desired = self.analyzer.desire('transform')
        for job, is_success in zip(jobs, self.scheduler.run(jobs, desired, 'make mcc_acc',
                                                            timeout)):
            if is_success:
                result = self.analyzer.analyze(job, 'transform')
                if not result:
                    LOG.error('Failed to analyze result of %s after Merlin transformation',
                              job.key)
                    continue
                assert isinstance(result, MerlinResult)
                if not result.criticals:
                    # No critical problems, keep running HLS
                    pending_hls.append(job)
                else:
                    # Merlin failed to perform certain transformations, stop here
                    # but still consider as a success evaluation
                    pending_commit.append((job.key, result))
                    success += 1

        # Run HLS and analyze the Merlin report
        desired = self.analyzer.desire('hls')
        for job, is_success in zip(
                pending_hls, self.scheduler.run(pending_hls, desired, 'make mcc_estimate',
                                                timeout)):
            if is_success:
                result = self.analyzer.analyze(job, 'hls')
                if not result:
                    LOG.error('Failed to analyze result of %s after HLS', job.key)
                    continue
                success += 1
                assert isinstance(result, HLSResult)
                pending_commit.append((job.key, result))

        self.db.batch_commit(pending_commit)
        return success

    def submit_accurate(self, jobs: List[Job], timeout: int = 0) -> int:
        #pylint:disable=missing-docstring

        success = 0

        pending_commit: List[Tuple[str, ResultBase]] = []
        desired = self.analyzer.desire('bitgen')
        for job, is_success in zip(jobs,
                                   self.scheduler.run(jobs, desired, 'make mcc_bitgen', timeout)):
            if is_success:
                result = self.analyzer.analyze(job, 'bitgen')
                if not result:
                    LOG.error('Failed to analyze result of %s after bitgen', job.key)
                    continue
                success += 1
                assert isinstance(result, BitgenResult)
                pending_commit.append((job.key, result))

        self.db.batch_commit(pending_commit)
        return success
