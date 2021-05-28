import itertools
import time
import typing as t

import requests
from PIL import Image


def to_hex(rgb: tuple[int, int, int]) -> str:
    """Return the hex representation of an rgb tuple."""
    return ''.join(format(colour, '02x') for colour in rgb)


class Pixel(t.NamedTuple):
    """Represents a pixel to be changed."""

    x: int
    y: int
    rgb: str


def image_differences(left: Image.Image,
                      right: Image.Image,
                      /,
                      offset: tuple[int, int] = (0, 0)
                      ) -> list[Pixel]:
    """Fetch pixels to change in the left image to obtain the right.

    The images must be in the RGB mode.

    The offset is used to determine the starting point of the area
    from the first provided image. The area must be enough to cover
    the second image.

    A list of Pixel's are returned. Each pixel has a coordinate
    in the left image and the colour (rgb) it should be changed to.
    """
    second_width, second_height = right.size
    offset_x, offset_y = offset

    differences: list[Pixel] = []
    for x, y in itertools.product(range(second_width), range(second_height)):
        right_pixel = right.getpixel((x, y))
        left_coord = offset_x + x, offset_y + y
        left_pixel = left.getpixel(left_coord)

        if left_pixel != right_pixel:
            differences.append(Pixel(*left_coord, to_hex(right_pixel)))

    return differences


def ratelimit_wait(responses: t.Iterable[requests.Response]) -> None:
    """Sleep to not exceed ratelimits for the given API responses."""
    remaining_reqs = [int(resp.headers['Requests-Remaining'])
                      for resp in responses]
    if not all(remaining_reqs):
        resets = [int(resp.headers['Requests-Reset'])
                  for resp in responses]
        time.sleep(max(resets))
