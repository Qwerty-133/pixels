import logging
from pathlib import Path
from sys import stdout

from loguru import logger

LOG_FILE = Path('all.log')
MINIMAL_LOG_FORMAT = (
    '<green>{time:HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    '<level>{message}</level>'
)

sink_handler = {
    'sink': stdout,
    'level': 'INFO',
    'backtrace': False,
    'diagnose': False,
    'format': MINIMAL_LOG_FORMAT
}
base_log_file_handler = {
    'sink': LOG_FILE,
    'level': 'TRACE',
    'rotation': '20 MB',
    'retention': 0
}
colorised_log_file_handler = base_log_file_handler | {
    'sink': LOG_FILE.with_stem(f'colorised-{LOG_FILE.stem}'),
    'colorize': True
}

handlers = [sink_handler, base_log_file_handler, colorised_log_file_handler]
logger.configure(handlers=handlers)


class InterceptHandler(logging.Handler):
    """Intercept logs from `logging` into `loguru`."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the actual logrecords into `logger`."""
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage())


root_logger = logging.getLogger('')
root_logger.setLevel(logging.WARNING)
root_logger.addHandler(InterceptHandler())
