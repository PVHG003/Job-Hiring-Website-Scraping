import cloudscraper
from bs4 import BeautifulSoup
import time
import random

TOPCV_URL = 'https://www.topcv.vn'
PAGE_START = 1
PAGE_END = 200
OUTPUT_FILE = "topcv_job_urls.txt"
MAX_RETRIES = 5
SLEEP_MIN = 3
SLEEP_MAX = 5


def create_scraper():
    return cloudscraper.create_scraper(
        browser={'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )


def fetch_page(scraper, url, page_num, total_pages):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = scraper.get(url)
            status = response.status_code

            if status == 200:
                print(f"[{page_num}/{total_pages}] ✅ Fetched successfully on attempt {attempt}")
                return response.content

            elif status == 429:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(
                    f"[{page_num}/{total_pages}] ⚠️ 429 Too Many Requests on attempt {attempt}. Waiting {wait_time:.2f}s...")
                time.sleep(wait_time)

            else:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(
                    f"[{page_num}/{total_pages}] ⚠️ Unexpected status {status} on attempt {attempt}. Waiting {wait_time:.2f}s...")
                time.sleep(wait_time)

        except cloudscraper.exceptions.CloudflareChallengeError:
            wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
            print(
                f"[{page_num}/{total_pages}] ⛔ Cloudflare challenge on attempt {attempt}. Waiting {wait_time:.2f}s...")
            time.sleep(wait_time)

        except Exception as e:
            wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
            print(f"[{page_num}/{total_pages}] ❌ Error on attempt {attempt}: {e}. Waiting {wait_time:.2f}s...")
            time.sleep(wait_time)

    print(f"[{page_num}/{total_pages}] ❌ Failed to fetch page after {MAX_RETRIES} attempts. Skipping...")
    return None


def main():
    scraper = create_scraper()
    print("Cloudscraper session created successfully!")

    total_pages = PAGE_END - PAGE_START + 1
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for page in range(PAGE_START, PAGE_END + 1):
            url = f"{TOPCV_URL}/tim-viec-lam-moi-nhat?type_keyword=1&page={page}&sba=1"
            content = fetch_page(scraper, url, page, total_pages)
            if content is None:
                continue

            soup = BeautifulSoup(content, "html.parser")
            job_list = soup.find_all("div", class_="job-item-search-result")

            if not job_list:
                print(f"[{page}/{total_pages}] No jobs found. Stopping scraper.")
                break

            for job in job_list:
                link_element = job.find("a")
                if link_element and "href" in link_element.attrs:
                    job_url = link_element["href"]
                    if job_url.startswith("/"):
                        job_url = TOPCV_URL + job_url
                    f.write(f"{job_url}\n")

            print(f"[{page}/{total_pages}] Processed {len(job_list)} jobs.")

            sleep_time = random.uniform(SLEEP_MIN, SLEEP_MAX)
            print(f"[{page}/{total_pages}] Sleeping for {sleep_time:.2f}s before next page...\n")
            time.sleep(sleep_time)


if __name__ == '__main__':
    main()