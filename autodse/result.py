"""
The definition of evaluation results
"""

from typing import Any, Dict, List, Optional, Tuple


class ResultBase(object):
    """The base module of evaluation result"""

    def __init__(self, key: str = ''):
        self.key = key
        self.ret_code: int = 0
        self.perf: float = 0.0
        self.res_util: Optional[Dict[str, float]] = None
        self.eval_time: float = 0.0


class HLSResult(ResultBase):
    """The result after running the HLS"""

    def __init__(self, key: str = ''):
        super(HLSResult, self).__init__(key)

        # Merlin report (in JSON format)
        self.report: Optional[Dict[str, Any]] = None

        # The topo IDs and the performance bottleneck type (compute, memory)
        # in the order of importance
        self.ordered_hotspot: Optional[List[Tuple[str, str]]] = None
