"""
The module of reporter.
"""
from typing import Any, Dict, List, Tuple
import texttable as tt

from .database import Database
from .logger import get_default_logger
from .result import Result


class Reporter():
    """Main reporter class"""

    ANIME = ['-', '\\', '|', '/']
    RetCodeMap = {
        Result.RetCode.PASS: 'Finished',
        Result.RetCode.UNAVAILABLE: 'Unknown',
        Result.RetCode.ANALYZE_ERROR: 'Error',
        Result.RetCode.TIMEOUT: 'Timeout',
        Result.RetCode.EARLY_REJECT: 'Early Reject'
    }
    BestHistFormat = '|{0:7s}|{1:7s}|{2:43s}|'

    def __init__(self, config: Dict[str, Any], db: Database):
        self.log = get_default_logger('Report')

        self.config = config
        self.db = db
        self.anime_ptr = 0

        self.is_first_best = True
        self.best_quality = -float('inf')

    def log_config(self) -> None:
        """Log important configs"""

        self.log.info('DSE Configure')
        tbl = tt.Texttable()
        tbl.header(['Config', 'Value'])
        tbl.add_row(['Project', self.config['project']['name']])
        tbl.add_row(['Backup mode', self.config['project']['backup']])
        tbl.add_row(['Expected output', str(self.config['project']['output-num'])])
        tbl.add_row(['Evaluate mode', self.config['evaluate']['estimate-mode']])
        tbl.add_row(['Search approach', self.config['search']['algorithm']['name']])
        tbl.add_row(['DSE time', str(self.config['timeout']['exploration'])])
        tbl.add_row(['HLS time', str(self.config['timeout']['hls'])])
        tbl.add_row(['P&R time', str(self.config['timeout']['bitgen'])])
        for line in tbl.draw().split('\n'):
            self.log.info(line)
        self.log.info('The actual elapsed time may be over the set up exploration time because '
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
            self.log.info('Best result reporting...')
            self.log.info('+{0:7s}+{1:7s}+{2:43s}+'.format('-' * 7, '-' * 7, '-' * 43))
            self.log.info(self.BestHistFormat.format('Quality', 'Perf.', 'Resource'))
            self.log.info('+{0:7s}+{1:7s}+{2:43s}+'.format('-' * 7, '-' * 7, '-' * 43))
            self.is_first_best = False

        if self.best_quality < best_quality:
            self.best_quality = best_quality
            self.log.info(
                self.BestHistFormat.format(
                    '{:.1e}'.format(best_quality), '{:.1e}'.format(best_result.perf), ', '.join([
                        '{0}:{1:.1f}%'.format(k[5:], v * 100.0)
                        for k, v in best_result.res_util.items() if k.startswith('util')
                    ])))
            self.log.info('+{0:7s}+{1:7s}+{2:43s}+'.format('-' * 7, '-' * 7, '-' * 43))

    def report_output(self, outputs: List[Result]) -> str:
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
            self.log.warning('No design point is outputed')
            return ''

        tbl = tt.Texttable()
        tbl.header(['Directory', 'Quality', 'Perf.', 'Resource'])

        for result in outputs:
            assert result.path is not None
            tbl.add_row([
                result.path, '{:.1e}'.format(result.quality), '{:.1e}'.format(result.perf),
                ', '.join([
                    '{0}:{1:.1f}%'.format(k[5:], v * 100.0) for k, v in result.res_util.items()
                    if k.startswith('util')
                ])
            ])

        return tbl.draw()

    def report_summary(self) -> Tuple[str, str]:
        """Summarize the explored points in the DB

        Returns
        -------
        str:
            The summary report.
        """

        total = max(self.db.count() - 1, 0)  # Exclude the metadata

        rpt = 'DSE Summary\n'
        tbl = tt.Texttable()
        tbl.add_row(['Total Explored', str(total)])
        tbl.add_row(['Timeout', str(self.db.count_ret_code(Result.RetCode.TIMEOUT))])
        tbl.add_row(['Analysis Error', str(self.db.count_ret_code(Result.RetCode.ANALYZE_ERROR))])
        tbl.add_row(['Early Reject', str(self.db.count_ret_code(Result.RetCode.EARLY_REJECT))])
        tbl.add_row(['Output Points', str(self.db.best_cache.qsize())])

        try:
            _, _, best_result = max(self.db.best_cache.queue, key=lambda r: r[0])  # type: ignore
            if self.config['evaluate']['estimate-mode'] == 'FAST':
                tbl.add_row(['Best Cycle', str(best_result.perf)])
            #else:
            #    tbl.add_row(['Best Freq.', str(best_result.perf)])
            #    tbl.add_row(['Best Runtime', str(best_result.freq)])
        except ValueError:
            pass

        rpt += tbl.draw()
        if not total:
            return rpt, ''

        data = [r for r in self.db.query_all() if isinstance(r, Result)]
        assert data[0].point is not None
        param_names = list(data[0].point.keys())

        detail_rpt = 'Result Details\n'
        detail_tbl = tt.Texttable(max_width=100)
        detail_tbl.set_cols_align(['c'] * 6)
        detail_tbl.set_cols_dtype([
            't',  # ID
            't',  # Performance
            't',  # Resource
            't',  # Status
            't',  # Valid
            'f'   # Time
        ])
        detail_tbl.set_precision(1)
        detail_tbl.header([
            'ID', 'Perf.',
            ', '.join([k[5:] for k in data[0].res_util.keys() if k.startswith('util')]), 'Status',
            'Valid', 'Time'
        ])
        for idx, result in enumerate(data):
            row = [str(idx)]

            # Attach result
            row.append('{:.2e}'.format(result.perf) if result.perf else '----')
            if all([v == 0 for k, v in result.res_util.items() if k.startswith('util')]):
                row.append('----')
            else:
                row.append(', '.join([
                    '{:.1f}%'.format(v * 100.0) for k, v in result.res_util.items()
                    if k.startswith('util')
                ]))
            row.append(self.RetCodeMap[result.ret_code])
            row.append('Yes' if result.valid else 'No')
            row.append(str(result.eval_time / 60.0))
            detail_tbl.add_row(row)
        detail_rpt += detail_tbl.draw()
        detail_rpt += '\n\n'

        detail_rpt += 'Explored Points\n'
        for start in range(0, len(param_names), 8):
            names = param_names[start:min(start + 8, len(param_names))]
            point_tbl = tt.Texttable(max_width=100)
            point_tbl.set_cols_align(['c'] * (len(names) + 1))
            point_tbl.set_cols_dtype(['t'] * (len(names) + 1))
            point_tbl.header(['ID'] + names)
            for idx, result in enumerate(data):
                if result.point is not None:
                    point_tbl.add_row([str(idx)] + [str(result.point[p]) for p in names])
                else:
                    point_tbl.add_row([str(idx)] + ['?'] * len(names))
            detail_rpt += point_tbl.draw()
            detail_rpt += '\n'

        return rpt, detail_rpt

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
