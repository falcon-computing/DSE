"""
DSE config settings
"""
from typing import Any, Dict, Optional

from autodse.logger import get_logger

LOG = get_logger('Config')

# All configurable attributes. Please follow the following rules if you want to add new config.
# 1) Follow the naming: <main-category>.<attribute>.<sub-attribute>
# 2) 'require' is necessary for every config.
# 3) If the config is optional ('require' is False), then 'default' is necessary.
# 4) If the config is limited to certain options, add 'options' to the config attribute.
CONFIG_SETTING: Dict[str, Dict[str, Any]] = {
    'project.name': {
        'require': False,
        'default': 'project'
    },
    'project.backup': {
        'require': False,
        'default': 'NO_BACKUP',
        'options': ['NO_BACKUP', 'BACKUP_ERROR', 'BACKUP_ALL']
    },
    'design-space.definition': {
        'require': True
    },
    'design-space.max-part-num': {
        'require': False,
        'default': 4
    },
    'evaluate.worker-per-part': {
        'require': False,
        'default': 2
    },
    'evaluate.estimate-mode': {
        'require': True,
        'options': ['FAST', 'ACCURATE']
    },
    'evaluate.command.transform': {
        'require': True,
    },
    'evaluate.command.hls': {
        'require': True,
    },
    'evaluate.command.bitgen': {
        'require': True,
    },
    'search.algorithm.name': {
        'require': False,
        'default': 'exhaustive',
        'options': ['exhaustive']
    },
    'search.algorithm.exhaustive.batch-size': {
        'require': False,
        'default': 8
    },
    'timeout.exploration': {
        'require': True,
    },
    'timeout.transform': {
        'require': True,
    },
    'timeout.hls': {
        'require': True,
    },
    'timeout.bitgen': {
        'require': True,
    }
}


def build_config(user_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check user config and apply default value to optional configs

    Parameters
    ----------
    user_config:
        The user config to be referred.

    Returns
    -------
    Dict[str, Any]:
        A nested dict of configs, or None if there has any errors
    """

    # Check user config and make up optional values
    error = 0
    for key, attr in CONFIG_SETTING.items():
        if key in user_config:
            if 'options' in attr:
                # Specified config, check if it is legal
                if user_config[key] not in attr['options']:
                    LOG.error('"%s" is not a valid option for %s', user_config[key], key)
                    error += 1
        else:
            # Missing config, check if it is optional (set to default if so)
            if attr['require']:
                LOG.error('Missing "%s" in the config which is required', key)
                error += 1
            else:
                LOG.debug('Use default value for %s: %s', key, str(attr['default']))
                user_config[key] = attr['default']

    if error > 0:
        return None

    # Build config
    config: Dict[str, Any] = {}
    for key, attr in user_config.items():
        curr = config
        levels = key.split('.')
        for level in levels[:-1]:
            if level not in curr:
                curr[level] = {}
            curr = curr[level]
        curr[levels[-1]] = attr

    return config
