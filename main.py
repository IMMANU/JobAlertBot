import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Testing ke liye 24 hours.
# Jab everything works, ise r3600 kar dena.
TIME_FILTER = "r86400"

MIN_SCORE = 40

# Tumhare ~5 years experience ke hisaab se
MIN_YEARS = 3


# ============================================================
# SEARCH TERMS
# ============================================================

# Bahut saare LinkedIn requests ek saath mat maaro.
# Ye 6 searches enough hain.

SEARCH_TERMS = [
    "AWS Cloud Engineer",
    "Cloud Engineer",
    "Cloud Infrastructure Engineer",
    "AWS Infrastructure Engineer",
    "Cloud Operations Engineer",
    "Infrastructure Engineer",
]


# ============================================================
# TARGET TITLE KEYWORDS
# ============================================================

TITLE_SCORES = {

    # Strongest matches
    "aws cloud engineer": 35,
    "cloud infrastructure engineer": 30,
    "aws infrastructure engineer": 30,

    "cloud engineer": 28,
    "aws engineer": 25,

    "cloud operations engineer": 25,
    "cloud operations": 20,

    "infrastructure engineer": 22,
    "aws infrastructure": 22,

    "cloud platform engineer": 22,
    "aws platform engineer": 22,
    "platform engineer": 15,

    "aws systems engineer": 20,
    "cloud systems engineer": 18,

    "cloud migration engineer": 20,
    "aws migration engineer": 20,

    "infrastructure automation engineer": 20,

    "cloud consultant": 12,
    "aws consultant": 12,

    # Lower priority
    "site reliability engineer": 8,
    "site reliability": 5,
    "sre": 5,
}


# ============================================================
# RESUME SKILLS
# ============================================================

SKILLS = {

    # AWS
    "aws": 10,
    "amazon web services": 10,

    # IaC
    "terraform": 15,
    "terraform modules": 15,
    "infrastructure as code": 12,
    "iac": 8,
    "cloudformation": 12,

    # AWS services
    "ec2": 7,
    "s3": 5,
    "rds": 5,
    "ecs": 7,
    "ecr": 6,
    "iam": 7,
    "cloudwatch": 10,
    "vpc": 7,
    "load balancer": 5,
    "elastic load balancer": 5,

    # Operations
    "cloud operations": 12,
    "cloud infrastructure": 12,
    "infrastructure automation": 12,
    "cloud automation": 10,
    "cloud migration": 10,
    "migration": 5,

    # Monitoring
    "monitoring": 7,
    "observability": 8,
    "alerting": 5,

    # Systems
    "aws systems manager": 10,
    "systems manager": 8,
    "ssm": 7,

    # Other AWS
    "aws service catalog": 8,
    "service catalog": 6,
    "kms": 5,
    "secrets manager": 5,

    # Networking
    "subnets": 4,
    "route tables": 4,
    "security groups": 5,
    "network acl": 4,
    "nacl": 4,
    "networking": 5,

    # Containers
    "docker": 5,

    # Automation / CI
    "bash": 5,
    "github actions": 5,
    "git": 3,
    "linux": 5,
}


# ============================================================
# HARD BLOCKED TITLE KEYWORDS
# ============================================================

# Agar title mein ye hain -> direct reject

BLOCKED_TITLE_KEYWORDS = [

    # DevOps
    "devops",
    "dev sec ops",
    "devsecops",

    # Other clouds
    "azure engineer",
    "azure cloud engineer",
    "microsoft azure",
    "gcp engineer",
    "google cloud engineer",

    # Developers
    "software developer",
    "software engineer",
    "software development engineer",
    "java developer",
    "python developer",
    "backend developer",
    "frontend developer",
    "full stack developer",
    "fullstack developer",
    "react developer",
    "android developer",
    "ios developer",

    # Data
    "data engineer",
    "data scientist",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",

    # QA
    "qa engineer",
    "test engineer",
    "testing engineer",
    "automation tester",

    # Security
    "cybersecurity",
    "cyber security",
    "security engineer",

    # Networking
    "network engineer",
    "network administrator",

    # Salesforce
    "salesforce",

    # SAP
    "sap consultant",
    "sap engineer",
]


# ============================================================
# SOFT NEGATIVE WORDS
# ============================================================

# Description mein hone se direct reject nahi hoga.
# Sirf score reduce hoga.

