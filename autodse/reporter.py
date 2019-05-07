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
    ConfigFormat = '|{0:15s}|{1:40s}|'
    BestHistFormat = '|{0:7s}|{1:7s}|{2:43s}|'
    OutputFormat = '|{0:14s}|{1:7s}|{2:7s}|{3:43s}|\n'
    SummaryFormat = '|{0:15s}|{1:15s}|\n'

    def __init__(self, config: Dict[str, Any], db: Database):
        self.config = config
        self.db = db
        self.anime_ptr = 0

        self.is_first_best = True
        self.best_quality = -float('inf')

    def log_config(self) -> None:
        """Log important configs"""

        LOG.info('DSE Configure')
        LOG.info(self.ConfigFormat.format('-' * 15, '-' * 40))
        LOG.info(self.ConfigFormat.format('Config', 'Value'))
        LOG.info(self.ConfigFormat.format('-' * 15, '-' * 40))
        LOG.info(self.ConfigFormat.format('Project', self.config['project']['name']))
        LOG.info(self.ConfigFormat.format('Backup mode', self.config['project']['backup']))
        LOG.info(
            self.ConfigFormat.format('Expected output', str(self.config['project']['output-num'])))
        LOG.info(
            self.ConfigFormat.format('Evaluate mode', self.config['evaluate']['estimate-mode']))
        LOG.info(
            self.ConfigFormat.format('Search approach',
                                     self.config['search']['algorithm']['name']))
        LOG.info(self.ConfigFormat.format('DSE time', str(self.config['timeout']['exploration'])))
        LOG.info(self.ConfigFormat.format('HLS time', str(self.config['timeout']['hls'])))
        LOG.info(self.ConfigFormat.format('P&R time', str(self.config['timeout']['bitgen'])))
        LOG.info(self.ConfigFormat.format('-' * 15, '-' * 40))
        LOG.info('The actual elapsed time may be over the set up exploration time because '
                 'we do not abandon the effort of running cases')

    def log_best(self) -> None:
        """Log the new best result if available"""

        try:
            best_quality, _, best_result = max(self.db.best_cache.queue,
                                               key=lambda r: r[0])  # type: ignore
        except ValueError:
            # Best cache is still empty
            return

        if self.is_first_best:
            LOG.info('Best result reporting...')
            LOG.info(self.BestHistFormat.format('-' * 7, '-' * 7, '-' * 43))
            LOG.info(self.BestHistFormat.format('Quality', 'Perf.', 'Resource'))
            LOG.info(self.BestHistFormat.format('-' * 7, '-' * 7, '-' * 43))
            self.is_first_best = False

        if self.best_quality < best_quality:
            self.best_quality = best_quality
            LOG.info(
                self.BestHistFormat.format(
                    '{:.1e}'.format(best_quality), '{:.1e}'.format(best_result.perf), ', '.join([
                        '{0}:{1:.1f}%'.format(k[5:], v * 100.0)
                        for k, v in best_result.res_util.items() if k.startswith('util')
                    ])))

    def log_best_close(self) -> None:
        """Log the final line of the best result progress"""

        LOG.info(self.BestHistFormat.format('-' * 7, '-' * 7, '-' * 43))

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
        rpt += self.OutputFormat.format('-' * 14, '-' * 7, '-' * 7, '-' * 43)
        rpt += self.OutputFormat.format('Directory', 'Quality', 'Perf.', 'Resource')
        rpt += self.OutputFormat.format('-' * 14, '-' * 7, '-' * 7, '-' * 43)

        for result in outputs:
            assert result.path is not None
            rpt += self.OutputFormat.format(
                result.path, '{:.1e}'.format(result.quality), '{:.1e}'.format(result.perf),
                ', '.join([
                    '{0}:{1:.1f}%'.format(k[5:], v * 100.0) for k, v in result.res_util.items()
                    if k.startswith('util')
                ]))

        rpt += self.OutputFormat.format('-' * 14, '-' * 7, '-' * 7, '-' * 43)
        return rpt

    def report_summary(self) -> str:
        """Summarize the explored points in the DB

        Returns
        -------
        str:
            The summary report.
        """

        rpt = ''
        rpt += self.SummaryFormat.format('-' * 15, '-' * 15)
        rpt += self.SummaryFormat.format('Total Explored', str(self.db.count_ret_code(0)))
        rpt += self.SummaryFormat.format('Timeout', str(self.db.count_ret_code(-3)))
        rpt += self.SummaryFormat.format('Analysis Error', str(self.db.count_ret_code(-2)))
        rpt += self.SummaryFormat.format('Output Points', str(self.db.best_cache.qsize()))

        try:
            _, _, best_result = max(self.db.best_cache.queue, key=lambda r: r[0])  # type: ignore
            if self.config['evaluate']['estimate-mode'] == 'FAST':
                rpt += self.SummaryFormat.format('Best Cycle', str(best_result.perf))
            #else:
            #    rpt += self.SummaryFormat.format('Best Freq.', str(best_result.perf))
            #    rpt += self.SummaryFormat.format('Best Runtime', str(best_result.freq))
        except ValueError:
            pass

        rpt += self.SummaryFormat.format('-' * 15, '-' * 15)
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
