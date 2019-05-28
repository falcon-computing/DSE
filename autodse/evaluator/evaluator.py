"""
The main module of evaluator.
"""
import os
import re
import shutil
import tempfile
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Tuple

from ..database import Database
from ..logger import get_eval_logger
from ..parameter import DesignPoint, gen_key_from_design_point
from ..result import BitgenResult, HLSResult, Job, MerlinResult, Result
from ..util import copy_dir
from .analyzer import Analyzer, MerlinAnalyzer
from .scheduler import Scheduler


class BackupMode(Enum):
    NO_BACKUP = 0
    BACKUP_ERROR = 1
    BACKUP_ALL = 2


class Evaluator():
    """Main evaluator class"""

    def __init__(self,
                 src_path: str,
                 work_path: str,
                 db: Database,
                 scheduler: Scheduler,
                 analyzer_cls: Type[Analyzer],
                 backup_mode: BackupMode,
                 dse_config: Dict[str, Any],
                 temp_prefix: str = 'eval'):
        self.log = get_eval_logger('Evaluator')
        self.db = db
        self.src_path = src_path
        self.work_path = work_path
        self.temp_dir_prefix = '{0}_'.format(temp_prefix)
        self.scheduler = scheduler
        self.backup_mode = backup_mode
        self.config = dse_config
        self.analyzer = analyzer_cls
        self.timeouts: Dict[str, int] = {'transform': 0, 'hls': 0, 'bitgen': 0}
        self.commands: Dict[str, str] = {}

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
        self.auto_map: Dict[str, List[str]] = {}
        for root, _, files in os.walk(src_path):
            for file_name in files:
                file_abs_path = os.path.join(root, file_name)
                has_auto = False
                # "errors" is an optional string that specifies how encoding and decoding errors
                # are to be handled. 'replace' causes a replacement marker (such as '?') to be
                # inserted where there is malformed data.
                with open(file_abs_path, 'r', errors='replace') as filep:
                    for idx, line in enumerate(filep.readlines()):
                        autos = re.findall(r'auto{(.*?)}', line, re.IGNORECASE)
                        if autos:
                            has_auto = True
                            # Note
                            # 1) The line number starts from one instead of zero.
                            # 2) The scope for pragmas other than loop-pragmas may not be accurate.
                            self.auto_map['{0}:{1}'.format(file_name, idx + 1)] = autos
                if has_auto:
                    self.src_files.append(os.path.relpath(file_abs_path, src_path))

        if not self.src_files:
            self.log.error('Cannot find any kernel files with auto pragma.')
            raise RuntimeError()

        self.log.info('Source files with design parameters:')
        for file_name in self.src_files:
            self.log.info(file_name)

    def set_timeout(self, config: Dict[str, int]) -> None:
        """Set timeout to a specific evaluation mode

        Parameters
        ----------
        config:
            A mode-timeout pair to specify the timeout in minutes for each mode.
        """

        for mode, timeout in config.items():
            self.timeouts[mode] = timeout

    def set_command(self, config: Dict[str, str]) -> None:
        """Set command to a specific evaluation mode

        Parameters
        ----------
        config:
            A mode-command pair to specify the command to be executed for each mode.
        """

        for mode, command in config.items():
            self.commands[mode] = command

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
        #self.log.debug('Created a new job at %s', path)
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
            self.log.error('Job with key %s at %s cannot be applied again', job.key, job.path)
            return False

        job_path = job.path
        applied: Set[str] = set()
        for file_name in self.src_files:
            with open(os.path.join(job_path, file_name), 'r', errors='replace') as src_file, \
                 open('{0}/applier_temp.txt'.format(job_path), 'w', errors='replace') as dest_file:
                for line in src_file:
                    for auto, ds_id in re.findall(r'(auto{(.*?)})', line, re.IGNORECASE):
                        if ds_id not in point:
                            self.log.debug('Parameter %s not found in design point', ds_id)
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
                self.log.error('Cannot find the corresponding auto{%s} in source files', ds_id)
                error += 1

        # Assign the key to the job
        job.point = point
        job.key = gen_key_from_design_point(point)
        job.status = Job.Status.APPLIED
        return error == 0

    def submit(self, jobs: List[Job], eval_lv: int) -> List[Tuple[str, Result]]:
        """Submit a list of jobs for evaluation and get desired result files.
           1) When this method returns, the wanted result files should be available locally
           except for duplicated jobs. 2) All results will be committed to the database.

        Parameters
        ----------
        job:
            The job object to be submitted.

        eval_lv:
            The evaluation level (1-3).

        Returns
        -------
        List[Tuple[str, Result]]:
            Results of jobs mapped by their keys.
        """

        assert all([job.status == Job.Status.APPLIED for job in jobs])
        self.log.info('Submit %d jobs for evaluation', len(jobs))

        result_prefix = 'lv{}'.format(eval_lv)
        if eval_lv == 1:
            submitter = self.submit_lv1
        elif eval_lv == 2:
            submitter = self.submit_lv2
        elif eval_lv == 3:
            submitter = self.submit_lv3
        else:
            self.log.error('Incorrect evaluation %d. Expect 1-3', eval_lv)
            raise RuntimeError()

        # Submit and commit results to the database
        job_n_results = submitter(jobs)
        for job, result in job_n_results:
            result.point = job.point

        self.log.debug('Committing %d results', len(job_n_results))
        self.db.batch_commit([('{0}:{1}'.format(result_prefix, job.key), result)
                              for job, result in job_n_results])
        self.log.info('Results are committed to the database')

        # Backup jobs if needed
        if self.backup_mode == BackupMode.NO_BACKUP:
            for job in jobs:
                shutil.rmtree(job.path)
        else:
            if self.backup_mode == BackupMode.BACKUP_ERROR:
                for job, result in job_n_results:
                    if result.ret_code in [Result.RetCode.PASS, Result.RetCode.EARLY_REJECT]:
                        shutil.rmtree(job.path)

            # Map the job path to the result if it has a backup
            for job, result in job_n_results:
                if os.path.exists(job.path):
                    result.path = job.path
        return [(job.key, result) for job, result in job_n_results]

    def submit_lv1(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        """The level 1 job evaluation flow.

        Parameters
        ----------
        job:
            The job object to be submitted.

        Returns
        -------
        List[Tuple[Job, Result]]:
            Result to each job. The ret_code in each result should be PASS if the evaluation
            was done successfully.
        """
        raise NotImplementedError()

    def submit_lv2(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        """The level 2 job evaluation flow.

        Parameters
        ----------
        job:
            The job object to be submitted.

        Returns
        -------
        List[Tuple[Job, Result]]:
            Result to each job. The ret_code in each result should be PASS if the evaluation
            was done successfully.
        """
        raise NotImplementedError()

    def submit_lv3(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        """The level 3 job evaluation flow.

        Parameters
        ----------
        job:
            The job object to be submitted.

        Returns
        -------
        List[Tuple[Job, Result]]:
            Result to each job. The ret_code in each result should be PASS if the evaluation
            was done successfully.
        """
        raise NotImplementedError()


class MerlinEvaluator(Evaluator):
    """Evaluate Merlin compiler projects"""

    def __init__(self, src_path: str, work_path: str, db: Database, scheduler: Scheduler,
                 analyzer_cls: Type[MerlinAnalyzer], backup_mode: BackupMode,
                 dse_config: Dict[str, Any]):
        super(MerlinEvaluator, self).__init__(src_path, work_path, db, scheduler, analyzer_cls,
                                              backup_mode, dse_config, 'merlin')

        self.scope_map: Optional[Dict[str, str]] = None

    def build_scope_map(self) -> bool:
        """Build the scope map that maps auto positions to the scope in source code.

        Returns
        -------
        bool:
            Indicate if the build was success or not.
        """

        scope_map = self.db.query('scope-map')
        if scope_map is not None:
            self.log.info('Load the scope map from database')
            self.scope_map = scope_map
            return True

        if self.analyzer != MerlinAnalyzer:
            self.log.error('MerlinAnalyer is requied to build the scope map')
            return False

        if 'hls' not in self.commands:
            self.log.error('Command for HLS is not properly set up.')
            return False

        job = self.create_job()
        assert job is not None
        sche_rets = self.scheduler.run([job], self.analyzer.desire('hls'), self.commands['hls'],
                                       self.timeouts['hls'])
        assert len(sche_rets) == 1
        _, ret = sche_rets[0]
        if ret == Result.RetCode.PASS:
            scope_map = self.analyzer.analyze_scope(job, self.auto_map)  # type: ignore
            if scope_map is not None:
                self.scope_map = scope_map
                self.db.commit('scope-map', scope_map)
                return True

        self.log.error('Failed to build the scope map')
        return False

    def submit_lv1(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        #pylint:disable=missing-docstring

        results: Dict[str, Result] = {job.key: Result('UNAVAILABLE') for job in jobs}
        job_map: Dict[str, Job] = {job.key: job for job in jobs}

        # Check commands
        if 'transform' not in self.commands:
            self.log.error('Command for transform is not properly set up.')
            return [(job, Result('UNAVAILABLE')) for job in jobs]

        # Run Merlin transformations and make sure it works as expected
        sche_rets = self.scheduler.run(jobs, self.analyzer.desire('transform'),
                                       self.commands['transform'], self.timeouts['transform'])
        for job_key, ret_code in sche_rets:
            if ret_code == Result.RetCode.PASS:
                result = self.analyzer.analyze(job_map[job_key], 'transform', self.config)
                if not result:
                    self.log.warning('Failed to analyze result of %s after Merlin transformation',
                                     job_map[job_key].key)
                    results[job_key].ret_code = Result.RetCode.ANALYZE_ERROR
                    continue
                assert isinstance(result, MerlinResult)
                if not result.valid:  # Merlin failed to perform certain transformations
                    result.ret_code = Result.RetCode.EARLY_REJECT
                results[job_key] = result
            else:
                results[job_key].ret_code = ret_code

        return [(job, results[job.key]) for job in jobs]

    def submit_lv2(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        #pylint:disable=missing-docstring

        results: Dict[str, Result] = {job.key: Result('UNAVAILABLE') for job in jobs}
        job_map: Dict[str, Job] = {job.key: job for job in jobs}

        # Check commands
        if 'hls' not in self.commands:
            self.log.error('Command for HLS is not properly set up.')
            return [(job, Result('UNAVAILABLE')) for job in jobs]

        # Run HLS and analyze the Merlin report
        sche_rets = self.scheduler.run(jobs, self.analyzer.desire('hls'), self.commands['hls'],
                                       self.timeouts['hls'])
        for job_key, ret_code in sche_rets:
            if ret_code == Result.RetCode.PASS:
                result = self.analyzer.analyze(job_map[job_key], 'hls', self.config)
                if not result:
                    self.log.warning('Failed to analyze result of %s after HLS', job_key)
                    results[job_key].ret_code = Result.RetCode.ANALYZE_ERROR
                    continue
                results[job_key] = result
                assert isinstance(result, HLSResult)
            else:
                results[job_key].ret_code = ret_code

        return [(job, results[job.key]) for job in jobs]

    def submit_lv3(self, jobs: List[Job]) -> List[Tuple[Job, Result]]:
        #pylint:disable=missing-docstring

        results: Dict[str, Result] = {job.key: Result('UNAVAILABLE') for job in jobs}
        job_map: Dict[str, Job] = {job.key: job for job in jobs}

        # Check commands
        if 'bitgen' not in self.commands:
            self.log.error('Command for bitgen is not properly set up.')
            return [(job, Result('UNAVAILABLE')) for job in jobs]

        sche_rets = self.scheduler.run(jobs, self.analyzer.desire('bitgen'),
                                       self.commands['bitgen'], self.timeouts['bitgen'])
        for job_key, ret_code in sche_rets:
            if ret_code == Result.RetCode.PASS:
                result = self.analyzer.analyze(job_map[job_key], 'bitgen', self.config)
                if not result:
                    self.log.warning('Failed to analyze result of %s after bitgen', job_key)
                    results[job_key].ret_code = Result.RetCode.ANALYZE_ERROR
                    continue
                assert isinstance(result, BitgenResult)
                results[job_key] = result
            else:
                results[job_key].ret_code = ret_code

        return [(job, results[job.key]) for job in jobs]
