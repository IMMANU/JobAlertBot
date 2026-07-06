import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID   = os.environ["CHAT_ID"]

# ─── Sirf yahi titles chahiye tujhe ───────────────────────────
ALLOWED_KEYWORDS = [
    "aws", "cloud engineer", "platform engineer",
    "cloudops", "site reliability", "sre"
]

# ─── Yeh titles filter OUT ho jayenge ─────────────────────────
BLOCKED_KEYWORDS = [
    "salesforce", "azure", "gcp", "google cloud",
    "java developer", "frontend", "react", "android"
]

# ─── Last 1 hour only (3600 seconds) ──────────────────────────
URL = (
    "https://www.linkedin.com/jobs/search/"
    "?keywords=AWS+Cloud+Engineer+OR+Platform+Engineer+OR+SRE+OR+CloudOps"
    "&location=India"
    "&f_TPR=r3600"   # <-- 1 hour (was r86400 = 24hr)
    "&sortBy=DD"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── Seen jobs track karne ke liye (in-memory, cron run ke andar) ──
seen_links = set()


def is_relevant(title: str) -> bool:
    """Title mein allowed keyword hai AND blocked keyword nahi."""
    t = title.lower()
    has_good = any(kw in t for kw in ALLOWED_KEYWORDS)
    has_bad  = any(kw in t for kw in BLOCKED_KEYWORDS)
    return has_good and not has_bad


def send_telegram(text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10
    )


def main():
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Fetch failed: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("div", class_="base-search-card")

    print(f"Total cards found: {len(cards)}")

    sent = 0
    for job in cards:
        try:
            title   = job.find("h3").text.strip()
            company = job.find("h4").text.strip()
            link    = job.find("a")["href"].split("?")[0]  # clean URL
        except Exception:
            continue

        # Skip if not relevant
        if not is_relevant(title):
            print(f"  SKIP: {title}")
            continue

        # Skip duplicates within this run
        if link in seen_links:
            continue
        seen_links.add(link)

        msg = (
            f"🚀 <b>New Job Alert</b>\n\n"
            f"💼 <b>{title}</b>\n"
            f"🏢 {company}\n\n"
            f"🔗 <a href='{link}'>Apply Now</a>"
        )
        send_telegram(msg)
        print(f"  SENT: {title} @ {company}")
        sent += 1

    print(f"Done — sent {sent} alerts.")


if __name__ == "__main__":
    main()
