import logging
import random
import time

import cloudscraper
import requests
from bs4 import BeautifulSoup

from common.common import MAX_RETRIES, scrape_page_with_retry, MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS

scraper = cloudscraper.create_scraper({
    'browser': 'chrome',
    'platform': 'windows',
})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_job_url(soup):
    job_urls = []

    jobs = soup.find_all("h2", {"class": "job__list-item-title"})
    print(len(jobs))
    for job in jobs:
        url = job.find("a").get("href")
        cleaned_url = url.split('?')[0] if url else None
        if cleaned_url:
            job_urls.append(cleaned_url)

    return job_urls


def main():
    page = 1
    url = "https://123job.vn/tuyen-dung?sort=new&page={page}"
    consecutive_failures = 0
    max_consecutive_failures = 5

    while True:
        try:
            response = scrape_page_with_retry(scraper, url, page)
            consecutive_failures = 0  # Reset on success

            soup = BeautifulSoup(response.text, "html.parser")
            job_urls = extract_job_url(soup)

            with open('job_urls.txt', 'a', encoding='utf-8') as file:
                for job_url in job_urls:
                    file.write(job_url + '\n')

            page += 1
            # break

            delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
            logger.info(f"Waiting {delay:.2f} seconds...")
            time.sleep(delay)

        except requests.RequestException as error:
            consecutive_failures += 1
            logger.warning(f"Failed to scrape page {page} after {MAX_RETRIES} attempts")

            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping.")
                break

            # Skip this page and try the next one
            if hasattr(error, 'response') and error.response and error.response.status_code == 404:
                logger.info("404 error - likely reached the end of available pages.")
                break
            else:
                logger.error(f"Skipping page {page} and trying next page...")
                page += 1

        except Exception as error:
            logger.error(f"Unexpected error on page {page}: {error}")
            break

    logger.info(f"Scraping completed. Last attempted page: {page}")


if __name__ == '__main__':
    main()
