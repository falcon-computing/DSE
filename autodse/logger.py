"""
The format and config of logging.
"""
import logging
import threading


class LogFormatter(logging.Formatter):
    """Customized log formatter."""

    def format(self, record: logging.LogRecord) -> str:
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
        # Display the elapsed time in minutes
        record.relativeCreated = int(record.relativeCreated / 1000.0 / 60.0)
        return super(LogFormatter, self).format(record)


logging.Formatter = LogFormatter  # type: ignore


def get_default_logger(name: str, level: str = 'DEFAULT') -> logging.Logger:
    """Attach to the default logger"""

    logger = logging.getLogger(name)
    if level != 'DEFAULT':
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG)

    handler1 = logging.StreamHandler()
    handler1.setFormatter(
        logging.Formatter('[%(relativeCreated)4.0fm] %(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler1)

    handler2 = logging.FileHandler('dse.log')
    handler2.setFormatter(
        logging.Formatter('[%(relativeCreated)4.0fm] %(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler2)

    return logger


def get_algo_logger(name: str, file_name: str, level: str = 'DEFAULT') -> logging.Logger:
    """Attach to the algorithm logger"""

    class ThreadFilter():
        """TBA"""

        def __init__(self, tid):
            self.tid = tid

        def filter(self, record):
            return record.thread == self.tid

    logger = logging.getLogger(name)
    if level != 'DEFAULT':
        logger.setLevel(level)
    else:
        logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(file_name)
    handler.setFormatter(
        logging.Formatter('[%(relativeCreated)4.0fm] %(levelname)7s %(name)s: %(message)s'))
    handler.addFilter(ThreadFilter(threading.get_ident()))  # type: ignore
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
        logging.Formatter('[%(relativeCreated)4.0fm][%(thread)d] '
                          '%(levelname)7s %(name)s: %(message)s'))
    logger.addHandler(handler)

    return logger
