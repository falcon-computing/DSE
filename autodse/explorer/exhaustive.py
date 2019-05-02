"""
The exhaustive search algorithm
"""
from typing import Generator, List

from .algorithm import SearchAlgorithm
from ..dsproc.dsproc import topo_sort_param_ids
from ..logger import get_logger
from ..parameter import DesignPoint, DesignSpace
from ..result import ResultBase

LOG = get_logger('Exhaustive', config='ALGORITHM')

class ExhaustiveAlgorithm(SearchAlgorithm):
    """Exhaustively explore the design space. The order is based on the topological order
       of design parameters. Considering the evaluation overhead, we let users configure
       the batch size for evaluation.
    """

    def __init__(self, ds: DesignSpace, batch_size: int = 8):
        super(ExhaustiveAlgorithm, self).__init__(ds)
        self.batch_size = batch_size
        self.ordered_pids = topo_sort_param_ids(ds)

    def traverse(self, point: DesignPoint, idx: int) -> Generator[DesignPoint, None, None]:
        """DFS traverse the design space and yield leaf points

        Parameters
        ----------
        point:
            The current design point.

        idx:
            The current manipulated parameter index.

        Returns
        -------
        Generator[DesignPoint, None, None]:
            A resursive generator for traversing.
        """

        if idx == len(self.ordered_pids):
            # Finish a point
            yield point
        else:
            yield from self.traverse(point, idx + 1)

            # Manipulate idx-th point
            new_point = self.clone_point(point)
            while self.move_by(new_point, self.ordered_pids[idx]) == 1:
                yield from self.traverse(new_point, idx + 1)
                new_point = self.clone_point(new_point)

    def gen(self) -> Generator[List[DesignPoint], List[ResultBase], None]:
        #pylint:disable=missing-docstring

        LOG.info('Launch exhaustive search algorithm')

        traverser = self.traverse(self.get_default_point(), 0)
        iter_cnt = 0
        while True:
            next_points: List[DesignPoint] = []
            try:
                iter_cnt += 1
                LOG.info('Iteration %d', iter_cnt)
                while len(next_points) < self.batch_size:
                    next_points.append(next(traverser))
                    LOG.info('\t%s', str(next_points[-1]))
                yield next_points
            except StopIteration:
                if next_points:
                    yield next_points
                break

        LOG.info('No more points to be explored, stop.')
