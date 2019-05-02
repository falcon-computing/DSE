"""
The main module of explorer.
"""
import time
from typing import List, Optional, Type

from .algorithm import SearchAlgorithm
from ..evaluator.evaluator import Evaluator
from ..logger import get_logger
from ..database import Database
from ..parameter import DesignSpace, gen_key_from_design_point
from ..result import ResultBase

LOG = get_logger('Explorer')


class Explorer():
    """Main explorer class"""

    def __init__(self,
                 ds: DesignSpace,
                 db: Database,
                 evaluator: Evaluator,
                 algo_cls: Type[SearchAlgorithm],
                 timeout: Optional[int] = None):
        self.ds = ds
        self.db = db
        self.evaluator = evaluator
        self.timeout = timeout if timeout is not None else float('inf')
        self.algo = algo_cls(ds)
        self.gen_next = self.algo.gen()

    def run(self):
        """The main function of the explorer to launch the search algorithm."""

        timer = time.time()
        duplicated_iters = 0
        results: Optional[List[ResultBase]] = None
        while (time.time() - timer) < self.timeout:
            try:
                # Generate the next set of design points
                next_points = self.gen_next.send(results)
                LOG.debug('The algorithm generates %d design points', len(next_points))
            except StopIteration:
                break

            # Create jobs and check duplications
            jobs = []
            keys = [gen_key_from_design_point(point) for point in next_points]
            for point, result in zip(next_points, self.db.batch_query(keys)):
                if result is None:
                    job = self.evaluator.create_job()
                    self.evaluator.apply_design_point(job, point)
                    jobs.append(job)
            if not jobs:
                duplicated_iters += 1
                LOG.debug('All design points are already evaluated (%d iterations)',
                          duplicated_iters)

                if duplicated_iters == 10:
                    LOG.warning('No new design points have been generated '
                                'in the past 10 iterations, terminated.')
                    break
                continue
            duplicated_iters = 0

            # Evaluate design points and get results
            LOG.debug('Evaluating %d new design points', len(jobs))
            results = self.evaluator.submit(jobs)
