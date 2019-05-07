"""
The definition of evaluation results
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .parameter import DesignPoint

class Job(object):
    """The info and properties of a job"""

    class Status(Enum):
        INIT = 0
        APPLIED = 1
        EVALUATED = 2

    def __init__(self, path: str):
        self.path: str = path
        self.key: str = 'NotAPPLIED'
        self.point: Optional[DesignPoint] = None
        self.status: Job.Status = Job.Status.INIT


class ResultBase(object):
    """The base module of evaluation result"""

    def __init__(self, ret_code: int = 0):

        # The design point of this result.
        self.point: Optional[DesignPoint] = None

        # The return code of the evaluation. 0 means normal while negative numbers mean errors.
        self.ret_code: int = ret_code

        # Indicate if this result is valid to be a final output. For example, a result that
        # out-of-resource is invalid.
        self.valid: bool = False

        # The quantified QoR value. Larger the better.
        self.quality: float = 0.0

        # Performance in terms of estimated cycle or onboard runtime.
        self.perf: float = 0.0

        # Resource utilizations
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

        # Elapsed time for evaluation
        self.eval_time: float = 0.0


class MerlinResult(ResultBase):
    """The result after running Merlin transformations"""

    def __init__(self, ret_code: int = 0):
        super(MerlinResult, self).__init__(ret_code)

        # Critical messages from the Merlin transformations
        self.criticals: List[str] = []


class HLSResult(ResultBase):
    """The result after running the HLS"""

    def __init__(self, ret_code: int = 0):
        super(HLSResult, self).__init__(ret_code)

        # Merlin report (in JSON format)
        self.report: Optional[Dict[str, Any]] = None

        # The topo IDs and the performance bottleneck type (compute, memory)
        # in the order of importance
        self.ordered_hotspot: Optional[List[Tuple[str, str]]] = None


class BitgenResult(ResultBase):
    """The result after bit-stream generation"""

    def __init__(self, ret_code: int = 0):
        super(BitgenResult, self).__init__(ret_code)

        # Frequency
        self.freq: float = 0.0
