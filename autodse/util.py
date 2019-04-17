"""
The utilizes of Merlin DSE module.
"""
from typing import Dict, Any, Union, Optional
import logging
import math #pylint: disable=unused-import

MLOGGER = logging.getLogger('Util')

SAFE_LIST = {'__builtins__': ['range'],
             'math': ['ceil', 'floor', 'pow', 'log', 'log10', 'fabs', 'fmod',
                      'exp', 'frexp', 'sqrt']}

SAFE_BUILTINS = {}
for pkg in SAFE_LIST:
    pkg_obj = locals().get(pkg, None)
    for func in SAFE_LIST[pkg]:
        try:
            func_obj = getattr(pkg_obj, func)
            SAFE_BUILTINS[func] = func_obj
        except AttributeError:
            MLOGGER.warning('Failed to import function %s', func)


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
    dup = dict(local) if local else {} # Make a copy to avoid changing the input dict
    return eval(expr, SAFE_BUILTINS, dup) #pylint: disable=eval-used
