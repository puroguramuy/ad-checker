import requests
from bs4 import BeautifulSoup

def scrape_text(url: str) -> str:
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    # ดึงเฉพาะข้อความ
    text = soup.get_text(separator=" ")
    return text.strip()
