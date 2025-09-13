import random
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.topcv.vn"
OUTPUT_FILE = "topcv_job_urls.txt"

TIMEOUT_MIN = 10
TIMEOUT_MAX = 30

DELAY_MIN = 1
DELAY_MAX = 3

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
}

with open(OUTPUT_FILE, "a", encoding="utf-8") as file:
    for page_num in range(1, 200):
        topcv_url = f"{BASE_URL}/tim-viec-lam-moi-nhat?type_keyword=1&page={page_num}&sba=1"

        while True:
            timeout_value = random.uniform(TIMEOUT_MIN, TIMEOUT_MAX)
            try:
                response = requests.get(topcv_url, headers=headers, timeout=timeout_value)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    break
                elif response.status_code == 429:
                    print(f"⚠️ Rate limited on page {page_num}, waiting {int(timeout_value)}s...")
                    time.sleep(timeout_value)
                else:
                    print(f"❌ Failed with status {response.status_code} on page {page_num}, skipping...")
                    soup = None
                    break

            except requests.exceptions.RequestException as e:
                print(f"⚠️ Request error: {e}, retrying after {int(timeout_value)}s...")
                time.sleep(timeout_value)

        if not soup:
            continue

        job_list = soup.find_all("div", class_="job-item-search-result")
        for job in job_list:
            job_link = job.find("a")["href"]
            if job_link.startswith("/"):
                job_link = BASE_URL + job_link
            file.write(f"{job_link}\n")

        print(f"✅ Finished page {page_num}")

        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"⏳ Sleeping {delay:.2f}s before next request...")
        time.sleep(delay)