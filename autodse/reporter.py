"""
The module of reporter.
"""
from typing import Any, Dict, List, Tuple
import texttable as tt

from .database import Database
from .logger import get_default_logger
from .result import BitgenResult, Result


class Reporter():
    """Main reporter class"""

    ANIME = ['-', '\\', '|', '/']
    RetCodeMap = {
        Result.RetCode.PASS: 'Finished',
        Result.RetCode.UNAVAILABLE: 'Unavailable',
        Result.RetCode.ANALYZE_ERROR: 'Error',
        Result.RetCode.TIMEOUT: 'Timeout',
        Result.RetCode.EARLY_REJECT: 'Early Reject',
        Result.RetCode.DUPLICATED: 'Duplicate'
    }
    BestHistFormat = '|{0:7s}|{1:7s}|{2:43s}|'

    def __init__(self, config: Dict[str, Any], db: Database):
        self.log = get_default_logger('Report')

        self.config = config
        self.db = db
        self.anime_ptr = 0

        self.is_first_best = True
        self.best_quality = -float('inf')

    def log_config(self, mode: str) -> None:
        """Log important configs"""

        self.log.info('DSE Configure')
        tbl = tt.Texttable()
        tbl.header(['Config', 'Value'])
        tbl.add_row(['Project', self.config['project']['name']])
        tbl.add_row(['Backup mode', self.config['project']['backup']])
        tbl.add_row(['Fast mode output #', str(self.config['project']['fast-output-num'])])
        tbl.add_row(['Execution mode', mode])
        tbl.add_row(['Search approach', self.config['search']['algorithm']['name']])
        tbl.add_row(['DSE time', str(self.config['timeout']['exploration'])])
        tbl.add_row(['HLS time', str(self.config['timeout']['hls'])])
        if mode == 'accurate-dse':
            tbl.add_row(['P&R time', str(self.config['timeout']['bitgen'])])
        for line in tbl.draw().split('\n'):
            self.log.info(line)
        self.log.info('The actual elapsed time may be over the set up exploration time')
        self.log.info('because we do not abandon the effort of running cases')

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

        # Reset the best quality
        self.best_quality = -float('inf')

        if not outputs:
            self.log.warning('No design point is outputed')
            return ''

        tbl = tt.Texttable()
        tbl.header(['Directory', 'Quality', 'Perf.', 'Resource', 'Frequency'])
        tbl.set_cols_dtype(['t'] * 5)

        for result in outputs:
            assert result.path is not None
            row = [
                result.path, '{0:.2e}'.format(result.quality), '{0:.0f}'.format(result.perf),
                ', '.join([
                    '{0}:{1:.1f}%'.format(k[5:], v * 100.0) for k, v in result.res_util.items()
                    if k.startswith('util')
                ])
            ]
            if isinstance(result, BitgenResult):
                row.append('{0:.2f}'.format(result.freq))
            else:
                row.append('----')
            tbl.add_row(row)
        return tbl.draw()

    def report_summary(self) -> Tuple[str, str]:
        """Summarize the explored points in the DB

        Returns
        -------
        str:
            The summary report.
        """

        keys = self.db.query_keys()

        # Query total explored points
        cnt_keys = [k for k in keys if k.startswith('meta-expr-cnt')]
        total = sum([cnt for cnt in self.db.batch_query(cnt_keys) if isinstance(cnt, int)])
        rpt = 'DSE Summary\n'
        tbl = tt.Texttable()
        tbl.add_row(['Total Explored', str(total)])

        lv_keys = []
        lv_data = []

        # Query level 1 results
        lv_keys.append([k for k in keys if k.startswith('lv1')])
        lv_data.append([r for r in self.db.batch_query(lv_keys[0]) if r is not None])

        tbl.add_row([
            'Level 1 Timeout',
            str(sum([1 for r in lv_data[0] if r.ret_code == Result.RetCode.TIMEOUT]))
        ])
        tbl.add_row([
            'Level 1 Analysis Error',
            str(sum([1 for r in lv_data[0] if r.ret_code == Result.RetCode.ANALYZE_ERROR]))
        ])
        tbl.add_row([
            'Level 1 Early Reject',
            str(sum([1 for r in lv_data[0] if r.ret_code == Result.RetCode.EARLY_REJECT]))
        ])
        tbl.add_row([
            'Level 1 Result Unavailable',
            str(sum([1 for r in lv_data[0] if r.ret_code == Result.RetCode.UNAVAILABLE]))
        ])

        # Query level 2 results
        lv_keys.append([k for k in keys if k.startswith('lv2')])
        lv_data.append([r for r in self.db.batch_query(lv_keys[1]) if r is not None])
        tbl.add_row([
            'Level 2 Timeout',
            str(sum([1 for r in lv_data[1] if r.ret_code == Result.RetCode.TIMEOUT]))
        ])
        tbl.add_row([
            'Level 2 Analysis Error',
            str(sum([1 for r in lv_data[1] if r.ret_code == Result.RetCode.ANALYZE_ERROR]))
        ])
        tbl.add_row([
            'Level 2 Duplicate',
            str(sum([1 for r in lv_data[1] if r.ret_code == Result.RetCode.DUPLICATED]))
        ])
        tbl.add_row([
            'Level 2 Result Unavailable',
            str(sum([1 for r in lv_data[1] if r.ret_code == Result.RetCode.UNAVAILABLE]))
        ])

        # Query level 3 results
        lv_keys.append([k for k in keys if k.startswith('lv3')])
        lv_data.append([r for r in self.db.batch_query(lv_keys[2]) if r is not None])
        if lv_data[2]:
            tbl.add_row([
                'Level 3 Timeout',
                str(sum([1 for r in lv_data[2] if r.ret_code == Result.RetCode.TIMEOUT]))
            ])
            tbl.add_row([
                'Level 3 Analysis Error',
                str(sum([1 for r in lv_data[2] if r.ret_code == Result.RetCode.ANALYZE_ERROR]))
            ])
            tbl.add_row([
                'Level 3 Result Unavailable',
                str(sum([1 for r in lv_data[2] if r.ret_code == Result.RetCode.UNAVAILABLE]))
            ])

        tbl.add_row(['Output Points', str(self.db.best_cache.qsize())])

        try:
            _, _, best_result = max(self.db.best_cache.queue, key=lambda r: r[0])  # type: ignore
            tbl.add_row(['Best Performance (cycle)', str(best_result.perf)])
            if isinstance(best_result, BitgenResult):
                tbl.add_row(['Best Freq.', str(best_result.freq)])
        except ValueError:
            pass

        rpt += tbl.draw()
        if not total:
            return rpt, ''

        assert lv_data[0][0].point is not None
        param_names = list(lv_data[0][0].point.keys())

        for lv_idx, data in enumerate(lv_data):
            if not data:
                continue
            detail_rpt = 'Level {0} Result Details\n'.format(lv_idx + 1)
            detail_tbl = tt.Texttable(max_width=100)
            detail_tbl.set_cols_align(['c'] * 6)
            detail_tbl.set_cols_dtype([
                't',  # ID
                't',  # Performance
                't',  # Resource
                't',  # Status
                't',  # Valid
                'f'  # Time
            ])
            detail_tbl.set_precision(1)
            detail_tbl.header([
                'ID', 'Perf.',
                ', '.join([k[5:] for k in data[0].res_util.keys() if k.startswith('util')]),
                'Status', 'Valid', 'Time'
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

    def print_status(self, timer: float, count: int) -> None:
        """Pretty print the current exploration status

        Parameters
        ----------
        timer:
            The elapsed time for exploration.

        count:
            The number of explored points.
        """

        if timer < float(self.config['timeout']['exploration']):
            print('[{0:4.0f}m] Explored {1} points, still working...{2}'.format(
                timer, count, self.ANIME[self.anime_ptr]),
                  end='\r')
        else:
            print('[{0:4.0f}m] Explored {1} points, finishing...{2}    '.format(
                timer, count, self.ANIME[self.anime_ptr]),
                  end='\r')
        self.anime_ptr = 0 if self.anime_ptr == 3 else self.anime_ptr + 1
