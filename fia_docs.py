import os, json, re, time, requests
import fitz
from bs4 import BeautifulSoup

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
PAGE = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/season/season-2026-2072"
STATE = "seen_docs.json"
PING = "<@&1558202136678895749>"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MAX_PDF = 6 * 1024 * 1024
MAX_PAGES = 4

try:
    seen = set(json.load(open(STATE)))
    first_run = False
except Exception:
    seen, first_run = set(), True


def make_previews(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = len(doc)
    pngs = []
    for i in range(min(total, MAX_PAGES)):
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        pngs.append(pix.tobytes("png"))
    return pngs, total


def post_doc(url, title, published):
    desc = f"Published {published}" if published else ""
    embeds = [{
        "title": title[:256],
        "url": url,
        "description": desc,
        "footer": {"text": "FIA F1 Documents"},
        "color": 0xE10600,
    }]
    files = {}
    try:
        pr = requests.get(url, headers=HEADERS, timeout=60)
        pr.raise_for_status()
        pdf = pr.content
        pngs, total = make_previews(pdf)
        if total > len(pngs):
            embeds[0]["description"] = (desc + f"\nShowing first {len(pngs)} of {total} pages. Full PDF attached.").strip()
        for i, png in enumerate(pngs):
            name = f"page{i + 1}.png"
            files[f"files[{i}]"] = (name, png, "image/png")
            if i == 0:
                embeds[0]["image"] = {"url": f"attachment://{name}"}
            else:
                embeds.append({"url": url, "image": {"url": f"attachment://{name}"}})
        if len(pdf) <= MAX_PDF:
            files[f"files[{len(pngs)}]"] = (url.split("/")[-1], pdf, "application/pdf")
    except Exception as ex:
        print("Preview failed, posting link only:", ex)
        embeds = embeds[:1]
        embeds[0].pop("image", None)
        files = {}
    payload = {
        "content": PING,
        "allowed_mentions": {"parse": ["roles"]},
        "username": "FIA Documents",
        "embeds": embeds,
    }
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
    title, published = (m.group(1),
