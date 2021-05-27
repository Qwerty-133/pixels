import functools
import os
import typing as t

import requests
from PIL import Image
from loguru import logger

HEADERS = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}

URL = t.TypeVar('URL', str, bytes)

logger.add('all.log', level='TRACE')


def request(func: t.Callable[..., requests.Response]
            ) -> t.Callable[[URL], requests.Response]:
    """Log requests and responses and handle rate-limits."""
    @functools.wraps(func)
    def request(url: URL) -> requests.Response:
        logger.debug('Sending {0} request to {1}', func.__name__.upper(), url)
        response = func(url, headers=HEADERS)

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

board = get("https://pixels.pythondiscord.com/get_pixels")
size_json = get("https://pixels.pythondiscord.com/get_size").json()
size = size_json['width'], size_json['height']

img = Image.frombytes(
    'RGB',
    size,
    board.content
)
img.show()
