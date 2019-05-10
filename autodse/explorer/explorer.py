"""
The main module of explorer.
"""
import time
from typing import Any, Dict, Optional

from .algorithmfactory import AlgorithmFactory
from ..evaluator.evaluator import Evaluator
from ..logger import get_algo_logger
from ..database import Database
from ..parameter import DesignSpace, gen_key_from_design_point
from ..result import Result


class Explorer():
    """Main explorer class"""

    def __init__(self,
                 ds: DesignSpace,
                 db: Database,
                 evaluator: Evaluator,
                 timeout: int,
                 tag: str = ''):
        self.ds = ds
        self.db = db
        self.evaluator = evaluator
        self.timeout = timeout * 60.0
        self.log_file_name = '{0}_algo.log'.format(tag) if tag else 'algo.log'
        self.log = get_algo_logger('Explorer', self.log_file_name)

    def run(self, algo_config: Dict[str, Any]) -> None:
        """The main function of the explorer to launch the search algorithm

        Parameters
        ----------
        algo_name:
            The corresponding algorithm name for running this exploration.

        algo_config:
            The configurable values for the algorithm.
        """

        # Create a search algorithm generator
        algo = AlgorithmFactory.make(algo_config, self.ds, self.log_file_name)
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
            jobs = []
            keys = [gen_key_from_design_point(point) for point in next_points]
            for point, result in zip(next_points, self.db.batch_query(keys)):
                if result is None:
                    job = self.evaluator.create_job()
                    if job:
                        self.evaluator.apply_design_point(job, point)
                        jobs.append(job)
                    else:
                        self.log.error('Fail to create a new job (disk space?)')
                        return
                else:
                    results[gen_key_from_design_point(point)] = result
            if not jobs:
                duplicated_iters += 1
                self.log.debug('All design points are already evaluated (%d iterations)',
                               duplicated_iters)
                continue

            duplicated_iters = 0

            # Evaluate design points and get results
            self.log.debug('Evaluating %d new design points', len(jobs))
            for key, result in self.evaluator.submit(jobs):
                results[key] = result
