import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os

INPUT_FILE = "topcv_job_urls.txt"
OUTPUT_DIR = "batches"  # Folder to save batch files

# Timeout range for requests
TIMEOUT_MIN = 10
TIMEOUT_MAX = 30

# Delay range between requests
DELAY_MIN = 2
DELAY_MAX = 6

SAVE_BATCH = 10  # Save every 10 jobs

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
}

def extract_job_data(soup):
    job_data = {}

    # --- Basic Info ---
    title_tag = soup.find("h1", class_="job-detail__info--title")
    job_data["title"] = title_tag.get_text(strip=True) if title_tag else None

    salary_tag = soup.select_one(".job-detail__info--section-content-value")
    job_data["salary"] = salary_tag.get_text(strip=True) if salary_tag else None

    location_tag = soup.select_one("#header-job-info .job-detail__info--section:nth-of-type(2) .job-detail__info--section-content-value")
    job_data["location"] = location_tag.get_text(strip=True) if location_tag else None

    exp_tag = soup.select_one("#job-detail-info-experience .job-detail__info--section-content-value")
    job_data["experience"] = exp_tag.get_text(strip=True) if exp_tag else None

    deadline = soup.select_one(".job-detail__info--deadline")
    job_data["deadline"] = deadline.get_text(strip=True).replace("Hạn nộp hồ sơ:", "").strip() if deadline else None

    # --- Tags / Categories ---
    job_data["tags"] = [tag.get_text(strip=True) for tag in soup.select(".job-tags a")]

    # --- Job Description Sections ---
    job_data["description"] = {}
    for section in soup.select(".job-description__item"):
        title = section.find("h3")
        content = section.select_one(".job-description__item--content")
        if title and content:
            job_data["description"][title.get_text(strip=True)] = " ".join(content.stripped_strings)

    # --- Extra Info ---
    workplace = soup.find("h3", string="Địa điểm làm việc")
    if workplace:
        job_data["workplace"] = " ".join(workplace.find_next("div").stripped_strings)

    working_time = soup.find("h3", string="Thời gian làm việc")
    if working_time:
        job_data["working_time"] = " ".join(working_time.find_next("div").stripped_strings)

    apply_method = soup.find("h3", string="Cách thức ứng tuyển")
    if apply_method:
        job_data["apply_method"] = " ".join(apply_method.find_next("div").stripped_strings)

    return job_data


if __name__ == "__main__":
    batch_jobs = []
    batch_count = 1

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        job_urls = [url.strip() for url in file if url.strip()]

    for idx, job_url in enumerate(job_urls, start=1):
        try:
            print(f"[{idx}/{len(job_urls)}] Fetching: {job_url}")

            timeout_value = random.uniform(TIMEOUT_MIN, TIMEOUT_MAX)
            response = requests.get(job_url, headers=headers, timeout=timeout_value)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            job_data = extract_job_data(soup)
            job_data["url"] = job_url
            batch_jobs.append(job_data)

            # Save every N jobs into a new file
            if len(batch_jobs) >= SAVE_BATCH:
                batch_filename = os.path.join(OUTPUT_DIR, f"batch_{batch_count}.json")
                with open(batch_filename, "w", encoding="utf-8") as f:
                    json.dump(batch_jobs, f, ensure_ascii=False, indent=4)

                print(f"💾 Saved batch {batch_count} with {len(batch_jobs)} jobs")
                batch_jobs = []
                batch_count += 1

            # Random delay to avoid rate-limit
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"⏳ Sleeping {delay:.2f}s before next request...")
            time.sleep(delay)

        except Exception as e:
            print(f"⚠️ Failed to scrape {job_url}: {e}")

    # Save remaining jobs in last batch
    if batch_jobs:
        batch_filename = os.path.join(OUTPUT_DIR, f"batch_{batch_count}.json")
        with open(batch_filename, "w", encoding="utf-8") as f:
            json.dump(batch_jobs, f, ensure_ascii=False, indent=4)

        print(f"💾 Final batch {batch_count} saved with {len(batch_jobs)} jobs")

    print(f"✅ Scraping finished. All jobs saved into '{OUTPUT_DIR}/'")
