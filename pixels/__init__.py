from pathlib import Path
from sys import stderr

from loguru import logger

LOG_FILE = Path('all.log')
MINIMAL_LOG_FORMAT = (
    '<green>{time:HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    '<level>{message}</level>'
)

sink_handler = {
    'sink': stderr,
    'level': 'INFO',
    'backtrace': False,
    'diagnose': False,
    'format': MINIMAL_LOG_FORMAT
}
base_log_file_handler = {
    'sink': LOG_FILE,
    'level': 'TRACE',
    'rotation': '1 day',
    'retention': 0
}
colorised_log_file_handler = base_log_file_handler | {
    'sink': LOG_FILE.with_stem(f'colorised-{LOG_FILE.stem}'),
    'colorize': True
}

handlers = [sink_handler, base_log_file_handler, colorised_log_file_handler]
logger.configure(handlers=handlers)
