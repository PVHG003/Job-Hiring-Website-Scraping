import logging
import random
import time
from typing import Tuple, Optional, Any

import requests
from cloudscraper.exceptions import CloudflareException

# Configuration constants - can be overridden when importing
MIN_DELAY_BETWEEN_REQUESTS = 2
MAX_DELAY_BETWEEN_REQUESTS = 5
CLOUDFLARE_TIMEOUT = 10
TOO_MANY_REQUESTS_TIMEOUT = 30
REQUEST_TIMEOUT = 30

# Retry configuration
MAX_RETRIES = 5
BACKOFF_FACTOR = 2
INITIAL_BACKOFF_DELAY = 5

USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",

    # Chrome (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",

    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",

    # Firefox (Mac)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.3; rv:115.0) Gecko/20100101 Firefox/115.0",

    # Chrome (Android)
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",

    # Safari (iPhone)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
]


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Custom exception for scraping-related errors"""
    pass


class RetryConfig:
    """Configuration class for retry settings"""

    def __init__(self, max_retries=MAX_RETRIES, backoff_factor=BACKOFF_FACTOR,
                 initial_delay=INITIAL_BACKOFF_DELAY):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay


def calculate_backoff_delay(retry_count: int, base_delay: int = INITIAL_BACKOFF_DELAY,
                            backoff_factor: int = BACKOFF_FACTOR) -> int:
    """
    Calculate exponential backoff delay

    Args:
        retry_count: Current retry attempt (0-based)
        base_delay: Base delay in seconds
        backoff_factor: Multiplier for exponential backoff

    Returns:
        Calculated delay in seconds
    """
    return base_delay * (backoff_factor ** retry_count)


def handle_request_error(error: requests.RequestException, retry_count: int = 0) -> Tuple[str, bool]:
    """
    Handle request errors and return appropriate action.

    Args:
        error: The request exception that occurred
        retry_count: Current retry attempt (0-based)

    Returns:
        tuple: (action, should_retry)
        action: 'continue', 'break', 'wait'
        should_retry: bool indicating if retry is recommended
    """
    logger.error(f"Request error (attempt {retry_count + 1}): {error}")

    if hasattr(error, 'response') and error.response:
        status_code = error.response.status_code

        if status_code == 429:
            logger.warning("Rate limited, waiting...")
            backoff_delay = calculate_backoff_delay(retry_count, TOO_MANY_REQUESTS_TIMEOUT)
            logger.info(f"Backing off for {backoff_delay} seconds...")
            time.sleep(backoff_delay)
            return 'wait', True
        elif status_code == 404:
            logger.info("Page not found, likely reached the end.")
            return 'break', False
        elif status_code >= 401:
            logger.warning("Unauthorized")
            return 'break', False
        elif status_code in [500, 502, 503, 504]:  # Server errors - worth retrying
            backoff_delay = calculate_backoff_delay(retry_count)
            logger.warning(f"Server error {status_code}, backing off for {backoff_delay} seconds...")
            time.sleep(backoff_delay)
            return 'wait', True
        else:
            logger.error(f"HTTP error {status_code}")
            return 'break', False
    else:
        # Network errors - might be temporary
        logger.warning("Network error (no response)")
        backoff_delay = calculate_backoff_delay(retry_count)
        logger.info(f"Network error, backing off for {backoff_delay} seconds...")
        time.sleep(backoff_delay)
        return 'wait', True


def scrape_page_with_retry(scraper: Any, url: str, page: int,
                           retry_config: Optional[RetryConfig] = None) -> requests.Response:
    """
    Scrape a single page with retry logic

    Args:
        scraper: Cloudscraper instance
        url: URL template with {page} placeholder
        page: Page number to scrape
        retry_config: Optional retry configuration

    Returns:
        Response object on success

    Raises:
        ScrapingError: When all retries are exhausted
    """
    if retry_config is None:
        retry_config = RetryConfig()

    for retry_count in range(retry_config.max_retries):
        try:
            logger.info(f"Scraping page {page} (attempt {retry_count + 1}/{retry_config.max_retries})...")

            response = scraper.get(url.format(page=page), timeout=REQUEST_TIMEOUT, headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": url.split("/")[0],
            })
            response.raise_for_status()

            logger.info(f"Successfully scraped page {page}")
            logger.debug(f"{response.status_code} - {url.format(page=page)}")

            return response

        except CloudflareException as error:
            logger.error(f"Cloudflare error (attempt {retry_count + 1}): {error}")
            if retry_count < retry_config.max_retries - 1:
                backoff_delay = calculate_backoff_delay(retry_count, CLOUDFLARE_TIMEOUT)
                logger.info(f"Retrying in {backoff_delay} seconds...")
                time.sleep(backoff_delay)
            else:
                logger.error("Max retries reached for Cloudflare error")
                raise ScrapingError(f"Cloudflare error after {retry_config.max_retries} attempts: {error}")

        except requests.RequestException as error:
            action, should_retry = handle_request_error(error, retry_count)

            if action == 'break':
                raise ScrapingError(f"Non-retryable request error: {error}")

            if not should_retry or retry_count >= retry_config.max_retries - 1:
                if retry_count >= retry_config.max_retries - 1:
                    logger.error("Max retries reached for request error")
                raise ScrapingError(f"Request error after {retry_config.max_retries} attempts: {error}")

        except Exception as error:
            logger.error(f"Unexpected error (attempt {retry_count + 1}): {error}")
            if retry_count < retry_config.max_retries - 1:
                backoff_delay = calculate_backoff_delay(retry_count)
                logger.info(f"Retrying in {backoff_delay} seconds...")
                time.sleep(backoff_delay)
            else:
                logger.error("Max retries reached for unexpected error")
                raise ScrapingError(f"Unexpected error after {retry_config.max_retries} attempts: {error}")

    raise ScrapingError("Unexpected end of retry loop")