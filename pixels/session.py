import functools
import os
import reprlib
import typing as t

import requests
from loguru import logger

HEADERS = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}
API_URL = 'https://pixels.pythondiscord.com/'


session = requests.Session()
session.headers.update(HEADERS)


def request(func: t.Callable[..., requests.Response],
            prefix_url: str = ''
            ) -> t.Callable[[str], requests.Response]:
    """Handle logging and append the prefix url before each request."""
    @functools.wraps(func)
    def wrapper(url: str, **kwargs: t.Any) -> requests.Response:
        logger.debug('Sending {0} request to {1}', func.__name__.upper(), url)
        response = func(prefix_url + url, **kwargs)

        logger.opt(lazy=True).trace(
            'Recieved response headers={0} content={1}',
            lambda: response.headers, lambda: reprlib.repr(response.content)
        )

        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.exception('Exception when sending request:')
            raise

        return response
    return wrapper


get = request(session.get, API_URL)
post = request(session.post, API_URL)
