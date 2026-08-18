import os
import re
import time
import random
import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import quote


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Testing:
# r86400 = last 24 hours
# r3600  = last 1 hour
TIME_FILTER = "r86400"

# Persistent duplicate tracking file
SEEN_JOBS_FILE = "seen_jobs.json"


# ============================================================
# SEARCH TERMS
# ============================================================

SEARCH_TERMS = [
    "AWS Cloud Engineer",
    "AWS Engineer",
    "AWS Infrastructure Engineer",
    "Cloud Engineer",
    "Cloud Infrastructure Engineer",
    "Cloud Operations Engineer",
    "Cloud Operation Engineer",
    "Cloud Consultant",
    "AWS Consultant",
    "AWS Solution Architect",
    "Cloud support engineer",
    "AWS cloud support engineer",
    "AWS support engineer",
    "AWS systems engineer",
    "cloud systems engineer",
    "Cloud Platform Engineer",
    "Infrastructure Engineer",
    "SRE AWS",
]


# ============================================================
# ALLOWED TITLE KEYWORDS
# ============================================================

ALLOWED_TITLE_KEYWORDS = [

    # AWS / Cloud
    "aws cloud engineer",
    "aws engineer",
    "cloud engineer",

    # Infrastructure
    "cloud infrastructure engineer",
    "aws infrastructure engineer",
    "infrastructure engineer",
    "infrastructure automation engineer",
    "infrastructure platform engineer",

    # Cloud Operations
    "cloud operations engineer",
    "cloud operation engineer",
    "cloud operations",
    "cloud operations specialist",
    "cloud operation specialist",

    # Platform
    "cloud platform engineer",
    "aws platform engineer",
    "platform engineer",

    # Systems
    "aws systems engineer",
    "cloud systems engineer",
    "systems engineer",

    # Migration
    "cloud migration engineer",
    "aws migration engineer",
    "cloud migration",

    # Support
    "cloud support engineer",
    "aws cloud support engineer",
    "aws support engineer",

    # Reliability
    "site reliability engineer",
    "site reliability",
    "sre",

    # Consulting
    "cloud consultant",
    "aws consultant",
]


# ============================================================
# BLOCKED TITLE KEYWORDS
# ============================================================

BLOCKED_TITLE_KEYWORDS = [

    # --------------------------------------------------------
    # DEVOPS
    # --------------------------------------------------------

    "devops",
    "dev sec ops",
    "devsecops",

    # --------------------------------------------------------
    # OTHER CLOUDS
    # --------------------------------------------------------

    "azure engineer",
    "azure cloud engineer",
    "azure infrastructure engineer",
    "azure platform engineer",
    "microsoft azure",
    "azure",

    "gcp engineer",
    "gcp cloud engineer",
    "gcp infrastructure engineer",
    "gcp platform engineer",
    "google cloud engineer",
    "google cloud",

    # VMware / private cloud
    "vmware",
    "private cloud",

    # --------------------------------------------------------
    # SOFTWARE DEVELOPMENT
    # --------------------------------------------------------

    "software engineer",
    "software developer",
    "software development engineer",
    "software development",

    "java developer",
    "java engineer",

    "python developer",
    "python engineer",

    "backend developer",
    "backend engineer",

    "frontend developer",
    "frontend engineer",

    "full stack developer",
    "fullstack developer",
    "full stack engineer",
    "fullstack engineer",

    "react developer",
    "react engineer",

    "angular developer",
    "angular engineer",

    "android developer",
    "android engineer",

    "ios developer",
    "ios engineer",

    # SDE
    "sde ",
    "sde-",

    # --------------------------------------------------------
    # DATA / AI
    # --------------------------------------------------------

    "data engineer",
    "data scientist",
    "data analyst",

    "machine learning engineer",
    "machine learning",

    "ml engineer",
    "ai engineer",
    "ai/ml",

    "analytics platform",

    # --------------------------------------------------------
    # QA / TESTING
    # --------------------------------------------------------

    "qa engineer",
    "qa automation engineer",
    "test engineer",
    "testing engineer",
    "software test engineer",
    "automation tester",

    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------

    "network engineer",
    "network administrator",
    "network architect",

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    "cybersecurity",
    "cyber security",
    "security engineer",
    "information security engineer",

    # --------------------------------------------------------
    # SALESFORCE
    # --------------------------------------------------------

    "salesforce",

    # --------------------------------------------------------
    # SAP
    # --------------------------------------------------------

    "sap consultant",
    "sap engineer",
    "sap developer",

    # --------------------------------------------------------
    # GENERIC SUPPORT
    # --------------------------------------------------------

    "desktop support",
    "help desk",
    "service desk",
    "technical support representative",
]


