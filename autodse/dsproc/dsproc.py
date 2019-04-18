"""
Design Space Processor
"""
import ast
from collections import deque
from copy import deepcopy
from logging import getLogger
from typing import Deque, Dict, List, Optional, Set, Tuple, Union

from ..database import DesignParameter, DesignSpace
from ..util import SAFE_LIST, safe_eval

LOG = getLogger('DSProc')


def compile_design_space(user_ds_config: Dict[str, Dict[str, Union[str, int]]]
                         ) -> Optional[DesignSpace]:
    """Compile the design space from the config JSON file

    Parameters
    ----------
    user_ds_config:
        The input design space configure loaded from a JSON file.
        Note that the duplicated ID checking should be done when loading the JSON file and
        here we assume no duplications.

    Returns
    -------
    Optional[DesignSpace]:
        The design space compiled from the kernel code; or None if failed.

    """
    params: Dict[str, DesignParameter] = {}
    for param_id, param_config in user_ds_config.items():
        param = create_design_parameter(param_id, param_config)
        if param:
            params[param_id] = param
            print(param.__dict__)

    error = check_design_space(params)
    if error > 0:
        LOG.error('Design space has %d errors', error)
        return None

    LOG.info('Finished design space compilation')
    return params


def check_design_space(params: DesignSpace) -> int:
    """Check design space for missing dependency and duplication

    Parameters
    ----------
    params:
        The overall design space

    Returns
    -------
    int:
        The number of errors found in the design space
    """
    error = 0

    # Check dependencies
    for pid, param in params.items():
        for dep in param.deps:
            if dep == pid:
                LOG.error('Parameter %s cannot depend on itself', pid)
                error += 1
            if dep not in params.keys():
                LOG.error('Parameter %s depends on %s which is undefined or not allowed', pid, dep)
                error += 1
    return error


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


def create_design_parameter(param_id: str,
                            ds_config: Dict[str, Union[str, int]]) -> Optional[DesignParameter]:
    """Create DesignParameter from the string in auto pragma

    Parameters
    ----------
    attr_str:
        The design space string in the auto pragma

    Returns
    -------
    Optional[DesignParameter]:
        The created DesignParameter object
    """
    param = DesignParameter(param_id)

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

    # Type checking
    if 'ds_type' not in ds_config:
        LOG.warning('Missing attribute "ds_type in %s. Some optimization may not be triggered',
                    param_id)
    else:
        param.ds_type = str(ds_config['ds_type']).upper()

    return param


def topo_sort_param_ids(space: DesignSpace) -> List[str]:
    """Sort the parameter IDs topologically

    Parameters
    ----------
    space:
        The design space to be sorted

    Returns
    -------
    List[str]:
        The sorted IDs
    """

    def helper(curr_id: str, visited: Set[str], stack: List[str]) -> None:
        """The helper function for topological sort

        Parameters
        ----------
        curr_id:
            The current visiting parameter ID

        visited:
            The set of visited parameter IDs

        stack:
            The sorted parameter IDs

        Returns
        -------
            None
        """
        visited.add(curr_id)
        for dep in space[curr_id].deps:
            if dep not in visited:
                helper(dep, visited, stack)
        stack.append(curr_id)

    visited: Set[str] = set()
    stack: List[str] = []
    for pid in space.keys():
        if pid not in visited:
            helper(pid, visited, stack)
    return stack


def partition(space: DesignSpace, limit: int) -> Optional[List[DesignSpace]]:
    """Partition the given design space to at most the limit parts

    Parameters
    ----------
    space:
        The design space to be partitioned

    limit:
        The maximum number of partitions

    Returns
    -------
    Optional[List[DesignSpace]]:
        The list of design space partitions
    """

    sorted_ids = topo_sort_param_ids(space)

    part_queue = deque([deepcopy(space)])
    ptr = 0
    while len(part_queue) < limit and ptr < len(space):
        next_queue: Deque[DesignSpace] = deque()
        while part_queue:
            # Partition based on the current parameter
            curr_space = part_queue.pop()
            param_id = sorted_ids[ptr]
            param = curr_space[param_id]

            # Assign default value to dependent parameters
            local = {}
            for dep in param.deps:
                local[dep] = curr_space[dep].default

            # Evaluate the available options
            parts: Optional[Dict[int, List[Union[str, int]]]] = None
            if param.order and param.ds_type == 'PIPELINE':
                for option in safe_eval(param.option_expr, local):
                    part_idx = safe_eval(param.order['expr'], {param.order['var']: option})
                    if parts is None:
                        parts = {}
                    if part_idx not in parts:
                        parts[part_idx] = []
                    parts[part_idx].append(option)

            accum_part = len(part_queue) + len(next_queue)
            if parts and len(parts) == 1:
                # Do not partition because it is fully shadowed
                copied_space = deepcopy(curr_space)
                default = copied_space[param_id].default
                copied_space[param_id].option_expr = '[{0}]'.format(default)
                next_queue.append(copied_space)
                LOG.debug('%d: Stop partition %s due to shadow', ptr, param_id)
            elif not parts or accum_part + len(parts) > limit:
                # Do not partition because it is either
                # 1) not a partitionable parameter, or
                # 2) the accumulated partition number reaches to the limit
                copied_space = deepcopy(curr_space)
                next_queue.append(copied_space)
                LOG.debug('%d: Stop partition %s due to not partitionable or too many %d', ptr,
                          param_id, limit)
            else:
                # Partition
                for part in parts.values():
                    copied_space = deepcopy(curr_space)
                    copied_space[param_id].option_expr = str(part)
                    copied_space[param_id].default = part[0]
                    next_queue.append(copied_space)
                LOG.debug('%d: Partition %s to %d parts, so far %d parts', ptr, param_id,
                          len(parts),
                          len(part_queue) + len(next_queue))
        part_queue = next_queue
        ptr += 1
    return [part for part in reversed(part_queue)]
