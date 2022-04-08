import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests
from lxml import html
from selenium.common.exceptions import TimeoutException
from selenium import webdriver

from framework import await_page_load

logger = logging.getLogger('url_checker')

ERROR_KEYWORDS = (
    '404 not found',
    'unauthorized',
    'bad gateway',
    'internal server error'
)


@dataclass(frozen=True)
class CheckUrlResponse:
    message: str
    is_valid: float
    status_code: int = None
    title: str = None


def get_title_from_response(response: requests.Response) -> Optional[str]:
    """Receive title from response body. Is title is empty returns None."""
    response.encoding = 'utf-8'
    parsed_body = html.fromstring(response.text)
    try:
        title = parsed_body.xpath('//title/text()')[0]
    except IndexError:
        title = None
    return title


def check_url(url: str) -> CheckUrlResponse:
    """
    Checks if the page is available for the given url.
    Returns tuple of (is_available, page_title if available)
    """
    logger.info('Checking %s', url)

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
    }

    try:
        requests_response = requests.get(url, headers=headers)
    except requests.exceptions.MissingSchema:
        return_message = f'Invalid URL \'{url}\': No schema supplied.'
        logger.warning(return_message)
        return CheckUrlResponse(message=return_message, is_valid=False)
    except requests.exceptions.ConnectionError:
        # If cannot connect - url is broken
        return_message = 'URL check failed: cannot connect'
        logger.warning(return_message)
        return CheckUrlResponse(message=return_message, is_valid=False)

    actual_url = requests_response.url
    if actual_url != url:
        logger.warning('Actual URL is %s', actual_url)

    response_status_code = requests_response.status_code

    if response_status_code > 400 and response_status_code != 401:
        # If cannot connect - url is broken
        return_message = f'URL check failed: HTTP code {response_status_code}'
        logger.warning(return_message)
        return CheckUrlResponse(message=return_message, is_valid=False)

    logger.info('Requests check successful, proceeding with selenium check')
    webdriver_instance = webdriver.Firefox()
    webdriver_instance.set_page_load_timeout(20)
    try:
        webdriver_instance.get(url)
    except TimeoutException:
        logger.warning('Get timed out, processing with partially loaded site')
    logger.info('Waiting for the page to load')
    await_page_load.wait_for_page_load(webdriver_instance)

    # The website is pretending that the request was correct
    # Let's check if it is an error page that returned 200 for some reason

    for keyword in ERROR_KEYWORDS:
        if re.search(keyword, webdriver_instance.title, re.IGNORECASE):
            return_message = f'URL check failed: error keyword \'{keyword}\' found'
            logger.warning(return_message)
            webdriver_instance.quit()
            return CheckUrlResponse(message=return_message, is_valid=False, status_code=response_status_code)

    webdriver_instance.quit()

    title = get_title_from_response(response=requests_response) or actual_url
    return_message = 'Success'

    return CheckUrlResponse(message=return_message, is_valid=True, status_code=response_status_code, title=title)
