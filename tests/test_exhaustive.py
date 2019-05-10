"""
The unit test module for exhaustive serach algorithm.
"""

from autodse import logger
from autodse.parameter import MerlinParameter
from autodse.explorer.exhaustive import ExhaustiveAlgorithm
from autodse.result import Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_exhaustive():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing exhaustive search algorithm start ===')

    space = {}
    param = MerlinParameter()
    param.name = 'A'
    param.option_expr = '[x for x in range(10) if x==0 or B!="flatten" and C!="flatten"]'
    param.deps = ['B', 'C']
    param.default = 0
    space['A'] = param

    param = MerlinParameter()
    param.name = 'B'
    param.option_expr = '[x for x in ["off", "", "flatten"] if x=="off" or C!="flatten"]'
    param.deps = ['C']
    param.child = ['A']
    param.default = 'off'
    space['B'] = param

    param = MerlinParameter()
    param.name = 'C'
    param.option_expr = '[x for x in ["off", "", "flatten"]]'
    param.child = ['A', 'B']
    param.default = 'off'
    space['C'] = param

    algo = ExhaustiveAlgorithm(space)
    gen = algo.gen()
    results = [Result()] * 8
    iter_cnt = 0
    point_cnt = 0

    while True:
        try:
            points = gen.send(results if iter_cnt > 0 else None)
            point_cnt += len(points)
            iter_cnt += 1
        except StopIteration:
            break

    assert point_cnt == 43 and iter_cnt == 6

    LOG.debug('=== Testing exhaustive search algorithm end ===')
