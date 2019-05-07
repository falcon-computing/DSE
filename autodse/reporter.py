"""
The module of reporter.
"""
from typing import Any, Dict, List

from .database import Database
from .logger import get_default_logger
from .result import ResultBase

LOG = get_default_logger('Report')


class Reporter():
    """Main reporter class"""

    ANIME = ['-', '\\', '|', '/']
    BestHistFormat = '|{0:7s}|{1:7s}|{2:43s}|'
    OutputFormat = '|{0:14s}|{1:7s}|{2:7s}|{3:43s}|'

    def __init__(self, config: Dict[str, Any], db: Database):
        self.config = config
        self.db = db
        self.anime_ptr = 0

        self.is_first_best = True
        self.best_quality = -float('inf')

    def log_best(self) -> None:
        """Log the new best result if available"""

        try:
            best_quality, best_result = max(self.db.best_cache, key=lambda r: r[0])  # type: ignore
        except ValueError:
            # Best cache is still empty
            return

        if self.is_first_best:
            LOG.info('Best result reporting...')
            LOG.info('-' * 57)
            LOG.info(self.BestHistFormat.format('Quality', 'Perf.', 'Resource'))
            LOG.info(self.BestHistFormat.format('-' * 7, '-' * 7, '-' * 43))
            self.is_first_best = False

        if self.best_quality < best_quality:
            self.best_quality = best_quality
            LOG.info(
                self.BestHistFormat.format(
                    '{:.1e}'.format(best_quality), '{:.1e}'.format(best_result.perf), ', '.join([
                        '{0}:{1:.1f}%'.format(k[5:], v) for k, v in best_result.res_util.items()
                        if k.startswith('util')
                    ])))

    def report_output(self, outputs: List[ResultBase]) -> str:
        """Report the final output.

        Parameters
        ----------
        outputs:
            A list results to be reported and outputed.

        Returns
        -------
        str:
            The output report.
        """

        if not outputs:
            LOG.warning('No design point is outputed')
            return ''

        rpt = ''
        rpt += '-' * 71
        rpt += '\n'
        rpt += self.OutputFormat.format('Directory', 'Quality', 'Perf.', 'Resource')
        rpt += '\n'
        rpt += self.OutputFormat.format('-' * 14, '-' * 7, '-' * 7, '-' * 43)
        rpt += '\n'

        for result in outputs:
            assert result.path is not None
            rpt += self.OutputFormat.format(
                result.path, '{:.1e}'.format(result.quality), '{:.1e}'.format(result.perf),
                ', '.join([
                    '{0}:{1:.1f}%'.format(k[5:], v) for k, v in result.res_util.items()
                    if k.startswith('util')
                ]))
            rpt += '\n'

        rpt += '-' * 71
        rpt += '\n'

        return rpt

    def print_status(self, timer: float) -> None:
        """Pretty print the current exploration status

        Parameters
        ----------
        timer:
            The elapsed time for exploration.
        """

        count = self.db.count()
        if timer < float(self.config['timeout']['exploration']):
            print('[{0:4.0f}m] Explored {1} points, still working...{2}'.format(
                timer, count, self.ANIME[self.anime_ptr]),
                  end='\r')
        else:
            print('[{0:4.0f}m] Explored {1} points, finishing...{2}    '.format(
                timer, count, self.ANIME[self.anime_ptr]),
                  end='\r')
        self.anime_ptr = 0 if self.anime_ptr == 3 else self.anime_ptr + 1