SOFT_NEGATIVE = [
    "jenkins",
    "kubernetes",
    "helm",
    "argocd",
    "ansible",
    "gitlab ci",
    "azure",
    "gcp",
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

    "Accept-Language": "en-US,en;q=0.9",

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
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

    if not text:
        return False

    # Multi-word phrase
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
# TITLE BLOCK CHECK
# ============================================================

def blocked_title(title):

    t = normalize(title)

    for keyword in BLOCKED_TITLE_KEYWORDS:

        if contains(t, keyword):

            return True, keyword

    return False, None


# ============================================================
# TITLE SCORE
# ============================================================

def get_title_score(title):

    t = normalize(title)

    score = 0
    matches = []

    for keyword, points in TITLE_SCORES.items():

        if contains(t, keyword):

            score += points
            matches.append(keyword)

    return score, matches


# ============================================================
# DESCRIPTION / SKILL SCORE
# ============================================================

def get_skill_score(description):

    d = normalize(description)

    score = 0
    matches = []

    for skill, points in SKILLS.items():

        if contains(d, skill):

            score += points
            matches.append(skill)

    return score, matches


# ============================================================
# EXPERIENCE CHECK
# ============================================================

def get_experience(description):

    d = normalize(description)

    # 3-5 years
    match = re.search(
        r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)",
        d
    )

    if match:

        return int(match.group(1)), int(match.group(2))

    # 5+ years
    match = re.search(
        r"(\d+)\s*\+\s*(?:years?|yrs?)",
        d
    )

    if match:

        return int(match.group(1)), None

    # 5 years of experience
    match = re.search(
        r"(\d+)\s*(?:years?|yrs?)\s*(?:of)?\s*experience",
        d
    )

    if match:

        years = int(match.group(1))

        return years, years

    return None, None


def experience_ok(description):

    low, high = get_experience(description)

    # Agar experience detect nahi hua,
    # job ko reject mat karo.
    if low is None:
        return True

    # Example 0-2 years
    if high is not None and high < MIN_YEARS:

        return False

    # Example 1+ years
    if high is None and low < MIN_YEARS:

        return False

    return True


# ============================================================
# JOB EVALUATION
# ============================================================

def evaluate_job(title, description):

    title = normalize(title)
    description = normalize(description)

    # --------------------------------------------------------
    # 1. HARD TITLE BLOCK
    # --------------------------------------------------------

    is_blocked, reason = blocked_title(title)

    if is_blocked:

        return {
            "relevant": False,
            "score": 0,
            "skills": [],
            "reason": f"Blocked title: {reason}",
        }


    # --------------------------------------------------------
    # 2. TITLE MUST BE CLOUD/INFRASTRUCTURE RELATED
    # --------------------------------------------------------

    title_score, title_matches = get_title_score(title)

    if title_score == 0:

        return {
            "relevant": False,
            "score": 0,
            "skills": [],
            "reason": "Title not relevant",
        }


    # --------------------------------------------------------
    # 3. EXPERIENCE
    # --------------------------------------------------------

    if not experience_ok(description):

        return {
            "relevant": False,
            "score": 0,
            "skills": [],
            "reason": "Too junior",
        }


    # --------------------------------------------------------
    # 4. SKILL SCORE
    # --------------------------------------------------------

    skill_score, skill_matches = get_skill_score(
        description
    )


    # --------------------------------------------------------
    # 5. AWS CHECK
    #
    # IMPORTANT:
    # AWS title mein mandatory nahi hai.
    # Description mein AWS hona enough hai.
    # --------------------------------------------------------

    has_aws = (
        contains(title, "aws")
        or contains(description, "aws")
        or contains(description, "amazon web services")
    )


    if not has_aws:

        return {
            "relevant": False,
            "score": 0,
            "skills": skill_matches,
            "reason": "No AWS signal",
        }


    # --------------------------------------------------------
    # 6. AWS BONUS
    # --------------------------------------------------------

    score = title_score + skill_score

    if has_aws:

        score += 10


    # --------------------------------------------------------
    # 7. CLOUD INFRASTRUCTURE BONUS
    # --------------------------------------------------------

    if contains(description, "cloud infrastructure"):

        score += 8


    if contains(description, "infrastructure as code"):

        score += 8


    if contains(description, "terraform"):

        score += 8


    # --------------------------------------------------------
    # 8. DEVOPS PENALTY
    #
    # DevOps title already rejected.
    # But if description contains DevOps, reduce score heavily.
    # --------------------------------------------------------

    if contains(description, "devops"):

        score -= 25


    # --------------------------------------------------------
    # 9. SOFT NEGATIVE
    # --------------------------------------------------------

    negative_count = 0

    for word in SOFT_NEGATIVE:

        if contains(description, word):

            negative_count += 1


    score -= negative_count * 2


    # --------------------------------------------------------
    # 10. SCORE LIMIT
    # --------------------------------------------------------

    score = max(
        0,
        min(score, 100)
    )


    # --------------------------------------------------------
    # 11. FINAL DECISION
    # --------------------------------------------------------

    if score < MIN_SCORE:

        return {
            "relevant": False,
            "score": score,
            "skills": skill_matches,
            "reason": "Score too low",
        }


    return {
        "relevant": True,
        "score": score,
        "skills": skill_matches,
        "reason": "Good match",
    }


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    try:

        response = requests.post(

            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/sendMessage",

            data={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },

            timeout=15,
        )

        response.raise_for_status()

        return True

    except Exception as e:

        print(
            f"Telegram error: {e}"
        )

        return False


