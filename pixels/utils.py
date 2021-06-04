import itertools
import time
import typing as t
from dataclasses import dataclass

import requests
from PIL import Image

from pixels.session import head


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

    The images must be in the RGB mode. Although the right image can be
    in the RGBA mode in which case fully transparent pixels are
    ignored.

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
        left_coord = offset_x + x, offset_y + y
        left_pixel = list(left.getpixel(left_coord))

        right_pixel = right.getpixel((x, y))
        if len(right_pixel) == 4:
            *right_pixel, opaque = right_pixel
            if not opaque:
                # Doesn't get counted as a difference
                right_pixel = left_pixel

        if left_pixel != right_pixel:
            differences.append(Pixel(*left_coord, to_hex(right_pixel)))

    return differences


@dataclass
class RatelimitInfo:
    """Easy access to ratelimits and cooldowns."""

    response: requests.Response

    def _header_getter(self, key: str) -> t.Optional[float]:
        """Fetch the value of a key from the headers of the response.

        If the value is found, it's converted to a float first.
        If the value isn't found, None is returned.
        """
        try:
            return float(self.response.headers[key])
        except KeyError:
            return None

    @property
    def remaining(self) -> t.Optional[float]:
        """Return the value of the Requests-Remaining header."""
        return self._header_getter('Requests-Remaining')

    @property
    def reset(self) -> t.Optional[float]:
        """Return the value of the Requests-Reset header."""
        return self._header_getter('Requests-Reset')

    @property
    def period(self) -> t.Optional[float]:
        """Return the value of the Requests-Period header."""
        return self._header_getter('Requests-Period')

    @property
    def limit(self) -> t.Optional[float]:
        """Return the value of the Requests-Limit header."""
        return self._header_getter('Requests-Limit')

    @property
    def cooldown_reset(self) -> t.Optional[float]:
        """Return the value of the Cooldown-Reset header."""
        return self._header_getter('Cooldown-Reset')


def ratelimit_duration_left(responses: t.Iterable[requests.Response]) -> float:
    """Return the time needed before the requests can be made again.

    This gives back the minimum time needed; If the requests can be
    made again immediately, 0 is returned.
    """
    duration_needed = 0

    for resp in responses:
        resp = RatelimitInfo(resp)

        if resp.remaining == 0 or resp.cooldown_reset:
            current_duration_needed = resp.cooldown_reset or resp.reset
        else:
            current_duration_needed = 0

        duration_needed = max(duration_needed, current_duration_needed)

    return duration_needed


def all_endpoints_wait(endpoints: t.Iterable[str]) -> None:
    """Wait till Requests-Remaining for these endpoints is maxed out."""
    endpoints = set(endpoints)

    while True:
        if not endpoints:
            break

        for endpoint in endpoints.copy():
            resp = RatelimitInfo(head(endpoint))
            if resp.remaining != resp.limit:
                time.sleep(resp.reset)
            else:
                # The endpoint either wasn't ratelimited or is maxed
                # out.
                endpoints.remove(endpoint)


def even_ratelimit_duration_left(responses: t.Iterable[requests.Response]
                                 ) -> float:
    """Return the time needed before the requests can be made again.

    The time returned will be enough to not waste requests but
    optimally enough to make requests in even intervals.
    """
    duration_needed = 0

    for resp in responses:
        resp = RatelimitInfo(resp)

        if resp.cooldown_reset is not None:
            current_duration_needed = resp.cooldown_reset
        elif resp.remaining is not None:
            # This request is rate-limited.
            optimal_time = resp.period / resp.limit

            if resp.remaining >= resp.limit - 1:
                # We're at the limit or about to hit the limit.
                # Take the faster route.
                current_duration_needed = min(resp.reset, optimal_time)
            elif resp.remaining == 0:
                # We have some leniency to try and stabilise this
                # duration and avoid a chain of hitting resets.
                current_duration_needed = max(resp.reset, optimal_time)
            else:
                current_duration_needed = optimal_time
        else:
            current_duration_needed = 0

        duration_needed = max(duration_needed, current_duration_needed)

    return duration_needed


def ratelimit_wait(responses: t.Iterable[requests.Response]) -> float:
    """Sleep to not exceed ratelimits for the given API responses.

    Return the duration slept for. This gives back the minimum time
    needed; If the requests can be made again immediately, 0 is
    returned.
    """
    to_wait = ratelimit_duration_left(responses)
    time.sleep(to_wait)
    return to_wait


def even_ratelimit_wait(responses: t.Iterable[requests.Response]) -> float:
    """Sleep to not exceed ratelimits for the given API responses.

    Return the duration slept for. The time slept for will be enough to
    not waste requests and to make requests in even intervals.
    """
    to_wait = even_ratelimit_duration_left(responses)
    time.sleep(to_wait)
    return to_wait
