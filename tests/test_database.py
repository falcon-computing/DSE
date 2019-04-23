"""
The unit test module for database.
"""
import os
import pytest

from autodse import logger
from autodse.database import PickleDatabase, RedisDatabase
from autodse.result import HLSResult

LOG = logger.get_logger('UNIT-TEST')


def test_redis_database():
    #pylint:disable=missing-docstring

    # Clean up to avoid re-run errors
    if os.path.exists('./redisDB_test.db'):
        os.remove('./redisDB_test.db')

    # A new database
    try:
        rdb = RedisDatabase('redisDB_test')
    except RuntimeError:
        LOG.warning('The unit test of Redis database is skipped due to not installed.')
        return

    # Query a non-exist point
    ret = rdb.query('point0')
    assert ret is None

    # Commit a point
    point = HLSResult()
    point.key = 'point0'
    assert rdb.commit('point0', point)

    # Query the point
    point = rdb.query('point0')

    # Override a point
    point = HLSResult()
    point.key = 'point0'
    point.ret_code = 0
    point.perf = 1024.0
    point.res_util = {'BRAM': 47.5, 'FF': 1, 'LUT': 50.4, 'DSP': 78.2}
    point.eval_time = 148.2
    point.report = {'F_0_0_1': {'latency': 10}, 'L_0_0_1': {'latency': 20}}
    point.ordered_hotspot = [('L_0_0_1', 'compute'), ('F_0_0_1', 'memory')]
    assert rdb.commit('point0', point)

    # Persist
    rdb.persist()
    del rdb

    # Load the database with data
    rdb2 = RedisDatabase('redisDB_test', './redisDB_test.db')
    assert rdb2.count() == 1
    del rdb2

    # Clean up
    os.remove('./redisDB_test.db')


def test_pickle_database():
    #pylint:disable=missing-docstring

    # Clean up to avoid re-run errors
    if os.path.exists('./pickleDB_test.db'):
        os.remove('./pickleDB_test.db')

    # A new database
    pdb = PickleDatabase('pickleDB_test')

    # Query a non-exist point
    ret = pdb.query('point0')
    assert ret is None

    # Commit a point
    point = HLSResult()
    point.key = 'point0'
    assert pdb.commit('point0', point)

    # Query the point
    point = pdb.query('point0')

    # Override a point
    point = HLSResult()
    point.key = 'point0'
    point.ret_code = 0
    point.perf = 1024.0
    point.res_util = {'BRAM': 47.5, 'FF': 1, 'LUT': 50.4, 'DSP': 78.2}
    point.eval_time = 148.2
    point.report = {'F_0_0_1': {'latency': 10}, 'L_0_0_1': {'latency': 20}}
    point.ordered_hotspot = [('L_0_0_1', 'compute'), ('F_0_0_1', 'memory')]
    assert pdb.commit('point0', point)

    # Persist
    pdb.persist()
    del pdb

    # Load the database with data
    pdb2 = PickleDatabase('pickleDB_test', './pickleDB_test.db')
    assert pdb2.count() == 1
    del pdb2

    # Instrument errors to the persist database
    with open('./pickleDB_test.db', 'r') as filep:
        text_db = filep.read().replace('"', '')
    with open('./pickleDB_test.db', 'w') as filep:
        filep.write(text_db)

    # Load the database with error
    with pytest.raises(RuntimeError):
        PickleDatabase('pickleDB_test', './pickleDB_test.db')

    # Clean up
    os.remove('./pickleDB_test.db')
