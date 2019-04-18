"""
The unit test module for dsproc.
"""
from autodse.dsproc import dsproc
from autodse.database import DesignParameter


def test_check_option_syntax():
    #pylint:disable=missing-docstring
    # Basic
    ds_opt0 = "[32,64,128,256,512]"
    ret0 = dsproc.check_option_syntax(ds_opt0)
    assert ret0[0], 'expect success'
    assert not ret0[1], 'expect no dependency'

    # Dependency
    ds_opt1 = ("[x for x in ['','reduction = dist'] "
               "if x=='' or (CGPIP1!='flatten' and CGPIP2!='flatten')]")
    ret1 = dsproc.check_option_syntax(ds_opt1)
    assert ret1[0], 'expect success'
    assert len(ret1[1]) == 2 and sorted(ret1[1]) == ['CGPIP1', 'CGPIP2'], 'expect 2 dependencies'

    # Syntax error
    ds_opt2 = "[x, y for x in [1,2,4,8,16]]"
    ret2 = dsproc.check_option_syntax(ds_opt2)
    assert not ret2[0], 'expect failure'

    # The use of legel builtin functions
    ds_opt3 = "[sqrt(x) for x in range(20)]"
    ret3 = dsproc.check_option_syntax(ds_opt3)
    assert ret3[0], 'expect success'
    assert not ret3[1], 'expect no dependency'

    # The use of legal type casting
    ds_opt4 = "[int(x) for x in [1,2,3,4,5,6]]"
    ret4 = dsproc.check_option_syntax(ds_opt4)
    assert ret4[0], 'expect success'
    assert not ret4[1], 'expect no dependency'


def test_check_order_syntax():
    #pylint:disable=missing-docstring
    # Basic
    exp0 = "0 if x!='flatten' else 1"
    ret0 = dsproc.check_order_syntax(exp0)
    assert ret0[0], 'expect success'
    assert ret0[1] == 'x', 'expect variable name "x"'

    exp0 = "0 if x&(x-1)== 0 else 1"
    ret0 = dsproc.check_order_syntax(exp0)
    assert ret0[0], 'expect success'
    assert ret0[1] == 'x', 'expect variable name "x"'

    # Syntax error
    exp1 = "0 if x!='flatten'"
    ret1 = dsproc.check_order_syntax(exp1)
    assert not ret1[0], 'expect failure'

    # Variable number error
    exp2 = "0 if x==1 and y==2 else 1"
    ret2 = dsproc.check_order_syntax(exp2)
    assert not ret2[0], 'expect failure'
    exp2 = "0"
    ret2 = dsproc.check_order_syntax(exp2)
    assert not ret2[0], 'expect failure'


def test_create_design_parameter():
    #pylint:disable=missing-docstring
    # Basic
    param_id = 'X'
    ds_config = {
        "options": "[x**2 for x in range(10) if x==0 or Y!='flatten']",
        "order": "0 if x < 512 else 1",
        "ds_type": "parallel",
        "default": 1
    }
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is not None, 'expect to be created'
    assert param.name == 'X'
    assert param.option_expr == "[x**2 for x in range(10) if x==0 or Y!='flatten']"
    assert len(param.deps) == 1 and param.deps[0] == 'Y'
    assert param.order == {'expr': "0 if x < 512 else 1", 'var': "x"}
    assert param.default == 1
    assert param.ds_type == "PARALLEL"

    # Missing options
    ds_config = {"order": "0 if x < 512 else 1", "default": 1}
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is None, 'expect failure'

    # Error options expression
    ds_config = {
        "options": "[ for x in range(10) if x==0 or Y!='flatten']",
        "order": "0",
        "default": 1
    }
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is None, 'expect failure'

    # Error order expression
    ds_config = {
        "options": "[x**2 for x in range(10) if x==0 or Y!='flatten']",
        "order": "0",
        "default": 1
    }
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is not None, 'expect to be created'
    assert not param.order, 'expect to be an empty dictionary'

    # Missing default
    ds_config = {"options": "[x**2 for x in range(10) if x==0 or Y!='flatten']"}
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is None, 'expect failure'

    # Missing type
    ds_config = {"options": "[x**2 for x in range(10) if x==0 or Y!='flatten']", "default": 1}
    param = dsproc.create_design_parameter(param_id, ds_config)
    assert param is not None, 'expect to be created'
    assert param.ds_type == 'UNKNOWN'


def test_compile_design_space(mocker):
    #pylint:disable=missing-docstring
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


def test_check_design_space():
    #pylint:disable=missing-docstring
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


def test_topo_sort_param_ids():
    #pylint:disable=missing-docstring
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


def test_partition(mocker):
    #pylint:disable=missing-docstring

    # Mock sorting function
    mocker.patch('autodse.dsproc.dsproc.topo_sort_param_ids', return_value=['C', 'B', 'A'])

    space = {}
    param = DesignParameter()
    param.name = 'A'
    param.ds_type = 'PARALLEL'
    param.option_expr = '[x for x in range(10) if x==1 or B!="flatten" and C!="flatten"]'
    param.deps = ['B', 'C']
    param.default = 0
    space['A'] = param

    param = DesignParameter()
    param.name = 'B'
    param.ds_type = 'PIPELINE'
    param.option_expr = '[x for x in ["off", "", "flatten"] if x=="off" or C!="flatten"]'
    param.order = {'expr': '0 if x!="flatten" else 1', 'var': 'x'}
    param.deps = ['C']
    param.default = 'off'
    space['B'] = param

    param = DesignParameter()
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
