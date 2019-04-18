"""
The utilizes of Merlin DSE module.
"""
from typing import Dict, Any, Union, Optional
import logging
import math

LOG = logging.getLogger('Util')

SAFE_BUILTINS: Dict[str, Any] = {'builtins': None}
SAFE_BUILTINS['range'] = range
SAFE_BUILTINS['ceil'] = math.ceil
SAFE_BUILTINS['floor'] = math.floor
SAFE_BUILTINS['pow'] = math.pow
SAFE_BUILTINS['log'] = math.log
SAFE_BUILTINS['log10'] = math.log10
SAFE_BUILTINS['fabs'] = math.fabs
SAFE_BUILTINS['fmod'] = math.fmod
SAFE_BUILTINS['exp'] = math.exp
SAFE_BUILTINS['frexp'] = math.frexp
SAFE_BUILTINS['sqrt'] = math.sqrt
SAFE_LIST = list(SAFE_BUILTINS.keys())

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
    if local is not None:
        table.update(local)

    try:
        return eval(expr, table) #pylint: disable=eval-used
    except NameError as err:
        LOG.error('eval failed: %s', str(err))
        raise
