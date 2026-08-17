import os
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# ------------------------------------------------------------
# LinkedIn search terms
# Multiple targeted searches are better than one broad query
# ------------------------------------------------------------

SEARCH_TERMS = [
    "AWS Cloud Engineer",
    "Cloud Infrastructure Engineer",
    "AWS Infrastructure Engineer",
    "Cloud Engineer",
    "AWS Cloud Operations",
    "Cloud Operations Engineer",
    "AWS Platform Engineer",
    "Cloud Platform Engineer",
    "Infrastructure Engineer",
    "Infrastructure Automation Engineer",
    "AWS Systems Engineer",
    "AWS Migration Engineer",
]

# ------------------------------------------------------------
# Strong title keywords
# ------------------------------------------------------------

TITLE_KEYWORDS = {
    "aws cloud engineer": 35,
    "aws engineer": 25,
    "cloud infrastructure engineer": 30,
    "aws infrastructure engineer": 30,
    "cloud engineer": 25,
    "cloud operations engineer": 25,
    "aws cloud operations": 25,
    "cloud operations": 20,
    "cloud platform engineer": 25,
    "aws platform engineer": 25,
    "platform engineer": 15,
    "infrastructure engineer": 20,
    "infrastructure automation engineer": 25,
    "aws systems engineer": 20,
    "cloud systems engineer": 20,
    "aws migration engineer": 20,
    "cloud migration engineer": 20,
    "cloud consultant": 10,
    "aws consultant": 10,
    "site reliability engineer": 8,
    "site reliability": 5,
    "sre": 5,
}

# ------------------------------------------------------------
# Resume-based technical skills
# ------------------------------------------------------------

SKILLS = {
    "aws": 10,
    "terraform": 15,
    "cloudformation": 12,
    "cloudwatch": 10,
    "ec2": 7,
    "vpc": 7,
    "iam": 7,
    "s3": 5,
    "rds": 5,
    "ecs": 7,
    "ecr": 5,
    "aws systems manager": 10,
    "ssm": 7,
    "aws service catalog": 8,
    "service catalog": 6,
    "kms": 5,
    "secrets manager": 5,
    "load balancer": 5,
    "elastic load balancer": 5,
    "infrastructure as code": 12,
    "infrastructure automation": 12,
    "cloud automation": 10,
    "cloud operations": 12,
    "cloud infrastructure": 12,
    "cloud migration": 10,
    "migration": 5,
    "monitoring": 7,
    "observability": 8,
    "bash": 5,
    "github actions": 5,
    "docker": 5,
    "linux": 5,
    "networking": 5,
    "security groups": 5,
    "nacl": 4,
    "subnets": 4,
}

# ------------------------------------------------------------
# HARD BLOCKS
#
# If these appear in the JOB TITLE, reject immediately.
# This is important because you don't want DevOps-heavy roles.
# ------------------------------------------------------------

BLOCKED_TITLE_KEYWORDS = [
    "devops",
    "dev sec ops",
    "devsecops",
    "devops engineer",

    "azure engineer",
    "azure cloud engineer",
    "microsoft azure",

    "gcp engineer",
    "google cloud engineer",

    "salesforce",

    "java developer",
    "python developer",
    "software developer",
    "software engineer",
    "backend developer",
    "frontend developer",
    "full stack developer",
    "fullstack developer",
    "mobile developer",
    "android developer",
    "ios developer",

    "data engineer",
    "data scientist",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",

    "qa engineer",
    "test engineer",
    "automation tester",
    "quality analyst",

    "network engineer",
    "network administrator",

    "cyber security",
    "cybersecurity",
    "security engineer",

    "sap consultant",
    "sap engineer",

    "database administrator",
    "dba",
]

# ------------------------------------------------------------
# Words that are undesirable anywhere in the job description.
#
# These don't automatically reject the job because sometimes
# a good cloud job mentions these technologies incidentally.
# ------------------------------------------------------------

NEGATIVE_DESCRIPTION_KEYWORDS = [
    "azure only",
    "gcp only",
    "google cloud only",
    "salesforce developer",
    "java developer",
    "frontend developer",
    "backend developer",
    "data engineer",
    "data scientist",
]

# ------------------------------------------------------------
# Experience filters
# User has ~5 years experience.
# ------------------------------------------------------------

MIN_YEARS = 3
MAX_YEARS = 8

# Minimum score required to send the job
MIN_SCORE = 45

# ------------------------------------------------------------
# Last 1 hour
# ------------------------------------------------------------

TIME_FILTER = "r3600"


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ============================================================
# HELPERS
# ============================================================

