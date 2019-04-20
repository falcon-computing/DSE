"""
The unit test module for database.
"""
import os
import pytest

from autodse.database import HLSResult, PickleDatabase


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
