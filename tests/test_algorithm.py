"""
The unit test module for design point manipulation in search algorithm.
"""
import pytest

from autodse import logger
from autodse.explorer.algorithm import SearchAlgorithm
from autodse.explorer.algorithmfactory import AlgorithmFactory
from autodse.explorer.exhaustive import ExhaustiveAlgorithm
from autodse.parameter import MerlinParameter

LOG = logger.get_logger('UNIT-TEST', 'DEBUG', True)


@pytest.fixture
def fixture_space():
    #pylint:disable=missing-docstring

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
    param.option_expr = '[x for x in ["off", "", "flatten"]]'  # if x=="off" or A&(A-1)==0]'
    #param.deps = ['A']
    param.child = ['A', 'B']
    param.default = 'off'
    space['C'] = param
    return space


def test_algorithm(fixture_space):
    #pylint:disable=missing-docstring, redefined-outer-name

    LOG.debug('=== Testing design point manipulation in search algorithm start ===')

    algo = SearchAlgorithm(fixture_space)

    # Test default point generation
    point = algo.get_default_point()
    assert point['A'] == 0 and point['B'] == 'off' and point['C'] == 'off'

    # Test basic option generation
    options = algo.gen_options(point, 'A')
    assert len(options) == 10
    options = algo.gen_options(point, 'B')
    assert len(options) == 3
    options = algo.gen_options(point, 'C')
    assert len(options) == 3

    # Test manipulation
    assert algo.move_by(point, 'C') == 1
    assert point['A'] == 0 and point['B'] == 'off' and point['C'] == ''
    point2 = algo.clone_point(point)

    # Cannot move 'B' because 'C' is 'flatten'
    assert algo.move_by(point, 'C') == 1
    assert point['A'] == 0 and point['B'] == 'off' and point['C'] == 'flatten'
    assert algo.move_by(point, 'B') == 0

    # Move 'A' and 'B' successfully
    assert algo.move_by(point2, 'A', 99) == 9
    assert algo.move_by(point2, 'B') == 1
    assert point2['A'] == 9 and point2['B'] == '' and point2['C'] == ''

    # Move 'C' to flatten and both 'A' and 'B' will be invalied
    assert algo.move_by(point2, 'C') == 1
    assert point2['A'] == 0 and point2['B'] == 'off' and point2['C'] == 'flatten'

    # Back move 'C' for a long distance
    assert algo.move_by(point2, 'C', -99) == -2

    LOG.debug('=== Testing design point manipulation in search algorithm end ===')


def test_algorithm_factory(fixture_space):
    #pylint:disable=missing-docstring, redefined-outer-name

    LOG.debug('=== Testing algorithm factory start ===')

    # Create an exhaustive algorithm
    config = {'name': 'exhaustive', 'exhaustive': {'batch-size': 7}}
    algo = AlgorithmFactory.make(config, fixture_space, '')
    assert isinstance(algo, ExhaustiveAlgorithm)

    LOG.debug('=== Testing algorithm factory end ===')
