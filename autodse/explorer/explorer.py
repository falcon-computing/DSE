"""
The main module of explorer.
"""
import time
from typing import Any, Dict, List, Optional

from .algorithmfactory import AlgorithmFactory
from ..evaluator.evaluator import Evaluator
from ..logger import get_algo_logger
from ..database import Database
from ..parameter import DesignPoint, DesignSpace, gen_key_from_design_point
from ..result import Job, Result


class Explorer():
    """Main explorer class"""

    def __init__(self, db: Database, evaluator: Evaluator, tag):
        self.db = db
        self.evaluator = evaluator
        self.tag = tag
        self.algo_log_file_name = '{0}_algo.log'.format(self.tag)
        self.log = get_algo_logger('Explorer', '{0}_expr.log'.format(self.tag))

        # Status checking
        self.best_result: Result = Result()
        self.explored_point = 0

    def update_best(self, result: Result) -> None:
        """Keep tracking the best result found in this explorer.

        Parameters
        ---------
        result:
            The new result to be checked.

        """
        if result.valid and result.quality > self.best_result.quality:
            self.best_result = result
            self.log.info('Found a better result at #%04d: Quality %.1e, Perf %.1e',
                          self.explored_point, result.quality, result.perf)

    def run(self, algo_config: Dict[str, Any]) -> None:
        """The main function of the explorer to launch the search algorithm

        Parameters
        ----------
        algo_name:
            The corresponding algorithm name for running this exploration.

        algo_config:
            The configurable values for the algorithm.
        """
        raise NotImplementedError()


class FastExplorer(Explorer):
    """"Fast explorer class"""

    def __init__(self, db: Database, evaluator: Evaluator, timeout: int, tag: str,
                 ds: DesignSpace):
        super(FastExplorer, self).__init__(db, evaluator, tag)
        self.timeout = timeout * 60.0
        self.ds = ds

    def create_job_and_apply_point(self, point) -> Optional[Job]:
        """Create a new job and apply the given design point

        Parameters
        ----------
        point:
            The point to be applied.

        Returns
        -------
        Optional[Job]:
            The created job, or None if failed.
        """

        job = self.evaluator.create_job()
        if job:
            if not self.evaluator.apply_design_point(job, point):
                return None
        else:
            self.log.error('Fail to create a new job (disk space?)')
            return None
        return job

    def run(self, algo_config: Dict[str, Any]) -> None:
        #pylint:disable=missing-docstring

        # Create a search algorithm generator
        algo = AlgorithmFactory.make(algo_config, self.ds, self.algo_log_file_name)
        gen_next = algo.gen()

        timer = time.time()
        duplicated_iters = 0
        results: Optional[Dict[str, Result]] = None
        while (time.time() - timer) < self.timeout:
            try:
                # Generate the next set of design points
                next_points = gen_next.send(results)
                self.log.debug('The algorithm generates %d design points', len(next_points))
            except StopIteration:
                break

            results = {}

            # Create jobs and check duplications
            jobs: List[Job] = []
            keys: List[str] = [gen_key_from_design_point(point) for point in next_points]
            for point, result in zip(next_points, self.db.batch_query(keys)):
                key = gen_key_from_design_point(point)
                if result is None:
                    job = self.create_job_and_apply_point(point)
                    if job:
                        jobs.append(job)
                    else:
                        return
                else:
                    self.update_best(result)
                    results[key] = result
            if not jobs:
                duplicated_iters += 1
                self.log.debug('All design points are already evaluated (%d iterations)',
                               duplicated_iters)
                continue

            duplicated_iters = 0

            # Evaluate design points using level 1 to fast check if it is suitable for HLS
            self.log.debug('Evaluating %d design points: Level 1', len(jobs))
            pending: List[Job] = []
            for key, result in self.evaluator.submit(jobs, 1):
                if result.ret_code == Result.RetCode.PASS:
                    job = self.create_job_and_apply_point(result.point)
                    if job:
                        pending.append(job)
                    else:
                        return
                else:
                    results[key] = result

            # Evaluate design points using level 2 that runs HLS
            self.log.debug('Evaluating %d design points: Level 2', len(pending))
            for key, result in self.evaluator.submit(pending, 2):
                self.update_best(result)
                results[key] = result

            self.explored_point += len(jobs)
            self.db.commit('meta-expr-cnt-{0}'.format(self.tag), self.explored_point)

        self.log.info('Explored %d points', self.explored_point)


class AccurateExplorer(Explorer):
    """The accurate explorer class"""

    def __init__(self, db: Database, evaluator: Evaluator, tag: str, points: List[DesignPoint]):
        super(AccurateExplorer, self).__init__(db, evaluator, tag)
        self.points = points

    def run(self, algo_config: Dict[str, Any]) -> None:
        #pylint:disable=missing-docstring
        pass
