"""
The definition of evaluation results
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Job(object):
    """The info and properties of a job"""

    class Status(Enum):
        INIT = 0
        APPLIED = 1
        EVALUATED = 2

    def __init__(self, path: str):
        self.path: str = path
        self.key: str = 'NotAPPLIED'
        self.status: Job.Status = Job.Status.INIT


class ResultBase(object):
    """The base module of evaluation result"""

    def __init__(self, key: str = ''):
        self.key = key
        self.ret_code: int = 0
        self.perf: float = 0.0
        self.res_util: Dict[str, float] = {
            'util-BRAM': 0,
            'util-DSP': 0,
            'util-LUT': 0,
            'util-FF': 0,
            'total-BRAM': 0,
            'total-DSP': 0,
            'total-LUT': 0,
            'total-FF': 0
        }
        self.eval_time: float = 0.0


class MerlinResult(ResultBase):
    """The result after running Merlin transformations"""

    def __init__(self, key: str = ''):
        super(MerlinResult, self).__init__(key)

        # Critical messages from the Merlin transformations
        self.criticals: List[str] = []


class HLSResult(ResultBase):
    """The result after running the HLS"""

    def __init__(self, key: str = ''):
        super(HLSResult, self).__init__(key)

        # Merlin report (in JSON format)
        self.report: Optional[Dict[str, Any]] = None

        # The topo IDs and the performance bottleneck type (compute, memory)
        # in the order of importance
        self.ordered_hotspot: Optional[List[Tuple[str, str]]] = None


class BitgenResult(ResultBase):
    """The result after bit-stream generation"""

    def __init__(self, key: str = ''):
        super(BitgenResult, self).__init__(key)

        # Frequency
        self.freq: float = 0.0
