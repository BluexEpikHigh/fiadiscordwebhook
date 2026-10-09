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

   for label, url in FEEDS.items():
       feed = feedparser.parse(url)
       for e in reversed(feed.entries):
           uid = e.get("id") or e.link
           if uid in seen:
               continue
           seen.add(uid)
           if first_run:
               continue  # first run only records existing posts
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

   json.dump(list(seen), open(STATE, "w"))