# ============================================================
# BUILD LINKEDIN URL
# ============================================================

def build_url(search_term):

    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote(search_term)}"
        "&location=India"
        f"&f_TPR={TIME_FILTER}"
        "&sortBy=DD"
    )


# ============================================================
# FETCH WITH RETRY
# ============================================================

def fetch_search(search_term):

    url = build_url(search_term)

    print()
    print(
        f"Searching: {search_term}"
    )

    # Small random delay
    time.sleep(
        random.uniform(3, 6)
    )

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
            )

            # ------------------------------------------------
            # Rate limit
            # ------------------------------------------------

            if response.status_code == 429:

                wait = 15 * (attempt + 1)

                print(
                    f"429 rate limit. "
                    f"Waiting {wait}s..."
                )

                time.sleep(wait)

                continue


            response.raise_for_status()

            print(
                f"Status: {response.status_code}"
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


        except Exception as e:

            print(
                f"Fetch failed: {e}"
            )

            time.sleep(5)


    return []


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


        if not link_element:

            return None


        link = link_element.get(
            "href"
        )


        if not link:

            return None


        link = link.split("?")[0]


        # ----------------------------------------------------
        # Search card snippet
        # ----------------------------------------------------

        snippet_element = card.find(
            "p",
            class_="base-search-card__snippet"
        )


        if snippet_element:

            description = snippet_element.get_text(
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


        if location_element:

            location = location_element.get_text(
                " ",
                strip=True
            )

        else:

            location = "India"


        return {

            "title": title,

            "company": company,

            "location": location,

            "description": description,

            "link": link,
        }


    except Exception as e:

        print(
            f"Extraction error: {e}"
        )

        return None


# ============================================================
# SCORE LABEL
# ============================================================

def score_label(score):

    if score >= 85:

        return "🔥 Excellent Match"

    elif score >= 70:

        return "🟢 Strong Match"

    elif score >= 55:

        return "✅ Good Match"

    else:

        return "🟡 Possible Match"


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(
    job,
    result
):

    score = result["score"]

    skills = result["skills"][:12]

    if skills:

        skills_text = ", ".join(
            skill.upper()
            for skill in skills
        )

    else:

        skills_text = "AWS / Cloud"


    return (

        "🚀 <b>AWS CLOUD JOB ALERT</b>\n\n"

        f"💼 <b>"
        f"{escape_html(job['title'])}"
        f"</b>\n"

        f"🏢 "
        f"{escape_html(job['company'])}\n"

        f"📍 "
        f"{escape_html(job['location'])}\n\n"

        f"🎯 <b>Match: "
        f"{score}/100</b>\n"

        f"{score_label(score)}\n\n"

        f"🛠 <b>Matched Skills</b>\n"
        f"{escape_html(skills_text)}\n\n"

        f"🔗 "
        f"<a href='{job['link']}'>"
        f"Apply Now"
        f"</a>"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "AWS CLOUD JOB ALERT"
    )

    print(
        "Target: AWS Cloud Infrastructure / Cloud Operations"
    )

    print(
        "DevOps: BLOCKED"
    )

    print(
        f"Time filter: {TIME_FILTER}"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # Telegram test
    # --------------------------------------------------------

    print(
        "\nTesting Telegram..."
    )

    if send_telegram(
        "✅ <b>AWS Job Alert Bot</b>\n"
        "Telegram connection is working."
    ):

        print(
            "Telegram: OK"
        )

    else:

        print(
            "Telegram: FAILED"
        )

        return


    # --------------------------------------------------------
    # Track duplicates
    # --------------------------------------------------------

    seen_links = set()

    sent = 0

    rejected = 0


    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    for search_term in SEARCH_TERMS:

        cards = fetch_search(
            search_term
        )


        for card in cards:

            job = extract_job(card)


            if not job:

                continue


            link = job["link"]


            # ------------------------------------------------
            # Duplicate
            # ------------------------------------------------

            if link in seen_links:

                continue


            seen_links.add(link)


            # ------------------------------------------------
            # Evaluate
            # ------------------------------------------------

            result = evaluate_job(

                job["title"],

                job["description"]
            )


            if not result["relevant"]:

                print(
                    f"  ❌ SKIP: "
                    f"{job['title']} "
                    f"| {result['reason']}"
                )

                rejected += 1

                continue


            # ------------------------------------------------
            # Send
            # ------------------------------------------------

            message = build_message(
                job,
                result
            )


            if send_telegram(message):

                print(
                    f"  ✅ SENT: "
                    f"{job['title']} "
                    f"| Score "
                    f"{result['score']}/100"
                )

                sent += 1

            else:

                print(
                    f"  ❌ Telegram failed: "
                    f"{job['title']}"
                )


            # Small delay between Telegram messages

            time.sleep(
                random.uniform(1, 2)
            )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)

    print(
        f"Done | "
        f"Sent: {sent} | "
        f"Rejected: {rejected}"
    )

    print("=" * 60)


if __name__ == "__main__":

    main()
