#!/usr/bin/env python3
"""Baymax independent, low-volume background knowledge collector.

No OpenAI, Puter, LLM API, or third-party pretrained model. The only
remote source is Wikipedia's public article API. Only PUBLIC encyclopedia
summaries are written to docs/knowledge.json; no browser secrets.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "docs" / "knowledge.json"
TOPICS = ROOT / "topics.json"
USER_AGENT = "BaymaxOriginalLearning/1.0 (independent educational robot research; GitHub Actions)"
MAX_KEEP = 60


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_article(title, lang="en"):
    if lang not in ("en", "si"):
        raise ValueError("Only en/si Wikipedia is supported")
    if not isinstance(title, str) or not 2 <= len(title) <= 120:
        raise ValueError("Invalid topic title")
    args = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "extracts|info", "exintro": "1", "explaintext": "1",
        "inprop": "url", "redirects": "1", "titles": title,
    })
    url = f"https://{lang}.wikipedia.org/w/api.php?{args}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(300_000)
    payload = json.loads(body)
    pages = payload.get("query", {}).get("pages", [])
    for page in pages:
        summary = re.sub(r"\s+", " ", page.get("extract") or "").strip()
        source = page.get("fullurl") or ""
        location = urllib.parse.urlparse(source)
        if (not page.get("missing") and len(summary) >= 85
                and location.scheme == "https"
                and location.hostname == f"{lang}.wikipedia.org"
                and location.path.startswith("/wiki/")):
            return {
                "id": f"{lang}:{page['title']}",
                "title": str(page["title"])[:120],
                "summary": summary[:650],
                "source": source,
                "lang": lang,
                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            }
    return None


def run():
    topics = read_json(TOPICS, [])
    if not isinstance(topics, list) or not 1 <= len(topics) <= 100:
        raise RuntimeError("topics.json should contain 1-100 public article titles")
    for item in topics:
        if not isinstance(item, dict) or item.get("lang", "en") not in ("en", "si") or not isinstance(item.get("title"), str):
            raise RuntimeError("Invalid topic entry")

    data = read_json(DATA, {"schema": 1, "cursor": 0, "updated_at": None, "items": []})
    if data.get("schema") != 1 or not isinstance(data.get("items"), list):
        raise RuntimeError("Unexpected knowledge.json schema")
    items = {str(x.get("id")): x for x in data["items"] if isinstance(x, dict) and x.get("id")}
    cursor = int(data.get("cursor", 0)) % len(topics)
    added = 0
    # Rotate through a controlled list of safe, public encyclopedia topics.
    # Do not spider arbitrary sites or scrape personal/private sources.
    for offset in range(min(2, len(topics))):
        cfg = topics[(cursor + offset) % len(topics)]
        title = cfg["title"]
        lang = cfg.get("lang", "en")
        try:
            item = fetch_article(title, lang)
            if item is None:
                print(f"No usable article: {title}")
                continue
            items[item["id"]] = item
            added += 1
            print(f"Read: {item['title']} ({lang})")
        except Exception as exc:
            print(f"Could not read {title}: {type(exc).__name__}: {exc}", file=sys.stderr)

    ordered = sorted(items.values(), key=lambda x: x.get("fetched_at") or "")[-MAX_KEEP:]
    data = {
        "schema": 1,
        "cursor": (cursor + min(2, len(topics))) % len(topics),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "items": ordered,
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Completed: refreshed {added} public summaries; saved {len(ordered)} records")


if __name__ == "__main__":
    run()