def normalize(text):
    """Normalize text for matching."""
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_keyword(text, keyword):
    """
    Safer keyword matching.
    Example:
    'sre' won't accidentally match unrelated words.
    """
    text = normalize(text)
    keyword = normalize(keyword)

    if " " in keyword:
        return keyword in text

    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def clean_html(text):
    """Remove HTML and normalize text."""
    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")
    return normalize(soup.get_text(" ", strip=True))


# ============================================================
# TITLE FILTER
# ============================================================

def is_blocked_title(title):
    """
    Hard reject if the job title itself contains something
    that doesn't fit the user's target.
    """

    t = normalize(title)

    for keyword in BLOCKED_TITLE_KEYWORDS:
        if contains_keyword(t, keyword):
            return True

    return False


# ============================================================
# SCORE TITLE
# ============================================================

def score_title(title):
    """
    Calculate title relevance score.
    """

    t = normalize(title)

    score = 0
    matched = []

    for keyword, points in TITLE_KEYWORDS.items():

        if contains_keyword(t, keyword):
            score += points
            matched.append(keyword)

    return score, matched


# ============================================================
# SCORE JOB DESCRIPTION
# ============================================================

def score_description(description):
    """
    Score job based on skills from the user's resume.
    """

    d = normalize(description)

    score = 0
    matched_skills = []

    for skill, points in SKILLS.items():

        if contains_keyword(d, skill):
            score += points
            matched_skills.append(skill)

    return score, matched_skills


# ============================================================
# NEGATIVE DESCRIPTION CHECK
# ============================================================

def has_bad_description_signal(description):
    d = normalize(description)

    for keyword in NEGATIVE_DESCRIPTION_KEYWORDS:
        if keyword in d:
            return True

    return False


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience(description):
    """
    Try to detect experience requirements.

    Examples:
    3+ years
    4-6 years
    5 years of experience
    minimum 3 years
    """

    d = normalize(description)

    ranges = re.findall(
        r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)",
        d
    )

    for low, high in ranges:
        return int(low), int(high)

    plus_matches = re.findall(
        r"(\d+)\s*\+\s*(?:years?|yrs?)",
        d
    )

    if plus_matches:
        years = int(plus_matches[0])
        return years, None

    single_matches = re.findall(
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
        d
    )

    if single_matches:
        years = int(single_matches[0])
        return years, years

    return None, None


def experience_is_relevant(description):
    """
    Reject obvious junior/fresher roles.

    If no experience requirement is found, don't reject.
    """

    low, high = extract_experience(description)

    if low is None:
        return True

    # Example: 0-2 years
    if high is not None and high < MIN_YEARS:
        return False

    # Example: 1+ years
    if high is None and low < MIN_YEARS:
        return False

    return True


# ============================================================
# FINAL JOB EVALUATION
# ============================================================

def evaluate_job(title, description):
    """
    Returns:

    relevant
    score
    matched skills
    reason
    """

    title = normalize(title)
    description = normalize(description)

    # --------------------------------------------------------
    # 1. Hard reject title
    # --------------------------------------------------------

    if is_blocked_title(title):
        return (
            False,
            0,
            [],
            "Blocked title"
        )

    # --------------------------------------------------------
    # 2. Experience check
    # --------------------------------------------------------

    if not experience_is_relevant(description):
        return (
            False,
            0,
            [],
            "Too junior"
        )

    # --------------------------------------------------------
    # 3. Title score
    # --------------------------------------------------------

    title_score, title_matches = score_title(title)

    # If title has no target role at all, reject.
    if title_score == 0:
        return (
            False,
            0,
            [],
            "Title not relevant"
        )

    # --------------------------------------------------------
    # 4. Description score
    # --------------------------------------------------------

    description_score, skill_matches = score_description(description)

    # --------------------------------------------------------
    # 5. Strong negative description
    # --------------------------------------------------------

    if has_bad_description_signal(description):

        # Don't immediately reject every mention.
        # But if there are very few AWS/cloud signals,
        # reject it.

        if description_score < 25:
            return (
                False,
                0,
                skill_matches,
                "Bad description signal"
            )

    # --------------------------------------------------------
    # 6. AWS requirement
    #
    # Since this is specifically for the user's AWS profile,
    # we strongly prefer AWS.
    # --------------------------------------------------------

    has_aws = contains_keyword(title, "aws") or contains_keyword(
        description,
        "aws"
    )

    if not has_aws:
        return (
            False,
            0,
            skill_matches,
            "No AWS signal"
        )

    # --------------------------------------------------------
    # 7. Final score
    # --------------------------------------------------------

    total_score = title_score + description_score

    # Cap score at 100
    total_score = min(total_score, 100)

    # --------------------------------------------------------
    # 8. Final threshold
    # --------------------------------------------------------

    if total_score < MIN_SCORE:
        return (
            False,
            total_score,
            skill_matches,
            "Score below threshold"
        )

    return (
        True,
        total_score,
        skill_matches,
        "Good match"
    )


