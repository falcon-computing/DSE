"""
The unit test module for database.
"""
import os
import pytest

from autodse import logger
from autodse.database import PickleDatabase, RedisDatabase
from autodse.result import HLSResult

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_redis_database():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing Redis database start')

    # Clean up to avoid re-run errors
    if os.path.exists('./redisDB_test.db'):
        os.remove('./redisDB_test.db')

    # A new database
    try:
        rdb = RedisDatabase('redisDB_test', 2)
    except RuntimeError:
        LOG.warning('The unit test of Redis database is skipped due to not installed.')
        return

    # Commit a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 5
    rdb.commit('point0', point)

    # Note that we will also commit meta-best-cache
    assert rdb.count() == 2

    # Query the point
    point = rdb.query('point0')
    assert point and point.key == 'point0'

    # Override a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 10
    point.ret_code = 0
    point.perf = 1024.0
    point.res_util = {'BRAM': 47.5, 'FF': 1, 'LUT': 50.4, 'DSP': 78.2}
    rdb.commit('point0', point)
    assert rdb.count() == 2

    # Commit two more points
    point = HLSResult()
    point.key = 'point1'
    point.valid = True
    point.quality = 20
    point.ret_code = 0
    point.perf = 512.0
    point.res_util = {'BRAM': 74.4, 'FF': 4, 'LUT': 75.4, 'DSP': 78.2}
    rdb.commit('point1', point)

    point = HLSResult()
    point.key = 'point2'
    point.valid = True
    point.quality = 5
    point.ret_code = 0
    point.perf = 2048.0
    point.res_util = {'BRAM': 5.4, 'FF': 1, 'LUT': 4, 'DSP': 8}
    rdb.commit('point2', point)
    assert rdb.count() == 4

    # Persist
    rdb.persist()
    del rdb

    # Load the database with data
    rdb2 = RedisDatabase('redisDB_test', 2, './redisDB_test.db')
    rdb2.load()
    assert rdb2.count() == 4
    assert len(rdb2.best_cache) == 2
    assert rdb2.best_cache[0][0] == 10
    del rdb2

    # Clean up
    os.remove('./redisDB_test.db')

    LOG.debug('=== Testing Redis database end')


def test_pickle_database():
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing PickleDB database start')

    # Clean up to avoid re-run errors
    if os.path.exists('./pickleDB_test.db'):
        os.remove('./pickleDB_test.db')

    # A new database
    pdb = PickleDatabase('pickleDB_test', 2)

    # Query a non-exist point
    ret = pdb.query('point0')
    assert ret is None

    # Commit a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 5
    pdb.commit('point0', point)

    # Note that we will also commit meta-best-cache
    assert pdb.count() == 2

    # Query the point
    point = pdb.query('point0')
    assert point and point.key == 'point0'

    # Override a point
    point = HLSResult()
    point.key = 'point0'
    point.valid = True
    point.quality = 10
    point.ret_code = 0
    point.perf = 1024.0
    point.res_util = {'BRAM': 47.5, 'FF': 1, 'LUT': 50.4, 'DSP': 78.2}
    pdb.commit('point0', point)
    assert pdb.count() == 2

    # Commit two more points
    point = HLSResult()
    point.key = 'point1'
    point.valid = True
    point.quality = 20
    point.ret_code = 0
    point.perf = 512.0
    point.res_util = {'BRAM': 74.4, 'FF': 4, 'LUT': 75.4, 'DSP': 78.2}
    pdb.commit('point1', point)

    point = HLSResult()
    point.key = 'point2'
    point.valid = True
    point.quality = 5
    point.ret_code = 0
    point.perf = 2048.0
    point.res_util = {'BRAM': 5.4, 'FF': 1, 'LUT': 4, 'DSP': 8}
    pdb.commit('point2', point)
    assert pdb.count() == 4

    # Persist
    pdb.persist()
    del pdb

    # Load the database with data
    pdb2 = PickleDatabase('pickleDB_test', 2, './pickleDB_test.db')
    pdb2.load()
    assert pdb2.count() == 4
    assert len(pdb2.best_cache) == 2
    assert pdb2.best_cache[0][0] == 10
    del pdb2

    # Instrument errors to the persist database
    with open('./pickleDB_test.db', 'r') as filep:
        text_db = filep.read().replace('"', '')
    with open('./pickleDB_test.db', 'w') as filep:
        filep.write(text_db)

    # Load the database with error
    with pytest.raises(RuntimeError):
        PickleDatabase('pickleDB_test', 2, './pickleDB_test.db')

    # Clean up
    os.remove('./pickleDB_test.db')

    LOG.debug('=== Testing PickleDB database end')
