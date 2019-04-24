"""
Design Space Processor
"""
from collections import deque
from copy import deepcopy
from typing import Deque, Dict, List, Optional, Set, Union

from ..logger import get_logger
from ..parameter import (DesignParameter, DesignSpace, MerlinParameter, create_design_parameter)
from ..util import safe_eval

LOG = get_logger('DSProc')


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
        param = create_design_parameter(param_id, param_config, MerlinParameter)
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
            if param.order and isinstance(param, MerlinParameter) and param.ds_type == 'PIPELINE':
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
