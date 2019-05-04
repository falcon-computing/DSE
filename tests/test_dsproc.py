"""
The unit test module for dsproc.
"""

from autodse import logger
from autodse.dsproc import dsproc
from autodse.parameter import DesignParameter, MerlinParameter

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_compile_design_space(mocker):
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing compile_design_space start')

    # Basic
    ds_config = {'X': {}}
    param = DesignParameter()
    param.name = 'X'
    mocker.patch('autodse.dsproc.dsproc.create_design_parameter', return_value=param)
    mock1 = mocker.patch('autodse.dsproc.dsproc.check_design_space', return_value=0)
    ret = dsproc.compile_design_space(ds_config)
    assert len(ret) == 1
    mock1.assert_called_once()

    # Design space with errors
    mocker.patch('autodse.dsproc.dsproc.check_design_space', return_value=1)
    ret = dsproc.compile_design_space(ds_config)
    assert ret is None

    LOG.debug('=== Testing compile_design_space end')


def test_analyze_child_in_design_space():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing analyze_child_in_design_space start')

    space = {}
    param = MerlinParameter()
    param.name = 'A'
    param.deps = ['B', 'C']
    space['A'] = param

    param = MerlinParameter()
    param.name = 'B'
    param.deps = ['C']
    space['B'] = param

    param = MerlinParameter()
    param.name = 'C'
    param.deps = ['A']
    space['C'] = param

    dsproc.analyze_child_in_design_space(space)
    assert len(space['A'].child) == 1 and space['A'].child[0] == 'C'
    assert len(space['B'].child) == 1 and space['B'].child[0] == 'A'
    assert len(space['C'].child) == 2 and 'A' in space['C'].child and 'B' in space['C'].child

    LOG.debug('=== Testing analyze_child_in_design_space end')


def test_check_design_space():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing check_design_space start')

    # Basic
    params = {}
    param = DesignParameter()
    param.name = 'X'
    param.deps = ['Y']
    params['X'] = param
    param = DesignParameter()
    param.name = 'Y'
    param.deps = []
    params['Y'] = param
    assert dsproc.check_design_space(params) == 0, 'expect no errors'

    # Self-dependent
    param = DesignParameter()
    param.name = 'Z'
    param.deps = ['X', 'Z']
    params['Z'] = param
    assert dsproc.check_design_space(params) == 1, 'expect 1 error'
    del params['Z']

    # Missing dependency
    param = DesignParameter()
    param.name = 'A'
    param.deps = ['K']
    params['A'] = param
    assert dsproc.check_design_space(params) == 1, 'expect 1 error'
    del params['A']

    # Use illegal builtin
    param = DesignParameter()
    param.name = 'B'
    param.deps = ['X', 'sin']
    params['B'] = param
    assert dsproc.check_design_space(params) == 1, 'expect 1 error'

    LOG.debug('=== Testing check_design_space end')


def test_topo_sort_param_ids():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing topo_sort_param_ids start')

    # Basic
    space = {}
    param = DesignParameter()
    param.name = 'A'
    param.deps = ['B', 'C']
    space['A'] = param

    param = DesignParameter()
    param.name = 'B'
    param.deps = ['C']
    space['B'] = param

    param = DesignParameter()
    param.name = 'C'
    param.deps = []
    space['C'] = param

    sorted_ids = dsproc.topo_sort_param_ids(space)
    assert all([a == b for a, b in zip(sorted_ids, ['C', 'B', 'A'])])

    # Has cycle
    space['C'].deps = ['A']
    sorted_ids = dsproc.topo_sort_param_ids(space)
    assert all([a == b for a, b in zip(sorted_ids, ['C', 'B', 'A'])])

    LOG.debug('=== Testing topo_sort_param_ids end')


def test_partition(mocker):
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing partition start')

    # Mock sorting function
    mocker.patch('autodse.dsproc.dsproc.topo_sort_param_ids', return_value=['C', 'B', 'A'])

    space = {}
    param = MerlinParameter()
    param.name = 'A'
    param.ds_type = 'PARALLEL'
    param.option_expr = '[x for x in range(10) if x==1 or B!="flatten" and C!="flatten"]'
    param.deps = ['B', 'C']
    param.default = 0
    space['A'] = param

    param = MerlinParameter()
    param.name = 'B'
    param.ds_type = 'PIPELINE'
    param.option_expr = '[x for x in ["off", "", "flatten"] if x=="off" or C!="flatten"]'
    param.order = {'expr': '0 if x!="flatten" else 1', 'var': 'x'}
    param.deps = ['C']
    param.default = 'off'
    space['B'] = param

    param = MerlinParameter()
    param.name = 'C'
    param.ds_type = 'PIPELINE'
    param.option_expr = '[x for x in ["off", "", "flatten"] if x=="off" or A&(A-1)==0]'
    param.order = {'expr': '0 if x!="flatten" else 1', 'var': 'x'}
    param.deps = ['A']
    param.default = 'off'
    space['C'] = param

    # Part: C(off, on), B(off, on)
    # Part: C(off, on), B(flatten)
    # Part: C(flatten), B(off)
    parts = dsproc.partition(space, 8)
    assert len(parts) == 3

    # Part: C(off, on), B(off, on, flatten)
    # Part: C(flatten), B(off)
    parts = dsproc.partition(space, 2)
    assert len(parts) == 2

    LOG.debug('=== Testing partition end')
