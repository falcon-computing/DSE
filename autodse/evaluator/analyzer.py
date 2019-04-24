"""
The main module of analyzer.
"""
import json
import os
from typing import List, Optional, Tuple

from ..logger import get_logger
from ..result import HLSResult, Job, MerlinResult, ResultBase

LOG = get_logger('Analyzer')


class Analyzer():
    """Main analyzer class"""

    @staticmethod
    def analyze(job: Job, mode: str) -> Optional[ResultBase]:
        """Analyze the job result and return a result object

        Parameters
        ----------
        job:
            The job to be analyzed.

        mode:
            The customized mode for analysis.

        Returns
        -------
        Optional[ResultBase]:
            The analysis result.
        """
        raise NotImplementedError()

    @staticmethod
    def desire(mode: str) -> List[str]:
        """Return a list of desired file name wildcards for analysis

        Parameters
        ----------
        mode:
            The customized mode for analysis.

        Returns
        -------
        List[str]:
            A list of desired file name wildcards for analysis.
        """
        raise NotImplementedError()


class MerlinAnalyzer(Analyzer):
    """"The analyzer especially for Merlin projects"""

    critical_msgs = [
        'Memory burst NOT inferred', 'Coarse-grained pipelining NOT applied on loop',
        'Coarse-grained parallelization NOT applied'
    ]

    resource_types = ['BRAM', 'FF', 'LUT', 'DSP']

    @staticmethod
    def analyze_merlin_log(job: Job, success_msg) -> Tuple[bool, float]:
        """Analyze merlin.log to check if Merlin flow encounters any issues

        Parameters
        ----------
        job:
            The job to be analyzed.

        success_msg:
            A string in the log file to indicate the flow was success.

        Returns
        -------
        Tuple[bool, float]:
            Indicate if the flow was success and the total runtime if success.
        """

        merlin_log_path = os.path.join(job.path, 'merlin.log')
        if not os.path.exists(merlin_log_path):
            LOG.debug('Cannot find merlin.log for analysis')
            return (False, -1)

        success = False
        eval_time = 0.0
        with open(merlin_log_path, 'r') as log_file:
            for line in log_file:
                if line.find(success_msg) != -1:
                    success = True
                elif line.find('Total time: ') != -1:
                    try:
                        eval_time += float(line[12:line.find('seconds')])
                    except ValueError:
                        LOG.error('Failed to convert runtime %s to float',
                                  line[12:line.find('seconds')])
                        return (False, -1)
        return (success, eval_time)

    @staticmethod
    def analyze_merlin_transform(job: Job) -> Optional[MerlinResult]:
        """Analyze the Merlin transformation result and fetch critical messages

        Parameters
        ----------
        job:
            The job to be analyzed.

        Returns
        -------
        Optional[MerlinResult]:
            The analysis result.
        """

        merlin_log_path = os.path.join(job.path, 'merlin.log')
        if not os.path.exists(merlin_log_path):
            LOG.debug('Cannot find merlin.log for analysis')
            return None

        success, eval_time = MerlinAnalyzer.analyze_merlin_log(
            job, 'Compilation finished successfully')
        if not success:
            return None

        result = MerlinResult(job.key)
        result.eval_time = eval_time
        with open(merlin_log_path, 'r') as log_file:
            for line in log_file:
                if any(line.find(msg) != -1 for msg in MerlinAnalyzer.critical_msgs):
                    result.criticals.append(line.replace('\n', ''))

        return result

    @staticmethod
    def analyze_merlin_hls(job: Job) -> Optional[HLSResult]:
        """Analyze the Merlin HLS result for QoR and performance bottleneck

        Parameters
        ----------
        job:
            The job to be analyzed.

        Returns
        -------
        Optional[HLSResult]:
            The analysis result.
        """

        success, eval_time = MerlinAnalyzer.analyze_merlin_log(job, 'Estimation successfully.')
        if not success:
            return None

        result = HLSResult(job.key)
        result.eval_time = eval_time

        # Merlin HLS report analysis
        report_path = os.path.join(job.path, '.merlin_prj/run/implement/exec/hls/report_merlin')
        hier_path = os.path.join(report_path, 'hierarchy.json')
        info_path = os.path.join(report_path, 'final_info.json')
        if not os.path.exists(hier_path) or not os.path.exists(info_path):
            LOG.debug('Cannot find Merlin report files for analysis')
            return None

        with open(info_path, 'r') as filep:
            try:
                hls_info = json.load(filep)
            except ValueError as err:
                LOG.error('Failed to read Merlin report %s: %s', info_path, str(err))
                return None

        # Backup an entire report for future usage
        #result.report = hls_info

        # Fetch total cycle and resource util as performance QoR
        for elt in hls_info:
            # Extract cycles
            if 'CYCLE_TOT' in hls_info[elt]:
                try:
                    result.perf = max(float(hls_info[elt]['CYCLE_TOT']), result.perf)
                except ValueError:
                    # Some compoenents may be flatten and do not have cycle number
                    pass

            # Extract resource utilizations
            for res in MerlinAnalyzer.resource_types:
                util_key = 'util-{0}'.format(res)
                total_key = 'total-{0}'.format(res)

                if not util_key in hls_info[elt] or not total_key in hls_info[elt]:
                    continue

                try:
                    result.res_util[util_key] = max(
                        float(hls_info[elt][util_key]) / 100.0, result.res_util[util_key])
                    result.res_util[total_key] = max(float(hls_info[elt][total_key]),
                                                     result.res_util[total_key])
                except ValueError:
                    # Some compoenents may not have resource number
                    pass

        # TODO: Hotspot analysis

        return result

    @staticmethod
    def analyze(job: Job, mode: str) -> Optional[ResultBase]:
        #pylint:disable=missing-docstring

        if mode == 'transform':
            return MerlinAnalyzer.analyze_merlin_transform(job)
        if mode == 'hls':
            return MerlinAnalyzer.analyze_merlin_hls(job)

        LOG.error('Unrecognized analysis target %s', mode)
        return None

    @staticmethod
    def desire(mode: str) -> List[str]:
        #pylint:disable=missing-docstirng

        if mode == 'transform':
            return ['merlin.log']
        if mode == 'hls':
            return [
                'merlin.log', '.merlin_prj/run/implement/exec/hls/report_merlin/final_info.json',
                '.merlin_prj/run/implement/exec/hls/report_merlin/hierarchy.json'
            ]

        LOG.error('Unrecognized analysis target %s', mode)
        return []
