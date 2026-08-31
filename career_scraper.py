import os
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# ─── Teri skills se match karne wale keywords ──────────────────
RELEVANT_KEYWORDS = [
    "aws", "cloud engineer", "cloud infrastructure", "terraform",
    "cloudops", "site reliability", "sre", "platform engineer",
    "devops", "cloud operations", "ecs", "docker", "cloudwatch",
    "vpc", "iac", "infrastructure"
]

BLOCKED_KEYWORDS = [
    "azure", "gcp", "salesforce", "java developer", "frontend",
    "react", "android", "data engineer", "machine learning",
    "sap", ".net", "oracle", "intern", "trainee", "fresher"
]

# ─── Company career pages ──────────────────────────────────────
COMPANIES = [
    # IT Services
    {
        "name": "Infosys",
        "url": "https://career.infosys.com/joblist",
        "job_selector": ".job-title",
        "link_base": "https://career.infosys.com"
    },
    {
        "name": "Wipro",
        "url": "https://careers.wipro.com/careers-home/jobs?keywords=aws+cloud",
        "job_selector": ".job-title",
        "link_base": "https://careers.wipro.com"
    },
    {
        "name": "HCL",
        "url": "https://www.hcltech.com/careers/job-search?keyword=aws+cloud",
        "job_selector": ".job-listing-title",
        "link_base": "https://www.hcltech.com"
    },
    {
        "name": "Tech Mahindra",
        "url": "https://careers.techmahindra.com/search/?q=aws+cloud&locationsearch=india",
        "job_selector": ".job-title",
        "link_base": "https://careers.techmahindra.com"
    },
    {
        "name": "Mphasis",
        "url": "https://careers.mphasis.com/search/?q=aws+cloud&locationsearch=india",
        "job_selector": ".job-title",
        "link_base": "https://careers.mphasis.com"
    },
    # MNC
    {
        "name": "IBM",
        "url": "https://www.ibm.com/careers/search?field_keyword_08[0]=Cloud&field_keyword_18[0]=India",
        "job_selector": ".bx--tile",
        "link_base": "https://www.ibm.com"
    },
    {
        "name": "Accenture",
        "url": "https://www.accenture.com/in-en/careers/jobsearch?jk=aws+cloud&ct=India",
        "job_selector": ".cmp-teaser__title",
        "link_base": "https://www.accenture.com"
    },
    {
        "name": "Capgemini",
        "url": "https://www.capgemini.com/in-en/careers/job-search/?search_term=aws+cloud",
        "job_selector": ".job-title",
        "link_base": "https://www.capgemini.com"
    },
    # Cloud Focused
    {
        "name": "Opstree",
        "url": "https://opstree.com/careers/",
        "job_selector": ".job-title, h3, .position",
        "link_base": "https://opstree.com"
    },
    {
        "name": "Powerupcloud",
        "url": "https://powerupcloud.com/careers/",
        "job_selector": ".job-title, h3",
        "link_base": "https://powerupcloud.com"
    },
    # BFSI
    {
        "name": "Razorpay",
        "url": "https://razorpay.com/jobs/?department=Engineering",
        "job_selector": ".job-title, .opening-title",
        "link_base": "https://razorpay.com"
    },
    {
        "name": "PhonePe",
        "url": "https://www.phonepe.com/careers/all-jobs/",
        "job_selector": ".job-title, h3",
        "link_base": "https://www.phonepe.com"
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── Seen jobs store (JSON file for persistence) ───────────────
SEEN_FILE = "seen_jobs.json"

def load_seen():
    if Path(SEEN_FILE).exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


# ─── Filtering ─────────────────────────────────────────────────
def is_relevant(title: str) -> bool:
    t = title.lower()
    has_good = any(kw in t for kw in RELEVANT_KEYWORDS)
    has_bad  = any(kw in t for kw in BLOCKED_KEYWORDS)
    return has_good and not has_bad


# ─── Telegram ──────────────────────────────────────────────────
def send_alert(title: str, company: str, link: str):
    msg = (
        f"🏢 <b>Career Page Alert</b>\n\n"
        f"💼 <b>{title}</b>\n"
        f"🏢 {company}\n\n"
        f"🔗 <a href='{link}'>Apply Now</a>"
    )
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )


# ─── Main scraper ──────────────────────────────────────────────
def scrape_company(company: dict, seen: set) -> list:
    new_jobs = []
    try:
        resp = requests.get(company["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ❌ {company['name']}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(company["job_selector"])

    for card in cards:
        title = card.get_text(strip=True)
        if not title or not is_relevant(title):
            continue

        # Get link
        link_tag = card.find("a") or card.find_parent("a")
        if link_tag and link_tag.get("href"):
            href = link_tag["href"]
            link = href if href.startswith("http") else company["link_base"] + href
        else:
            link = company["url"]

        job_id = f"{company['name']}_{title}"
        if job_id in seen:
            continue

        new_jobs.append({
            "title":   title,
            "company": company["name"],
            "link":    link,
            "id":      job_id
        })

    return new_jobs


def main():
    seen = load_seen()
    total_sent = 0

    for company in COMPANIES:
        print(f"🔍 Scraping {company['name']}...")
        new_jobs = scrape_company(company, seen)

        for job in new_jobs:
            send_alert(job["title"], job["company"], job["link"])
            seen.add(job["id"])
            total_sent += 1
            print(f"  ✅ Sent: {job['title']} @ {job['company']}")

    save_seen(seen)
    print(f"\nDone — {total_sent} new alerts sent.")


if __name__ == "__main__":
    main()
