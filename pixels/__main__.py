import random
import reprlib
from pathlib import Path
from sys import stderr

from PIL import Image
from fire import Fire
from loguru import logger
from pixels.session import get, post
from pixels.utils import image_differences, ratelimit_wait

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


def main(xy: tuple[int, int], path: str, linear: bool = True) -> None:
    """Draw a specified image on the Pixels canvas.

    xy: The top-left corner of the image goes here.
    path: The path to the image.
    linear: Whether pixels should be filled linearly or randomly.
    """
    drawing = Image.open(path).convert('RGBA')
    while True:
        board_response = get('get_pixels')
        size_json = get('get_size').json()
        size = size_json['width'], size_json['height']
        board = Image.frombytes(
            'RGB',
            size,
            board_response.content
        )

        responses = [board_response]
        differences = image_differences(board, drawing, offset=xy)

        if differences:
            logger.opt(lazy=True).debug(
                'Remaining changes: {0}', lambda: reprlib.repr(differences)
            )
            logger.info('{0} changes remaining.', len(differences))

            if linear:
                to_change = differences[0]
            else:
                to_change = random.choice(differences)

            logger.debug('Attempting to change {0}', to_change)

            data = {'x': to_change.x, 'y': to_change.y, 'rgb': to_change.rgb}
            post_response = post('set_pixel', json=data)
            logger.info(post_response.json()['message'])
            responses.append(post_response)
        else:
            logger.debug('Doing nothing as no changes can be made.')

        ratelimit_wait(responses)


Fire(main)
