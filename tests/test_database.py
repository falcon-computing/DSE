"""
The unit test module for database.
"""
import os

from autodse import logger
from autodse.database import PickleDatabase, RedisDatabase
from autodse.result import HLSResult, Result

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def database_tester(db_cls):
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing %s database start', db_cls.__name__)

    # Clean up to avoid re-run errors
    if os.path.exists('./DB_test.db'):
        os.remove('./DB_test.db')

    # A new database
    try:
        db = db_cls('DB_test', 2)
    except RuntimeError:
        LOG.warning('The unit test of this database is skipped due to not installed.')
        return

    # Commit a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 5
    db.commit('point0', point)
    assert db.count() == 1

    # Query the point
    point = db.query('point0')
    assert point and point.key == 'point0'

    # Override a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 10
    point.ret_code = Result.RetCode.PASS
    point.perf = 1024.0
    point.res_util = {'BRAM': 47.5, 'FF': 1, 'LUT': 50.4, 'DSP': 78.2}
    db.commit('point0', point)
    assert db.count() == 1

    # Commit one more point
    point = HLSResult()
    point.key = 'point1'
    point.valid = True
    point.quality = 20
    point.ret_code = Result.RetCode.PASS
    point.perf = 512.0
    point.res_util = {'BRAM': 74.4, 'FF': 4, 'LUT': 75.4, 'DSP': 78.2}
    db.commit('point1', point)

    # Commit another point with the same quality
    point = HLSResult()
    point.key = 'point2'
    point.valid = True
    point.quality = 20
    point.ret_code = Result.RetCode.PASS
    point.perf = 2048.0
    point.res_util = {'BRAM': 5.4, 'FF': 1, 'LUT': 4, 'DSP': 8}
    db.commit('point2', point)
    assert db.count() == 3

    # Commit an invalid point
    point = HLSResult()
    point.key = 'point3'
    point.valid = False
    point.quality = 20
    point.ret_code = Result.RetCode.TIMEOUT
    point.perf = 2046.0
    point.res_util = {'BRAM': 5.4, 'FF': 1, 'LUT': 4, 'DSP': 8}
    db.commit('point3', point)
    assert db.count() == 4

    # Query count
    assert db.count_ret_code(Result.RetCode.TIMEOUT) == 1

    # Query all data
    data = db.query_all()
    assert len(data) == 4

    # Commit best cache
    db.commit_best()
    assert db.count() == 5

    # Persist
    db.persist()
    del db

    # Load the database with data
    # Note that the cache size has no affect when loading and it should be maintained
    # elsewhere.
    db2 = db_cls('DB_test', 1, './DB_test.db')
    db2.load()
    assert db2.count() == 5
    assert db2.best_cache.qsize() == 4
    assert db2.best_cache.queue[0][0] == 5
    del db2

    # Clean up
    os.remove('./DB_test.db')

    LOG.debug('=== Testing %s database end', db_cls.__name__)


def test_redis_database():
    #pylint:disable=missing-docstring

    database_tester(RedisDatabase)


def test_pickle_database():
    #pylint:disable=missing-docstring

    database_tester(PickleDatabase)
