"""
The unit test module for gradient-based serach algorithm.
"""

from autodse import logger
from autodse.database import RedisDatabase
from autodse.dsproc.dsproc import compile_design_space
from autodse.parameter import gen_key_from_design_point
from autodse.explorer.gradient import GradientAlgorithm

LOG = logger.get_default_logger('UNIT-TEST', 'DEBUG')


def test_gradient(test_dir):
    #pylint:disable=missing-docstring

    LOG.debug('=== Testing gradient search algorithm start ===')

    config = {
        'search': {
            'algorithm': {
                'name': 'gradient',
                'gradient': {
                    'batch-size': 8
                }
            }
        },
        'design-space': {
            'max-part-num': 4,
            'definition': {
                'B': {
                    'options': '[8,512]',
                    'ds_type': 'INTERFACE',
                    'default': 8
                },
                'CGPAR1': {
                    'options': '[1,2,4,8,16]',
                    'ds_type': 'PARALLEL',
                    'default': 1
                },
                'CGPIP1': {
                    'options': "['off', '']",
                    'order': "0 if v == 'off' else 1",
                    'ds_type': 'PIPELINE',
                    'default': 'off'
                },
                'CGPAR2': {
                    'options': '[1,2,3,4,5,6,7,8,16]',
                    'order': '0 if v&(v-1)==0 else 1',
                    'ds_type': 'PARALLEL',
                    'default': 1
                },
                'CGPIP2': {
                    'options': "['off', '', 'flatten']",
                    'order': "0 if v=='flatten' else 1",
                    'ds_type': 'PIPELINE',
                    'default': 'off'
                }
            }
        }
    }

    db = RedisDatabase('test', 3, '{0}/temp_fixture/db/1.db'.format(test_dir))
    db.load()
    ds = compile_design_space(config['design-space']['definition'])
    algo = GradientAlgorithm(ds)
    gen = algo.gen()
    results = None

    while True:
        try:
            points = gen.send(results)
            keys = [gen_key_from_design_point(p) for p in points]
        except StopIteration:
            break

        results = {k: r for k, r in zip(keys, db.batch_query(keys))}

    LOG.debug('=== Testing gradient search algorithm end ===')