# ============================================================
# HTTP HEADERS
# ============================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 "
        "Safari/537.36"
    ),

    "Accept-Language": (
        "en-US,en;q=0.9"
    ),

    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,"
        "image/webp,"
        "*/*;q=0.8"
    ),
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize(text):

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains(text, keyword):

    text = normalize(text)
    keyword = normalize(keyword)

    if not text or not keyword:
        return False

    if " " in keyword:
        return keyword in text

    return re.search(
        r"\b" + re.escape(keyword) + r"\b",
        text
    ) is not None


def escape_html(text):

    if not text:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================================
# PERSISTENT DUPLICATE TRACKING
# ============================================================

def load_seen_jobs():

    if not os.path.exists(SEEN_JOBS_FILE):

        print(
            "ℹ️ No seen_jobs.json found. "
            "Starting fresh."
        )

        return set()

    try:

        with open(
            SEEN_JOBS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(data, list):

            print(
                "⚠️ Invalid seen_jobs.json. "
                "Starting fresh."
            )

            return set()

        seen_jobs = set(data)

        print(
            f"📦 Previously sent jobs: "
            f"{len(seen_jobs)}"
        )

        return seen_jobs

    except Exception as e:

        print(
            f"⚠️ Could not read "
            f"{SEEN_JOBS_FILE}: {e}"
        )

        return set()


def save_seen_jobs(seen_jobs):

    try:

        with open(
            SEEN_JOBS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                sorted(seen_jobs),
                file,
                indent=2,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            f"❌ Could not save "
            f"{SEEN_JOBS_FILE}: {e}"
        )

        return False


# ============================================================
# JOB FILTER
# ============================================================

def is_relevant(title, description):

    title = normalize(title)
    description = normalize(description)

    # --------------------------------------------------------
    # 1. HARD BLOCK
    # --------------------------------------------------------

    for keyword in BLOCKED_TITLE_KEYWORDS:

        if contains(title, keyword):

            return False, (
                f"Blocked title: {keyword}"
            )


    # --------------------------------------------------------
    # 2. TARGET ROLE
    # --------------------------------------------------------

    for keyword in ALLOWED_TITLE_KEYWORDS:

        if contains(title, keyword):

            return True, "Eligible"


    # --------------------------------------------------------
    # 3. NOT TARGET
    # --------------------------------------------------------

    return False, "Title not relevant"


# ============================================================
# BUILD LINKEDIN SEARCH URL
# ============================================================

def build_search_url(search_term):

    encoded_term = quote(
        search_term
    )

    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={encoded_term}"
        "&location=India"
        f"&f_TPR={TIME_FILTER}"
        "&sortBy=DD"
    )


# ============================================================
# FETCH LINKEDIN JOBS
# ============================================================

def fetch_jobs(search_term):

    url = build_search_url(
        search_term
    )

    print()
    print("=" * 60)
    print(
        f"Searching: {search_term}"
    )

    # --------------------------------------------------------
    # Delay to reduce 429
    # --------------------------------------------------------

    delay = random.uniform(
        5,
        9
    )

    print(
        f"Waiting {delay:.1f}s..."
    )

    time.sleep(delay)


    # --------------------------------------------------------
    # Retry
    # --------------------------------------------------------

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20
            )

            # ------------------------------------------------
            # Rate limit
            # ------------------------------------------------

            if response.status_code == 429:

                wait_time = (
                    30 * (attempt + 1)
                )

                print(
                    "⚠️ LinkedIn rate limited "
                    "(429)"
                )

                print(
                    f"Waiting {wait_time}s..."
                )

                time.sleep(
                    wait_time
                )

                continue


            response.raise_for_status()


            print(
                f"Status: "
                f"{response.status_code}"
            )

            print(
                f"Response size: "
                f"{len(response.text)}"
            )


            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )


            cards = soup.find_all(
                "div",
                class_="base-search-card"
            )


            print(
                f"Found {len(cards)} cards"
            )


            return cards


        except requests.RequestException as e:

            print(
                f"Fetch failed: {e}"
            )

            if attempt < 2:

                wait_time = (
                    15 * (attempt + 1)
                )

                print(
                    f"Retrying in "
                    f"{wait_time}s..."
                )

                time.sleep(
                    wait_time
                )


        except Exception as e:

            print(
                f"Unexpected error: {e}"
            )

            break


    return []


# ============================================================
# EXTRACT JOB
# ============================================================

