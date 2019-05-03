"""
The unit test module of config.
"""

from autodse.config import build_config
from autodse.logger import get_logger

LOG = get_logger('UNIT-TEST', 'DEBUG', True)

def test_build_config():
    #pylint:disable=missing-docstring

    LOG.info('=== Testing build_config start')

    # The config with some required fields missing
    user_config = {
        'design-space.definition': {
            'A': {
                "options": "[x**2 for x in range(10) if x==0 or B!='flatten']",
                "order": "0 if x < 512 else 1",
                "ds_type": "parallel",
                "default": 1
            },
            'B': {
                "options": "['off', '', 'flatten']",
                "ds_type": "pipeline",
                "default": 'off'
            }
        },
        'evaluate.estimate-mode': 'FAST',
        'evaluate.command.transform': 'make mcc_acc',
        'evaluate.command.hls': 'make mcc_estimate',
        'evaluate.command.bitgen': 'make mcc_bitgen',
        'timeout.transform': '5',
        'timeout.hls': '30',
        'timeout.bitgen': '480'
    }

    config = build_config(user_config)
    assert config is None

    # The most concise valid config that contains only required fields
    user_config['timeout.exploration'] = '240'

    config = build_config(user_config)
    assert config is not None

    # Make up a default value to an unspecified optional field
    assert 'project' in config
    assert 'name' in config['project']
    assert config['project']['name'] == 'project'

    # User specified value
    assert 'evaluate' in config
    assert 'command' in config['evaluate']
    assert 'hls' in config['evaluate']['command']
    assert config['evaluate']['command']['hls'] == 'make mcc_estimate'

    # The most comprehensive config
    user_config['project.name'] = 'test_project'
    user_config['project.backup'] = 'BACKUP_ERROR'
    user_config['design-space.max-part-num'] = 8
    user_config['evaluate.worker-per-part'] = 4

    config = build_config(user_config)
    assert config is not None

    # Use user specified value to an optional field
    assert 'project' in config
    assert 'name' in config['project']
    assert config['project']['name'] == 'test_project'

    LOG.info('=== Testing build_config end')
