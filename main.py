import functools
import os
import typing as t
from pathlib import Path
from sys import stderr

import requests
from PIL import Image
from loguru import logger

LOG_FILE = Path('all.log')

sink_handler = {
    'sink': stderr,
    'level': 'INFO',
    'backtrace': False,
    'diagnose': False
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

HEADERS = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}
API_URL = 'https://pixels.pythondiscord.com/'


def request(func: t.Callable[..., requests.Response]
            ) -> t.Callable[[str], requests.Response]:
    """Handle logging, url completion and rate-limits."""
    @functools.wraps(func)
    def request(url: str) -> requests.Response:
        logger.debug('Sending {0} request to {1}', func.__name__.upper(), url)
        response = func(API_URL + url, headers=HEADERS)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.exception('Exception when sending request:')

        logger.trace('Recieved response headers={0} content={1}',
                     response.headers, response.content)
        return response
    return request


get = request(requests.get)
post = request(requests.post)


board = get('get_pixels')
size_json = get('get_size').json()
size = size_json['width'], size_json['height']

img = Image.frombytes(
    'RGB',
    size,
    board.content
)
img.show()
