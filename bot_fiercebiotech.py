import os, json, time, feedparser, html
from dotenv import load_dotenv
from urllib.parse import urlparse
from telegram import Bot, ParseMode

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID")
FEED_URL  = os.getenv("FEED_URL", "https://www.fiercebiotech.com/rss/biotech/xml")
STATE_FILE = "seen_entries.json"
CHECK_EVERY_SEC = 60  # 5 minute

bot = Bot(token=BOT_TOKEN)

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen_set):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_set), f, ensure_ascii=False, indent=2)

def format_msg(entry):
    title = entry.get("title", "Untitled")
    link  = entry.get("link", "")
    summ  = entry.get("summary", "")
    # Curăță și limitează sumarul (Telegram are limită 4096 char/mesaj)
    summ = html.unescape(summ)
    if len(summ) > 700:
        summ = summ[:700].rstrip() + "…"
    host = urlparse(link).netloc
    return f"🧬 *{title}*\n{summ}\n\n🔗 {link}  _(via {host})_"

def fetch_and_notify():
    d = feedparser.parse(FEED_URL)
    if d.bozo:
        # feed invalid sau eroare de rețea
        return
    seen = load_seen()
    new_entries = []
    for e in d.entries:
        # Folosește id / link / titlu ca fallback pentru dedup
        entry_id = e.get("id") or e.get("guid") or e.get("link") or e.get("title")
        if not entry_id:
            continue
        if entry_id not in seen:
            new_entries.append((entry_id, e))
    # Trimite cele mai noi primele (de obicei RSS e invers)
    for entry_id, e in reversed(new_entries):
        msg = format_msg(e)
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)
        seen.add(entry_id)
        time.sleep(1)  # mică pauză anti-ratelimit
    if new_entries:
        save_seen(seen)

if __name__ == "__main__":
    # Rulare continuă (polling la interval fix)
    while True:
        try:
            fetch_and_notify()
        except Exception as ex:
            # log simplu la consolă
            print("Error:", ex)
        time.sleep(CHECK_EVERY_SEC)
