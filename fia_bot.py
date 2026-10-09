import os, json, re, feedparser, requests

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
FEEDS = {
    "FIA News": "https://www.fia.com/rss/news",
    "FIA Press Release": "https://www.fia.com/rss/press-release",
}
STATE = "seen.json"

try:
    seen = set(json.load(open(STATE)))
    first_run = False
except Exception:
    seen, first_run = set(), True

def clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

total = 0
for label, url in FEEDS.items():
    feed = feedparser.parse(url)
    print(f"{label}: {len(feed.entries)} entries")
    total += len(feed.entries)
    for e in reversed(feed.entries):
        uid = e.get("id") or e.link
        if uid in seen:
            continue
        seen.add(uid)
        if first_run:
            continue
        requests.post(WEBHOOK, json={
            "username": "FIA",
            "embeds": [{
                "title": e.title[:256],
                "url": e.link,
                "description": clean(e.get("summary"))[:400],
                "footer": {"text": label},
                "color": 0x0B1F4B,
            }],
        })
        print("Posted:", e.title)

if total == 0:
    print("No entries fetched, not saving state")
else:
    json.dump(list(seen), open(STATE, "w"))
