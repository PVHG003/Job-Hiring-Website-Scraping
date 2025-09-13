import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
from urllib.parse import urlparse

INPUT_FILE = "topcv_job_urls.txt"
OUTPUT_DIR = "batches"  # Folder to save batch files

# Timeout range for requests
TIMEOUT_MIN = 5
TIMEOUT_MAX = 10

# Delay range between requests
DELAY_MIN = 0
DELAY_MAX = 3

SAVE_BATCH = 10  # Save every 10 jobs

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
}

def extract_job_data(soup):
    job_data = {}

    # --- Basic Left Side Info ---
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

    # --- Right Side Info ---
    company = {}
    company_block = soup.select_one(".job-detail__company--information-item.company-name")
    if company_block:
        name_tag = company_block.select_one("a.name")
        if name_tag:
            company["name"] = name_tag.get_text(strip=True)
            company["url"] = name_tag["href"]

        logo_tag = company_block.select_one("a.company-logo img")
        if logo_tag and logo_tag.get("src"):
            company["logo"] = logo_tag["src"]

    job_data["company"] = company

    general_info = {}
    for group in soup.select(".job-detail__box--right .box-general-group"):
        title_tag = group.select_one(".box-general-group-info-title")
        value_tag = group.select_one(".box-general-group-info-value")
        if title_tag and value_tag:
            general_info[title_tag.get_text(strip=True)] = value_tag.get_text(strip=True)
    job_data["general_info"] = general_info

    categories = {}
    for category in soup.select(".job-detail__box--right.job-detail__body-right--box-category .box-category"):
        title_tag = category.select_one(".box-title")
        tags = category.select(".box-category-tags .box-category-tag")
        if title_tag and tags:
            categories[title_tag.get_text(strip=True)] = [tag.get_text(strip=True) for tag in tags]
    job_data["categories"] = categories

    return job_data


def scrape_job_urls(input_file):
    """Read job URLs, filter out 'brand' ones."""
    job_urls = []
    with open(input_file, "r", encoding="utf-8") as file:
        for url in file:
            url = url.strip()
            if not url:
                continue
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if path_parts and path_parts[0] == "brand":
                print(f"⏭️ Skipping brand URL: {url}")
                continue
            job_urls.append(url)
    return job_urls


def scrape_jobs(job_urls, output_dir, save_batch):
    os.makedirs(output_dir, exist_ok=True)
    batch_jobs, batch_count = [], 1

    for idx, job_url in enumerate(job_urls, start=1):
        try:
            parsed = urlparse(job_url)
            path_parts = parsed.path.strip("/").split("/")
            job_slug = "/".join(path_parts[-2:])

            print(f"[{idx}/{len(job_urls)}] Fetching: {job_slug}")

            timeout_value = random.uniform(TIMEOUT_MIN, TIMEOUT_MAX)
            response = requests.get(job_url, headers=headers, timeout=timeout_value)
            soup = BeautifulSoup(response.text, "html.parser")

            job_data = extract_job_data(soup)
            job_data["url"] = job_url
            batch_jobs.append(job_data)

            if len(batch_jobs) >= save_batch:
                batch_filename = os.path.join(output_dir, f"batch_{batch_count}.json")
                with open(batch_filename, "w", encoding="utf-8") as f:
                    json.dump(batch_jobs, f, ensure_ascii=False, indent=4)
                print(f"💾 Saved batch {batch_count} with {len(batch_jobs)} jobs")
                batch_jobs, batch_count = [], batch_count + 1

            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"⏳ Sleeping {delay:.2f}s before next request...")
            time.sleep(delay)

        except Exception as e:
            print(f"⚠️ Failed to scrape {job_url}: {e}")

    if batch_jobs:
        batch_filename = os.path.join(output_dir, f"batch_{batch_count}.json")
        with open(batch_filename, "w", encoding="utf-8") as f:
            json.dump(batch_jobs, f, ensure_ascii=False, indent=4)
        print(f"💾 Final batch {batch_count} saved with {len(batch_jobs)} jobs")

    print(f"✅ Scraping finished. All jobs saved into '{output_dir}/'")


def main():
    job_urls = scrape_job_urls(INPUT_FILE)
    scrape_jobs(job_urls, OUTPUT_DIR, SAVE_BATCH)


if __name__ == "__main__":
    main()