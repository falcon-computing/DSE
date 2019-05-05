"""
The main module of search algorithm.
"""
from typing import Generator, List, Optional, Union

from ..logger import get_algo_logger
from ..parameter import DesignSpace, DesignPoint
from ..result import ResultBase
from ..util import safe_eval


class SearchAlgorithm():
    """Main serach algorithm class"""

    def __init__(self, ds: DesignSpace, log_file_name: str = 'algo.log'):
        self.ds = ds
        self.log = get_algo_logger('Search', log_file_name)

    def get_default_point(self) -> DesignPoint:
        """Generate a design point with all default values

        Returns
        -------
        DesignPoint:
            The design point with all default value applied.
        """

        point: DesignPoint = {}
        for pid, param in self.ds.items():
            point[pid] = param.default

        return point

    def gen_options(self, point: DesignPoint, pid: str) -> List[Union[int, str]]:
        """Evaluate available options of the target design parameter

        Parameters
        ----------
        point:
            The current design point.

        pid:
            The target design parameter ID.

        Returns
        -------
        List[Union[int, str]]:
            A list of available options.
        """
        dep_values = {dep: point[dep] for dep in self.ds[pid].deps}
        options = safe_eval(self.ds[pid].option_expr, dep_values)
        if options is None:
            self.log.error('Failed to evaluate %s with dep %s', self.ds[pid].option_expr,
                           str(dep_values))
            raise RuntimeError()

        return options

    def update_child(self, point: DesignPoint, pid: str) -> None:
        """Check values of affect parameters and update them in place if it is invalid

        Parameters
        ----------
        point:
            The current design point.

        pid:
            The design parameter ID that just be changed.
        """

        pendings = [child for child in self.ds[pid].child if self.validate_value(point, child)]
        for child in pendings:
            self.update_child(point, child)

    def validate_value(self, point: DesignPoint, pid: str) -> bool:
        """Check if the current value is valid and set it to the closest value if not

        Parameters
        ----------
        point:
            The current design point.

        pid:
            The design parameter ID that just be changed.

        Returns
        -------
            True if the value is changed.
        """

        options = self.gen_options(point, pid)
        value = point[pid]
        if not options:  # All invalid (something not right), set to default
            self.log.warning('No valid options for %s with point %s', pid, str(point))
            point[pid] = self.ds[pid].default
            return False

        if isinstance(value, int):
            # Note that we assume all options have the same type (int or str)
            cand = min(options, key=lambda x: abs(int(x) - int(value)))
            if cand != value:
                point[pid] = cand
                return True

        if value not in options:
            point[pid] = self.ds[pid].default
            return True
        return False

    def move_by(self, point: DesignPoint, pid: str, step: int = 1) -> int:
        """Move N steps of pid parameter's value in a design point in place

        Parameters
        ----------
        point:
            The design point to be manipulated.

        pid:
            The target design parameter.

        step:
            The steps to move. Note that step can be positive or negatie,
            but we will not move cirulatory even the step is too large.

        Returns
        -------
        int:
            The actual move steps.
        """

        try:
            options = self.gen_options(point, pid)
            idx = options.index(point[pid])
        except (AttributeError, ValueError) as err:
            self.log.error(
                'Fail to identify the index of value %s of parameter %s at design point %s: %s',
                point[pid], pid, str(point), str(err))
            raise RuntimeError()

        target = idx + step
        if target >= len(options):
            target = len(options) - 1
        elif target < 0:
            target = 0

        if target != idx:
            point[pid] = options[target]
            self.update_child(point, pid)
        return target - idx

    @staticmethod
    def clone_point(point: DesignPoint) -> DesignPoint:
        """Clone the given design point

        Parameters
        ----------
        point:
            The design point to be cloned.

        Returns
        -------
        DesignPoint:
            A cloned design point with same values.
        """
        return dict(point)

    def gen(self) -> Generator[List[DesignPoint], Optional[List[ResultBase]], None]:
        """The main generator function of search algorithm

        Returns
        -------
        Generator[List[DesignPoint], None, None]:
            A generator that keeps producing design points for exploration.
        """
        raise NotImplementedError()
