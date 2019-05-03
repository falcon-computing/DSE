"""
DSE config settings
"""
from typing import Any, Dict

from autodse.logger import get_logger

LOG = get_logger('Config')

# All configurable attributes. Please follow the following rules if you want to add new config.
# 1) Follow the naming: <main-category>.<attribute>.<sub-attribute>
# 2) 'require' is necessary for every config.
# 3) If the config is optional ('require' is False), then 'default' is necessary.
# 4) If the config is limited to certain options, add 'options' to the config attribute.
CONFIG_SETTING: Dict[str, Dict[str, Any]] = {
    'main.project-name': {
        'require': False,
        'default': 'project'
    },
    'design-space.definition': {
        'require': True
    },
    'design-space.max-partition': {
        'require': False,
        'default': 4
    },
    'evaluator.backup': {
        'require': False,
        'default': 'NO_BACKUP',
        'options': ['NO_BACKUP', 'BACKUP_ERROR', 'BACKUP_ALL']
    },
    'evaluator.max-worker-per-part': {
        'require': False,
        'default': 2
    },
    'evaluator.estimation': {
        'require': True,
        'options': ['FAST', 'ACCURATE']
    },
    'evaluator.command.transform': {
        'require': True,
    },
    'evaluator.command.hls': {
        'require': True,
    },
    'evaluator.command.bitgen': {
        'require': True,
    }
}


def check_config(config: Dict[str, Any]) -> bool:
    """Check user config and apply default value to optional configs

    Parameters
    ----------
    config:
        The config to be checked

    Returns
    -------
    bool:
        Indicate if all required configs are specified.
    """

    error = 0
    for key, attr in CONFIG_SETTING.items():
        if key in config and 'options' in attr:
            # Specified config, check if it is legal
            if config[key] not in attr['options']:
                LOG.error('"%s" is not a valid option for %s', config[key], key)
                error += 1
        else:
            # Missing config, check if it is optional (set to default if so)
            if CONFIG_SETTING[key]['require']:
                LOG.error('Missing "%s" in the config which is required', key)
                error += 1
            else:
                LOG.debug('Use default value for %s: %s', key, str(attr['default']))
                config[key] = attr['default']
    return error == 0
