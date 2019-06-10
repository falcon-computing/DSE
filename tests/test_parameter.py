"""
The unit test module for parameter.
"""
from autodse import logger
from autodse.parameter import (MerlinParameter, check_option_syntax, check_order_syntax,
                               create_design_parameter, get_default_point)

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_default_point():
    #pylint:disable=missing-docstring

    ds = {}
    param = MerlinParameter()
    param.default = 0
    ds['A'] = param
    param = MerlinParameter()
    param.default = 'off'
    ds['B'] = param
    param = MerlinParameter()
    param.default = 'off'
    ds['C'] = param

    point = get_default_point(ds)
    assert point['A'] == 0 and point['B'] == 'off' and point['C'] == 'off'


def test_check_option_syntax():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing check_option_syntax start')

    # Basic
    ds_opt0 = "[32,64,128,256,512]"
    ret0 = check_option_syntax(ds_opt0)
    assert ret0[0], 'expect success'
    assert not ret0[1], 'expect no dependency'

    # Dependency
    ds_opt1 = ("[x for x in ['','reduction = dist'] "
               "if x=='' or (CGPIP1!='flatten' and CGPIP2!='flatten')]")
    ret1 = check_option_syntax(ds_opt1)
    assert ret1[0], 'expect success'
    assert len(ret1[1]) == 2 and sorted(ret1[1]) == ['CGPIP1', 'CGPIP2'], 'expect 2 dependencies'

    # Syntax error
    ds_opt2 = "[x, y for x in [1,2,4,8,16]]"
    ret2 = check_option_syntax(ds_opt2)
    assert not ret2[0], 'expect failure'

    # The use of legel builtin functions
    ds_opt3 = "[sqrt(x) for x in range(20)]"
    ret3 = check_option_syntax(ds_opt3)
    assert ret3[0], 'expect success'
    assert not ret3[1], 'expect no dependency'

    # The use of legal type casting
    ds_opt4 = "[int(x) for x in [1,2,3,4,5,6]]"
    ret4 = check_option_syntax(ds_opt4)
    assert ret4[0], 'expect success'
    assert not ret4[1], 'expect no dependency'

    LOG.debug('=== Testing check_option_syntax end')


def test_check_order_syntax():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing check_order_syntax start')

    # Basic
    exp0 = "0 if x!='flatten' else 1"
    ret0 = check_order_syntax(exp0)
    assert ret0[0], 'expect success'
    assert ret0[1] == 'x', 'expect variable name "x"'

    exp0 = "0 if x&(x-1)== 0 else 1"
    ret0 = check_order_syntax(exp0)
    assert ret0[0], 'expect success'
    assert ret0[1] == 'x', 'expect variable name "x"'

    # Syntax error
    exp1 = "0 if x!='flatten'"
    ret1 = check_order_syntax(exp1)
    assert not ret1[0], 'expect failure'

    # Variable number error
    exp2 = "0 if x==1 and y==2 else 1"
    ret2 = check_order_syntax(exp2)
    assert not ret2[0], 'expect failure'
    exp2 = "0"
    ret2 = check_order_syntax(exp2)
    assert not ret2[0], 'expect failure'

    LOG.debug('=== Testing check_order_syntax end')


def test_create_design_parameter():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing create_design_parameter start')

    # Basic
    param_id = 'X'
    ds_config = {
        "options": "[x**2 for x in range(10) if x==0 or Y!='flatten']",
        "order": "0 if x < 512 else 1",
        "ds_type": "parallel",
        "default": 1
    }
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is not None, 'expect to be created'
    assert param.name == 'X'
    assert param.option_expr == "[x**2 for x in range(10) if x==0 or Y!='flatten']"
    assert len(param.deps) == 1 and param.deps[0] == 'Y'
    assert param.order == {'expr': "0 if x < 512 else 1", 'var': "x"}
    assert param.default == 1
    assert param.ds_type == "PARALLEL"

    # Missing options
    ds_config = {"order": "0 if x < 512 else 1", "default": 1}
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is None, 'expect failure'

    # Error options expression
    ds_config = {
        "options": "[ for x in range(10) if x==0 or Y!='flatten']",
        "order": "0",
        "default": 1
    }
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is None, 'expect failure'

    # Error order expression
    ds_config = {
        "options": "[x**2 for x in range(10) if x==0 or Y!='flatten']",
        "order": "0",
        "default": 1
    }
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is not None, 'expect to be created'
    assert not param.order, 'expect to be an empty dictionary'

    # Missing default
    ds_config = {"options": "[x**2 for x in range(10) if x==0 or Y!='flatten']"}
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is None, 'expect failure'

    # Missing type
    ds_config = {"options": "[x**2 for x in range(10) if x==0 or Y!='flatten']", "default": 1}
    param = create_design_parameter(param_id, ds_config, MerlinParameter)
    assert param is not None, 'expect to be created'
    assert param.ds_type == 'UNKNOWN'

    LOG.debug('=== Testing create_design_parameter end')
