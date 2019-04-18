"""
The result database.
"""
from typing import List, Dict, Union

class DesignParameter(object):
    """
    A tunable design parameter
    """

    def __init__(self, name: str = ''):
        self.name: str = name
        self.default: Union[str, int] = 1
        self.file_name: str = ''
        self.option_expr: str = ''
        self.ds_type: str = 'UNKNOWN'
        self.scope: List[str] = []
        self.order: Dict[str, str] = {}
        self.deps: List[str] = []
        self.child: List[str] = []

DesignSpace = Dict[str, DesignParameter]