# ============================================================
# TELEGRAM
# ============================================================

def escape_html(text):
    """
    Telegram HTML-safe text.
    """

    if not text:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_telegram(text):
    try:

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )

        response.raise_for_status()

        return True

    except Exception as e:

        print(f"Telegram failed: {e}")

        return False


# ============================================================
# LINKEDIN SEARCH
# ============================================================

def build_search_url(search_term):

    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={requests.utils.quote(search_term)}"
        "&location=India"
        f"&f_TPR={TIME_FILTER}"
        "&sortBy=DD"
    )


def fetch_jobs(search_term):

    url = build_search_url(search_term)

    print(f"\nSearching: {search_term}")

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
        )

        response.raise_for_status()

    except Exception as e:

        print(f"Fetch failed for {search_term}: {e}")

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    cards = soup.find_all(
        "div",
        class_="base-search-card"
    )

    print(
        f"Found {len(cards)} cards for '{search_term}'"
    )

    return cards


# ============================================================
# EXTRACT JOB
# ============================================================

def extract_job(card):

    try:

        title_element = card.find("h3")
        company_element = card.find("h4")
        link_element = card.find("a")

        if not title_element:
            return None

        title = title_element.get_text(
            " ",
            strip=True
        )

        company = (
            company_element.get_text(
                " ",
                strip=True
            )
            if company_element
            else "Unknown"
        )

        link = (
            link_element.get("href")
            if link_element
            else None
        )

        if not link:
            return None

        link = link.split("?")[0]

        # ----------------------------------------------------
        # Try to get job description from card
        # ----------------------------------------------------

        description_element = card.find(
            "p",
            class_="base-search-card__snippet"
        )

        if description_element:

            description = description_element.get_text(
                " ",
                strip=True
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

        location = (
            location_element.get_text(
                " ",
                strip=True
            )
            if location_element
            else "India"
        )

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "link": link,
        }

    except Exception as e:

        print(f"Extraction failed: {e}")

        return None


# ============================================================
# SCORE LABEL
# ============================================================

def score_label(score):

    if score >= 85:
        return "🔥 Excellent Match"

    if score >= 70:
        return "🟢 Strong Match"

    if score >= 60:
        return "✅ Good Match"

    return "🟡 Possible Match"


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(job, score, matched_skills):

    title = escape_html(job["title"])
    company = escape_html(job["company"])
    location = escape_html(job["location"])
    link = job["link"]

    label = score_label(score)

    # Show only the most useful skills
    display_skills = matched_skills[:12]

    skills_text = ", ".join(
        skill.upper()
        for skill in display_skills
    )

    if not skills_text:
        skills_text = "AWS / Cloud"

    message = (
        f"🚀 <b>AWS Cloud Job Alert</b>\n\n"

        f"💼 <b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}\n\n"

        f"🎯 <b>Match Score: {score}/100</b>\n"
        f"{label}\n\n"

        f"🛠 <b>Matched Skills:</b>\n"
        f"{escape_html(skills_text)}\n\n"

        f"🔗 <a href='{link}'>Apply Now</a>"
    )

    return message


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("AWS CLOUD JOB ALERT")
    print("Target: Cloud Infrastructure / Cloud Operations")
    print("DevOps: BLOCKED")
    print("=" * 60)

    seen_links = set()

    sent = 0
    rejected = 0

    # --------------------------------------------------------
    # Run all targeted searches
    # --------------------------------------------------------

    for search_term in SEARCH_TERMS:

        cards = fetch_jobs(search_term)

        for card in cards:

            job = extract_job(card)

            if not job:
                continue

            link = job["link"]

            # ------------------------------------------------
            # Duplicate check
            # ------------------------------------------------

            if link in seen_links:
                continue

            seen_links.add(link)

            # ------------------------------------------------
            # Evaluate
            # ------------------------------------------------

            relevant, score, matched_skills, reason = evaluate_job(
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
            # Telegram
            # ------------------------------------------------

            message = build_message(
                job,
                score,
                matched_skills
            )

            if send_telegram(message):

                print(
                    f"  ✅ SENT: "
                    f"{job['title']} "
                    f"| {score}/100 "
                    f"| {job['company']}"
                )

                sent += 1

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print(
        f"Done | Sent: {sent} | Rejected: {rejected}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
