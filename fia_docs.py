import os, json, re, time, requests
import fitz
from bs4 import BeautifulSoup

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
PAGE = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072"
STATE = "seen_docs.json"
PING = "<@&1558202136678895749>"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MAX_PDF = 8 * 1024 * 1024

try:
    seen = set(json.load(open(STATE)))
    first_run = False
except Exception:
    seen, first_run = set(), True


def make_preview(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(1.6, 1.6))
    return pix.tobytes("png")


def post_doc(url, title, published):
    embed = {
        "title": title[:256],
        "url": url,
        "description": f"Published {published}" if published else "",
        "footer": {"text": "FIA F1 Documents"},
        "color": 0xE10600,
    }
    files = {}
    try:
        pr = requests.get(url, headers=HEADERS, timeout=60)
        pr.raise_for_status()
        pdf = pr.content
        png = make_preview(pdf)
        embed["image"] = {"url": "attachment://preview.png"}
        files["files[0]"] = ("preview.png", png, "image/png")
        if len(pdf) <= MAX_PDF:
            files["files[1]"] = (url.split("/")[-1], pdf, "application/pdf")
    except Exception as ex:
        print("Preview failed, posting link only:", ex)
        embed.pop("image", None)
        files = {}
    payload = {"username": "FIA Documents", "embeds": [embed]}
    if files:
        r = requests.post(WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files)
    else:
        r = requests.post(WEBHOOK, json=payload)
    print("Discord status:", r.status_code)


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
    post_doc(url, title, published)
    print("Posted:", title)
    time.sleep(2)

if docs:
    json.dump(list(seen), open(STATE, "w"))
else:
    print("No documents found, not saving state")