def extract_job(card):

    try:

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title_element = card.find(
            "h3"
        )

        if not title_element:
            return None


        title = title_element.get_text(
            " ",
            strip=True
        )


        # ----------------------------------------------------
        # Company
        # ----------------------------------------------------

        company_element = card.find(
            "h4"
        )

        if company_element:

            company = company_element.get_text(
                " ",
                strip=True
            )

        else:

            company = "Unknown"


        # ----------------------------------------------------
        # Link
        # ----------------------------------------------------

        link_element = card.find(
            "a"
        )

        if not link_element:
            return None


        link = link_element.get(
            "href"
        )

        if not link:
            return None


        # Remove query parameters
        link = link.split("?")[0]


        # ----------------------------------------------------
        # Description snippet
        # ----------------------------------------------------

        description_element = card.find(
            "p",
            class_="base-search-card__snippet"
        )

        if description_element:

            description = (
                description_element.get_text(
                    " ",
                    strip=True
                )
            )

        else:

            description = ""


        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location_element = card.find(
            "span",
            class_="job-search-card__location"
        )

        if location_element:

            location = (
                location_element.get_text(
                    " ",
                    strip=True
                )
            )

        else:

            location = "India"


        return {

            "title": title,
            "company": company,
            "link": link,
            "description": description,
            "location": location,

        }


    except Exception as e:

        print(
            f"Extraction error: {e}"
        )

        return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    try:

        response = requests.post(

            url,

            data={

                "chat_id": CHAT_ID,

                "text": message,

                "parse_mode": "HTML",

                "disable_web_page_preview": False,

            },

            timeout=15
        )


        response.raise_for_status()

        return True


    except Exception as e:

        print(
            f"❌ Telegram error: {e}"
        )

        return False


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(job):

    title = escape_html(
        job["title"]
    )

    company = escape_html(
        job["company"]
    )

    location = escape_html(
        job["location"]
    )

    return (

        "🚀 <b>AWS CLOUD JOB ALERT</b>\n\n"

        f"💼 <b>{title}</b>\n"

        f"🏢 {company}\n"

        f"📍 {location}\n\n"

        "☁️ <b>Target:</b> "
        "AWS / Cloud Infrastructure\n\n"

        f"🔗 <a href='{job['link']}'>"
        "Apply Now"
        "</a>"

    )


# ============================================================
# TELEGRAM TEST
# ============================================================

def telegram_test():

    print()
    print(
        "Testing Telegram..."
    )

    message = (

        "✅ <b>AWS Job Alert Bot</b>\n\n"

        "Telegram connection is working."

    )

    if send_telegram(message):

        print(
            "✅ Telegram: OK"
        )

        return True


    print(
        "❌ Telegram: FAILED"
    )

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)

    print(
        "AWS CLOUD JOB ALERT"
    )

    print(
        "Target: AWS Cloud / Infrastructure / "
        "Cloud Operations / Platform / SRE"
    )

    print(
        "DevOps: BLOCKED"
    )

    print(
        "Scoring: DISABLED"
    )

    print(
        f"Searches: {len(SEARCH_TERMS)}"
    )

    print(
        f"Time filter: {TIME_FILTER}"
    )

    print(
        f"Duplicate file: {SEEN_JOBS_FILE}"
    )

    print("=" * 60)


    # ========================================================
    # TELEGRAM TEST
    # ========================================================

    if not telegram_test():

        print(
            "Stopping: Telegram unavailable."
        )

        return


    # ========================================================
    # LOAD PERSISTENT DUPLICATES
    # ========================================================

    seen_links = load_seen_jobs()

    sent = 0
    rejected = 0
    duplicates = 0


    # ========================================================
    # SEARCH ALL TERMS
    # ========================================================

    for search_term in SEARCH_TERMS:

        cards = fetch_jobs(
            search_term
        )


        for card in cards:

            job = extract_job(
                card
            )


            if not job:
                continue


            # ------------------------------------------------
            # Persistent duplicate check
            # ------------------------------------------------

            link = job["link"]

            if link in seen_links:

                duplicates += 1

                print(
                    f"  🔁 DUPLICATE: "
                    f"{job['title']}"
                )

                continue


            # ------------------------------------------------
            # Filter
            # ------------------------------------------------

            relevant, reason = is_relevant(

                job["title"],

                job["description"]

            )


            if not relevant:

                print(
                    f"  ❌ SKIP: "
                    f"{job['title']} "
                    f"| {reason}"
                )

                rejected += 1

                continue


            # ------------------------------------------------
            # SEND TO TELEGRAM
            # ------------------------------------------------

            message = build_message(
                job
            )


            if send_telegram(message):

                print(
                    f"  ✅ SENT: "
                    f"{job['title']} "
                    f"@ {job['company']}"
                )

                sent += 1


                # --------------------------------------------
                # IMPORTANT
                #
                # Save ONLY after Telegram succeeds.
                # --------------------------------------------

                seen_links.add(link)

                save_seen_jobs(
                    seen_links
                )


            else:

                print(
                    f"  ❌ Telegram failed: "
                    f"{job['title']}"
                )


            # ------------------------------------------------
            # Telegram delay
            # ------------------------------------------------

            time.sleep(
                random.uniform(
                    1,
                    2
                )
            )


    # ========================================================
    # FINAL SAVE
    # ========================================================

    save_seen_jobs(
        seen_links
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 60)

    print(
        f"Done | "
        f"Sent: {sent} | "
        f"Rejected: {rejected} | "
        f"Duplicates: {duplicates}"
    )

    print(
        f"Total saved jobs: "
        f"{len(seen_links)}"
    )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
