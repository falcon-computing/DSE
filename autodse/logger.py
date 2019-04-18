"""
The format and config of logging.
"""
import logging
from logging import LogRecord
from logging.config import dictConfig


class LogFormatter(logging.Formatter):
    """Customized log formatter."""

    def format(self, record: LogRecord) -> str:
        """The customized formatter function

        Parameters
        ----------
        record:
            The original formatted log data

        Returns
        -------
        format:
            The customized formatted log data
        """
        # Display the elapsed time in seconds
        record.relativeCreated = int(record.relativeCreated / 1000.0)
        return super(LogFormatter, self).format(record)


logging.Formatter = LogFormatter  # type: ignore

LOGGING_CONFIG_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '[%(relativeCreated)6.0fs] %(levelname)7s %(name)s: %(message)s'
        },
        'file': {
            'format':
            '[%(relativeCreated)6.0fs] %(levelname)7s %(name)s: %(message)s '
            '@%(filename)s:%(lineno)d'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'autodse.log',
            'formatter': 'file',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True
        }
    }
}
dictConfig(LOGGING_CONFIG_DICT)
