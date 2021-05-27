import functools
import itertools
import os
import random
import reprlib
import time
import typing as t
from pathlib import Path
from sys import stderr

import requests
from PIL import Image
from loguru import logger

LOG_FILE = Path('all.log')

log_format = (
    '<green>{HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    '<level>{message}</level>'
)

sink_handler = {
    'sink': stderr,
    'level': 'INFO',
    'backtrace': False,
    'diagnose': False,
    'format': log_format
}
base_log_file_handler = {
    'sink': LOG_FILE,
    'level': 'TRACE',
    'rotation': '1 day',
    'retention': 0,
    'format': log_format
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
    def request(url: str, **kwargs: t.Any) -> requests.Response:
        logger.debug('Sending {0} request to {1}', func.__name__.upper(), url)
        response = func(API_URL + url, headers=HEADERS, **kwargs)

        logger.trace('Recieved response headers={0} content={1}',
                     response.headers, reprlib.repr(response.content))

        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.exception('Exception when sending request:')
            raise

        return response
    return request


get = request(requests.get)
post = request(requests.post)


def to_hex(rgb: tuple[str, str, str]) -> str:
    """Return the hex representation of an rgb tuple."""
    return ''.join(format(colour, '02x') for colour in rgb)


class Pixel(t.NamedTuple):
    """Represents a pixel to be changed."""

    x: int
    y: int
    rgb: str


drawing = Image.open('draw.png').convert('RGB')

while True:
    board_response = get('get_pixels')
    size_json = get('get_size').json()
    size = size_json['width'], size_json['height']
    board = Image.frombytes(
        'RGB',
        size,
        board_response.content
    )
    drawing_width, drawing_height = drawing.size
    start_x, start_y = (int(os.environ[key]) for key in ('X', 'Y'))

    differences = []
    for x, y in itertools.product(range(drawing_width), range(drawing_height)):
        drawing_pixel = drawing.getpixel((x, y))
        corresponding_board_coord = start_x + x, start_y + y
        img_pixel = board.getpixel(corresponding_board_coord)
        if img_pixel != drawing_pixel:
            change_pixel = Pixel(*corresponding_board_coord,
                                 to_hex(drawing_pixel))
            differences.append(change_pixel)

    logger.debug('Remaining changes: {0}', reprlib.repr(differences))
    logger.info('{0} changes remaining.', len(differences))

    to_change = random.choice(differences)
    logger.debug('Attempting to change {0}', to_change)

    data = {'x': to_change.x, 'y': to_change.y, 'rgb': to_change.rgb}
    post_response = post('set_pixel', json=data)
    logger.info(post_response.json()['message'])

    responses = [board_response, post_response]
    remaining_reqs = [int(resp.headers['Requests-Remaining'])
                      for resp in responses]
    if not all(remaining_reqs):
        resets = [int(resp.headers['Requests-Reset'])
                  for resp in responses]
        time.sleep(max(resets))
