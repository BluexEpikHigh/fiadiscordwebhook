import os, json, re, time, requests
from bs4 import BeautifulSoup

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
PAGE = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072"
STATE = "seen_docs.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

try:
    seen = set(json.load(open(STATE)))
    first_run = False
except Exception:
    seen, first_run = set(), True

r = requests.get(PAGE, headers=HEADERS, timeout=30)
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

docs = {}
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/system/files/decision-document/" not in href or not href.endswith(".pdf"):
        continue
    if "grand_prix" not in href.lower():
        continue
    url = href if href.startswith("http") else "https://www.fia.com" + href
    text = " ".join(a.get_text(" ").split())
    m = re.match(r"(.*?)\s*Published on\s*(.*)", text)
    title, published = (m.group(1), m.group(2)) if m else (text, "")
    docs[url] = (title or url.split("/")[-1], published)

print(f"Found {len(docs)} documents")

for url, (title, published) in reversed(list(docs.items())):
    if url in seen:
        continue
    seen.add(url)
    if first_run:
        continue
    requests.post(WEBHOOK, json={
        "username": "FIA Documents",
        "embeds": [{
            "title": title[:256],
            "url": url,
            "description": f"Published {published}" if published else "",
            "footer": {"text": "FIA F1 Documents"},
            "color": 0xE10600,
        }],
    })
    print("Posted:", title)
    time.sleep(1.5)

if docs:
    json.dump(list(seen), open(STATE, "w"))
else:
    print("No documents found, not saving state")
