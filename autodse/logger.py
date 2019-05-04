"""
The format and config of logging.
"""
from copy import deepcopy
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


def get_default_logger(name: str, level: str = 'DEFAULT') -> logging.Logger:
    """Attach to the default logger"""

    logger = logging.getLogger(name)
    if level != 'DEFAULT':
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)6.0fs] %(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler)

    handler = logging.FileHandler('dse.log')
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)6.0fs][%(process)d][%(thread)d] '
                          '%(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler)

    return logger


def get_algo_logger(name: str, file_name: str, level: str = 'DEFAULT') -> logging.Logger:
    """Attach to the algorithm logger"""

    logger = logging.getLogger(name)
    if level != 'DEFAULT':
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(file_name)
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)6.0fs] %(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler)

    return logger


def get_eval_logger(name: str, level: str = 'DEFAULT') -> logging.Logger:
    """Attach to the evaluator logger"""

    logger = logging.getLogger(name)
    if level != 'DEFAULT':
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler('eval.log')
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)6.0fs] %(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler)

    return logger
