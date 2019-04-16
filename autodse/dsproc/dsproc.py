"""
Design Space Processor
"""
from typing import Optional, Dict, List, Tuple, Union
from logging import getLogger
from os import listdir
from os.path import isfile, join
import ast
import json
import re

from ..database import DesignParameter, DesignSpace
from ..util import SAFE_LIST, safe_eval

log = getLogger('DSProc')

class DSProc():
    """
    The module to process design space
    """

    def __init__(self, src_path: str, work_path: str):
        self.src_path = src_path
        self.work_path = work_path

        # TODO: File checking
        self.user_ds_file = '{0}/design_space.json'.format(self.src_path)

    def compile(self) -> Optional[DesignSpace]:
        """Compile the design space from Merlin C kernel auto pragmas

        Parameters
        ----------

        Returns
        -------
        ds:
            The design space compiled from the kernel code; otherwise None
        """

        with open(self.user_ds_file, 'r') as ds_file:
            user_ds_config = json.load(ds_file)
        if not user_ds_config:
            log.error('Design space not found.')
            return None

        params = []
        for param_id, param_config in user_ds_config.items():
            param = create_design_parameter_from_config(param_id, param_config)
            if param:
                params.append(param)
                print (param.__dict__)

        log.info('Finished design space compilation')
        return params

def check_option_syntax(option_expr: str) -> Tuple[bool, List[str]]:
    """Check the syntax of design options and extract dependent design parameter IDs

        Parameters
        ----------
        option_expr:
            The design space option expression

        Returns
        -------
        check:
            Indicate if the expression is valid or not
        deps:
            A list of dependent design parameter IDs
    """
    try:
        st = ast.parse(option_expr)
    except SyntaxError:
        log.error('"options" error: Illegal option list %s',
                      option_expr)
        return (False, [])

    # Traverse AST of the option_expression for all variables
    names = set()
    iter_val = None
    for node in ast.walk(st):
        if isinstance(node, ast.ListComp):
            funcs = [n.func.id for n in ast.walk(node.elt)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
            elt_vals = [n.id for n in ast.walk(node.elt)
                        if isinstance(n, ast.Name) and n.id not in funcs
                        and n.id != '_']
            assert len(elt_vals) <= 1, 'Found more than one iterators in {0}'.format(option_expr)
            if len(elt_vals) == 1:
                iter_val = elt_vals[0]
        elif isinstance(node, ast.Name):
            names.add(node.id)

    # Ignore the list comprehension iterator
    if iter_val:
        names.remove(iter_val)

    # Ignore legal builtin functions
    for _, funcs in SAFE_LIST.items():
        for func in funcs:
            if func in names:
                names.remove(func)

    # Ignore builtin primitive type casting
    for ptype in ['int', 'str', 'float']:
        if ptype in names:
            names.remove(ptype)

    return (True, list(names))

def check_order_syntax(option_expr: str):
    """Check the syntax of the partition rule and extract the variable name

    Parameters
    ----------
        option_expr:
            The design space option expression

    Returns
    -------
    check:
        Indicate if the expression is valid or not

    deps:
        A list of dependent design parameter IDs
    """
    local: Dict[str, Union[str, int]] = {}
    while True:
        try:
            safe_eval(option_expr, local)
            return (True, list(local.keys())[0])
        except SyntaxError:
            log.error('"order" syntax error: %s', option_expr)
        except NameError as err:
            tokens = re.search(r"'(.+)' is not defined", str(err))
            if tokens:
                name = tokens.group(1)
                if not local:
                    local[name] = 0
                    continue
            elif not tokens:
                log.error('Unkonwn error message: %s', str(err))
            else:
                var = list(local.keys())[0]
                log.error('"order" should have only one argument, '
                              'but already found two: %s and %s in %s', var, name, option_expr)
        break
    return (False, '')

def create_design_parameter_from_config(param_id: str,
                                        ds_config: Dict[str, Union[str, int]]) -> Optional[DesignParameter]:
    """Create DesignParameter from the string in auto pragma

        Parameters
        ----------
        attr_str:
            The design space string in the auto pragma

        Returns
        -------
        param_id:
            The unique design parameter ID
        param:
            The created DesignParameter object
    """
    param = DesignParameter(param_id)

    # Option checking
    if 'options' not in ds_config:
        log.error('Missing attribute "options" in %s', param_id)
        return None
    param.option_expr = str(ds_config['options'])
    check, param.deps = check_option_syntax(param.option_expr)
    if not check:
        return None

    # Partition checking
    if 'order' in ds_config:
        check, var = check_order_syntax(str(ds_config['order']))
        if not check:
            log.warning('Failed to parse "order" of %s, ignore.', param_id)
        else:
            param.order = {'expr': str(ds_config['order']), 'var': var}

    # Default checking
    if 'default' not in ds_config:
        log.error('Missing attribute "default" in %s', param_id)
        return None
    param.default = ds_config['default']

    return param
