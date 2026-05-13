import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://www.linkedin.com/jobs/search/?keywords=AWS%20OR%20AWS%20Cloud%20OR%20Cloud%20Engineer%20OR%20Platform%20Engineer%20OR%20CloudOps%20OR%20Site%20Reliability%20Engineer&location=India&f_TPR=r86400&sortBy=DD"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(URL, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

jobs = soup.find_all("div", class_="base-search-card")

for job in jobs[:5]:

    title = job.find("h3").text.strip()

    company = job.find("h4").text.strip()

    link = job.find("a")["href"]

    text = f"""
🚀 New LinkedIn Job

💼 {title}
🏢 {company}

🔗 {link}
"""

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        telegram_url,
        data={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

print("Done")
