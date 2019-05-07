"""
The unit test module of config.
"""
import queue

from autodse.database import Database
from autodse.logger import get_default_logger
from autodse.result import ResultBase
from autodse.reporter import Reporter

LOG = get_default_logger('UNIT-TEST', 'DEBUG')


def test_reporter(mocker, capsys):
    #pylint:disable=missing-docstring

    LOG.info('=== Testing reporter start')

    config = {}
    config['timeout'] = {}
    config['timeout']['exploration'] = '2'

    with mocker.patch.object(Database, '__init__', return_value=None):
        db = Database('test')
        reporter = Reporter(config, db)

        # Test print status
        mocker.patch.object(reporter.db, 'count', return_value=3)
        reporter.print_status(0)
        captured = capsys.readouterr()
        assert captured.out == '[   0m] Explored 3 points, still working...-\r'

        mocker.patch.object(reporter.db, 'count', return_value=5)
        reporter.print_status(1)
        captured = capsys.readouterr()
        assert captured.out == '[   1m] Explored 5 points, still working...\\\r'

        mocker.patch.object(reporter.db, 'count', return_value=8)
        reporter.print_status(2)
        captured = capsys.readouterr()
        assert captured.out == '[   2m] Explored 8 points, finishing...|    \r'

        # Test log best
        # TODO: Capture log and check the format
        cache = queue.PriorityQueue()
        result1 = ResultBase()
        result1.path = '1'
        result1.valid = True
        result1.quality = 5
        cache.put((5, result1))
        reporter.db.best_cache = cache

        reporter.log_best()

        result2 = ResultBase()
        result2.path = '2'
        result2.valid = True
        result2.quality = 33
        cache.put((33, result2))
        reporter.log_best()

        result3 = ResultBase()
        result3.path = '3'
        result3.valid = True
        result3.quality = 48
        cache.put((48, result3))
        reporter.log_best()

        # Test output
        output = []
        while not cache.empty():
            output.append(cache.get()[1])
        assert reporter.report_output(output)

    LOG.info('=== Testing reporter end')
