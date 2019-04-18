"""
The utilizes of Merlin DSE module.
"""
from typing import Dict, Any, Union, Optional
import logging
import math #pylint: disable=unused-import

LOG = logging.getLogger('Util')

SAFE_LIST = {'builtins': ['range'],
             'math': ['ceil', 'floor', 'pow', 'log', 'log10', 'fabs', 'fmod',
                      'exp', 'frexp', 'sqrt']}

SAFE_BUILTINS = {'builtins': None}
for pkg in SAFE_LIST:
    if pkg == 'builtins':
        for func in SAFE_LIST[pkg]:
            try:
                func_obj = __builtins__[func]
                SAFE_BUILTINS[func] = func_obj
            except KeyError:
                LOG.warning('Failed to import function %s', func)
    else:
        pkg_obj = locals().get(pkg, None)
        for func in SAFE_LIST[pkg]:
            try:
                func_obj = getattr(pkg_obj, func)
                SAFE_BUILTINS[func] = func_obj
            except AttributeError as err:
                LOG.warning('Failed to import function %s', func)

def safe_eval(expr: str, local: Optional[Dict[str, Union[str, int]]] = None) -> Any:
    """A safe wrapper of Python builtin eval

        Parameters
        ----------
        expr:
            The expression string for evaluation
        local:
            The variable and value pairs for the expression

        Returns
        -------
        result:
            The evaluated value
    """
    table = dict(SAFE_BUILTINS)
    if local:
        table.update(local)

    try:
        return eval(expr, table) #pylint: disable=eval-used
    except NameError as err:
        LOG.error('eval failed: %s', str(err))
        raise
