"""
The unit test module of config.
"""

from autodse.database import PickleDatabase
from autodse.logger import get_default_logger
from autodse.reporter import Reporter

LOG = get_default_logger('UNIT-TEST', 'DEBUG')


def test_reporter(test_dir, capsys):
    #pylint:disable=missing-docstring

    LOG.info('=== Testing reporter start')

    config = {}
    config['evaluate'] = {}
    config['evaluate']['estimate-mode'] = 'FAST'
    config['timeout'] = {}
    config['timeout']['exploration'] = '2'
    db = PickleDatabase('test', 2, '{0}/temp_fixture/db/0.db'.format(test_dir))
    db.load()

    while db.best_cache.qsize() > 2:
        db.best_cache.get()

    reporter = Reporter(config, db)

    # Test print status
    reporter.print_status(0)
    captured = capsys.readouterr()
    assert captured.out == '[   0m] Explored 145 points, still working...-\r'

    reporter.print_status(1)
    captured = capsys.readouterr()
    assert captured.out == '[   1m] Explored 145 points, still working...\\\r'

    reporter.print_status(2)
    captured = capsys.readouterr()
    assert captured.out == '[   2m] Explored 145 points, finishing...|    \r'

    # Test log best
    # TODO: Capture log and check the format
    reporter.log_best()

    # Test summary
    rpt = reporter.report_summary()
    assert rpt[0].find('Total Explored') != -1
    assert rpt[1].find('Result Details') != -1

    # Test output
    output = []
    idx = 0
    best_cache = db.best_cache
    while not best_cache.empty():
        _, _, result = best_cache.get()
        result.path = str(idx)
        output.append(result)
        idx += 1
    assert reporter.report_output(output)

    LOG.info('=== Testing reporter end')
