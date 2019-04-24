"""
The utilizes of Merlin DSE module.
"""
import math
import os
import shutil
from subprocess import PIPE, Popen, TimeoutExpired
from typing import Any, Dict, Optional, Tuple, Union

from .logger import get_logger

LOG = get_logger('Util')

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
        return eval(expr, table)  #pylint: disable=eval-used
    except NameError as err:
        LOG.error('eval failed: %s', str(err))
        raise


def copy_dir(src: str, dest: str) -> bool:
    """Recursively copy a directory

    Parameters
    ----------
    src:
        The source directory

    dest:
        The destination directory

    Returns
    -------
    bool:
        Indicate if the copy was success or not
    """

    if os.path.exists(dest):
        shutil.rmtree(dest, ignore_errors=True)

    try:
        shutil.copytree(src, dest)
    except shutil.Error as err:  # Directories are the same
        LOG.error('Directory not copied. Error: %s', str(err))
        return False
    except OSError as err:  # Any error saying that the directory doesn't exist
        LOG.error('Directory not copied. Error: %s', str(err))
        return False
    return True


def command(cmd: str, timeout: Optional[int] = None) -> Tuple[bool, str]:
    """Run an OS command

    Parameters
    ----------
    cmd:
        The string of the given command.

    timeout:
        The time limit of running this command.

    Returns
    -------
    Tuple[bool, str]:
        Indicate if the command was success and the stdout of the command.
    """

    try:
        proc = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
        stdout, _ = proc.communicate(timeout=timeout)
        return (True, stdout)
    except ValueError as err:
        LOG.error('Command %s has errors: %s', cmd, str(err))
        return (False, '')
    except TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        return (False, stdout)
