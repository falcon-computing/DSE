"""
The unit test module of config.
"""

from autodse.database import PickleDatabase
from autodse.logger import get_default_logger
from autodse.reporter import Reporter
from autodse.result import BitgenResult, HLSResult, Result

LOG = get_default_logger('UNIT-TEST', 'DEBUG')


def test_reporter(test_dir, capsys):
    #pylint:disable=missing-docstring

    LOG.info('=== Testing reporter start')

    config = {}
    config['timeout'] = {}
    config['timeout']['exploration'] = '2'
    db = PickleDatabase('test', '{0}/temp_fixture/db/0.db'.format(test_dir))
    db.load()

    while db.best_cache.qsize() > 1:
        db.best_cache.get()

    reporter = Reporter(config, db)

    # Test print status
    reporter.print_status(0, 130)
    captured = capsys.readouterr()
    assert captured.out == '[   0m] Explored 130 points, still working...-\r'

    reporter.print_status(1, 145)
    captured = capsys.readouterr()
    assert captured.out == '[   1m] Explored 145 points, still working...\\\r'

    reporter.print_status(2, 150)
    captured = capsys.readouterr()
    assert captured.out == '[   2m] Explored 150 points, finishing...|    \r'

    # Test log best
    # TODO: Capture log and check the format
    reporter.log_best()

    # Test summary
    rpt = reporter.report_summary()
    assert rpt[0].find('Total Explored') != -1, rpt
    assert rpt[1].find('Result Details') != -1, rpt

    # Test fast output
    output = []
    idx = 0
    results = [r for r in db.query_all() if isinstance(r, HLSResult)]
    for result in results:
        result.path = str(idx)
        output.append(result)
        idx += 1
    assert reporter.report_output(output)

    # Test accurate output
    output = []
    result = Result()
    result.path = '0'
    result.res_util = {'util-BRAM': 0, 'util-LUT': 0, 'util-DSP': 0, 'util-FF': 0}
    output.append(result)
    result = BitgenResult()
    result.perf = 5e6
    result.freq = 275
    result.path = '1'
    result.quality = 1 / result.perf / result.quality
    result.res_util = {'util-BRAM': 0.3, 'util-LUT': 0.2, 'util-DSP': 0, 'util-FF': 0.1}
    output.append(result)
    result = BitgenResult()
    result.perf = 10e5
    result.freq = 120
    result.path = '2'
    result.quality = 1 / result.perf / result.quality
    result.res_util = {'util-BRAM': 0.6, 'util-LUT': 0.7, 'util-DSP': 0, 'util-FF': 0.4}
    output.append(result)
    #assert reporter.report_output(output)
    LOG.info(reporter.report_output(output))

    LOG.info('=== Testing reporter end')
