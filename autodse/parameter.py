"""
The definition of supported design parameters
"""
import ast
from typing import Dict, List, Optional, Tuple, Type, Union

from .logger import get_default_logger
from .util import SAFE_LIST

LOG = get_default_logger('Parameter')


class DesignParameter(object):
    """A tunable design parameter"""

    def __init__(self, name: str = ''):
        self.name: str = name
        self.default: Union[str, int] = 1
        self.file_name: str = ''
        self.option_expr: str = ''
        self.scope: List[str] = []
        self.order: Dict[str, str] = {}
        self.deps: List[str] = []
        self.child: List[str] = []
        self.value: Union[str, int] = 1


class MerlinParameter(DesignParameter):
    """A tunable design parameter especially for Merlin"""

    def __init__(self, name: str = ''):
        super(MerlinParameter, self).__init__(name)
        self.ds_type: str = 'UNKNOWN'


DesignSpace = Dict[str, DesignParameter]
DesignPoint = Dict[str, Union[int, str]]


def gen_key_from_design_point(point: DesignPoint) -> str:
    """Generate a unique key from the given design point

    Parameters
    ----------
    point:
        The given design point

    Returns
    -------
    str:
        The generated key in the format of "param1-value1.param2-value2"
    """

    return '.'.join([
        '{0}-{1}'.format(pid,
                         str(point[pid]) if point[pid] else 'NA') for pid in sorted(point.keys())
    ])


def check_option_syntax(option_expr: str) -> Tuple[bool, List[str]]:
    """Check the syntax of design options and extract dependent design parameter IDs

        Parameters
        ----------
        option_expr:
            The design space option expression

        Returns
        -------
        Tuple[bool, List[str]]:
            Indicate if the expression is valid or not;
            A list of dependent design parameter IDs
    """
    try:
        stree = ast.parse(option_expr)
    except SyntaxError:
        LOG.error('"options" error: Illegal option list %s', option_expr)
        return (False, [])

    # Traverse AST of the option_expression for all variables
    names = set()
    iter_val = None
    for node in ast.walk(stree):
        if isinstance(node, ast.ListComp):
            funcs = [
                n.func.id for n in ast.walk(node.elt)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            elt_vals = [
                n.id for n in ast.walk(node.elt)
                if isinstance(n, ast.Name) and n.id not in funcs and n.id != '_'
            ]
            assert len(elt_vals) <= 1, 'Found more than one iterators in {0}'.format(option_expr)
            if len(elt_vals) == 1:
                iter_val = elt_vals[0]
        elif isinstance(node, ast.Name):
            names.add(node.id)

    # Ignore the list comprehension iterator
    if iter_val:
        names.remove(iter_val)

    # Ignore legal builtin functions
    for func in SAFE_LIST:
        if func in names:
            names.remove(func)

    # Ignore builtin primitive type casting
    for ptype in ['int', 'str', 'float']:
        if ptype in names:
            names.remove(ptype)

    return (True, list(names))


def check_order_syntax(order_expr: str) -> Tuple[bool, str]:
    """Check the syntax of the partition rule and extract the variable name

    Parameters
    ----------
    order_expr:
        The design space option expression

    Returns
    -------
    Tuple[bool, str]:
        Indicate if the expression is valid or not;
        The single variable name in the expression
    """
    try:
        stree = ast.parse(order_expr)
    except SyntaxError:
        LOG.error('"order" error: Illegal order expression %s', order_expr)
        return (False, '')

    # Traverse AST of the expression for the variable
    names = set()
    for node in ast.walk(stree):
        if isinstance(node, ast.Name):
            names.add(node.id)

    if len(names) != 1:
        LOG.error('"order" should have one and only one variable in %s but found %d', order_expr,
                  len(names))
        return (False, '')
    return (True, names.pop())


def create_design_parameter(param_id: str, ds_config: Dict[str, Union[str, int]],
                            param_cls: Type[DesignParameter]) -> Optional[DesignParameter]:
    """Create DesignParameter from the string

    Parameters
    ----------
    param_id:
        The unique parameter ID

    attr_str:
        The design space string in the auto pragma

    param_cls:
        The class of parameter we will create

    Returns
    -------
    Optional[DesignParameter]:
        The created DesignParameter object
    """

    if param_cls == MerlinParameter:
        param = MerlinParameter(param_id)

        # Type checking
        if 'ds_type' not in ds_config:
            LOG.warning(
                'Missing attribute "ds_type" in %s. Some optimization may not be triggered',
                param_id)
        else:
            param.ds_type = str(ds_config['ds_type']).upper()
    else:
        param = param_cls(param_id)

    # General settings for parameters
    # Option checking
    if 'options' not in ds_config:
        LOG.error('Missing attribute "options" in %s', param_id)
        return None
    param.option_expr = str(ds_config['options'])
    check, param.deps = check_option_syntax(param.option_expr)
    if not check:
        return None

    # Partition checking
    if 'order' in ds_config:
        check, var = check_order_syntax(str(ds_config['order']))
        if not check:
            LOG.warning('Failed to parse "order" of %s, ignore.', param_id)
        else:
            param.order = {'expr': str(ds_config['order']), 'var': var}

    # Default checking
    if 'default' not in ds_config:
        LOG.error('Missing attribute "default" in %s', param_id)
        return None
    param.default = ds_config['default']

    return param
