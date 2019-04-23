"""
The main module of evaluator.
"""
import os
import re
import shutil
import tempfile
from enum import Enum
from typing import List, Optional, Set

from ..logger import get_logger
from ..parameter import DesignPoint
from ..result import HLSResult, ResultBase
from ..util import copy_dir

LOG = get_logger('Evaluator')

TEMP_DIR_PREFIX = 'merlin_'


class EvalMode(Enum):
    HLS = 0
    BITGEN = 1
    PROFILE = 2


class Evaluator():
    """Main evaluator class"""

    def __init__(self, src_path: str, work_path: str):
        self.src_path = src_path
        self.work_path = work_path

        if os.path.exists(self.work_path):
            shutil.rmtree(self.work_path, ignore_errors=True)
        os.mkdir(self.work_path)

        # Scan the folder and identify the files with design parameters (auto keyword)
        # Note that since we directly scan the text in source code, we will not know if
        # an auto keyword is in comments or macros. Now we expect these invalid parameters
        # will not have corresponding definitions in design point and will ignore them when
        # applying the design point. If a valid parameter does not have corresponding definition
        # in the design point, then the Merlin compiler will error out so we could let user know.
        self.src_files: List[str] = []
        for file_name in os.listdir(src_path):
            with open('{0}/{1}'.format(src_path, file_name), 'r') as filep:
                autos = re.findall(r'(auto{(.*?)})', filep.read(), re.IGNORECASE)
                if autos:
                    self.src_files.append(file_name)

        if not self.src_files:
            LOG.error('Cannot find any kernel files with auto pragma.')
            raise RuntimeError()

    def create_job(self) -> Optional[str]:
        """Create a new folder and copy source code for a design point to be evaluated

        Returns
        -------
        str:
            The job folder path
        """

        path = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX, dir='{0}/'.format(self.work_path))
        if not copy_dir(self.src_path, path):
            return None
        LOG.debug('Created a new job at %s', path)
        return path

    def apply_design_point(self, job_path: str, point: DesignPoint) -> bool:
        """Apply the given design point to the source code in job path

        Parameters
        ----------
        job_path:
            The path that contains kernel source code with auto pragmas to be applied

        point:
            The design point that indicates specific values to design parameters

        Returns
        -------
        bool:
            Indicate if the application was success or not
        """

        applied: Set[str] = set()
        for file_name in self.src_files:
            with open('{0}/{1}'.format(job_path, file_name),
                      'r') as src_file, open('{0}/applier_temp.txt'.format(job_path),
                                             'w') as dest_file:
                for line in src_file:
                    for auto, ds_id in re.findall(r'(auto{(.*?)})', line, re.IGNORECASE):
                        if ds_id not in point:
                            LOG.debug('Parameter %s not found in design point', ds_id)
                        else:
                            # Replace "auto{?}" with a specific value
                            line = line.replace(auto, str(point[ds_id]))
                            applied.add(ds_id)
                    dest_file.write(line)
            os.replace('{0}/applier_temp.txt'.format(job_path),
                       '{0}/{1}'.format(job_path, file_name))

        # Check if all design parameters were applied
        error = 0
        for ds_id in point.keys():
            if ds_id not in applied:
                LOG.error('Cannot find the corresponding auto{%s} in source files', ds_id)
                error += 1
        return error == 0

    @staticmethod
    def submit(job_path: str, mode: EvalMode, timeout: int = 0) -> bool:
        """Submit the given job to the scheduler for evaluation

        Parameters
        ----------
        job_path:
            The path that contains kernel source code

        mode:
            The evaluation mode

        timeout:
            The timeout of the evaluation. Set to 0 to indicate no timeout.

        Returns
        -------
        bool:
            Indicate if the evaluation was success or not. Note that an evaluation is considered
            as success as long as it was terminated without any error, so timeout or HLS faliure
            are also considered as success.
        """

        # TODO: Submit the job to scheduler.
        return True

    @staticmethod
    def parse_result(job_path, mode: EvalMode) -> Optional[ResultBase]:
        """Parse the evaluation result based on different mode

        Parameters
        ----------
        job_path:
            The path that contains kernel source code

        mode:
            The evaluation mode

        Returns
        -------
        bool:
            Indicate if the evaluation was success or not. Note that an evaluation is considered
            as success as long as it was terminated without any error, so timeout or HLS faliure
            are also considered as success.
        """

        # TODO: Parse the job directory and create a result object.
        return None
