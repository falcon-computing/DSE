"""
The module for making algorithm instance.
"""

from typing import Any, Dict

from .algorithm import SearchAlgorithm
from .exhaustive import ExhaustiveAlgorithm
from .gradient import GradientAlgorithm
from ..logger import get_default_logger
from ..parameter import DesignSpace


class AlgorithmFactory():
    """Static class for registering and making algorithm instances"""

    @staticmethod
    def make(config: Dict[str, Any], ds: DesignSpace,
             log_file_name: str = 'algo.log') -> SearchAlgorithm:
        """TBA
        """

        log = get_default_logger('AlgorithmFactory')

        name = config['name']
        assert isinstance(name, str)
        if name == 'exhaustive':
            algo_config = config[name]
            assert isinstance(algo_config, dict)
            return ExhaustiveAlgorithm(ds=ds,
                                       log_file_name=log_file_name,
                                       batch_size=algo_config['batch-size'])
        if name == 'gradient':
            return GradientAlgorithm(ds=ds, log_file_name=log_file_name)
        log.error('Unrecognized algorithm: %s', name)
        raise RuntimeError()
