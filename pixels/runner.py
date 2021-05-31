import random
import reprlib
import time

from PIL import Image
from loguru import logger
from pixels.session import get, head, post
from pixels.utils import (even_ratelimit_duration_left, even_ratelimit_wait,
                          image_differences)


def main(xy: tuple[int, int], path: str, linear: bool = True) -> None:
    """Draw a specified image on the Pixels canvas.

    xy: The top-left corner of the image goes here.
    path: The path to the image.
    linear: Whether pixels should be filled linearly or randomly.
    """
    drawing = Image.open(path).convert('RGBA')

    current_ratelimits = [head('get_pixels'), head('set_pixel')]
    to_wait = even_ratelimit_duration_left(current_ratelimits)
    if to_wait:
        logger.info('Waiting for {0} seconds.', to_wait)
        time.sleep(to_wait)

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
            logger.info('Doing nothing as no changes can be made.')

        even_ratelimit_wait(responses)
